"""Real authentication for isolated test clients, including mandatory Admin MFA.

Non-MFA tests use an in-memory authenticator/backup-code wallet. Dedicated MFA
tests use raw requests to test missing factors, expiry and replay separately.
"""
import re
import time
from contextlib import closing
from pathlib import Path

import pyotp
from app.database import connect

_WALLETS = {}


def csrf(client, path='/login', **options):
    page = client.get(path, **options)
    return re.search(rb'name="csrf_token" value="([^"]+)"', page.data)[1].decode()


def complete_mfa(client, response=None, **options):
    if response is not None and not (response.status_code == 302 and response.location.endswith('/login/mfa')):
        return response
    app = client.application
    assert app.testing, 'Unit authentication helper is restricted to isolated TESTING apps'
    service = app.extensions['mfa']
    # Keep one explicit server time step while this unit fixture submits OTP.
    # Wall-clock rollover during an HTTP round trip belongs to raw MFA tests.
    fixture_instant = service.clock()
    service.clock = lambda: fixture_instant
    with client.session_transaction() as state:
        value = state.get('_mfa_pending')
    if value is None:
        return response
    with closing(connect(app.config['DATABASE'])) as db:
        _, principal = service.pending(value, db)
    key = (str(Path(app.config['DATABASE']).resolve()), principal.subject)
    form = client.get('/login/mfa', **options)
    assert form.status_code == 200
    secret_match = re.search(rb'id="mfa-secret">([A-Z2-7]+)</code>', form.data)
    if secret_match:
        secret = secret_match[1].decode()
        _WALLETS[key] = {'secret': secret, 'codes': []}
        factor = pyotp.TOTP(secret).at(service.clock())
    else:
        wallet = _WALLETS[key]
        if wallet['codes']:
            factor = wallet['codes'].pop()
        else:
            with closing(connect(app.config['DATABASE'])) as db:
                counter = db.execute('SELECT last_counter FROM auth_mfa WHERE subject=?', (principal.subject,)).fetchone()[0]
            # Explicit test clock for repeated logins; no runtime MFA bypass.
            instant = max(time.time(), (counter + 1) * 30 + 1)
            service.clock = lambda: instant
            factor = pyotp.TOTP(wallet['secret']).at(instant)
    token = re.search(rb'name="csrf_token" value="([^"]+)"', form.data)[1].decode()
    verified = client.post('/login/mfa', data={'csrf_token': token, 'code': factor}, **options)
    if secret_match:
        assert verified.status_code == 200, {'http':verified.status_code,'step':int(service.clock()//30)}
        codes = re.findall(rb'<li><code>([0-9a-f-]{35})</code></li>', verified.data)
        assert len(codes) == 8
        _WALLETS[key]['codes'] = [value.decode() for value in codes]
    else:
        assert verified.status_code == 302 and verified.location.endswith('/dashboard')
    with client.session_transaction() as state:
        assert state.get('role') == 'admin' and state.get('_auth_sid') and not state.get('_mfa_pending')
    return response if response is not None else verified


def login(client, password='test-only-secret', role='admin', identifier='', **options):
    token = csrf(client, **options)
    response = client.post('/login', data={'password': password, 'role': role, 'identifier': identifier, 'csrf_token': token}, **options)
    return complete_mfa(client, response, **options)
