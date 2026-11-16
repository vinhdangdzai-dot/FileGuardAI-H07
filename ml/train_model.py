"""Train Logistic Regression on synthetic data; report held-out *families*.
Run from the project root with: python -m ml.train_model
"""
import argparse
import csv
import json
import platform
import shutil
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score,
                             recall_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml_features import FEATURE_NAMES, extract_features, simple_rule
from ml.generate_dataset import write_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def split_by_family(rows, seed=2026):
    """Keep path-template families exclusive across train and test."""
    families = defaultdict(set)
    for row in rows:
        if str(row['label']) not in {'0', '1'} or not row['family']:
            raise ValueError('Invalid labels or empty family')
        families[row['family']].add(int(row['label']))
    if not families or any(len(labels) != 1 for labels in families.values()):
        raise ValueError('Families must be nonempty and label-homogeneous')
    rng = np.random.default_rng(seed)
    test_families = set()
    for label in (0, 1):
        groups = sorted({r['family'] for r in rows if int(r['label']) == label})
        if len(groups) < 2:
            raise ValueError('Need at least two families per class for a grouped holdout')
        rng.shuffle(groups)
        count = max(1, round(0.2 * len(groups)))
        test_families.update(groups[:count])
    train = [r for r in rows if r['family'] not in test_families]
    test = [r for r in rows if r['family'] in test_families]
    if (not train or not test or {int(r['label']) for r in train} != {0, 1}
            or {int(r['label']) for r in test} != {0, 1}
            or {r['family'] for r in train} & {r['family'] for r in test}):
        raise ValueError('Unsafe grouped partition')
    return train, test


def metrics(y_true, pred):
    return {
        'accuracy': round(float(accuracy_score(y_true, pred)), 4),
        'precision': round(float(precision_score(y_true, pred, zero_division=0)), 4),
        'recall': round(float(recall_score(y_true, pred, zero_division=0)), 4),
        'f1': round(float(f1_score(y_true, pred, zero_division=0)), 4),
        'confusion_matrix': confusion_matrix(y_true, pred, labels=[0, 1]).tolist(),
    }


def build_model(seed=2026):
    """Unfitted pipeline; scaler is fitted only with the training partition."""
    return Pipeline([
        ('scale', StandardScaler()),
        ('model', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=seed)),
    ])


def train(csv_file, model_file, results_file):
    with open(csv_file, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if len({r['path'] for r in rows}) != len(rows):
        raise ValueError('Duplicate paths must be resolved before training')
    train_rows, test_rows = split_by_family(rows)
    x_train = [extract_features(r['path']) for r in train_rows]
    y_train = [int(r['label']) for r in train_rows]
    x_test = [extract_features(r['path']) for r in test_rows]
    y_test = [int(r['label']) for r in test_rows]
    pipeline = build_model()
    pipeline.fit(x_train, y_train)
    ml_pred = pipeline.predict(x_test)
    rules_pred = [simple_rule(r['path']) for r in test_rows]
    results = {
        'trained_at_utc': datetime.now(timezone.utc).isoformat(),
        'python_version': platform.python_version(),
        'sklearn_version': sklearn.__version__,
        'numpy_version': np.__version__,
        'dataset': 'Synthetic patterns generated locally; not real attack traffic',
        'total_samples': len(rows), 'train_samples': len(train_rows),
        'test_samples': len(test_rows),
        'train_families': sorted({r['family'] for r in train_rows}),
        'test_families': sorted({r['family'] for r in test_rows}),
        'feature_names': FEATURE_NAMES,
        'logistic_regression': metrics(y_test, ml_pred),
        'simple_regex_baseline': metrics(y_test, rules_pred),
        'classification_report': classification_report(y_test, ml_pred, zero_division=0),
    }
    model_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.parent.mkdir(parents=True, exist_ok=True)
    # Preserve each prior output before an explicitly requested training run.
    old_outputs = [p for p in (model_file, results_file) if p.exists()]
    if old_outputs:
        history = model_file.parent / 'history' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6])
        history.mkdir(parents=True, exist_ok=False)
        backups = {}
        for index, previous in enumerate(old_outputs):
            target = history / f'{index}_{previous.name}'
            shutil.copy2(previous, target)
            backups[str(previous.resolve())] = str(target.resolve())
        results['previous_outputs_preserved'] = backups
    joblib.dump(pipeline, model_file)
    results_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Trained Logistic Regression; results are on held-out synthetic families.')
    for name in ('logistic_regression', 'simple_regex_baseline'):
        print(name, results[name])
    print('Model:', model_file)
    print('Results:', results_file)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=10000)
    args = parser.parse_args()
    data_path = PROJECT_ROOT / 'data' / 'paths_synthetic.csv'
    model_path = PROJECT_ROOT / 'artifacts' / 'model.joblib'
    result_path = PROJECT_ROOT / 'artifacts' / 'training_results.json'
    if not data_path.exists():
        write_dataset(data_path, n=args.n)
    else:
        print('Using existing dataset without regeneration:', data_path)
    train(data_path, model_path, result_path)
