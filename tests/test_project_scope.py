"""H07 pillars: detection, independent prevention, monitoring and download RBAC."""
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sqlite3

import pytest

from app import create_app, documents, web
from app.account_store import register
from app.database import connect, init_db, insert_log, ips_statistics
from app.passwords import password_hash
from tests.auth_support import login

PASSWORD='scope-fixture-password'


@pytest.fixture
def lab(tmp_path):
    public=tmp_path/'shared';public.mkdir()
    (public/'public.txt').write_bytes(b'PUBLIC-DOCUMENT')
    restricted=public/'restricted';restricted.mkdir()
    (restricted/'internal.txt').write_bytes(b'RESTRICTED-SENTINEL')
    (restricted/'báo cáo.txt').write_bytes(b'PRIVATE-UNICODE')
    (tmp_path/'outside.txt').write_bytes(b'OUTSIDE-SENTINEL')
    cfg={'TESTING':True,'CSRF_ENABLED':True,'SECRET_KEY':'scope-tests-only',
         'DATABASE':tmp_path/'events.sqlite3','FILES_ROOT':public,'MODEL_PATH':tmp_path/'missing-model',
         'ADMIN_PASSWORD':PASSWORD,'AUDITOR_PASSWORD_HASH':password_hash(PASSWORD)}
    app=create_app(cfg)
    register(app.config['DATABASE'],'reader','reader@example.test','Reader',PASSWORD,'local')
    yield app,app.test_client(),cfg
    app.extensions['recovery_mail'].close();app.extensions['ai_explanations'].close()


def query(app,sql):
    with closing(connect(app.config['DATABASE'])) as db:return [tuple(r) for r in db.execute(sql).fetchall()]


def test_guest_public_home_and_public_download_hide_restricted_names(lab):
    app,client,_=lab
    page=client.get('/')
    assert page.status_code==200 and b'public.txt' in page.data
    assert b'restricted/internal.txt' not in page.data and 'báo cáo.txt'.encode() not in page.data
    assert 'Xây dựng hệ thống phát hiện và ngăn chặn tấn công Path Traversal'.encode() in page.data
    assert client.get('/download?path=public.txt').data==b'PUBLIC-DOCUMENT'
    assert client.get('/admin').status_code==302
    assert client.get('/admin/documents').status_code==302


def test_guest_restricted_and_nonexistent_restricted_are_same_denial(lab):
    app,client,_=lab
    one=client.get('/download?path=restricted/internal.txt')
    two=client.get('/download?path=restricted/not-present.txt')
    assert one.status_code==two.status_code==403 and one.data==two.data
    assert b'RESTRICTED-SENTINEL' not in one.data and b'internal.txt' not in one.data
    assert query(app,'SELECT action,http_status FROM access_logs ORDER BY id')==[('BLOCK',403),('BLOCK',403)]
    assert query(app,'SELECT path_outcome,visibility,access_outcome FROM download_context')==[('permitted','authenticated','login_required')]*2
    assert query(app,'SELECT COUNT(*) FROM alerts')[0][0]==0
    assert client.get('/download?path=not-present.txt').status_code==404


@pytest.mark.parametrize('role',['user','auditor','admin'])
def test_fully_authenticated_roles_can_read_restricted_documents(lab,role):
    app,client,_=lab
    login(client,password=PASSWORD,role=role,identifier='reader' if role=='user' else '')
    assert client.get('/download?path=restricted/internal.txt').data==b'RESTRICTED-SENTINEL'
    assert client.get('/download',query_string={'path':'restricted/báo cáo.txt'}).data==b'PRIVATE-UNICODE'
    assert b'restricted/internal.txt' in client.get('/').data
    assert client.get('/download?path=restricted/not-present.txt').status_code==404
    assert client.get('/admin').status_code==(200 if role=='admin' else 403)
    assert client.get('/admin/documents').status_code==(200 if role=='admin' else 403)


def test_admin_first_factor_does_not_grant_restricted_access(lab):
    app,client,_=lab
    import re
    token=re.search(rb'name="csrf_token" value="([^"]+)"',client.get('/login').data)[1].decode()
    assert client.post('/login',data={'csrf_token':token,'password':PASSWORD}).location.endswith('/login/mfa')
    assert client.get('/admin').status_code==302
    assert client.get('/download?path=restricted/internal.txt').status_code==403
    with client.session_transaction() as state:assert 'role' not in state


@pytest.mark.parametrize('path',['../outside.txt','restricted/../../outside.txt','..\\outside.txt',
    '/etc/passwd','C:/Windows/win.ini','%2e%2e%2foutside.txt','%252e%252e%252foutside.txt'])
def test_attack_cases_remain_path_policy_blocks_before_login_gate(lab,path):
    app,client,_=lab
    response=client.get('/download',query_string={'path':path})
    assert response.status_code==403 and b'OUTSIDE-SENTINEL' not in response.data
    assert query(app,'SELECT path_outcome,access_outcome FROM download_context')==[('rejected','not_applicable')]
    assert query(app,'SELECT rule,priority FROM alerts')==[('policy_block','high')]


def test_opened_windows_path_is_reclassified_before_streaming(lab,monkeypatch):
    app,client,cfg=lab
    handles=[];original=web.open_authorized
    def tracked(*args):
        value=original(*args);handles.append(value);return value
    monkeypatch.setattr(web,'open_authorized',tracked)
    monkeypatch.setattr(documents,'os',SimpleNamespace(name='nt'))
    monkeypatch.setattr(documents,'_windows_opened_path',lambda f:cfg['FILES_ROOT']/'restricted/internal.txt')
    response=client.get('/download?path=public.txt')
    assert response.status_code==403 and b'PUBLIC-DOCUMENT' not in response.data
    assert handles and all(f.closed for f in handles)


