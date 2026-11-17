import csv
import json
from pathlib import Path

import joblib
import numpy as np

from app import create_app
from app.ml_features import (FEATURE_NAMES, FEATURE_NAMES_V2, extract_features,
                             extract_features_v2, lexical_views)
from ml.evaluate import scores, sha256
from ml.external_corpus import canonical_key, label_reason
from ml.improve import REFERENCE, read_csv

ROOT = Path(__file__).resolve().parents[1]


def current_run():
    root = ROOT / 'docs/evaluations'
    # Regression checks must not depend on which experiment the UI last viewed.
    run = root / '20261116T154448Z_7a27a7'
    return run, json.loads((run / 'results.json').read_text(encoding='utf-8'))


def test_v1_contract_preserved_and_v2_bounded():
    for path in ('baocao.pdf', '%252e%252e%252fsecret.txt', r'..\secret.txt', 'báo cáo.txt'):
        assert len(extract_features(path)) == len(FEATURE_NAMES) == 18
        features = extract_features_v2(path)
        assert features[:18] == extract_features(path)
        assert len(features) == len(FEATURE_NAMES_V2) == 30
    assert lexical_views('%252e%252e%252fsecret.txt')[-1] == '../secret.txt'
    assert lexical_views('%25252e%25252e%25252fsecret.txt')[-1] == '%2e%2e%2fsecret.txt'
    assert all('+' in view for view in lexical_views('a+b.txt'))
    assert all(len(view) <= 4096 for view in lexical_views('x' * 9000))
    key = FEATURE_NAMES_V2.index('view_max_parent_components')
    for value in ('../secret.txt', r'..\secret.txt', '%2e%2e%2fsecret.txt', '%252e%252e%252fsecret.txt'):
        assert extract_features_v2(value)[key] == 1
    assert extract_features_v2('report..txt')[key] == 0


def test_independent_annotation_policy():
    assert label_reason('%252e%252e%252fetc/passwd')
    assert label_reason(r'C:\Windows\win.ini')
    assert label_reason('src/flask/app.py') is None
    assert label_reason('docs/report..txt') is None
    assert canonical_key('%252e%252e%252fetc/passwd') == canonical_key('../etc/passwd')


def test_frozen_split_and_training_statistics():
    run, result = current_run()
    assert result['schema_version'] == 2
    original = read_csv(REFERENCE / 'split.csv')
    development = read_csv(run / 'development_split.csv')
    training = [r for r in original if r['partition'] == 'train']
    test = [r for r in original if r['partition'] == 'test']
    assert {r['path'] for r in development} == {r['path'] for r in training}
    assert not ({r['family'] for r in development} & {r['family'] for r in test})
    assert not ({r['family'] for r in development if r['partition'] == 'fit'} &
                {r['family'] for r in development if r['partition'] == 'validation'})
    model = joblib.load(run / 'improved_model.joblib')
    assert model.named_steps['scale'].n_samples_seen_ == len(training)
    np.testing.assert_allclose(model.named_steps['scale'].mean_,
                               np.mean([extract_features_v2(r['path']) for r in training], axis=0))
    assert sha256(run / 'baseline_model.joblib') == sha256(REFERENCE / 'model.joblib')
    assert sha256(ROOT / 'artifacts/model.joblib') == result['protocol']['deployed_model_sha256']
    assert sha256(ROOT / 'data/paths_synthetic.csv') == result['protocol']['data_sha256']
    candidates = result['selection']['candidates']
    best = max(candidates, key=lambda r: (r['validation']['f1'], -r['C']))
    assert model.named_steps['model'].C == best['C'] == result['selection']['selected_C']


def test_metrics_recompute_and_external_provenance():
    run, result = current_run()
    for dataset, filename in [('frozen_holdout', 'holdout_predictions.csv'), ('external_public', 'external_predictions.csv')]:
        rows = read_csv(run / filename)
        truth = [int(r['label']) for r in rows]
        for key, column in [('logistic_regression', 'lr_v1_prediction'),
                            ('improved_logistic_regression', 'lr_v2_prediction'), ('regex', 'regex_prediction')]:
            assert scores(truth, [int(r[column]) for r in rows]) == result['datasets'][dataset]['models'][key]
    external = read_csv(run / 'external_predictions.csv')
    original = read_csv(REFERENCE / 'split.csv')
    assert not ({canonical_key(r['path']) for r in external} & {canonical_key(r['path']) for r in original})
    assert all(r['source_url'].startswith('https://') and r['source_revision'] and r['label_reason'] for r in external)
    assert all(bool(label_reason(r['path'])) == bool(int(r['label'])) for r in external)
    manifest = result['external_source_manifest']
    assert manifest['frozen_selection_sha256'] == sha256(run / 'selection.json')
    assert manifest['created_at_utc'] >= manifest['frozen_at_utc']
    for source in manifest['sources']:
        folder = ROOT / 'data/external' / Path(manifest['dataset_path'].replace('\\', '/')).name
        assert sha256(folder / source['file']) == source['sha256']


def test_comparison_dashboard_preserves_download_policy(tmp_path):
    run, result = current_run()
    base = tmp_path / 'shared'
    base.mkdir()
    (base / 'ok.txt').write_bytes(b'PUBLIC')
    evaluation_root = tmp_path / 'evaluations'
    target = evaluation_root / run.name
    target.mkdir(parents=True)
    (target / 'results.json').write_text(json.dumps(result), encoding='utf-8')
    (evaluation_root / 'latest.json').write_text(json.dumps({'run': run.name}), encoding='utf-8')
    app = create_app({'TESTING': True, 'FILES_ROOT': base, 'DATABASE': tmp_path / 'log.sqlite3',
                      'EVALUATION_ROOT': evaluation_root,
                      'ADMIN_PASSWORD': 'test-password'})
    c = app.test_client()
    assert c.get('/dashboard/ai-evaluation').status_code == 302
    c.post('/login', data={'password': 'test-password'})
    response = c.get('/dashboard/ai-evaluation')
    assert response.status_code == 200
    assert b'LR v1' in response.data and b'LR v2' in response.data
    for dataset in result['datasets'].values():
        for m in dataset['models'].values():
            assert f"{m['f1']:.4f}".encode() in response.data
    with c.get('/download?path=ok.txt') as r:
        assert r.status_code == 200 and r.data == b'PUBLIC'
    assert c.get('/download?path=%252e%252e%252fsecret.txt').status_code == 403
    assert c.get('/download?path=missing.txt').status_code == 404
