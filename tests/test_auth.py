import json
from pathlib import Path
import re
import sqlite3
from contextlib import closing

import pytest
from werkzeug.security import generate_password_hash, check_password_hash

from app import create_app
from app.database import init_db, insert_log, recent_logs
from tools.backup_logs import backup_logs
from tools.manage_credentials import store_password


@pytest.fixture
def auth(tmp_path):
    app = create_app({'TESTING': True, 'CSRF_ENABLED': True,
                      'FILES_ROOT': tmp_path / 'files', 'DATABASE': tmp_path / 'events.sqlite3',
                      'MODEL_PATH': tmp_path / 'missing.joblib', 'ADMIN_PASSWORD': 'admin-secret-test',
                      'AUDITOR_PASSWORD_HASH': generate_password_hash('auditor-secret-test')})
    return app, app.test_client()


def csrf(client, path='/login'):
    return re.search(rb'name="csrf_token" value="([^"]+)"', client.get(path).data).group(1).decode()


def test_csrf_and_admin_session(auth):
    app, c = auth
    assert c.post('/login', data={'password': 'admin-secret-test'}).status_code == 403
    token = csrf(c)
    assert c.post('/login', data={'password': 'admin-secret-test', 'csrf_token': token}).status_code == 302
    assert c.get('/dashboard').status_code == 200
    assert c.post('/logout').status_code == 403
    token = csrf(c, '/dashboard')
    assert c.post('/logout', data={'csrf_token': token}).status_code == 302
    assert c.get('/dashboard').status_code == 302
    assert c.post('/login', data={'csrf_token': token, 'password': 'admin-secret-test'}).status_code == 403


def test_auditor_cannot_export_or_promote_role(auth):
    app, c = auth
    token = csrf(c)
    c.post('/login', data={'role': 'auditor', 'password': 'auditor-secret-test', 'csrf_token': token})
    assert c.get('/dashboard').status_code == 403
    assert c.get('/dashboard/ai-evaluation').status_code == 403
    assert c.post('/dashboard/logs/export', data={'csrf_token': csrf(c, '/')}).status_code == 403
    assert c.post('/login', data={'role': 'admin', 'password': 'auditor-secret-test', 'csrf_token': csrf(c, '/')}).status_code == 200
    with c.session_transaction() as s:
        assert s['role'] == 'auditor'


def test_login_throttling_and_secret_not_logged(auth):
    app, c = auth
    token = csrf(c)
    for _ in range(5):
        assert c.post('/login', data={'csrf_token': token, 'password': 'not-logged-secret'}).status_code == 200
    r = c.post('/login', data={'csrf_token': token, 'password': 'admin-secret-test'})
    assert r.status_code == 429 and r.headers['Retry-After'] == '300'
    with closing(sqlite3.connect(app.config['DATABASE'])) as db:
        data = repr(db.execute('SELECT * FROM security_events').fetchall())
    assert 'not-logged-secret' not in data and 'admin-secret-test' not in data


def test_append_only_backup_and_export_formula_safety(auth, tmp_path):
    app, c = auth
    dbpath = app.config['DATABASE']
    insert_log(dbpath, '127.0.0.1', '=HYPERLINK("bad")', .7, 'suspicious', 'MISS', 404, 'missing', 1)
    with closing(sqlite3.connect(dbpath)) as db:
        for query in ['DELETE FROM access_logs', "UPDATE access_logs SET action='ALLOW'"]:
            with pytest.raises(sqlite3.IntegrityError, match='append-only'):
                db.execute(query)
    token = csrf(c)
    c.post('/login', data={'csrf_token': token, 'password': 'admin-secret-test'})
    with c.post('/dashboard/logs/export', data={'csrf_token': csrf(c, '/dashboard')}) as r:
        assert r.status_code == 200 and b"'=HYPERLINK" in r.data
    destination = backup_logs(dbpath, tmp_path / 'backup.sqlite3')
    assert len(recent_logs(destination)) == 1
    with pytest.raises(FileExistsError):
        backup_logs(dbpath, destination)


def test_password_hash_and_history(tmp_path):
    path = tmp_path / 'admin_password.hash'
    store_password('a-long-password-1', path)
    first = path.read_bytes()
    assert check_password_hash(first.decode().strip(), 'a-long-password-1')
    assert b'a-long-password-1' not in first
    store_password('a-long-password-2', path)
    assert next((tmp_path / 'credential_history').iterdir()).read_bytes() == first
    with pytest.raises(ValueError):
        store_password('short', path)


def test_private_storage_misconfiguration_is_rejected(tmp_path):
    with pytest.raises(ValueError, match='outside FILES_ROOT'):
        create_app({'TESTING': True, 'FILES_ROOT': tmp_path, 'DATABASE': tmp_path / 'events.sqlite3'})


def test_log_filter_validated_and_parameterized(auth):
    app, c = auth
    for action, status in [('ALLOW', 200), ('MISS', 404)]:
        insert_log(app.config['DATABASE'], '127.0.0.1', 'ok.txt', .1, 'benign', action, status, 'fixture', 1)
    assert len(recent_logs(app.config['DATABASE'], action='MISS')) == 1
    with pytest.raises(ValueError):
        recent_logs(app.config['DATABASE'], action="' OR 1=1 --")
    c.post('/login', data={'csrf_token': csrf(c), 'password': 'admin-secret-test'})
    assert c.get('/dashboard?action=MISS').status_code == 200
    assert c.get('/dashboard?action=invalid').status_code == 400
