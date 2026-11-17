"""Presentation preference does not alter authentication form contracts."""
from pathlib import Path
import pytest
from app import create_app

@pytest.mark.parametrize('route',['/','/login','/dashboard','/dashboard/ai-training','/dashboard/ai-evaluation','/download?path=absent.txt'])
def test_shared_text_controls_and_early_loader(tmp_path,route):
    public=tmp_path/'public';public.mkdir()
    app=create_app({'TESTING':True,'FILES_ROOT':public,'DATABASE':tmp_path/'test.sqlite3','ADMIN_PASSWORD':'fixture-only'})
    client=app.test_client()
    with client.session_transaction() as session:session['role']='admin';session.permanent=True
    response=client.get(route)
    html=response.get_data(as_text=True)
    assert html.index('text-size.js')<html.index('style.css')
    assert html.count('id="text-size-controls"')==1
    for mode in ['small','medium','large']:
        assert f'type="button" data-text-size="{mode}"' in html
    assert client.get('/static/text-size.js').status_code==200


def test_readable_root_and_local_preference_contract():
    root=Path(__file__).resolve().parents[1]
    css=(root/'app/static/style.css').read_text(encoding='utf-8')
    js=(root/'app/static/text-size.js').read_text(encoding='utf-8')
    assert '--base-font-size:18px' in css and 'font-size:var(--base-font-size)' in css
    assert 'small:16, medium:18, large:20' in js
    assert 'fg-text-size' in js and "catch (_)" in js
