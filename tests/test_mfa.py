"""Argon2, mandatory MFA, replay, key separation and session attack regressions."""
from contextlib import closing
import json
from pathlib import Path
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
import threading

import pyotp
import pytest
from werkzeug.security import generate_password_hash
from argon2 import extract_parameters, Type

from app import create_app
from app import account_store as store
from app.credential_store import read_hash
from app.database import connect
from app.mfa_keys import KeyRing, MFACryptoError
from app.passwords import password_hash, check_password_hash
from tools.manage_mfa import recover

PASSWORD = 'mfa-fixture-password'


@pytest.fixture
def lab(tmp_path):
    cfg = {'TESTING': True, 'CSRF_ENABLED': True, 'SECRET_KEY': 'mfa-tests-only',
           'DATABASE': tmp_path/'events.sqlite3', 'FILES_ROOT': tmp_path/'public',
           'MODEL_PATH': tmp_path/'missing', 'ADMIN_PASSWORD': PASSWORD}
    app = create_app(cfg)
    instant = [1800000001.0]
    app.extensions['mfa'].clock = lambda: instant[0]
    yield app, app.test_client(), cfg, instant
    app.extensions['recovery_mail'].close();app.extensions['ai_explanations'].close()


def csrf(client, path='/login'):
    return re.search(rb'name="csrf_token" value="([^"]+)"', client.get(path).data)[1].decode()


def post(client, path, fields, csrf_path='/login'):
    return client.post(path, data={**fields, 'csrf_token': csrf(client, csrf_path)})


def first(client, password=PASSWORD, **fields):
    return post(client, '/login', {'password': password, **fields})


def finish(client, code):
    return post(client, '/login/mfa', {'code': code}, '/login/mfa')


def enroll(app, client, **fields):
    assert first(client, **fields).location.endswith('/login/mfa')
    assert client.get('/dashboard').status_code == 302
    form = client.get('/login/mfa')
    secret = re.search(rb'id="mfa-secret">([A-Z2-7]+)', form.data)[1].decode()
    response = finish(client, pyotp.TOTP(secret).at(app.extensions['mfa'].clock()))
    assert response.status_code == 200
    codes = [c.decode() for c in re.findall(rb'<li><code>([0-9a-f-]{35})</code>', response.data)]
    assert len(codes) == 8
    return secret, codes


def query(app, sql, args=()):
    with closing(connect(app.config['DATABASE'])) as db:
        return db.execute(sql, args).fetchall()


def test_argon2id_random_salt_and_legacy_verification():
    one, two = password_hash(PASSWORD), password_hash(PASSWORD)
    p = extract_parameters(one)
    assert p.type == Type.ID and p.memory_cost == 65536 and p.time_cost == 3 and p.parallelism == 1
    assert p.salt_len == 16 and one != two and check_password_hash(one, PASSWORD)
    assert not check_password_hash(one, PASSWORD+'wrong')
    for method in ['pbkdf2:sha256:600000', 'scrypt:32768:8:1']:
        assert check_password_hash(generate_password_hash(PASSWORD, method=method), PASSWORD)
    for value in ['x'*5, 'x'*129]:
        with pytest.raises(ValueError):password_hash(value)
    assert check_password_hash(password_hash('x'*6), 'x'*6)


def test_admin_password_never_grants_role_without_totp(lab):
    app, client, _, _ = lab
    response = first(client)
    assert response.status_code == 302 and response.location.endswith('/login/mfa')
    with client.session_transaction() as state:
        assert 'role' not in state and 'user_id' not in state and '_mfa_pending' in state
    assert client.get('/dashboard').status_code == 302
    assert client.get('/admin/accounts').status_code == 302
    assert finish(client, 'wrong').status_code == 403
    assert query(app, 'SELECT COUNT(*) FROM auth_sessions')[0][0] == 0
    assert client.post('/login/mfa', data={'code': '123456'}).status_code == 403


