"""Account migration, authorization and recovery with isolated SQLite/mailbox."""
from contextlib import closing
import hashlib
import re
import sqlite3
import threading
from urllib.parse import urlsplit,parse_qs
import pytest
from app.passwords import check_password_hash
from tests.auth_support import complete_mfa
from app import create_app
from app import account_store as store

OLD='user-password-123';NEW='new-user-password-456';ADMIN='legacy-admin-password'


@pytest.fixture
def setup(tmp_path):
    mailbox=[]
    public=tmp_path/'public';public.mkdir();(public/'ok.txt').write_bytes(b'PUBLIC')
    cfg={'TESTING':True,'CSRF_ENABLED':True,'SECRET_KEY':'account-tests-only',
         'FILES_ROOT':public,'DATABASE':tmp_path/'events.sqlite3','MODEL_PATH':tmp_path/'missing.joblib',
         'ADMIN_PASSWORD':ADMIN,'ACCOUNT_RESET_ORIGIN':'https://example.test','ACCOUNT_MAIL_SENDER':lambda address,url:mailbox.append((address,url))}
    app=create_app(cfg)
    yield app,app.test_client(),mailbox,cfg
    app.extensions['recovery_mail'].close()


def token(client,path='/login'):
    return re.search(rb'name="csrf_token" value="([^"]+)"',client.get(path).data)[1].decode()


def post(client,path,data,csrf_path='/login'):
    response=client.post(path,data={**data,'csrf_token':token(client,csrf_path)})
    return complete_mfa(client,response) if path=='/login' else response


def register(client,username='alice',email='alice@example.test',**extra):
    return post(client,'/register',dict(username=username,email=email,display_name='Hữu Vinh',password=OLD,confirm_password=OLD,**extra))


def login(client,identifier='alice',password=OLD,**extra):
    return post(client,'/login',dict(identifier=identifier,password=password,**extra))


def query(app,sql,params=()):
    with closing(sqlite3.connect(app.config['DATABASE'])) as db:return db.execute(sql,params).fetchall()


def issued_token(app,client,mailbox,include_response=False):
    response=post(client,'/forgot-password',{'identifier':'alice'})
    service=app.extensions['recovery_mail'];done=threading.Event()
    threading.Thread(target=lambda:(service.queue.join(),done.set()),daemon=True).start()
    assert done.wait(5) and response.status_code==200 and mailbox
    url=mailbox[-1][1]
    assert urlsplit(url).query==''
    value=parse_qs(urlsplit(url).fragment)['token'][0]
    return (value,response) if include_response else value


def test_registration_hash_identity_login_and_legacy_access(setup):
    app,client,_,_=setup
    assert register(client).status_code==302
    row=query(app,'SELECT username,email,password_hash,role FROM auth_users')[0]
    assert row[:2]==('alice','alice@example.test') and row[3]=='user'
    assert row[2].startswith('$argon2id$') and check_password_hash(row[2],OLD)
    assert register(client,'bravo','bravo@example.test').status_code==302
    assert query(app,'SELECT password_hash FROM auth_users')[1][0]!=row[2]
    assert login(client,'ALICE@EXAMPLE.TEST',role='admin').status_code==302
    with client.session_transaction() as session:assert session['role']=='user' and not session['is_admin']
    assert client.get('/account').status_code==200
    for path in ['/dashboard','/admin/accounts','/dashboard/alerts','/dashboard/ai-training','/dashboard/ai-evaluation']:
        assert client.get(path).status_code==403
    assert client.get('/download?path=ok.txt').data==b'PUBLIC'
    assert client.get('/download?path=../secret').status_code==403
    assert post(client,'/logout',{}).status_code==302
    assert post(client,'/login',{'role':'admin','password':ADMIN}).status_code==302
    assert client.get('/dashboard').status_code==200


def test_invalid_signed_account_session_is_cleared_without_server_error(setup):
    app,client,_,_=setup
    assert register(client).status_code==302
    user_id=query(app,'SELECT id FROM auth_users')[0][0]
    for value,version in [(2**100,'invalid'),('1','invalid'),(user_id,'không-ascii')]:
        with client.session_transaction() as state:
            state.clear();state.update(user_id=value,role='user',_credential_version=version)
        response=client.get('/account')
        assert response.status_code==302 and '/login' in response.location
        with client.session_transaction() as state:assert 'user_id' not in state


def test_registration_validation_role_escalation_csrf_and_rate(setup):
    app,client,_,_=setup
    assert client.post('/register',data={}).status_code==403
    assert register(client,role='admin').status_code==400
    assert register(client,username="a' OR 1=1--").status_code==400
    for name in ['admin','auditor']:assert register(client,username=name).status_code==400
    assert query(app,'SELECT COUNT(*) FROM auth_users')==[(0,)]
    assert register(client).status_code==302
    assert register(client,'bobby','bobby@example.test').status_code==429


