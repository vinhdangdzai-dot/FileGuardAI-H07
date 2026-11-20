import json
import os
from pathlib import Path
import sqlite3
import subprocess
from unittest.mock import Mock

import pytest

from app import create_app
from app import database, security
from ml.generate_dataset import write_dataset, create_rows
from ml.train_model import train, split_by_family

ROOT = Path(__file__).resolve().parents[1]
COMPARISON = ROOT / 'docs/evaluations/20261116T154448Z_7a27a7/results.json'


def make_app(tmp_path, **config):
    base = tmp_path / 'files'
    base.mkdir(exist_ok=True)
    (base / 'ok.txt').write_bytes(b'PUBLIC')
    return create_app(dict(TESTING=True, FILES_ROOT=base, DATABASE=tmp_path / 'logs.sqlite3',
                           MODEL_PATH=tmp_path / 'missing.joblib', ADMIN_PASSWORD='review-password', **config))


@pytest.mark.parametrize('name', ['CONIN$', 'CONOUT$.txt', 'COM¹', 'lpt².txt', 'COM³.log', 'CON .txt'])
def test_windows_device_names_rejected_before_open(tmp_path, name):
    app = make_app(tmp_path)
    with app.test_client().get('/download', query_string={'path': name}) as response:
        assert response.status_code == 403


@pytest.mark.parametrize('probability', [float('nan'), 2, 'raise'])
def test_advisory_failure_does_not_decide_access(tmp_path, monkeypatch, probability):
    model_file = tmp_path / 'model.joblib'
    model_file.write_bytes(b'not-deserialized-in-this-test')
    model = Mock()
    if probability == 'raise':
        model.predict_proba.side_effect = RuntimeError('advisory model unavailable')
    else:
        model.predict_proba.return_value = [[0.1, probability]]
    monkeypatch.setattr('joblib.load', lambda path: model)
    # Use a subfolder so the helper's default MODEL_PATH remains absent.
    base = tmp_path / 'files'
    base.mkdir()
    (base / 'ok.txt').write_bytes(b'PUBLIC')
    app = create_app({'TESTING': True, 'FILES_ROOT': base, 'DATABASE': tmp_path / 'db.sqlite3',
                      'MODEL_PATH': model_file})
    c = app.test_client()
    for name, expected in [('ok.txt', 200), ('missing.txt', 404), ('../secret.txt', 403)]:
        with c.get('/download', query_string={'path': name}) as response:
            assert response.status_code == expected
        event = database.recent_logs(app.config['DATABASE'])[0]
        assert event['ml_label'] == 'error' and event['ml_score'] is None
    model.reset_mock()
    response = c.get('/download', query_string={'path': 'x' * 5000})
    assert response.status_code == 403
    model.predict_proba.assert_not_called()
    assert database.recent_logs(app.config['DATABASE'])[0]['ml_label'] == 'skipped'


def test_corrupt_model_and_duplicate_parameters(tmp_path):
    model = tmp_path / 'broken.joblib'
    model.write_bytes(b'corrupt artifact')
    base = tmp_path / 'files'
    base.mkdir()
    (base / 'ok.txt').write_bytes(b'PUBLIC')
    app = create_app({'TESTING': True, 'FILES_ROOT': base, 'DATABASE': tmp_path / 'db.sqlite3',
                      'MODEL_PATH': model})
    c = app.test_client()
    assert c.get('/health').json['model_status'] == 'error'
    with c.get('/download?path=ok.txt') as r:
        assert r.status_code == 200 and r.data == b'PUBLIC'
    assert c.get('/download?path=ok.txt&path=../secret.txt').status_code == 403
    assert c.get('/download').status_code == 403


def test_database_operations_close_connections(tmp_path, monkeypatch):
    opened = []
    original = database.connect

    def tracked(path):
        con = original(path)
        opened.append(con)
        return con

    monkeypatch.setattr(database, 'connect', tracked)
    db = tmp_path / 'db.sqlite3'
    database.init_db(db)
    database.insert_log(db, '127.0.0.1', "x' OR 1=1 --", .7, 'suspicious', 'MISS', 404, 'missing', .5)
    assert database.recent_logs(db)[0]['requested_path'] == "x' OR 1=1 --"
    assert database.summary(db)['total'] == 1
    for con in opened:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            con.execute('SELECT 1')
    # Windows must allow rename immediately without waiting for GC.
    db.rename(tmp_path / 'renamed.sqlite3')