def test_enrollment_encrypted_seed_hash_only_recovery_and_audit(lab, caplog):
    app, client, _, _ = lab
    secret, codes = enroll(app, client)
    assert client.get('/dashboard').status_code == 200
    rows = query(app, 'SELECT seed_cipher,last_counter FROM auth_mfa')
    assert secret not in rows[0]['seed_cipher']
    assert app.extensions['mfa'].keys.decrypt('legacy:admin', rows[0]['seed_cipher']) == secret
    serialized = str([tuple(r) for r in query(app, 'SELECT * FROM auth_backup_codes')])
    assert all(c not in serialized and c.replace('-', '') not in serialized for c in codes)
    assert client.get('/login/mfa/qr').status_code == 404
    assert client.get('/dashboard').status_code == 200
    assert PASSWORD not in caplog.text and secret not in caplog.text and not any(c in caplog.text for c in codes)


def test_otp_replay_and_expired_window(lab):
    app, client, _, instant = lab
    secret, codes = enroll(app, client)
    second = app.test_client();first(second)
    assert finish(second, pyotp.TOTP(secret).at(instant[0])).status_code == 403
    instant[0] += 30
    assert finish(second, pyotp.TOTP(secret).at(instant[0]-30)).status_code == 403
    assert finish(second, pyotp.TOTP(secret).at(instant[0])).status_code == 302


def test_backup_code_single_use_and_password_still_required(lab):
    app, client, _, _ = lab
    _, codes = enroll(app, client)
    other = app.test_client()
    assert other.get('/login/mfa').status_code == 302
    first(other)
    assert finish(other, codes[0]).status_code == 302
    third = app.test_client();first(third)
    assert finish(third, codes[0]).status_code == 403
    assert query(app, 'SELECT COUNT(*) FROM auth_backup_codes WHERE used=1')[0][0] == 1


def test_parallel_otp_is_consumed_exactly_once(lab):
    app, client, _, instant = lab
    secret, _ = enroll(app, client)
    instant[0] += 30
    clients = [app.test_client(), app.test_client()]
    for c in clients:first(c)
    tokens = [csrf(c, '/login/mfa') for c in clients]
    code = pyotp.TOTP(secret).at(instant[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda item:item[0].post('/login/mfa', data={'csrf_token':item[1], 'code':code}), zip(clients, tokens)))
    assert sorted(r.status_code for r in responses) == [302, 403]


def test_bruteforce_subject_limit_cannot_be_bypassed_by_changing_ip(lab):
    app, client, _, instant = lab
    enroll(app, client)
    other = app.test_client();first(other)
    token = csrf(other, '/login/mfa')
    for i in range(5):
        assert other.post('/login/mfa', data={'csrf_token':token,'code':'invalid'}, environ_overrides={'REMOTE_ADDR':f'192.0.2.{i+1}'}).status_code == 403
    assert other.post('/login/mfa', data={'csrf_token':token,'code':'invalid'}, environ_overrides={'REMOTE_ADDR':'192.0.2.99'}).status_code == 429
    assert client.get('/dashboard').status_code == 200  # Failed challenge does not revoke a legitimate session.


def test_pending_challenge_expires_and_cannot_be_replayed(lab):
    app, client, _, instant = lab
    first(client)
    instant[0] += 301
    assert client.get('/login/mfa').status_code == 302
    with client.session_transaction() as state:assert 'role' not in state


def test_logout_revokes_stolen_cookie_and_idle_absolute_timeouts(lab):
    app, client, _, instant = lab
    _, codes = enroll(app, client)
    stolen = client.get_cookie('session').value
    assert post(client, '/logout', {}).status_code == 302
    thief = app.test_client();thief.set_cookie('session', stolen)
    assert thief.get('/dashboard').status_code == 302
    first(client);finish(client, codes.pop())
    instant[0] += 901
    assert client.get('/dashboard').status_code == 302
    first(client);finish(client, codes.pop())
    for _ in range(33):
        instant[0] += 899
        response = client.get('/dashboard')
    assert response.status_code == 302


