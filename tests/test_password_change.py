"""Persistent credentials, server-side revocation, atomic failure and no secret reflection."""
from pathlib import Path
import re
import secrets
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from werkzeug.security import check_password_hash,generate_password_hash
from app import create_app
from app.credential_store import atomic_hash_write,credential_lock,read_hash

OLD=secrets.token_urlsafe(24)
NEW=secrets.token_urlsafe(24)


@pytest.fixture
def config(tmp_path):
    return dict(TESTING=True,CSRF_ENABLED=True,FILES_ROOT=tmp_path/'public',DATABASE=tmp_path/'audit.sqlite3',
                ADMIN_HASH_FILE=tmp_path/'admin_password.hash',AUDITOR_HASH_FILE=tmp_path/'auditor_password.hash',
                SECRET_KEY=secrets.token_hex(32),ADMIN_PASSWORD=OLD,
                MODEL_PATH=tmp_path/'not-present.joblib',AUDITOR_PASSWORD_HASH=generate_password_hash('auditor-fixture-118'))


def token(client,path='/login'):
    response=client.get(path)
    return re.search(rb'name="csrf_token" value="([^"]+)"',response.data)[1].decode()


def login(client,password=OLD,role='admin'):
    return client.post('/login',data={'csrf_token':token(client),'password':password,'role':role})


def change(client,current=OLD,new=NEW,confirmation=None):
    return client.post('/account/password',data={'csrf_token':token(client,'/account/password'),
             'current_password':current,'new_password':new,'confirm_password':new if confirmation is None else confirmation})


def test_hash_and_password_survive_repeated_factories_and_stable_secret_sessions(config):
    first=create_app(config);client=first.test_client();assert login(client).status_code==302
    path=Path(config['ADMIN_HASH_FILE']);original=path.read_bytes()
    cookie=client.get_cookie('session').value
    for _ in range(3):
        app=create_app({**config,'ADMIN_PASSWORD':'different-bootstrap-do-not-use'})
        assert path.read_bytes()==original
        other=app.test_client();other.set_cookie('session',cookie)
        assert other.get('/dashboard').status_code==200
        assert login(app.test_client()).status_code==302
    assert OLD.encode() not in original
    assert first.config['BOOTSTRAP_PASSWORD'] is None and 'ADMIN_PASSWORD' not in first.config


def test_success_revokes_other_workers_and_cli_changes_survive_restart(config,caplog):
    a=create_app(config);b=create_app(config);one=a.test_client();two=b.test_client()
    login(one);login(two)
    stale=two.get_cookie('session').value
    assert change(one).status_code==302
    assert one.get('/dashboard').status_code==302
    assert two.get('/dashboard').status_code==302
    two.set_cookie('session',stale);assert two.get('/dashboard').status_code==302
    restarted=create_app(config);client=restarted.test_client()
    assert login(client,OLD).status_code==200
    assert login(client,NEW).status_code==302
    assert client.get('/dashboard').status_code==200
    from tools.manage_credentials import store_password
    store_password('cli-fixture-password-741',config['ADMIN_HASH_FILE'])
    assert client.get('/dashboard').status_code==302
    assert login(client,'cli-fixture-password-741').status_code==302
    with sqlite3.connect(config['DATABASE']) as db:
        events=repr(db.execute('SELECT * FROM security_events').fetchall())
    assert 'password_change_success' in events
    assert OLD not in events+caplog.text and NEW not in events+caplog.text


@pytest.mark.parametrize('current,new,confirmation,expected',[
 ('incorrect-fixture-832',NEW,NEW,403),(OLD,'short','short',400),
 (OLD,'x'*129,'x'*129,400),(OLD,NEW,'confirmation-mismatch-592',400),(OLD,OLD,OLD,400)])
def test_invalid_change_keeps_original_hash_and_no_secret_reflection(config,current,new,confirmation,expected,caplog):
    app=create_app(config);client=app.test_client();login(client)
    before=Path(config['ADMIN_HASH_FILE']).read_bytes()
    result=change(client,current,new,confirmation)
    assert result.status_code==expected
    assert Path(config['ADMIN_HASH_FILE']).read_bytes()==before
    text=result.get_data(as_text=True)
    for secret in [current,new,confirmation]:
        assert secret not in text and secret not in caplog.text
    assert client.get('/dashboard').status_code==200
    with sqlite3.connect(config['DATABASE']) as db:
        assert db.execute("SELECT COUNT(*) FROM security_events WHERE event='password_change_failed'").fetchone()[0]==1


def test_write_failure_preserves_old_hash_login_and_sessions(config):
    app=create_app(config);client=app.test_client();login(client)
    path=Path(config['ADMIN_HASH_FILE']);before=path.read_bytes()
    with patch('app.credential_store.os.replace',side_effect=PermissionError('fixture denied')):
        assert change(client).status_code==503
    assert path.read_bytes()==before and not list(path.parent.glob('.credential-*.tmp'))
    assert client.get('/dashboard').status_code==200
    assert login(app.test_client()).status_code==302


def test_audit_unavailable_before_mutation_keeps_old_hash(config):
    app=create_app(config);client=app.test_client();login(client)
    before=Path(config['ADMIN_HASH_FILE']).read_bytes()
    with patch('app.web.insert_security_event',side_effect=sqlite3.OperationalError('fixture audit unavailable')):
        assert change(client).status_code==503
    assert Path(config['ADMIN_HASH_FILE']).read_bytes()==before


