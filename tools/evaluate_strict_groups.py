"""Offline experiment with strict grouped validation; no deployed writes."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
import sklearn
from app.ml_features import extract_features, extract_features_v2
from app.security import safe_path, RejectedPath
from ml.evaluate import audit_dataset, scores, sha256, write_csv
from ml.improve import read_csv, evaluate_rows, plots, json_write
from ml.strict_groups import strict_split
from ml.train_model import build_model


def main():
    data = ROOT / 'data/paths_synthetic.csv'
    protected = {str(p): sha256(p) for p in (data, ROOT/'artifacts/model.joblib',
                 ROOT/'docs/evaluations/20261116T154448Z_7a27a7/improved_model.joblib')}
    rows = read_csv(data)
    audit = audit_dataset(rows)
    parts, split = strict_split(rows)
    out = ROOT / 'docs/evaluations' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6])
    out.mkdir()
    plan = {'seed': 2026, 'candidate_C': [.1, 1, 10], 'threshold': .5, 'data_sha256': sha256(data),
            'selection': 'highest validation F1, ties choose smallest C', 'split': split,
            'caveat': 'New split of previously disclosed synthetic data, not a blind real-world test; no old artifact overwritten'}
    json_write(out/'plan_before_fit.json', plan)
    write_csv(out/'split.csv', [dict(r, partition=name) for name, part in parts.items() for r in part],
              ['path', 'label', 'family', 'partition'])
    fit, validation, test = parts['train'], parts['validation'], parts['test']
    candidates = []
    for c in plan['candidate_C']:
        model = build_model()
        model.set_params(model__C=c)
        model.fit([extract_features_v2(r['path']) for r in fit], [int(r['label']) for r in fit])
        candidates.append({'C': c, 'validation': scores([int(r['label']) for r in validation],
                           model.predict([extract_features_v2(r['path']) for r in validation]))})
    chosen = max(candidates, key=lambda r: (r['validation']['f1'], -r['C']))['C']
    development = fit + validation
    baseline, improved = build_model(), build_model()
    improved.set_params(model__C=chosen)
    truth = [int(r['label']) for r in development]
    baseline.fit([extract_features(r['path']) for r in development], truth)
    improved.fit([extract_features_v2(r['path']) for r in development], truth)
    joblib.dump(baseline, out/'v1_strict.joblib')
    joblib.dump(improved, out/'v2_strict.joblib')
    selection = {'selected_C': chosen, 'candidates': candidates, 'validation_samples': len(validation),
                 'fit_samples': len(fit), 'refit_samples': len(development),
                 'v1_sha256': sha256(out/'v1_strict.joblib'), 'v2_sha256': sha256(out/'v2_strict.joblib')}
    json_write(out/'models_frozen_before_test.json', selection)
    holdout, predictions = evaluate_rows(test, baseline, improved, 7)
    external = read_csv(ROOT/'data/external/h07_20261116T171550Z_5b8ba9/cases.csv')
    public, pp = evaluate_rows(external, baseline, improved, 7)
    scope = out/'policy_fixture'
    scope.mkdir()
    policy = []
    for row in test:
        try:
            safe_path(scope, row['path'])
            decision = 'relative_in_scope_may_be_missing'
        except RejectedPath:
            decision = 'reject_policy'
        except OSError:
            decision = 'os_error_not_classified'
        policy.append(dict(row, scope_decision=decision))
    write_csv(out/'policy_comparison.csv', policy, ['path', 'label', 'family', 'scope_decision'])
    result = {'schema_version': 2, 'experiment_type': 'canonical_grouped_validation',
              'created_at_utc': datetime.now(timezone.utc).isoformat(), 'seed': 2026, 'threshold': .5,
              'sklearn_version': sklearn.__version__, 'audit': audit, 'train_samples': len(development), 'test_samples': len(test),
              'train_families': sorted({r['family'] for r in development}), 'test_families': sorted({r['family'] for r in test}),
              'split': split, 'selection': selection, 'timing': holdout['timing'], **holdout['models'],
              'datasets': {'frozen_holdout': holdout, 'external_public': public},
              'dataset_descriptions': {'external_public': 'LFISuite + Starlette: nguồn ngoài; nhãn lexical'},
              'policy_comparison': {label: {decision: sum(r['label'] == label and r['scope_decision'] == decision for r in policy)
                                   for decision in ('reject_policy', 'relative_in_scope_may_be_missing', 'os_error_not_classified')}
                                   for label in ('0', '1')},
              'scope_note': 'Authorization rejects/accepts path scope; not a classifier of attack intent, no implicit HTTP 200 for missing files.',
              'protected_unchanged': all(sha256(Path(path)) == digest for path, digest in protected.items())}
    if not result['protected_unchanged']:
        raise RuntimeError('Protected input/model changed')
    write_csv(out/'holdout_predictions.csv', predictions, list(predictions[0]))
    write_csv(out/'external_predictions.csv', pp, list(pp[0]))
    json_write(out/'results.json', result)
    plots(result, out)
    json_write(out/'manifest.json', {p.name: sha256(p) for p in out.iterdir() if p.is_file()})
    # Keep the dashboard's current benchmark pointer unchanged; history shows
    # this additional experiment without replacing the disclosed benchmark.
    print('Experiment:', out.relative_to(ROOT))
    print(json.dumps({'split': split, 'selected_C': chosen,
                     'holdout': holdout['models'], 'external': public['models'], 'policy': result['policy_comparison']}, indent=2))


if __name__ == '__main__':
    main()
