import csv
import json
from pathlib import Path

import joblib
import numpy as np
import pytest

from app import create_app
from app.ml_features import extract_features
from ml.evaluate import audit_dataset, evaluate, partition, scores, sha256
from ml.generate_dataset import create_rows


def test_audit_rejects_duplicate_and_conflicting_labels():
    rows = [dict(r, label=str(r['label'])) for r in create_rows(100)]
    assert audit_dataset(rows)['duplicate_excess_rows'] == 0
    with pytest.raises(ValueError, match='duplicate/conflicting'):
        audit_dataset(rows + [rows[0]])
    conflicting = dict(rows[0], label=str(1 - int(rows[0]['label'])))
    with pytest.raises(ValueError, match='duplicate/conflicting'):
        audit_dataset(rows + [conflicting])


def test_partition_rejects_cross_family_duplicate():
    rows = [dict(r, label=str(r['label'])) for r in create_rows(400)]
    train, test, check = partition(rows, 2026)
    test[0]['path'] = train[0]['path']
    with pytest.raises(ValueError, match='Unsafe'):
        partition(rows, 2026)


@pytest.fixture(scope='module')
def experiment(tmp_path_factory):
    folder = tmp_path_factory.mktemp('evaluation')
    data = folder / 'dataset.csv'
    rows = create_rows(400)
    with data.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'label', 'family'])
        writer.writeheader()
        writer.writerows(rows)
    before = sha256(data)
    root = folder / 'runs'
    run = evaluate(data, root, repeats=3)
    assert sha256(data) == before
    return root, run


def test_saved_evaluation_is_recomputable_and_train_only(experiment):
    root, run = experiment
    results = json.loads((run / 'results.json').read_text(encoding='utf-8'))
    with (run / 'split.csv').open(encoding='utf-8-sig', newline='') as f:
        split = list(csv.DictReader(f))
    train = [r for r in split if r['partition'] == 'train']
    test = [r for r in split if r['partition'] == 'test']
    model = joblib.load(run / 'model.joblib')
    features = np.array([extract_features(r['path']) for r in train])
    # The saved scaler statistics must match train, never the entire corpus.
    assert model.named_steps['scale'].n_samples_seen_ == len(train)
    np.testing.assert_allclose(model.named_steps['scale'].mean_, features.mean(axis=0))
    assert not ({r['family'] for r in train} & {r['family'] for r in test})
    with (run / 'predictions.csv').open(encoding='utf-8-sig', newline='') as f:
        predictions = list(csv.DictReader(f))
    assert len(predictions) == len(test)
    truth = [int(r['label']) for r in predictions]
    assert scores(truth, [int(r['lr_prediction']) for r in predictions]) == results['logistic_regression']
    assert scores(truth, [int(r['regex_prediction']) for r in predictions]) == results['regex']
    manifest = json.loads((run / 'manifest.json').read_text())
    for name, digest in manifest.items():
        assert sha256(run / name) == digest
    for name in ('confusion_matrix.png', 'metrics.png', 'latency.png'):
        assert (run / name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert results['preservation_verified']
    assert len(results['robustness']) == 5


def evaluation_client(tmp_path, evaluation_root):
    return create_app({'TESTING': True, 'FILES_ROOT': tmp_path / 'files',
                       'DATABASE': tmp_path / 'events.sqlite3',
                       'MODEL_PATH': tmp_path / 'missing.joblib',
                       'EVALUATION_ROOT': evaluation_root,
                       'ADMIN_PASSWORD': 'evaluation-test'}).test_client()


def test_evaluation_page_and_charts_require_login(experiment, tmp_path):
    root, run = experiment
    c = evaluation_client(tmp_path, root)
    assert c.get('/dashboard/ai-evaluation').status_code == 302
    chart = '/dashboard/ai-evaluation/chart/metrics.png?run=' + run.name
    assert c.get(chart).status_code == 302
    c.post('/login', data={'password': 'evaluation-test'})
    page = c.get('/dashboard/ai-evaluation')
    assert page.status_code == 200
    assert run.name.encode() in page.data
    for name in ('confusion_matrix.png', 'metrics.png', 'latency.png'):
        response = c.get('/dashboard/ai-evaluation/chart/' + name, query_string={'run': run.name})
        assert response.status_code == 200
        assert response.mimetype == 'image/png'
        assert response.data == (run / name).read_bytes()
        response.close()
    assert c.get('/dashboard/ai-evaluation/chart/results.json').status_code == 404
    assert c.get(chart.replace(run.name, 'invalid')).status_code == 404
    assert c.get('/dashboard').status_code == 200


@pytest.mark.parametrize('pointer', [None, '{broken', '{"run":"../../artifacts"}'])
def test_missing_or_invalid_results_do_not_break_dashboard(tmp_path, pointer):
    root = tmp_path / 'runs'
    root.mkdir()
    if pointer is not None:
        (root / 'latest.json').write_text(pointer)
    c = evaluation_client(tmp_path, root)
    c.post('/login', data={'password': 'evaluation-test'})
    assert 'Chưa có kết quả'.encode() in c.get('/dashboard/ai-evaluation').data
    assert c.get('/dashboard').status_code == 200