def test_success_audit_outage_does_not_falsely_report_old_password_active(config,caplog):
    from app.web import insert_security_event
    app=create_app(config);client=app.test_client();login(client)
    def audit(*args):
        if args[-1]=='password_change_success':raise sqlite3.OperationalError('fixture outage after commit')
        return insert_security_event(*args)
    with patch('app.web.insert_security_event',side_effect=audit):
        assert change(client).status_code==302
    assert check_password_hash(read_hash(config['ADMIN_HASH_FILE']),NEW)
    assert client.get('/dashboard').status_code==302
    assert OLD not in caplog.text and NEW not in caplog.text


@pytest.mark.parametrize('length',[6,8,12,128])
def test_password_length_boundaries_accepted(config,length):
    app=create_app(config);client=app.test_client();login(client)
    assert change(client,new='z'*length).status_code==302
    assert login(client,'z'*length).status_code==302


def test_restart_with_random_session_key_keeps_password_but_requires_login(config):
    config.pop('SECRET_KEY')
    a=create_app(config);one=a.test_client();login(one)
    b=create_app(config);two=b.test_client();two.set_cookie('session',one.get_cookie('session').value)
    assert a.secret_key!=b.secret_key and two.get('/dashboard').status_code==302
    assert login(two).status_code==302


def test_change_csrf_permissions_and_missing_version_fail_closed(config):
    app=create_app(config);client=app.test_client()
    assert client.get('/account/password').status_code==302
    assert client.post('/account/password',data={'csrf_token':token(client)}).status_code==302
    login(client,role='auditor',password='auditor-fixture-118')
    assert client.get('/account/password').status_code==403
    assert client.post('/account/password',data={'csrf_token':token(client,'/')}).status_code==403
    login(client)
    assert client.post('/account/password',data={'current_password':OLD,'new_password':NEW}).status_code==403
    with client.session_transaction() as session:session.pop('_credential_version')
    assert client.get('/dashboard').status_code==302


def test_password_change_rate_limit_is_shared_across_workers(config):
    a=create_app(config);b=create_app(config);one=a.test_client();two=b.test_client();login(one);login(two)
    for client in [one,two,one,two,one]:assert change(client,current='incorrect-fixture-287').status_code==403
    result=change(two)
    assert result.status_code==429 and result.headers['Retry-After']=='300'
    assert check_password_hash(read_hash(config['ADMIN_HASH_FILE']),OLD)


def test_concurrent_password_changes_cannot_both_commit(config):
    app=create_app(config);clients=[app.test_client(),app.test_client()]
    for client in clients:login(client)
    tokens=[token(client,'/account/password') for client in clients]
    gate=threading.Barrier(2)
    def worker(i):
        gate.wait()
        return clients[i].post('/account/password',data={'csrf_token':tokens[i],'current_password':OLD,
              'new_password':'parallel-fixture-pass-'+str(i),'confirm_password':'parallel-fixture-pass-'+str(i)}).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:statuses=list(executor.map(worker,[0,1]))
    assert statuses.count(302)==1 and all(s in [302,403] for s in statuses)


def test_corrupt_hash_not_replaced_by_bootstrap(config):
    path=Path(config['ADMIN_HASH_FILE']);path.write_text('invalid-hash',encoding='utf-8')
    with pytest.raises(ValueError,match='Invalid Werkzeug'):create_app(config)
    assert path.read_text()=='invalid-hash'


def test_no_automatic_password_or_plaintext_console(config,monkeypatch):
    monkeypatch.delenv('ADMIN_PASSWORD',raising=False);monkeypatch.delenv('ADMIN_PASSWORD_HASH',raising=False)
    config.pop('ADMIN_PASSWORD')
    config['TESTING']=False
    with pytest.raises(ValueError,match='manage_credentials'):create_app(config)
    root=Path(__file__).resolve().parents[1]
    assert 'TEMPORARY ADMIN PASSWORD' not in (root/'run.py').read_text()

def test_existing_werkzeug_pbkdf2_hash_is_not_replaced(config):
    path=Path(config['ADMIN_HASH_FILE'])
    original=generate_password_hash(OLD,method='pbkdf2:sha256:1000')
    path.write_text(original+'\n',encoding='utf-8')
    app=create_app(config)
    assert path.read_text().strip()==original
    assert login(app.test_client()).status_code==302

@pytest.mark.parametrize('length,accepted',[(5,False),(6,True),(8,True),(12,True),(128,True),(129,False)])
@pytest.mark.parametrize('role',['admin','auditor'])
def test_cli_length_policy_for_both_roles(tmp_path,length,accepted,role):
    from tools.manage_credentials import store_password
    path=tmp_path/(role+'_password.hash')
    value='a'*length
    if accepted:
        store_password(value,path)
        assert check_password_hash(read_hash(path),value)
        assert path.read_text().strip()!=value
    else:
        with pytest.raises(ValueError):store_password(value,path)
        assert not path.exists()


@pytest.mark.parametrize('length,accepted',[(5,False),(6,True),(8,True),(12,True),(128,True),(129,False)])
def test_bootstrap_length_policy(config,length,accepted):
    config['ADMIN_PASSWORD']='a'*length
    if accepted:
        app=create_app(config)
        assert login(app.test_client(),'a'*length).status_code==302
    else:
        with pytest.raises(ValueError):create_app(config)
        assert not Path(config['ADMIN_HASH_FILE']).exists()


def test_six_character_password_persists_and_form_is_consistent(config):
    config['ADMIN_PASSWORD']='abcdef'
    app=create_app(config);client=app.test_client();login(client,'abcdef')
    html=client.get('/account/password').get_data(as_text=True)
    assert html.count('minlength="6"')==2 and 'minlength="12"' not in html
    assert change(client,current='abcdef',new='ghijkl').status_code==302
    restarted=create_app(config);other=restarted.test_client()
    assert login(other,'abcdef').status_code==200
    assert login(other,'ghijkl').status_code==302
    assert other.get('/dashboard').status_code==200
