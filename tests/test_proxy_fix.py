"""Single trusted proxy opt-in; keep all IP consumers on request.remote_addr."""
import re
import sqlite3
from contextlib import closing

import pytest
from flask import request
from werkzeug.middleware.proxy_fix import ProxyFix
from app import create_app


def make_app(tmp_path,monkeypatch,trust):
    if trust is None:monkeypatch.delenv('TRUST_PROXY',raising=False)
    else:monkeypatch.setenv('TRUST_PROXY',trust)
    public=tmp_path/'public';public.mkdir()
    (public/'ok.txt').write_bytes(b'PUBLIC')
    app=create_app({'TESTING':True,'CSRF_ENABLED':True,'FILES_ROOT':public,
                    'DATABASE':tmp_path/'fixture.sqlite3','ADMIN_PASSWORD':'fixture-password-813'})
    @app.get('/_test/proxy')
    def probe():
        return dict(ip=request.remote_addr,scheme=request.scheme,host=request.host,
                    prefix=request.script_root,port=request.environ['SERVER_PORT'])
    return app,app.test_client()


HEADERS={'X-Forwarded-For':'198.51.100.23','X-Forwarded-Proto':'https',
         'X-Forwarded-Host':'attacker.invalid','X-Forwarded-Port':'9999','X-Forwarded-Prefix':'/evil'}


@pytest.mark.parametrize('trust',[None,'0','true','yes','01','1'])
def test_only_exact_env_opt_in_and_no_host_port_prefix_trust(tmp_path,monkeypatch,trust):
    app,client=make_app(tmp_path,monkeypatch,trust)
    enabled=trust=='1'
    assert isinstance(app.wsgi_app,ProxyFix)==enabled
    response=client.get('/_test/proxy',headers=HEADERS,base_url='http://localhost:8000',environ_overrides={'REMOTE_ADDR':'127.0.0.1'})
    assert response.json=={'ip':'198.51.100.23' if enabled else '127.0.0.1',
                          'scheme':'https' if enabled else 'http','host':'localhost:8000','prefix':'','port':'8000'}
    if enabled:
        assert (app.wsgi_app.x_for,app.wsgi_app.x_proto,app.wsgi_app.x_host,app.wsgi_app.x_port,app.wsgi_app.x_prefix)==(1,1,0,0,0)


@pytest.mark.parametrize('trust',[None,'1'])
def test_download_and_block_logs_use_effective_ip(tmp_path,monkeypatch,trust):
    app,client=make_app(tmp_path,monkeypatch,trust)
    expected='198.51.100.23' if trust=='1' else '127.0.0.1'
    valid=client.get('/download?path=ok.txt',headers=HEADERS)
    assert valid.status_code==200 and valid.data==b'PUBLIC'
    assert client.get('/download?path=%252e%252e%252fsecret',headers=HEADERS).status_code==403
    assert client.get('/download?path=missing.txt',headers=HEADERS).status_code==404
    with closing(sqlite3.connect(app.config['DATABASE'])) as db:
        assert db.execute('SELECT client_ip,action,http_status FROM access_logs ORDER BY id').fetchall()==[(expected,'ALLOW',200),(expected,'BLOCK',403),(expected,'MISS',404)]


def csrf(client,headers,path='/login'):
    return re.search(rb'name="csrf_token" value="([^"]+)"',client.get(path,headers=headers).data)[1].decode()


@pytest.mark.parametrize('trust',[None,'1'])
def test_login_throttle_uses_effective_ip_and_successful_login(tmp_path,monkeypatch,trust):
    app,client=make_app(tmp_path,monkeypatch,trust)
    token=csrf(client,HEADERS)
    for _ in range(5):
        assert client.post('/login',headers=HEADERS,data={'csrf_token':token,'password':'wrong-fixture'}).status_code==200
    assert client.post('/login',headers=HEADERS,data={'csrf_token':token,'password':'fixture-password-813'}).status_code==429
    other={**HEADERS,'X-Forwarded-For':'203.0.113.44'}
    response=client.post('/login',headers=other,data={'csrf_token':token,'password':'fixture-password-813'})
    # Account-level throttling now also prevents a source-IP change bypass.
    assert response.status_code==429
    with closing(sqlite3.connect(app.config['DATABASE'])) as db:
        failed=db.execute("SELECT DISTINCT client_ip FROM security_events WHERE event='login_failed'").fetchall()
        assert failed==[('198.51.100.23' if trust=='1' else '127.0.0.1',)]
    if trust=='1':
        from app import account_store
        from tests.auth_support import complete_mfa
        instant=account_store.clock()
        monkeypatch.setattr(account_store,'clock',lambda:instant+301)
        response=client.post('/login',headers=other,data={'csrf_token':token,'password':'fixture-password-813'})
        assert response.status_code==302
        complete_mfa(client,response,headers=other)
        assert client.get('/dashboard',headers=other).status_code==200


def test_one_hop_uses_rightmost_and_missing_header_keeps_peer(tmp_path,monkeypatch):
    _,client=make_app(tmp_path,monkeypatch,'1')
    assert client.get('/_test/proxy',headers={'X-Forwarded-For':'192.0.2.9, 198.51.100.23'}).json['ip']=='198.51.100.23'
    assert client.get('/_test/proxy').json['ip']=='127.0.0.1'