def test_session_cookie_alone_and_user_privilege_forgery_do_not_grant_admin(lab):
    app, client, _, _ = lab
    with client.session_transaction() as state:
        state.update(role='admin', _credential_version=app.extensions['credentials'].version('admin'),
                     _auth_sid=secrets.token_urlsafe(32), is_admin=True)
    assert client.get('/dashboard').status_code == 302
    store.register(app.config['DATABASE'], 'normal', 'normal@example.test', 'Normal', PASSWORD, 'local')
    assert first(client, identifier='normal', role='admin').location.endswith('/account')
    assert client.get('/dashboard').status_code == 403
    assert client.get('/account/mfa').status_code == 403
    assert client.get('/login/mfa').status_code == 302
    assert client.get('/account').status_code == 200


def test_keyring_aad_tamper_and_missing_key_do_not_generate_replacement(lab):
    app, client, cfg, _ = lab
    _, _ = enroll(app, client)
    cipher = query(app, 'SELECT seed_cipher FROM auth_mfa')[0][0]
    ring = app.extensions['mfa'].keys
    with pytest.raises(MFACryptoError):ring.decrypt('user:1', cipher)
    with pytest.raises(MFACryptoError):ring.decrypt('legacy:admin', cipher[:-5]+'AAAAA')
    path = Path(app.config['MFA_KEY_FILE']);backup = path.with_suffix('.saved-key')
    path.rename(backup)
    with pytest.raises(MFACryptoError):create_app(cfg)
    assert not path.exists() and backup.exists()
    backup.rename(path)
    restarted = create_app(cfg)
    assert read_hash(restarted.config['ADMIN_HASH_FILE']) == read_hash(app.config['ADMIN_HASH_FILE'])
    restarted.extensions['recovery_mail'].close();restarted.extensions['ai_explanations'].close()


def test_local_recovery_requires_admin_password_and_forces_enrollment(lab):
    app, client, _, _ = lab
    enroll(app, client)
    before = read_hash(app.config['ADMIN_HASH_FILE'])
    with pytest.raises(ValueError):recover(app.config['DATABASE'], 'legacy:admin', 'incorrect', app.config['ADMIN_HASH_FILE'])
    assert client.get('/dashboard').status_code == 200
    recover(app.config['DATABASE'], 'legacy:admin', PASSWORD, app.config['ADMIN_HASH_FILE'])
    assert client.get('/dashboard').status_code == 302
    assert read_hash(app.config['ADMIN_HASH_FILE']) == before
    first(client)
    assert b'id="mfa-secret"' in client.get('/login/mfa').data


def test_password_reset_does_not_disable_admin_mfa(lab):
    app, client, _, _ = lab
    store.register(app.config['DATABASE'],'alice','alice@example.test','Alice',PASSWORD,'local')
    with closing(connect(app.config['DATABASE'])) as db, db:
        db.execute("UPDATE auth_users SET role='admin' WHERE username='alice'")
    _, codes = enroll(app, client, identifier='alice')
    original = tuple(query(app, "SELECT seed_cipher,version FROM auth_mfa WHERE subject='user:1'")[0])
    _, token, _ = store.issue_reset(app.config['DATABASE'],'alice','local')
    assert store.reset_password(app.config['DATABASE'], token, 'new-password-fixture', 'local')
    assert tuple(query(app, "SELECT seed_cipher,version FROM auth_mfa WHERE subject='user:1'")[0]) == original
    assert client.get('/dashboard').status_code == 302
    response = first(client, password='new-password-fixture', identifier='alice')
    assert response.location.endswith('/login/mfa')
    assert client.get('/dashboard').status_code == 302
    assert finish(client, codes[0]).status_code == 302


