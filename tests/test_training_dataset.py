"""Dataset browsing uses bounded SSR, original labels and unchanged admin controls."""
import csv
import io
import re
from pathlib import Path

import pytest
from app import create_app
from app.training_view import read_dataset, dataset_stats, dataset_page

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def browser(tmp_path):
    public = tmp_path/'public'
    public.mkdir()
    app = create_app({'TESTING':True, 'CSRF_ENABLED':True, 'FILES_ROOT':public,
                      'DATABASE':tmp_path/'fixture.sqlite3', 'ADMIN_PASSWORD':'fixture-only'})
    client = app.test_client()
    with client.session_transaction() as s:
        s['role'] = 'admin'
        s['_credential_version'] = client.application.extensions['credentials'].version('admin')
        s.permanent = True
    return app, client


def body_rows(response):
    html = response.get_data(as_text=True)
    table = html.split('id="dataset-table"',1)[1].split('</tbody>',1)[0]
    return re.findall(r'<tr><td>(\d+)</td><td class="path-cell">(.*?)</td>',table)


def test_original_dataset_contract_and_hash():
    path = ROOT/'data/paths_synthetic.csv'
    stats = dataset_stats(read_dataset(path),path)
    assert stats['rows']==10000
    assert stats['label_counts']=={'0':5000,'1':5000}
    assert len(stats['family_counts'])==35
    assert stats['exact_duplicate_excess']==0
    assert stats['canonical_duplicate_excess']==32
    assert stats['sha256']=='2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0'


@pytest.mark.parametrize('query,start,end', [({},1,50),({'page':200},9951,10000),({'page':100,'per_page':100},9901,10000),({'page':999999},9951,10000)])
def test_dataset_first_last_bounded_pages(browser,query,start,end):
    _,client=browser
    response=client.get('/dashboard/ai-training',query_string=query)
    assert response.status_code==200
    rows=body_rows(response)
    assert [int(r[0]) for r in rows]==list(range(start,end+1))
    assert len(rows)<=100
    html=response.get_data(as_text=True)
    assert ('rel="prev"' in html)==(start>1)
    assert ('rel="next"' in html)==(end<10000)


def test_combined_filters_unicode_literal_search_and_page_preservation(browser):
    app,client=browser
    rows=read_dataset(app.config['TRAINING_DATA_PATH'])
    query={'q':'TXT','label':'1','family':'1-00','per_page':50}
    expected=[(i,r) for i,r in enumerate(rows,1) if 'txt' in r['path'].casefold() and r['label']=='1' and r['family']=='1-00']
    page=client.get('/dashboard/ai-training',query_string=query)
    assert [int(r[0]) for r in body_rows(page)]==[i for i,r in expected[:50]]
    if len(expected)>50:
        html=page.get_data(as_text=True)
        assert 'q=TXT' in html and 'family=1-00' in html and 'label=1' in html
        assert [int(r[0]) for r in body_rows(client.get('/dashboard/ai-training',query_string={**query,'page':2}))]==[i for i,r in expected[50:100]]
    assert not body_rows(client.get('/dashboard/ai-training',query_string={'q':'%_no-such-path'}))
    assert dataset_page([{'path':'BÁO CÁO.txt','label':'0','family':'x'}],{'q':'báo cáo'})['total']==1


@pytest.mark.parametrize('query',[{'page':'oops'},{'page':0},{'per_page':10000},{'label':'2'},{'family':'../secret'},{'q':'x'*501}])
def test_invalid_dataset_parameters_rejected(browser,query):
    assert browser[1].get('/dashboard/ai-training',query_string=query).status_code==400


def test_xss_is_escaped_in_dataset_and_search(browser,tmp_path):
    app,client=browser
    payload='<img src=x onerror=alert(1)>'
    path=tmp_path/'xss.csv'
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['path','label','family']);writer.writeheader()
        writer.writerow(dict(path=payload,label='1',family=payload))
    app.config['TRAINING_DATA_PATH']=path
    html=client.get('/dashboard/ai-training',query_string={'q':payload,'family':payload}).get_data(as_text=True)
    assert payload not in html and '&lt;img src=x onerror=alert(1)&gt;' in html
    assert len(body_rows(client.get('/dashboard/ai-training')))==1


def test_full_export_csrf_and_roles(browser):
    _,client=browser
    html=client.get('/dashboard/ai-training?q=nonexistent').get_data(as_text=True)
    token=re.search(r'name="csrf_token" value="([^"]+)"',html)[1]
    assert client.post('/dashboard/ai-training/export',data={'kind':'dataset'}).status_code==403
    response=client.post('/dashboard/ai-training/export',data={'kind':'dataset','csrf_token':token})
    assert response.status_code==200
    rows=list(csv.DictReader(io.StringIO(response.data.decode('utf-8-sig'))))
    assert len(rows)==10000 and {r['label'] for r in rows}=={'0','1'}
    for role,status in [('auditor',403),(None,302)]:
        with client.session_transaction() as session:
            session.clear()
            if role:session['role']=role;session['_credential_version']=client.application.extensions['credentials'].version(role);session.permanent=True
        assert client.get('/dashboard/ai-training').status_code==status
        html=client.get('/login').get_data(as_text=True)
        csrf=re.search(r'name="csrf_token" value="([^"]+)"',html)[1]
        assert client.post('/dashboard/ai-training/export',data={'kind':'dataset','csrf_token':csrf}).status_code==status


def test_training_default_strict_and_explicit_run_do_not_mix(browser):
    import json
    from app.training_view import evaluation_history
    app,client=browser
    history=evaluation_history(app.config['EVALUATION_ROOT'])
    strict=next(r['run'] for r in history if r['experiment_type']=='canonical_grouped_validation')
    html=client.get('/dashboard/ai-training').get_data(as_text=True)
    assert f'data-field="run">{strict}</code>' in html
    for run in [strict,'20261116T172733Z_800c38']:
        data=json.loads((Path(app.config['EVALUATION_ROOT'])/run/'results.json').read_text(encoding='utf-8'))
        html=client.get('/dashboard/ai-training',query_string={'run':run}).get_data(as_text=True)
        assert f'data-field="run">{run}</code>' in html
        assert str(data['logistic_regression']['confusion_matrix']) in html
        assert f'data-field="test_samples">{data["test_samples"]}' in html
    assert client.get('/dashboard/ai-training?run=../../secret').status_code==404
