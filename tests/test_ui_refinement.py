"""Run-specific metadata must not borrow missing values from another run."""
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from test_ui import Page, admin, ui
from app.training_view import evaluation_history

ROOT=Path(__file__).resolve().parents[1]
RUNS=['20261116T153450Z_e5b13b','20261116T172733Z_800c38','20261116T181019Z_dea9ec']


class Facts(Page):
    def __init__(self,html):
        self.values={}
        self.field=None
        super().__init__(html)

    def handle_starttag(self,tag,attrs):
        super().handle_starttag(tag,attrs)
        fields=dict(attrs)
        if 'data-field' in fields:
            self.field=(tag,fields['data-field'])
            self.values[self.field[1]]=''

    def handle_data(self,data):
        super().handle_data(data)
        if self.field:
            self.values[self.field[1]]+=data

    def handle_endtag(self,tag):
        if self.field and tag==self.field[0]:
            self.field=None
        super().handle_endtag(tag)


@pytest.mark.parametrize('run',RUNS)
def test_run_metadata_and_metrics_match_only_selected_artifact(ui,run):
    _,client=ui
    admin(client)
    response=client.get('/dashboard/ai-evaluation',query_string={'run':run})
    assert response.status_code==200
    html=response.get_data(as_text=True)
    page=Facts(html)
    data=json.loads((ROOT/'docs/evaluations'/run/'results.json').read_text(encoding='utf-8'))
    selection=data.get('selection') or {}
    assert page.values['run']==run
    expected={'rows':data['audit']['rows'],'families':len(data['audit']['family_counts']),
              'label_0':data['audit']['label_counts']['0'],'label_1':data['audit']['label_counts']['1'],
              'fit_samples':selection.get('fit_samples') if selection else data['train_samples'],
              'validation_samples':selection.get('validation_samples'),
              'test_samples':data['test_samples'],'refit_samples':data['train_samples'],
              'seed':data['seed'],'threshold':data['threshold'],
              'duplicate_excess_rows':data['audit']['duplicate_excess_rows'],
              'group_overlap':len(data['split']['family_overlap']),
              'path_overlap':len(data['split']['path_overlap']),
              'canonical_overlap':len(data['split']['canonical_overlap']) if 'canonical_overlap' in data['split'] else None,
              'c_v1':None}
    if 'improved_logistic_regression' in data:
        expected['c_v2']=selection['selected_C']
    for key,value in expected.items():
        assert page.values[key].strip()==(str(value) if value is not None else 'Không được cung cấp'),key
    payload=json.loads(page.json_nodes['evaluation-data'])
    assert payload['v1']==data['logistic_regression']
    assert payload['regex']==data['regex']
    assert payload['v2']==data.get('improved_logistic_regression')
    images=[attrs['src'] for tag,attrs in page.tags if tag=='img' and '/ai-evaluation/chart/' in attrs.get('src','')]
    assert len(images)==3
    for image in images:
        assert parse_qs(urlsplit(image).query)['run']==[run]
    selected=[attrs['value'] for tag,attrs in page.tags if tag=='option' and 'selected' in attrs]
    assert selected==[run]
    assert 'Kết quả 100% trên tập dữ liệu kiểm thử không chứng minh hệ thống phát hiện hoặc ngăn chặn 100% các cuộc tấn công Path Traversal trong thực tế.' in html
    assert 'Strict canonical split' in page.values['split_method'] if 'canonical_overlap' in data['split'] else 'Group split' in page.values['split_method']


def test_selector_lists_only_validated_runs_and_classifies_metadata(tmp_path):
    root=tmp_path/'evaluations'
    root.mkdir()
    valid=root/RUNS[2]
    valid.mkdir()
    (valid/'results.json').write_bytes((ROOT/'docs/evaluations'/RUNS[2]/'results.json').read_bytes())
    corrupt=root/'20260101T000000Z_abcdef'
    corrupt.mkdir()
    (corrupt/'results.json').write_text('{}')
    ignored=root/'not-a-run'
    ignored.mkdir()
    (ignored/'results.json').write_bytes((valid/'results.json').read_bytes())
    actual=evaluation_history(root)
    assert len(actual)==1 and actual[0]['run']==RUNS[2]
    assert actual[0]['experiment_type']=='canonical_grouped_validation'


def test_invalid_run_does_not_fall_back_to_latest(ui):
    _,client=ui
    admin(client)
    response=client.get('/dashboard/ai-evaluation',query_string={'run':'../../instance/events.sqlite3'})
    assert response.status_code==200  # existing empty-page contract
    html=response.get_data(as_text=True)
    assert 'Chưa có kết quả đánh giá AI hợp lệ' in html
    assert 'evaluation-data' not in html


def test_password_toggle_cannot_submit_and_login_failure_remains_generic(ui):
    _,client=ui
    page=Page(client.get('/login').get_data(as_text=True))
    toggle=[attrs for tag,attrs in page.tags if tag=='button' and attrs.get('id')=='password-toggle'][0]
    assert toggle['type']=='button' and toggle['aria-controls']=='pw' and toggle['aria-pressed']=='false'
    csrf=[attrs['value'] for tag,attrs in page.tags if tag=='input' and attrs.get('name')=='csrf_token'][0]
    response=client.post('/login',data={'role':'admin','password':'wrong-fixture-password','csrf_token':csrf})
    assert response.status_code==200
    html=response.get_data(as_text=True)
    assert 'Đăng nhập không thành công' in html and 'role="alert"' in html
    assert 'wrong-fixture-password' not in html and 'ui-fixture-secret' not in html and 'Traceback' not in html
    assert 'data-loading-label="Đang xác thực…"' in html
    with client.session_transaction() as session:
        assert not session.get('role')


@pytest.mark.parametrize('role',[None,'auditor'])
def test_run_selection_cannot_bypass_admin_authorization(ui,role):
    _,client=ui
    if role:
        with client.session_transaction() as session:
            session['role']=role
            session['_credential_version']=client.application.extensions['credentials'].version(role)
            session.permanent=True
    response=client.get('/dashboard/ai-evaluation',query_string={'run':RUNS[2]})
    assert response.status_code==(403 if role else 302)
    assert 'data-field="run"' not in response.get_data(as_text=True)