def test_reserved_directory_case_variants_are_not_public(lab):
    app,client,cfg=lab
    directory=cfg['FILES_ROOT']/'RESTRICTED';directory.mkdir(exist_ok=True)
    (directory/'case.txt').write_bytes(b'PRIVATE-CASE')
    assert client.get('/download?path=RESTRICTED/case.txt').status_code==403
    assert b'case.txt' not in client.get('/').data


def test_application_ips_is_admin_only_and_uses_persisted_sqlite_data(lab):
    app,client,_=lab
    assert client.get('/admin/ips').status_code==302
    client.get('/download?path=public.txt')
    client.get('/download',query_string={'path':'../outside.txt'})
    client.get('/download?path=missing.txt')
    data=ips_statistics(app.config['DATABASE'])
    assert data['totals']['total']==3
    assert data['totals']['allowed']==data['totals']['blocked']==data['totals']['missing']==1
    assert data['timings']['samples']==3
    assert data['timings']['total_avg_ms']>=data['timings']['ids_avg_ms']
    assert data['logs'][0]['requested_path']=='../outside.txt'
    login(client,password=PASSWORD)
    page=client.get('/admin/ips')
    assert page.status_code==200 and b'Application IPS' in page.data and b'#2' in page.data


def test_ips_blocks_when_ids_is_unavailable_and_records_separate_timings(lab):
    app,client,_=lab
    response=client.get('/download',query_string={'path':'../outside.txt'})
    assert response.status_code==403 and b'OUTSIDE-SENTINEL' not in response.data
    assert query(app,'SELECT ml_score,ml_label,action,http_status FROM access_logs')==[(None,'unavailable','BLOCK',403)]
    timing=query(app,'SELECT ids_ms,ips_ms,total_ms FROM processing_timings')[0]
    assert timing[0]>=0 and timing[1]>=0 and timing[2]>=timing[0]+timing[1]


def test_processing_timing_is_append_only_and_validated(lab):
    app,client,_=lab
    client.get('/download?path=public.txt')
    with pytest.raises(sqlite3.IntegrityError):
        with closing(connect(app.config['DATABASE'])) as db,db:
            db.execute('UPDATE processing_timings SET ips_ms=0 WHERE event_id=1')
    with pytest.raises(ValueError):
        insert_log(app.config['DATABASE'],'127.0.0.1','x',.1,'benign','ALLOW',200,'ok',1,
                   context={'path_outcome':'permitted','visibility':'public','access_outcome':'allowed'},
                   timing={'ids_ms':1,'ips_ms':1,'total_ms':1})


@pytest.mark.parametrize('score,path,status,rule',[(.99,'public.txt',200,'ml_suspicious'),
    (.01,'../outside.txt',403,'policy_block'),(.99,'missing.txt',404,'ml_suspicious'),
    (.99,'restricted/internal.txt',403,'ml_suspicious')])
def test_ml_errors_never_decide_access_and_auth_denial_is_not_path_alert(lab,monkeypatch,score,path,status,rule):
    _,_,cfg=lab
    model=Path(cfg['DATABASE']).parent/'fixture-model';model.write_bytes(b'LOCAL-MOCK')
    monkeypatch.setattr('joblib.load',Mock(return_value=Mock(predict_proba=lambda rows:[[1-score,score]])))
    app=create_app({**cfg,'MODEL_PATH':model});client=app.test_client()
    submit=Mock();app.extensions['ai_explanations'].submit=submit
    response=client.get('/download',query_string={'path':path})
    assert response.status_code==status
    assert query(app,'SELECT ml_score FROM access_logs ORDER BY id DESC LIMIT 1')[0][0]==score
    assert query(app,'SELECT rule FROM alerts ORDER BY id DESC LIMIT 1')[0][0]==rule
    if path.startswith('restricted/'):
        assert not submit.called
    app.extensions['recovery_mail'].close();app.extensions['ai_explanations'].close()


def test_dedup_retains_all_event_ids_and_admin_detail_works_offline(lab):
    app,client,_=lab
    for _ in range(3):assert client.get('/download?path=../outside.txt').status_code==403
    assert query(app,'SELECT occurrences FROM alerts')==[(3,)]
    ids=[r[0] for r in query(app,'SELECT id FROM access_logs')]
    assert [r[0] for r in query(app,'SELECT event_id FROM alert_events ORDER BY event_id')]==ids
    assert client.get('/dashboard/events/1').status_code==302
    login(client,password=PASSWORD)
    page=client.get('/dashboard/events/1')
    assert page.status_code==200 and b'../outside.txt' in page.data
    assert 'Khuyến nghị cục bộ theo quy tắc'.encode() in page.data
    assert 'Gemini chỉ giải thích'.encode() in page.data
    assert client.get('/admin').status_code==200


def test_context_migration_is_additive_and_append_only(lab):
    app,client,cfg=lab
    client.get('/download?path=public.txt')
    original=query(app,'SELECT * FROM access_logs')
    init_db(cfg['DATABASE']);init_db(cfg['DATABASE'])
    assert query(app,'SELECT * FROM access_logs')==original
    with closing(connect(cfg['DATABASE'])) as db:
        with pytest.raises(sqlite3.IntegrityError,match='append-only'):db.execute('DELETE FROM download_context')


def test_auth_log_metadata_failure_withholds_restricted_content(lab,monkeypatch):
    app,client,_=lab
    login(client,password=PASSWORD,identifier='reader')
    monkeypatch.setattr(web,'insert_log',Mock(side_effect=sqlite3.OperationalError('fixture unavailable')))
    response=client.get('/download?path=restricted/internal.txt')
    assert response.status_code==503 and b'RESTRICTED-SENTINEL' not in response.data