def test_factor_rotation_requires_two_factors_and_revokes_old_sessions(lab):
    app, client, _, instant = lab
    secret, codes = enroll(app, client)
    stolen = client.get_cookie('session').value
    bad = post(client, '/account/mfa', {'current_password':'incorrect', 'code':codes[0]})
    assert bad.status_code == 403
    response = post(client, '/account/mfa', {'current_password':PASSWORD, 'code':codes[0]})
    assert response.location.endswith('/login/mfa')
    assert client.get('/dashboard').status_code == 302
    new_secret = re.search(rb'id="mfa-secret">([A-Z2-7]+)', client.get('/login/mfa').data)[1].decode()
    assert new_secret != secret
    assert finish(client, pyotp.TOTP(new_secret).at(instant[0])).status_code == 200
    old = app.test_client();old.set_cookie('session', stolen)
    assert old.get('/dashboard').status_code == 302
    first(old)
    assert finish(old, codes[1]).status_code == 403


def test_legacy_file_upgrades_after_verification_without_password_reset(tmp_path):
    original=generate_password_hash(PASSWORD,method='pbkdf2:sha256:1000')
    path=tmp_path/'admin_password.hash';path.write_text(original+'\n',encoding='utf-8')
    app=create_app({'TESTING':True,'CSRF_ENABLED':True,'DATABASE':tmp_path/'events.sqlite3',
                    'FILES_ROOT':tmp_path/'public','ADMIN_HASH_FILE':path,'MODEL_PATH':tmp_path/'absent'})
    assert read_hash(path)==original
    client=app.test_client();assert first(client).location.endswith('/login/mfa')
    assert read_hash(path).startswith('$argon2id$') and check_password_hash(read_hash(path),PASSWORD)
    assert any(p.read_text(encoding='utf-8').strip()==original for p in (tmp_path/'credential_history').iterdir())
    assert client.get('/dashboard').status_code==302
    app.extensions['recovery_mail'].close();app.extensions['ai_explanations'].close()


def test_database_rehash_race_does_not_authenticate_old_password(lab,monkeypatch):
    app,client,_,_=lab
    store.register(app.config['DATABASE'],'normal','normal@example.test','Normal',PASSWORD,'local')
    with closing(connect(app.config['DATABASE'])) as db,db:
        db.execute('UPDATE auth_users SET password_hash=?',(generate_password_hash(PASSWORD,method='pbkdf2:sha256:1000'),))
    changed=password_hash('a-concurrent-new-password')
    def concurrent_change(value):
        with closing(connect(app.config['DATABASE'])) as db,db:
            db.execute('UPDATE auth_users SET password_hash=?,session_version=?',(changed,secrets.token_urlsafe(32)))
        return password_hash(value)
    monkeypatch.setattr(store,'password_hash',concurrent_change)
    assert store.authenticate(app.config['DATABASE'],'normal',PASSWORD) is None
    assert check_password_hash(query(app,'SELECT password_hash FROM auth_users')[0][0],'a-concurrent-new-password')


def test_user_cannot_use_local_admin_recovery(lab):
    app,client,_,_=lab
    store.register(app.config['DATABASE'],'normal','normal@example.test','Normal',PASSWORD,'local')
    before=read_hash(app.config['ADMIN_HASH_FILE'])
    with pytest.raises(ValueError):recover(app.config['DATABASE'],'normal',PASSWORD,app.config['ADMIN_HASH_FILE'])
    assert read_hash(app.config['ADMIN_HASH_FILE'])==before
    assert query(app,'SELECT role FROM auth_users')[0][0]=='user'


def test_secret_key_rotation_does_not_destroy_totp_key_or_credentials(lab):
    app,client,cfg,instant=lab
    secret,codes=enroll(app,client)
    original=Path(app.config['MFA_KEY_FILE']).read_bytes()
    restarted=create_app({**cfg,'SECRET_KEY':'rotated-session-signing-secret'})
    other=restarted.test_client();other.set_cookie('session',client.get_cookie('session').value)
    assert other.get('/dashboard').status_code==302
    assert Path(restarted.config['MFA_KEY_FILE']).read_bytes()==original
    first(other)
    assert other.get('/dashboard').status_code==302
    assert finish(other,codes[0]).status_code==302
    assert restarted.extensions['mfa'].keys.decrypt('legacy:admin',query(app,'SELECT seed_cipher FROM auth_mfa')[0][0])==secret
    restarted.extensions['recovery_mail'].close();restarted.extensions['ai_explanations'].close()


