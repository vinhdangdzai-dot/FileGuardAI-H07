import json
from pathlib import Path

from app.evaluation_results import validate_evaluation
from ml.evaluate import scores, sha256
from ml.external_corpus import canonical_key
from ml.improve import read_csv

ROOT = Path(__file__).resolve().parents[1]


def test_new_external_source_is_disjoint_and_recomputable():
    source = ROOT / 'data/external/h07_20261116T171550Z_5b8ba9'
    run = ROOT / 'docs/evaluations/20261116T171550Z_5b8ba9'
    metadata = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    assert sha256(source / 'cases.csv') == metadata['cases_sha256']
    for snapshot in metadata['snapshots']:
        assert sha256(source / snapshot['file']) == snapshot['sha256']
    original = read_csv(ROOT / 'data/paths_synthetic.csv')
    public = read_csv(source / 'cases.csv')
    assert not ({canonical_key(r['path']) for r in public} & {canonical_key(r['path']) for r in original})
    rows = read_csv(run / 'external_h07_predictions.csv')
    result = validate_evaluation(json.loads((run / 'results.json').read_text(encoding='utf-8')))
    for method, column in [('logistic_regression', 'lr_v1_prediction'),
                           ('improved_logistic_regression', 'lr_v2_prediction'), ('regex', 'regex_prediction')]:
        assert scores([int(r['label']) for r in rows], [int(r[column]) for r in rows]) == result['datasets']['external_h07']['models'][method]


def test_public_encoding_challenge_provenance_and_scores():
    source = ROOT / 'data/external/owasp_20261116T172733Z_800c38'
    run = ROOT / 'docs/evaluations/20261116T172733Z_800c38'
    metadata = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    assert sha256(source / 'cases.csv') == metadata['cases_sha256']
    rows = read_csv(run / 'owasp_predictions.csv')
    results = validate_evaluation(json.loads((run / 'results.json').read_text(encoding='utf-8')))
    for method, column in [('logistic_regression', 'lr_v1_prediction'),
                           ('improved_logistic_regression', 'lr_v2_prediction'), ('regex', 'regex_prediction')]:
        assert scores([int(r['label']) for r in rows], [int(r[column]) for r in rows]) == results['datasets']['owasp_challenge']['models'][method]
    assert any('%252e' in r['path'] for r in rows)
    assert all(r['source_url'].startswith('https://') for r in rows)
