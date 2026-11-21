import csv
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
import re
import sqlite3
from unittest.mock import Mock

import joblib
import pytest
from werkzeug.security import generate_password_hash

from app import create_app, database
from app import web
from tests.auth_support import complete_mfa
from app.log_filters import normalize_filters
from ml.evaluate import sha256

ROOT = Path(__file__).resolve().parents[1]


def application(tmp_path, csrf=False):
    base = tmp_path / 'public'
    base.mkdir()
    (base / 'ok.txt').write_bytes(b'PUBLIC-CONTENT')
    data = tmp_path / 'annotated.csv'
    with data.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['path', 'label', 'family'])
        writer.writerow(['ok.txt', '0', 'normal'])
        writer.writerow(['=HYPERLINK("example")', '1', 'fixture'])
    return create_app({'TESTING': True, 'CSRF_ENABLED': csrf, 'FILES_ROOT': base,
                       'DATABASE': tmp_path / 'events.sqlite3', 'TRAINING_DATA_PATH': data,
                       'ADMIN_PASSWORD': 'extension-test-secret',
                       'AUDITOR_PASSWORD_HASH': generate_password_hash('auditor-password')})


def token(c, path='/login'):
    return re.search(rb'name="csrf_token" value="([^"]+)"', c.get(path).data).group(1).decode()


def login(c, role='admin', csrf=False):
    fields = {'password': 'extension-test-secret' if role == 'admin' else 'auditor-password', 'role': role}
    if csrf:
        fields['csrf_token'] = token(c)
    response=c.post('/login', data=fields)
    assert response.status_code == 302
    complete_mfa(c,response)


def test_all_log_filters_and_statistics_share_scope(tmp_path, monkeypatch):
    app = application(tmp_path)
    clock = Mock()
    clock.now.side_effect = [datetime(2026, 1, 1, h, tzinfo=timezone.utc) for h in (0, 1, 2)]
    monkeypatch.setattr(database, 'datetime', clock)
    for path, label, score, action, status in [('first', 'benign', .1, 'ALLOW', 200),
                                               ('second', 'suspicious', .9, 'BLOCK', 403),
                                               ('third', 'unavailable', None, 'MISS', 404)]:
        database.insert_log(app.config['DATABASE'], '127.0.0.1', path, score, label, action, status, 'fixture', 1)
    monkeypatch.undo()
    filters = normalize_filters(action='BLOCK', ml_label='suspicious', http_status='403',
                                start='2026-01-01T08:00:00+07:00', end='2026-01-01T01:00:00Z')
    assert [r['requested_path'] for r in database.recent_logs(app.config['DATABASE'], **filters)] == ['second']
    assert database.summary(app.config['DATABASE'], **filters) == {'total': 1, 'blocked': 1, 'allowed': 0, 'suspicious': 1}
    assert database.summary(app.config['DATABASE'])['total'] == 3
    c = app.test_client()
    login(c)
    page = c.get('/dashboard', query_string=filters)
    assert page.status_code == 200 and b'second' in page.data and b'first' not in page.data and b'third' not in page.data
    with c.post('/dashboard/logs/export', data=filters) as response:
        assert response.status_code == 200 and b'second' in response.data and b'first' not in response.data


@pytest.mark.parametrize('filters', [dict(ml_label="' OR 1=1 --"), dict(http_status='403 OR 1=1'),
                                     dict(start='not-a-date'), dict(start='2026-02-01', end='2026-01-01'),
                                     dict(http_status=True), dict(action=['BLOCK'])])
def test_invalid_log_filters_are_rejected(filters):
    with pytest.raises(ValueError):
        normalize_filters(**filters)


@pytest.mark.parametrize('field,value', [('score', float('nan')), ('score', 1.1), ('duration_ms', -1),
                                         ('duration_ms', float('inf')), ('action', 'DELETE'),
                                         ('ml_label', 'invented'), ('status', 200.0)])
def test_invalid_log_events_not_persisted(tmp_path, field, value):
    path = tmp_path / 'events.sqlite3'
    database.init_db(path)
    event = dict(ip='127.0.0.1', path='x', score=.1, ml_label='benign', action='ALLOW', status=200, reason='fixture', duration_ms=1)
    event[field] = value
    with pytest.raises(ValueError):
        database.insert_log(path, **event)
    assert database.summary(path)['total'] == 0


def test_failed_access_log_withholds_body_and_closes_handle(tmp_path, monkeypatch):
    app = application(tmp_path)
    original = web.open_authorized
    handles = []
    def tracked(*args):
        f = original(*args)
        handles.append(f)
        return f
    monkeypatch.setattr(web, 'open_authorized', tracked)
    monkeypatch.setattr(web, 'insert_log', Mock(side_effect=sqlite3.OperationalError('fixture: disk full')))
    response = app.test_client().get('/download?path=ok.txt')
    assert response.status_code == 503 and b'PUBLIC-CONTENT' not in response.data
    assert handles and all(f.closed for f in handles)
    assert database.summary(app.config['DATABASE'])['total'] == 0


def test_authentication_audit_failure_does_not_grant_role(tmp_path, monkeypatch):
    app = application(tmp_path)
    c = app.test_client()
    monkeypatch.setattr(web, 'insert_security_event', Mock(side_effect=sqlite3.OperationalError('fixture')))
    assert c.post('/login', data={'password': 'extension-test-secret'}).status_code == 503
    with c.session_transaction() as session:
        assert session.get('role') is None
    assert c.get('/dashboard').status_code == 302