def test_additive_v1_migration_keeps_old_hash_and_logs(tmp_path):
    from app.database import DDL
    path=tmp_path/'version-one.sqlite3'
    original=generate_password_hash(PASSWORD,method='pbkdf2:sha256:600000')
    with closing(connect(path)) as db:
        db.executescript(DDL+store.MIGRATION+'COMMIT;')
        db.execute("INSERT INTO auth_users(username,email,display_name,password_hash,session_version,created_at,updated_at) VALUES('normal','normal@example.test','Normal',?,'v1','old','old')",(original,))
        db.execute("INSERT INTO security_events(created_at,client_ip,actor_role,event) VALUES('old','local','admin','historical_event')")
        db.commit()
    store.migrate(path);store.migrate(path)
    with closing(connect(path)) as db:
        assert db.execute('SELECT password_hash FROM auth_users').fetchone()[0]==original
        assert db.execute('SELECT event FROM security_events').fetchone()[0]=='historical_event'
        assert [r[0] for r in db.execute('SELECT version FROM auth_schema_versions')]==[1,2]


def test_expensive_password_hashing_does_not_lock_event_writer(lab,monkeypatch):
    app,client,_,_=lab
    store.register(app.config['DATABASE'],'normal','normal@example.test','Normal',PASSWORD,'local')
    first(client,identifier='normal')
    token=csrf(client,'/account/password')
    (Path(app.config['FILES_ROOT'])/'ok.txt').write_bytes(b'PUBLIC')
    entered,release=threading.Event(),threading.Event()
    original=store.password_hash
    def expensive(value):
        entered.set()
        assert release.wait(15)
        return original(value)
    monkeypatch.setattr(store,'password_hash',expensive)
    with ThreadPoolExecutor(max_workers=1) as pool:
        job=pool.submit(client.post,'/account/password',data={'csrf_token':token,'current_password':PASSWORD,
                        'new_password':'fresh-password-fixture','confirm_password':'fresh-password-fixture'})
        try:
            assert entered.wait(5)
            response=app.test_client().get('/download?path=ok.txt')
            assert response.status_code==200 and response.data==b'PUBLIC'
        finally:
            release.set()
        assert job.result().status_code==302


def test_key_file_cannot_be_configured_under_public_files(lab):
    app,client,cfg,_=lab
    with pytest.raises(ValueError,match='outside FILES_ROOT'):
        create_app({**cfg,'MFA_KEY_FILE':Path(cfg['FILES_ROOT'])/'key.json'})
    assert not (Path(cfg['FILES_ROOT'])/'key.json').exists()


def test_corrupt_factor_does_not_bypass_auth_or_file_policy(lab):
    app,client,_,_=lab
    secret,_=enroll(app,client)
    with closing(connect(app.config['DATABASE'])) as db,db:
        db.execute("UPDATE auth_mfa SET seed_cipher='missing.invalid' WHERE subject='legacy:admin'")
    other=app.test_client();first(other)
    assert finish(other,pyotp.TOTP(secret).at(app.extensions['mfa'].clock())).status_code==503
    assert other.get('/dashboard').status_code==302
    (Path(app.config['FILES_ROOT'])/'ok.txt').write_bytes(b'PUBLIC')
    assert other.get('/download?path=ok.txt').data==b'PUBLIC'
    assert other.get('/download?path=../outside').status_code==403


def test_empty_optional_environment_keyring_keeps_existing_private_key(tmp_path):
    path=tmp_path/'mfa_keys.json'
    first=KeyRing(path,raw='')
    original=path.read_bytes()
    again=KeyRing(path,raw='')
    assert again.active==first.active and path.read_bytes()==original
    encrypted=first.encrypt('legacy:admin','fixture-seed')
    assert again.decrypt('legacy:admin',encrypted)=='fixture-seed'