def test_profile_xss_no_role_or_email_changes(setup):
    app,client,_,_=setup;register(client);login(client)
    assert post(client,'/account',{'display_name':'<script>alert(1)</script>'}).status_code==302
    page=client.get('/account')
    assert b'&lt;script&gt;' in page.data and b'<script>alert(1)</script>' not in page.data
    for data in [{'role':'admin'},{'email':'other@example.test'},{'active':'1'}]:
        assert post(client,'/account',{'display_name':'safe',**data}).status_code==400
    assert query(app,'SELECT role,email FROM auth_users')==[('user','alice@example.test')]


def test_login_failure_bruteforce_and_fixation(setup):
    app,client,_,_=setup;register(client)
    before=token(client)
    assert login(client).status_code==302
    assert token(client)!=before
    post(client,'/logout',{})
    for _ in range(5):assert login(client,password='wrong').status_code==200
    assert login(client).status_code==429
    attacker=app.test_client()
    assert attacker.post('/login',data={'identifier':"' OR 1=1--",'password':OLD,'csrf_token':token(attacker)},environ_overrides={'REMOTE_ADDR':'192.0.2.9'}).status_code==200
    assert attacker.get('/account').status_code==302


def test_change_password_revokes_other_sessions_and_survives_restart(setup):
    app,client,_,cfg=setup;register(client);login(client)
    other=app.test_client();login(other)
    assert post(client,'/account/password',{'current_password':'wrong','new_password':NEW,'confirm_password':NEW}).status_code==403
    assert post(client,'/account/password',{'current_password':OLD,'new_password':NEW,'confirm_password':'mismatch'}).status_code==400
    assert post(client,'/account/password',{'current_password':OLD,'new_password':NEW,'confirm_password':NEW}).status_code==302
    assert other.get('/account').status_code==302
    assert login(client,password=OLD).status_code==200
    assert login(client,password=NEW).status_code==302
    newer=create_app(cfg)
    try:
        assert login(newer.test_client(),password=NEW).status_code==302
        assert query(newer,'SELECT COUNT(*) FROM auth_users')==[(1,)]
    finally:newer.extensions['recovery_mail'].close()


def test_reset_uniform_response_token_hash_single_use_and_revocation(setup,caplog):
    app,client,mailbox,_=setup;register(client);login(client)
    other=app.test_client();login(other)
    anonymous=app.test_client()
    value,known=issued_token(app,anonymous,mailbox,include_response=True)
    unknown=post(anonymous,'/forgot-password',{'identifier':'not-found'})
    assert known.status_code==unknown.status_code==200 and known.data==unknown.data
    stored=query(app,'SELECT digest FROM auth_reset_tokens')[0][0]
    assert stored==hashlib.sha256(value.encode()).hexdigest() and stored!=value
    assert post(client,'/reset-password',{'token':value,'new_password':NEW,'confirm_password':NEW}).status_code==302
    assert other.get('/account').status_code==302
    assert post(client,'/reset-password',{'token':value,'new_password':OLD,'confirm_password':OLD}).status_code==400
    assert login(client,password=NEW).status_code==302
    assert value not in caplog.text and OLD not in caplog.text and NEW not in caplog.text


def test_expired_reset_token_rejected(setup,monkeypatch):
    app,client,mailbox,_=setup;register(client)
    value=issued_token(app,client,mailbox)
    expires=query(app,'SELECT expires FROM auth_reset_tokens')[0][0]
    monkeypatch.setattr(store,'clock',lambda:expires+1)
    assert post(client,'/reset-password',{'token':value,'new_password':NEW,'confirm_password':NEW}).status_code==400
    assert check_password_hash(query(app,'SELECT password_hash FROM auth_users')[0][0],OLD)


