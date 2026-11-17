"""Shared theme controls must not alter forms, routes or protected data."""
import pytest
from test_ui import Page, admin, ui


@pytest.mark.parametrize('path,status',[('/',200),('/login',200),('/download?path=missing.txt',404),('/download?path=../secret',403)])
def test_public_and_error_pages_share_theme_controls(ui,path,status):
    _,client=ui
    response=client.get(path)
    assert response.status_code==status
    html=response.get_data(as_text=True)
    page=Page(html)
    assert 'id="theme-picker"' in html
    choices=[attrs for tag,attrs in page.tags if tag=='button' and 'data-theme-choice' in attrs]
    assert [choice['data-theme-choice'] for choice in choices]==['light','dark','system']
    assert all(choice['type']=='button' and choice['role']=='menuitemradio' for choice in choices)
    assert 'id="sidebar"' not in html and 'evaluation-data' not in html


@pytest.mark.parametrize('path',['/dashboard','/dashboard/ai-evaluation','/dashboard/ai-training'])
def test_admin_pages_use_same_early_theme_loader(ui,path):
    _,client=ui
    admin(client)
    html=client.get(path).get_data(as_text=True)
    page=Page(html)
    scripts=[attrs for tag,attrs in page.tags if tag=='script' and attrs.get('src')=='/static/theme.js']
    assert len(scripts)==1 and 'defer' not in scripts[0] and 'async' not in scripts[0]
    assert html.index('/static/theme.js')<html.index('/static/vendor/bootstrap.min.css')<html.index('/static/style.css')
    assert client.get('/static/theme.js').status_code==200
    assert html.count('id="theme-toggle"')==1
    assert 'name="csrf_token"' in html


def test_theme_controls_do_not_become_authentication_form_fields(ui):
    _,client=ui
    page=Page(client.get('/login').get_data(as_text=True))
    # Menu controls have no name and cannot submit role/password/CSRF changes.
    controls=[attrs for tag,attrs in page.tags if tag=='button' and (attrs.get('id')=='theme-toggle' or 'data-theme-choice' in attrs)]
    assert len(controls)==4 and all('name' not in attrs and attrs['type']=='button' for attrs in controls)
    assert any(tag=='input' and attrs.get('name')=='password' and attrs['type']=='password' for tag,attrs in page.tags)
