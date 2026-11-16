"""Read-only training/evaluation inspection. Never fits or derives truth labels."""
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re

from .ml_features import FEATURE_NAMES, FEATURE_NAMES_V2
from .evaluation_results import validate_evaluation

V2_REFERENCE_SHA256 = '07e73c85cdbbd4a8acbc785565514a8330e3252483602c191c34208e04f8e368'


def read_dataset(path):
    path = Path(path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Dataset exceeds read-only inspection limit')
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not {'path', 'label', 'family'} <= set(reader.fieldnames or []):
            raise ValueError('Dataset requires path,label,family columns')
        rows = list(reader)
    if not rows or any(r['label'] not in {'0', '1'} or not r['path'] or not r['family'] for r in rows):
        raise ValueError('Dataset has invalid or missing annotated fields')
    return [{key: r[key] for key in ('path', 'label', 'family')} for r in rows]


def dataset_stats(rows, path):
    # Separate from ML features: an audit key is not an access-control path.
    from unicodedata import normalize
    from urllib.parse import unquote
    def key(text):
        return unquote(unquote(normalize('NFC', text))).replace('\\', '/').casefold()
    return {'rows': len(rows), 'label_counts': dict(Counter(r['label'] for r in rows)),
            'family_counts': dict(sorted(Counter(r['family'] for r in rows).items())),
            'exact_duplicate_excess': len(rows) - len({r['path'] for r in rows}),
            'canonical_duplicate_excess': len(rows) - len({key(r['path']) for r in rows}),
            'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'preview': rows[:20]}


def model_weights(model, names):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    if not isinstance(model, Pipeline) or not isinstance(model.named_steps.get('model'), LogisticRegression):
        raise ValueError('Not a fitted Logistic Regression pipeline')
    estimator, scaler = model.named_steps['model'], model.named_steps['scale']
    coefficients = estimator.coef_[0]
    if len(coefficients) != len(names):
        raise ValueError('Feature schema differs from the model')
    weights = [{'feature': name, 'coefficient': float(coefficients[i]),
                'train_mean': float(scaler.mean_[i]), 'train_scale': float(scaler.scale_[i])}
               for i, name in enumerate(names)]
    if not all(math.isfinite(r[k]) for r in weights for k in ('coefficient', 'train_mean', 'train_scale')):
        raise ValueError('Non-finite model metadata')
    return {'weights': weights, 'intercept': float(estimator.intercept_[0]),
            'C': float(estimator.C), 'features': len(names), 'train_samples': int(scaler.n_samples_seen_)}


def inspect_models(v1, v2_path):
    result = {}
    for version, names in [('v1', FEATURE_NAMES), ('v2', FEATURE_NAMES_V2)]:
        try:
            if version == 'v2':
                path = Path(v2_path)
                # Verify the trusted, frozen experiment BEFORE pickle loading.
                if hashlib.sha256(path.read_bytes()).hexdigest() != V2_REFERENCE_SHA256:
                    raise ValueError('Frozen v2 checksum mismatch')
                import joblib
                model = joblib.load(path)
            else:
                model = v1
            result[version] = model_weights(model, names)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
            result[version] = None
    return result


def evaluation_history(root):
    root = Path(root).resolve()
    history = []
    for folder in sorted(root.glob('*'), reverse=True):
        if len(history) >= 100:
            break
        if not re.fullmatch(r'\d{8}T\d{6}Z_[a-f0-9]{6}', folder.name):
            continue
        try:
            resolved = folder.resolve()
            file = (resolved / 'results.json').resolve()
            if not resolved.is_relative_to(root) or not file.is_relative_to(resolved) or file.stat().st_size > 2 * 1024 * 1024:
                continue
            data = validate_evaluation(json.loads(file.read_text(encoding='utf-8')))
            history.append({'run': folder.name, 'created_at_utc': data['created_at_utc'],
                            'test_samples': data['test_samples'], 'v1_f1': data['logistic_regression']['f1'],
                            'v2_f1': data.get('improved_logistic_regression', {}).get('f1')})
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return history