def test_logout_clears_session_even_when_audit_fails(tmp_path, monkeypatch):
    app = application(tmp_path)
    c = app.test_client()
    login(c)
    monkeypatch.setattr(web, 'insert_security_event', Mock(side_effect=sqlite3.OperationalError('fixture')))
    assert c.post('/logout').status_code == 302
    assert c.get('/dashboard').status_code == 302


def test_csrf_rejection_survives_audit_failure(tmp_path, monkeypatch):
    app = application(tmp_path, csrf=True)
    monkeypatch.setattr('app.auth.insert_security_event', Mock(side_effect=sqlite3.OperationalError('fixture')))
    assert app.test_client().post('/login', data={'password': 'extension-test-secret'}).status_code == 403


def test_training_metadata_and_csv_are_real_read_only_artifacts(tmp_path):
    app = application(tmp_path, csrf=True)
    c = app.test_client()
    login(c, csrf=True)
    data_hash = sha256(app.config['TRAINING_DATA_PATH'])
    model_hash = sha256(app.config['MODEL_PATH'])
    page = c.get('/dashboard/ai-training')
    assert page.status_code == 200 and b'view_max_parent_components' in page.data and b'length' in page.data
    csrf = token(c, '/dashboard/ai-training')
    with c.post('/dashboard/ai-training/export', data={'kind': 'v1', 'csrf_token': csrf}) as response:
        rows = list(csv.DictReader(StringIO(response.data.decode('utf-8-sig'))))
        model = joblib.load(app.config['MODEL_PATH'])
        assert response.status_code == 200 and len(rows) == 18
        assert float(rows[0]['coefficient']) == float(model.named_steps['model'].coef_[0][0])
    with c.post('/dashboard/ai-training/export', data={'kind': 'v2', 'csrf_token': csrf}) as response:
        assert response.status_code == 200
        assert len(list(csv.DictReader(StringIO(response.data.decode('utf-8-sig'))))) == 30
    with c.post('/dashboard/ai-training/export', data={'kind': 'dataset', 'csrf_token': csrf}) as response:
        assert response.status_code == 200 and b"'=HYPERLINK" in response.data
    assert c.post('/dashboard/ai-training/export', data={'kind': '../../secret', 'csrf_token': csrf}).status_code == 400
    assert c.post('/dashboard/ai-training/export', data={'kind': 'dataset'}).status_code == 403
    assert sha256(app.config['TRAINING_DATA_PATH']) == data_hash and sha256(app.config['MODEL_PATH']) == model_hash


def test_non_admin_cannot_access_any_management_data(tmp_path):
    app = application(tmp_path, csrf=True)
    c = app.test_client()
    paths = ['/dashboard', '/dashboard/ai-training', '/dashboard/ai-evaluation',
             '/dashboard/ai-evaluation/chart/metrics.png?run=20261116T154448Z_7a27a7']
    for path in paths:
        assert c.get(path).status_code == 302
    login(c, 'auditor', csrf=True)
    for path in paths:
        assert c.get(path).status_code == 403
    csrf = token(c, '/')
    assert c.post('/dashboard/ai-training/export', data={'kind': 'dataset', 'csrf_token': csrf}).status_code == 403
    assert c.post('/dashboard/logs/export', data={'csrf_token': csrf}).status_code == 403


def test_training_invalid_csv_fails_closed_without_fabrication(tmp_path):
    app = application(tmp_path)
    Path(app.config['TRAINING_DATA_PATH']).write_text('wrong,columns\n', encoding='utf-8')
    c = app.test_client()
    login(c)
    assert c.get('/dashboard/ai-training').status_code == 200
    assert c.post('/dashboard/ai-training/export', data={'kind': 'dataset'}).status_code == 404


def test_corrupt_experimental_model_is_not_deserialized(tmp_path, monkeypatch):
    from app.training_view import inspect_models
    bad = tmp_path / 'untrusted.joblib'
    bad.write_bytes(b'corrupt or substituted artifact')
    load = Mock(side_effect=AssertionError('must check checksum before pickle loading'))
    monkeypatch.setattr('joblib.load', load)
    assert inspect_models(None, bad) == {'v1': None, 'v2': None}
    load.assert_not_called()


def test_training_view_reports_canonical_duplicates(tmp_path):
    from app.training_view import read_dataset, dataset_stats
    file = tmp_path / 'data.csv'
    file.write_text('path,label,family\n../secret.txt,1,a\n%252e%252e%252fsecret.txt,1,b\n', encoding='utf-8')
    stats = dataset_stats(read_dataset(file), file)
    assert stats['rows'] == 2 and stats['exact_duplicate_excess'] == 0 and stats['canonical_duplicate_excess'] == 1


def test_history_request_pins_the_requested_archived_run(tmp_path):
    app = application(tmp_path)
    c = app.test_client()
    login(c)
    run = '20261116T153450Z_e5b13b'
    response = c.get('/dashboard/ai-evaluation', query_string={'run': run})
    assert response.status_code == 200 and run.encode() in response.data


@pytest.mark.parametrize('setting', ['TRAINING_DATA_PATH', 'EXPERIMENTAL_MODEL_PATH', 'EVALUATION_ROOT'])
def test_training_artifacts_cannot_be_configured_inside_public_root(tmp_path, setting):
    with pytest.raises(ValueError, match='outside FILES_ROOT'):
        create_app({'TESTING': True, 'FILES_ROOT': tmp_path/'public', 'DATABASE': tmp_path/'events.sqlite3',
                    setting: tmp_path/'public'/'private-artifact'})
