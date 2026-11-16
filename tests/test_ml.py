from app.ml_features import FEATURE_NAMES, extract_features, simple_rule
from ml.generate_dataset import create_rows
from ml.train_model import split_by_family


def test_features_consistent_length():
    for s in ['baocao.pdf', '../secret.txt', '..%2Fsecret.txt', 'báo cáo tốt nghiệp.pdf']:
        assert len(extract_features(s)) == len(FEATURE_NAMES)


def test_baseline_not_a_security_boundary():
    assert simple_rule('../secret.txt') == 1
    assert simple_rule('tailieu/chuong1.pdf') == 0


def test_datasets_split_by_group():
    data = create_rows(n=400, seed=2)
    train, test = split_by_family(data)
    assert not ({r['family'] for r in train} & {r['family'] for r in test})
    assert {r['label'] for r in train} == {0, 1}
    assert {r['label'] for r in test} == {0, 1}
