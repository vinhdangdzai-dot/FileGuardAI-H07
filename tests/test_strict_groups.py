import pytest
from ml.strict_groups import strict_split
from ml.external_corpus import canonical_key
from ml.generate_dataset import create_rows


def test_three_way_partition_preserves_families_and_equivalents():
    rows = create_rows(1000)
    parts, stats = strict_split(rows)
    assert sum(map(len, parts.values())) == len(rows)
    for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
        assert not ({r['family'] for r in parts[a]} & {r['family'] for r in parts[b]})
        assert not ({canonical_key(r['path']) for r in parts[a]} & {canonical_key(r['path']) for r in parts[b]})
    assert parts == strict_split(rows)[0]


def test_canonical_conflicting_labels_are_not_auto_relabelled():
    rows = [{'path': '../secret.txt', 'label': 1, 'family': 'a'},
            {'path': '%252e%252e%252fsecret.txt', 'label': 0, 'family': 'b'}]
    with pytest.raises(ValueError, match='conflicting labels'):
        strict_split(rows)


def test_insufficient_groups_fail_without_random_row_fallback():
    with pytest.raises(ValueError, match='Insufficient'):
        strict_split([{'path': 'ok', 'label': 0, 'family': 'one'}])


def test_saved_strict_experiment_has_no_leakage_and_recomputable_scores():
    import json
    from pathlib import Path
    import joblib
    import numpy as np
    from app.evaluation_results import validate_evaluation
    from app.ml_features import extract_features_v2
    from ml.improve import read_csv
    from ml.evaluate import scores, sha256
    root = Path(__file__).resolve().parents[1]
    run = root / 'docs/evaluations/20261116T181019Z_dea9ec'
    data = validate_evaluation(json.loads((run/'results.json').read_text(encoding='utf-8')))
    rows = read_csv(run/'split.csv')
    development = [r for r in rows if r['partition'] != 'test']
    test = [r for r in rows if r['partition'] == 'test']
    for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
        assert not ({canonical_key(r['path']) for r in rows if r['partition'] == a}
                    & {canonical_key(r['path']) for r in rows if r['partition'] == b})
    model = joblib.load(run/'v2_strict.joblib')
    assert model.named_steps['scale'].n_samples_seen_ == len(development)
    np.testing.assert_allclose(model.named_steps['scale'].mean_,
                               np.mean([extract_features_v2(r['path']) for r in development], axis=0))
    predictions = read_csv(run/'holdout_predictions.csv')
    assert {r['path'] for r in predictions} == {r['path'] for r in test}
    for method, column in [('logistic_regression', 'lr_v1_prediction'),
                           ('improved_logistic_regression', 'lr_v2_prediction'), ('regex', 'regex_prediction')]:
        assert scores([int(r['label']) for r in predictions], [int(r[column]) for r in predictions]) == data[method]
    assert sha256(root/'artifacts/model.joblib') == '4d7324aa302ecb3d1b731561210a0041e4aef3f740cc68d9187097a80e5a6322'