def test_admin_lock_unlock_role_change_and_self_protection(setup):
    app,client,_,_=setup;register(client);login(client)
    admin=app.test_client();post(admin,'/login',{'role':'admin','password':ADMIN})
    target=query(app,'SELECT id FROM auth_users')[0][0]
    assert admin.post('/admin/accounts',data={'user_id':target,'action':'lock'}).status_code==403
    assert post(admin,'/admin/accounts',{'user_id':target,'action':'lock','current_password':'wrong'}).status_code==403
    assert post(admin,'/admin/accounts',{'user_id':target,'action':'lock','current_password':ADMIN}).status_code==302
    assert client.get('/account').status_code==302
    assert login(client).status_code==200
    assert post(admin,'/admin/accounts',{'user_id':target,'action':'unlock','current_password':ADMIN}).status_code==302
    assert post(admin,'/admin/accounts',{'user_id':target,'action':'role','role':'auditor','current_password':ADMIN}).status_code==302
    assert login(client).status_code==302
    assert client.get('/dashboard').status_code==403 and client.get('/admin/accounts').status_code==403
    assert post(admin,'/admin/accounts',{'user_id':target,'action':'role','role':'admin','current_password':ADMIN}).status_code==302
    assert login(client).status_code==302 and client.get('/dashboard').status_code==200
    assert post(client,'/admin/accounts',{'user_id':target,'action':'lock','current_password':OLD}).status_code==409
    assert post(admin,'/admin/accounts',{'user_id':target,'action':'lock','current_password':ADMIN}).status_code==409


def test_legacy_hash_and_logs_preserved_by_migration(setup):
    app,client,_,cfg=setup
    client.get('/download?path=ok.txt')
    before=query(app,'SELECT * FROM access_logs');hashed=app.config['ADMIN_HASH_FILE'].read_bytes()
    store.migrate(app.config['DATABASE']);store.migrate(app.config['DATABASE'])
    assert query(app,'SELECT * FROM access_logs')==before and app.config['ADMIN_HASH_FILE'].read_bytes()==hashed
    assert query(app,'SELECT version FROM auth_schema_versions')==[(1,),(2,)]


def test_https_cookie_attributes_and_unsafe_public_http(setup):
    app,client,_,_=setup
    cookie=client.get('/login',base_url='https://localhost').headers['Set-Cookie']
    assert all(value in cookie for value in ['Secure','HttpOnly','SameSite=Lax'])
    app.config['TESTING']=False
    assert client.get('/login',base_url='http://public.example.test',environ_overrides={'REMOTE_ADDR':'192.0.2.8'}).status_code==400
    assert client.get('/login',base_url='https://public.example.test',environ_overrides={'REMOTE_ADDR':'192.0.2.8'}).status_code==200


def test_reset_consumption_is_atomic_under_concurrency(setup):
    from concurrent.futures import ThreadPoolExecutor
    app,client,mailbox,_=setup;register(client)
    value=issued_token(app,client,mailbox)
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes=list(executor.map(lambda _:store.reset_password(app.config['DATABASE'],value,NEW,'fixture'),range(2)))
    assert sorted(outcomes)==[False,True]
    assert query(app,"SELECT COUNT(*) FROM security_events WHERE event LIKE 'password_reset_success:%'")==[(1,)]


def test_disabled_mailer_never_displays_token_or_creates_reset(setup):
    app,client,_,_=setup;register(client)
    app.extensions['recovery_mail'].configured=False
    response=post(client,'/forgot-password',{'identifier':'alice'})
    assert response.status_code==200 and query(app,'SELECT COUNT(*) FROM auth_reset_tokens')==[(0,)]
    assert b'#token=' not in response.data


def test_mail_failure_invalidates_token_without_logging_secrets(setup,caplog):
    app,client,_,_=setup;register(client)
    service=app.extensions['recovery_mail']
    def failed(address,url):raise OSError('DO_NOT_LOG_MAIL_SECRET')
    service.sender=failed
    assert post(client,'/forgot-password',{'identifier':'alice'}).status_code==200
    done=threading.Event();threading.Thread(target=lambda:(service.queue.join(),done.set()),daemon=True).start()
    assert done.wait(5)
    assert query(app,'SELECT used FROM auth_reset_tokens')==[(1,)]
    assert 'DO_NOT_LOG_MAIL_SECRET' not in caplog.text


def test_reset_tokens_revoked_by_password_change(setup):
    app,client,mailbox,_=setup;register(client);login(client)
    value=issued_token(app,client,mailbox)
    post(client,'/account/password',{'current_password':OLD,'new_password':NEW,'confirm_password':NEW})
    assert not store.reset_password(app.config['DATABASE'],value,OLD,'fixture')


def test_migration_rolls_back_incompatible_existing_table(tmp_path):
    path=tmp_path/'incompatible.sqlite3'
    with closing(sqlite3.connect(path)) as db,db:
        db.execute('CREATE TABLE auth_users(id INTEGER PRIMARY KEY)');db.execute('INSERT INTO auth_users VALUES(42)')
    with pytest.raises(RuntimeError,match='Unsupported account table'):store.migrate(path)
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('SELECT * FROM auth_users').fetchall()==[(42,)]
        assert db.execute("SELECT name FROM sqlite_master WHERE name='auth_schema_versions'").fetchall()==[]
