"""Presentation contracts: actual data, escaping and unchanged native forms."""
from html.parser import HTMLParser
import json
from pathlib import Path

import pytest
from app import create_app, database
from app.passwords import password_hash
from tests.auth_support import login

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.json_nodes = {}
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        self.tags.append((tag, fields))
        if tag == 'script' and fields.get('type') == 'application/json':
            self.current = fields.get('id')
            self.json_nodes[self.current] = ''

    def handle_data(self, data):
        if self.current:
            self.json_nodes[self.current] += data

    def handle_endtag(self, tag):
        if tag == 'script':
            self.current = None


@pytest.fixture
def ui(tmp_path):
    public = tmp_path/'public'
    public.mkdir()
    (public/'báo cáo.txt').write_text('PUBLIC-UNICODE', encoding='utf-8')
    data = tmp_path/'annotated.csv'
    data.write_text('path,label,family\nok.txt,0,normal\n../secret,1,parent\n', encoding='utf-8')
    app = create_app({'TESTING':True, 'CSRF_ENABLED':True, 'FILES_ROOT':public,
                      'DATABASE':tmp_path/'logs.sqlite3', 'TRAINING_DATA_PATH':data,
                      'ADMIN_PASSWORD':'ui-fixture-secret','AUDITOR_PASSWORD_HASH':password_hash('auditor-fixture-only')})
    return app, app.test_client()


def admin(client):
    login(client,password='ui-fixture-secret')


def test_public_search_and_download_still_use_backend(ui):
    _, client = ui
    html = client.get('/').get_data(as_text=True)
    page = Page(html)
    assert 'data-bs-theme="dark"' in html and 'báo cáo.txt' in html
    assert ('form', {'method':'get', 'action':'/download', 'class':'download-form', 'data-download-form':None}) in page.tags
    assert any(tag=='input' and attrs.get('name')=='path' for tag,attrs in page.tags)
    assert any(tag=='a' and attrs.get('href','').startswith('/download?path=') for tag,attrs in page.tags)
    assert 'id="file-search"' in html and 'id="file-type"' in html
    assert 'id="sidebar"' not in html and 'chart-data' not in html
    assert client.get('/download',query_string={'path':'báo cáo.txt'}).data == b'PUBLIC-UNICODE'
    assert client.get('/download?path=%252e%252e%252fsecret').status_code == 403


def test_dashboard_charts_match_filtered_actual_rows_and_escape(ui):
    app, client = ui
    admin(client)
    payload = '</script><img src=x onerror=alert(1)>'
    database.insert_log(app.config['DATABASE'],'127.0.0.1',payload,.9,'suspicious','BLOCK',403,'fixture',1)
    database.insert_log(app.config['DATABASE'],'127.0.0.1','missing.txt',.2,'benign','MISS',404,'fixture',1)
    html = client.get('/dashboard?action=BLOCK').get_data(as_text=True)
    page = Page(html)
    assert json.loads(page.json_nodes['chart-data']) == {'allowed':0,'blocked':1,'missed':0}
    assert len(json.loads(page.json_nodes['trend-data'])) == 1
    assert payload not in html and '&lt;/script&gt;' in html
    assert 'status block' in html and 'id="sidebar"' in html
    assert 'không phải toàn bộ lịch sử' in html
    export = [attrs for tag,attrs in page.tags if tag=='form' and attrs.get('action')=='/dashboard/logs/export']
    assert len(export)==1 and export[0]['method']=='post'
    assert any(tag=='input' and attrs.get('name')=='csrf_token' and attrs.get('value') for tag,attrs in page.tags)
    assert 'name="action" value="BLOCK"' in html


def test_empty_dashboard_has_no_invented_trend(ui):
    _, client = ui
    admin(client)
    html = client.get('/dashboard').get_data(as_text=True)
    page = Page(html)
    assert json.loads(page.json_nodes['trend-data']) == []
    assert json.loads(page.json_nodes['chart-data']) == dict(allowed=0,blocked=0,missed=0)
    assert 'Chưa có nhật ký phù hợp' in html


@pytest.mark.parametrize('path', ['/dashboard','/dashboard/ai-evaluation','/dashboard/ai-training'])
def test_management_ui_is_not_exposed_to_guest_or_auditor(ui,path):
    _, client = ui
    assert client.get(path).status_code == 302
    login(client,password='auditor-fixture-only',role='auditor')
    assert client.get(path).status_code == 403


def test_training_label_chart_uses_csv_not_demo_numbers(ui):
    _, client = ui
    admin(client)
    html = client.get('/dashboard/ai-training').get_data(as_text=True)
    page = Page(html)
    assert json.loads(page.json_nodes['training-label-data']) == {'0':1,'1':1}
    assert 'view_max_parent_components' in html and 'entropy' in html
    assert '18 đặc trưng' in html and '30 đặc trưng' in html
    assert 'Đang triển khai' in html and 'Thử nghiệm' in html
    forms = [attrs for tag,attrs in page.tags if tag=='form']
    assert all(attrs.get('action') in ['/logout','/dashboard/ai-training/export','/dashboard/ai-training'] for attrs in forms)
    browsing = [attrs for attrs in forms if attrs.get('action')=='/dashboard/ai-training']
    assert len(browsing)==2 and all(attrs.get('method')=='get' for attrs in browsing)


def test_evaluation_cards_and_json_match_saved_artifact(ui):
    _, client = ui
    admin(client)
    html = client.get('/dashboard/ai-evaluation').get_data(as_text=True)
    page = Page(html)
    data = json.loads(page.json_nodes['evaluation-data'])
    root = ROOT/'docs/evaluations'
    run = json.loads((root/'latest.json').read_text())['run']
    actual = json.loads((root/run/'results.json').read_text(encoding='utf-8'))
    assert data['v1'] == actual['logistic_regression']
    assert data['v2'] == actual['improved_logistic_regression']
    assert data['regex'] == actual['regex']
    assert 'không phải độ chính xác 100% trên dữ liệu thực' in html


def test_login_csrf_and_error_state_are_preserved(ui):
    _, client = ui
    html = client.get('/login').get_data(as_text=True)
    page = Page(html)
    assert any(tag=='input' and attrs.get('name')=='csrf_token' and attrs.get('value') for tag,attrs in page.tags)
    assert any(tag=='input' and attrs.get('type')=='password' and attrs.get('autocomplete')=='current-password' for tag,attrs in page.tags)
    assert client.post('/login',data={'role':'admin','password':'ui-fixture-secret'}).status_code == 403
    response = client.get('/download?path=missing.txt')
    assert response.status_code==404 and 'Không tìm thấy tệp' in response.get_data(as_text=True)


@pytest.mark.parametrize('route',['/dashboard/ai-evaluation','/dashboard/ai-training'])
def test_all_styles_and_scripts_are_local_and_available(ui,route):
    _,client=ui
    admin(client)
    page=Page(client.get(route).get_data(as_text=True))
    sources=[attrs.get('src') for tag,attrs in page.tags if tag=='script' and attrs.get('src')]
    sources += [attrs['href'] for tag,attrs in page.tags if tag=='link' and attrs.get('rel')=='stylesheet']
    assert sources and all(src.startswith('/static/') for src in sources)
    for src in sources:
        assert client.get(src).status_code==200,src
