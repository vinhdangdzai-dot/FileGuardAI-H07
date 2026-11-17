"""Validate locally generated evaluation data before rendering the dashboard."""
import math


def _number(value, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Invalid numeric result type')
    try:
        finite = math.isfinite(value)
    except OverflowError as exc:
        raise ValueError('Numeric result out of range') from exc
    if (not finite or value < minimum
            or maximum is not None and value > maximum):
        raise ValueError('Invalid finite numeric result')
    return value


def _count(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError('Invalid sample count')
    return value


def _metrics(data, samples):
    matrix = data['confusion_matrix']
    if not isinstance(matrix, list) or len(matrix) != 2 or any(not isinstance(r, list) or len(r) != 2 for r in matrix):
        raise ValueError('Confusion matrix must be 2x2')
    (tn, fp), (fn, tp) = [[_count(v) for v in r] for r in matrix]
    if tn + fp + fn + tp != samples:
        raise ValueError('Confusion matrix/sample mismatch')
    expected = {'accuracy': (tn + tp) / samples,
                'precision': tp / (tp + fp) if tp + fp else 0,
                'recall': tp / (tp + fn) if tp + fn else 0,
                'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0}
    for key, value in expected.items():
        if abs(_number(data[key], maximum=1) - value) > 1e-4:
            raise ValueError('Metric inconsistent with confusion matrix')
    return (tn + fp, fn + tp)


def _timings(data, samples, improved):
    required = {'lr_inference_only', 'lr_end_to_end', 'regex_end_to_end'}
    if improved:
        required |= {'improved_inference_only', 'improved_end_to_end'}
    for key in required:
        t = data[key]
        if _count(t['repeats']) < 1 or _count(t['samples_per_batch']) != samples:
            raise ValueError('Timing/sample mismatch')
        for field in ('median_batch_ms', 'p95_batch_ms', 'amortized_us_per_path'):
            _number(t[field])


def validate_evaluation(data):
    """Accept historical v1 and comparison v2 schemas; reject corrupt reports.

    This checks internal consistency, not authenticity of locally writable
    reports. SHA-256 manifests are independently verified by the audit tool.
    """
    try:
        n = _count(data['test_samples'])
        training = _count(data['train_samples'])
        if n < 1 or training < 1 or training + n != _count(data['audit']['rows']):
            raise ValueError('Invalid dataset sizes')
        audit = data['audit']
        _count(audit['duplicate_excess_rows'])
        if sum(_count(v) for v in audit['label_counts'].values()) != training + n:
            raise ValueError('Label count mismatch')
        if sum(_count(v) for v in audit['family_counts'].values()) != training + n:
            raise ValueError('Family count mismatch')
        for key in ('family_overlap', 'path_overlap'):
            if not isinstance(data['split'][key], list):
                raise ValueError('Invalid split metadata')
        if not isinstance(data['created_at_utc'], str) or not data['created_at_utc']:
            raise ValueError('Missing evaluation timestamp')
        _number(data['threshold'], maximum=1)
        _count(data['seed'])
        improved = 'improved_logistic_regression' in data
        methods = ['logistic_regression', 'regex'] + (['improved_logistic_regression'] if improved else [])
        counts = [_metrics(data[key], n) for key in methods]
        if len(set(counts)) != 1:
            raise ValueError('Methods evaluated on different class counts')
        _timings(data['timing'], n, improved)
        if improved:
            selection = data['selection']
            _number(selection['selected_C'], minimum=1e-15)
            _count(selection['validation_samples'])
            if _count(selection['refit_samples']) != training:
                raise ValueError('Refit/sample mismatch')
            if not {'frozen_holdout', 'external_public'} <= data['datasets'].keys():
                raise ValueError('Required comparison datasets missing')
            for name in data['datasets']:
                dataset = data['datasets'][name]
                size = _count(dataset['samples'])
                labels = dataset['label_counts']
                expected_counts = (_count(labels['0']), _count(labels['1']))
                if size < 1 or sum(expected_counts) != size:
                    raise ValueError('Invalid evaluation class counts')
                for key in methods:
                    if _metrics(dataset['models'][key], size) != expected_counts:
                        raise ValueError('Dataset confusion matrix/class mismatch')
                _timings(dataset['timing'], size, True)
            if data['datasets']['frozen_holdout']['samples'] != n:
                raise ValueError('Holdout size changed')
            for key in methods:
                if data[key] != data['datasets']['frozen_holdout']['models'][key]:
                    raise ValueError('Top-level metrics differ from holdout')
        elif data.get('datasets') or data.get('selection'):
            raise ValueError('Incomplete comparison data')
    except (KeyError, TypeError, AttributeError, ZeroDivisionError) as exc:
        raise ValueError('Incomplete evaluation schema') from exc
    return data
