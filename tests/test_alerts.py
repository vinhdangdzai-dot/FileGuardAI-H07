"""Immediate alerts, grouping, workflow and independence from ML/API outcomes."""
import sqlite3
from contextlib import closing
from unittest.mock import Mock
import pytest
from app import create_app
from tests.auth_support import login
from app.ai_explanations import ProviderError
from app.database import insert_log,init_db
from tests.test_ai_explanations import app_fixture,Provider,wait,token


def query(app,sql):
    with closing(sqlite3.connect(app.config['DATABASE'])) as db:return db.execute(sql).fetchall()


def test_immediate_offline_and_duplicate_grouping(tmp_path,monkeypatch):
    monkeypatch.setattr('joblib.load',Mock(return_value=Mock(predict_proba=lambda x:[[.99,.01]])))
    app,client=app_fixture(tmp_path)
    assert client.get('/download?path=ok.txt').status_code==200
    assert client.get('/download?path=missing.txt').status_code==404
    assert query(app,'SELECT COUNT(*) FROM alerts')==[(0,)]
    for _ in range(3):assert client.get('/download?path=../secret').status_code==403
    assert query(app,'SELECT priority,state,occurrences FROM alerts')==[('high','new',3)]
    assert query(app,'SELECT COUNT(*) FROM alert_events')==[(3,)]
    assert query(app,'SELECT COUNT(*) FROM access_logs')==[(5,)]
    assert client.get('/dashboard/events/3').status_code==200
    feed=client.get('/dashboard/alerts/feed?after=0').json
    assert len(feed['items'])==1 and feed['items'][0]['occurrences']==3
    assert '127.0.0.1' not in str(feed) and 'secret' not in str(feed)
    assert not client.get('/dashboard/alerts/feed?after='+str(feed['cursor'])).json['items']


@pytest.mark.parametrize('probability,path,status,priority',[(.99,'ok.txt',200,'medium'),(.01,'../secret',403,'high')])
def test_ml_false_positive_and_false_negative_do_not_change_policy(tmp_path,monkeypatch,probability,path,status,priority):
    model=tmp_path/'fixture-model';model.write_bytes(b'not-a-real-model')
    monkeypatch.setattr('joblib.load',Mock(return_value=Mock(predict_proba=lambda x:[[1-probability,probability]])))
    files=tmp_path/'files';files.mkdir();(files/'ok.txt').write_bytes(b'PUBLIC')
    app=create_app({'TESTING':True,'DATABASE':tmp_path/'db.sqlite3','FILES_ROOT':files,'MODEL_PATH':model})
    response=app.test_client().get('/download',query_string={'path':path})
    assert response.status_code==status
    assert query(app,'SELECT priority FROM alerts')==[(priority,)]
    if status==200:assert response.data==b'PUBLIC'


@pytest.mark.parametrize('error',['network','timeout','quota','authentication','invalid_response'])
def test_gemini_failure_does_not_delay_or_remove_alert(tmp_path,error):
    app,client=app_fixture(tmp_path,Provider(ProviderError(error)))
    service=app.extensions['ai_explanations'];service.set_enabled(True)
    try:
        assert client.get('/download?path=../secret').status_code==403
        assert query(app,'SELECT priority FROM alerts')==[('high',)]
        wait(service)
        assert service.snapshot()['rows'][0]['status']==error
        assert query(app,'SELECT action,http_status FROM access_logs')==[('BLOCK',403)]
    finally:service.close()


def test_workflow_filters_settings_csrf_and_audit(tmp_path):
    app,client=app_fixture(tmp_path)
    client.get('/download?path=../secret')
    csrf=token(client)
    assert client.post('/dashboard/alerts/1/state',data={'state':'seen'}).status_code==403
    for state in ['seen','resolved']:
        assert client.post('/dashboard/alerts/1/state',data={'state':state,'csrf_token':csrf}).status_code==302
        assert query(app,'SELECT state FROM alerts')==[(state,)]
    assert client.get('/dashboard/alerts?state=new').status_code==200
    assert client.get('/dashboard/alerts?state=invalid').status_code==400
    assert client.get('/dashboard/alerts?page='+str(2**80)).status_code==400
    assert client.get('/dashboard/alerts/feed?after=-1').status_code==400
    assert client.post('/dashboard/alerts/1/state',data={'state':'bad','csrf_token':csrf}).status_code==400
    assert client.post('/dashboard/alerts/settings',data={'enabled':'0','csrf_token':csrf}).status_code==302
    client.get('/download?path=../secret')
    assert query(app,'SELECT COUNT(*) FROM alerts')==[(2,)]  # resolved group not reopened automatically
    assert client.get('/dashboard/alerts/feed?after=0').json['items']==[]
    assert query(app,'SELECT COUNT(*) FROM alert_events')==[(2,)]  # notifications off still records
    assert any('alert:1:state:resolved' in row for row in query(app,'SELECT event FROM security_events'))
    with client.session_transaction() as s:s.clear()
    assert client.get('/dashboard/alerts/feed').status_code==302
    login(client,password='auditor-fixture-only',role='auditor')
    assert client.get('/dashboard/alerts').status_code==403
    assert client.get('/dashboard/alerts/feed').status_code==403
    assert client.post('/dashboard/alerts/settings',data={'enabled':'1','csrf_token':csrf}).status_code==403


def test_window_distinct_sources_and_pagination(tmp_path,monkeypatch):
    from app import alerts
    app,client=app_fixture(tmp_path)
    monkeypatch.setattr(alerts,'clock',lambda:1000)
    client.get('/download?path=../secret')
    monkeypatch.setattr(alerts,'clock',lambda:1061)
    client.get('/download?path=../secret')
    assert query(app,'SELECT COUNT(*) FROM alerts')==[(2,)]
    for n in range(51):insert_log(app.config['DATABASE'],'192.0.2.'+str(n),'..',.9,'suspicious','BLOCK',403,'fixture',1)
    assert client.get('/dashboard/alerts?page=1').data.count(b'name="state"')==51  # filter + 50 forms
    assert client.get('/dashboard/alerts?page=2').data.count(b'name="state"')==4
    first=client.get('/dashboard/alerts/feed?after=0').json
    assert len(first['items'])==20
    second=client.get('/dashboard/alerts/feed?after='+str(first['cursor'])).json
    assert not {r['id'] for r in first['items']} & {r['id'] for r in second['items']}


def test_upgrade_preserves_old_logs_and_init_is_idempotent(tmp_path):
    app,client=app_fixture(tmp_path)
    client.get('/download?path=ok.txt')
    before=query(app,'SELECT * FROM access_logs')
    init_db(app.config['DATABASE']);init_db(app.config['DATABASE'])
    assert query(app,'SELECT * FROM access_logs')==before
