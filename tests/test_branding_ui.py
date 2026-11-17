"""Product identity only; technical routes and credentials remain unchanged."""
import pytest
from app import create_app


@pytest.mark.parametrize('path,status',[
    ('/',200),('/login',200),('/dashboard',200),('/dashboard/ai-training',200),
    ('/dashboard/ai-evaluation',200),('/account/password',200),
    ('/download?path=../private.txt',403),('/download?path=absent.txt',404)])
def test_brand_identity_on_pages_and_errors(tmp_path,path,status):
    public=tmp_path/'public';public.mkdir()
    app=create_app({'TESTING':True,'FILES_ROOT':public,'DATABASE':tmp_path/'fixture.sqlite3'})
    client=app.test_client()
    with client.session_transaction() as session:
        session['role']='admin';session.permanent=True
        session['_credential_version']=app.extensions['credentials'].version('admin')
    response=client.get(path)
    assert response.status_code==status
    html=response.get_data(as_text=True)
    assert 'CANH GÁC SỐ' in html and 'by HuuVinh' in html
    assert 'CANH GÁC SỐ' in html.split('<title>')[1].split('</title>')[0]
    assert 'FileGuard AI' not in html and 'FILEGUARD AI' not in html
    assert 'FileGuardAI-H07' not in html
    assert 'class="brand-svg"' in html
    svg=client.get('/static/favicon.svg')
    assert svg.status_code==200 and b'<circle' in svg.data


def test_branding_503_uses_shared_shell(tmp_path,monkeypatch):
    import sqlite3
    from app import web
    public=tmp_path/'public';public.mkdir();(public/'ok.txt').write_text('PUBLIC')
    app=create_app({'TESTING':True,'FILES_ROOT':public,'DATABASE':tmp_path/'fixture.sqlite3'})
    def unavailable(*args,**kwargs):raise sqlite3.OperationalError('fixture-only outage')
    monkeypatch.setattr(web,'insert_log',unavailable)
    response=app.test_client().get('/download?path=ok.txt')
    assert response.status_code==503
    html=response.get_data(as_text=True)
    assert 'CANH GÁC SỐ' in html and 'by HuuVinh' in html and 'FileGuard AI' not in html