def test_listing_never_descends_into_windows_junction(tmp_path, monkeypatch):
    if os.name != 'nt':
        pytest.skip('Windows junction check')
    base = tmp_path / 'files'
    outside = tmp_path / 'outside'
    base.mkdir()
    outside.mkdir()
    (outside / 'secret.txt').write_bytes(b'SECRET')
    (base / 'ok.txt').write_bytes(b'PUBLIC')
    junction = base / 'junction'
    created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(outside)], capture_output=True)
    if created.returncode:
        pytest.skip('Cannot create Windows junction')
    original = security.os.scandir

    def guarded(path):
        assert Path(path) != junction, 'Listing entered a forbidden junction'
        return original(path)

    try:
        monkeypatch.setattr(security.os, 'scandir', guarded)
        assert security.list_allowed_files(base) == ['ok.txt']
    finally:
        assert junction.parent.resolve() == base.resolve()
        junction.rmdir()


@pytest.mark.parametrize('mutation', ['audit', 'matrix', 'metric', 'timing', 'external', 'huge_number'])
def test_malformed_nested_artifact_falls_back_without_500(tmp_path, mutation):
    data = json.loads(COMPARISON.read_text(encoding='utf-8'))
    if mutation == 'audit':
        data['audit'] = None
    elif mutation == 'matrix':
        data['logistic_regression']['confusion_matrix'] = [[1]]
    elif mutation == 'metric':
        data['logistic_regression']['accuracy'] = float('nan')
    elif mutation == 'timing':
        data['timing']['lr_end_to_end']['median_batch_ms'] = -1
    elif mutation == 'external':
        del data['datasets']['external_public']
    else:
        data['selection']['selected_C'] = 10 ** 1000
    root = tmp_path / 'evaluations'
    run = root / '20261116T000000Z_aaaaaa'
    run.mkdir(parents=True)
    (run / 'results.json').write_text(json.dumps(data), encoding='utf-8')
    (root / 'latest.json').write_text(json.dumps({'run': run.name}))
    c = make_app(tmp_path, EVALUATION_ROOT=root).test_client()
    c.post('/login', data={'password': 'review-password'})
    from tests.auth_support import complete_mfa
    complete_mfa(c)
    response = c.get('/dashboard/ai-evaluation')
    assert response.status_code == 200 and 'Chưa có kết quả'.encode() in response.data
    assert c.get('/dashboard').status_code == 200


def test_chart_stays_on_archived_run_when_latest_changes(tmp_path):
    root = tmp_path / 'evaluations'
    data = COMPARISON.read_bytes()
    for name in ('20261116T000000Z_aaaaaa', '20261116T000001Z_bbbbbb'):
        run = root / name
        run.mkdir(parents=True)
        (run / 'results.json').write_bytes(data)
        (run / 'metrics.png').write_bytes(name.encode())
    first = '20261116T000000Z_aaaaaa'
    second = '20261116T000001Z_bbbbbb'
    (root / 'latest.json').write_text(json.dumps({'run': first}))
    c = make_app(tmp_path, EVALUATION_ROOT=root).test_client()
    c.post('/login', data={'password': 'review-password'})
    from tests.auth_support import complete_mfa
    complete_mfa(c)
    assert first.encode() in c.get('/dashboard/ai-evaluation').data
    (root / 'latest.json').write_text(json.dumps({'run': second}))
    with c.get('/dashboard/ai-evaluation/chart/metrics.png', query_string={'run': first}) as response:
        assert response.status_code == 200 and response.data == first.encode()


def test_training_preserves_prior_outputs_and_dataset(tmp_path):
    csv = tmp_path / 'dataset.csv'
    write_dataset(csv, n=100)
    before = csv.read_bytes()
    with pytest.raises(FileExistsError):
        write_dataset(csv, n=100)
    assert csv.read_bytes() == before
    model, results = tmp_path / 'model.joblib', tmp_path / 'results.json'
    train(csv, model, results)
    old = {str(p.resolve()): p.read_bytes() for p in (model, results)}
    second = train(csv, model, results)
    for name, backup in second['previous_outputs_preserved'].items():
        assert Path(backup).read_bytes() == old[name]
    assert csv.read_bytes() == before
    with pytest.raises(ValueError, match='even'):
        create_rows(101)
    with pytest.raises(ValueError, match='two families'):
        split_by_family([{'path': 'a', 'label': 0, 'family': 'a'}, {'path': '../b', 'label': 1, 'family': 'b'}])
