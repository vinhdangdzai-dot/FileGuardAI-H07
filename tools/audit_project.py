"""Read-only project/data/model audit and fresh prediction measurements.

No training, threshold selection, data generation or deployment occurs here.
Outputs are written only to a new/explicit review evidence directory.
"""
import argparse
import ast
from contextlib import closing
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import sys
import uuid
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
from sklearn.exceptions import InconsistentVersionWarning

from app.evaluation_results import validate_evaluation
from app.ml_features import extract_features
from ml.evaluate import audit_dataset, partition, scores, sha256, write_csv
from ml.external_corpus import canonical_key
from ml.improve import evaluate_rows, read_csv


def audit(output=None, repeats=7):
    output = output or ROOT / 'docs/reviews' / ('audit_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6])
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'audit.json'
    if target.exists():
        raise FileExistsError('Do not overwrite a prior audit')
    before = (json.loads((output / 'before.json').read_text())
              if (output / 'before.json').exists() else {})
    files = [ROOT / 'run.py'] + [p for name in ('app', 'ml', 'tests', 'tools') for p in (ROOT / name).rglob('*.py')]
    sources = {}
    for path in sorted(files):
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        sources[path.relative_to(ROOT).as_posix()] = sha256(path)
    data_path = ROOT / 'data/paths_synthetic.csv'
    model_path = ROOT / 'artifacts/model.joblib'
    protected = {'dataset': sha256(data_path), 'deployed_model': sha256(model_path)}
    rows = read_csv(data_path)
    data_audit = audit_dataset(rows)
    train, test, check = partition(rows, 2026)
    run = ROOT / 'docs/evaluations/20261116T154448Z_7a27a7'
    result = validate_evaluation(json.loads((run / 'results.json').read_text(encoding='utf-8')))
    reference = ROOT / 'docs/evaluations' / result['reference_run']
    frozen_test = [r for r in read_csv(reference / 'split.csv') if r['partition'] == 'test']
    checks = {
        'fixed_test_membership_and_labels': [(r['path'], r['label'], r['family']) for r in test] == [(r['path'], r['label'], r['family']) for r in frozen_test],
        'train_test_family_disjoint': not check['family_overlap'],
        'train_test_exact_disjoint': not check['path_overlap'],
    }
    manifest_results = {}
    for folder in (reference, run):
        manifest = json.loads((folder / 'manifest.json').read_text())
        manifest_results[folder.name] = {name: sha256(folder / name) == digest for name, digest in manifest.items()}
    checks['archived_manifests_intact'] = all(all(v.values()) for v in manifest_results.values())
    external_manifest = result['external_source_manifest']
    external_path = ROOT / 'data/external' / Path(external_manifest['dataset_path'].replace('\\', '/')).name
    outside = read_csv(external_path / 'external_cases.csv')
    checks['external_csv_intact'] = sha256(external_path / 'external_cases.csv') == external_manifest['external_cases_sha256']
    checks['external_sources_intact'] = all(sha256(external_path / s['file']) == s['sha256'] for s in external_manifest['sources'])
    checks['external_canonical_disjoint'] = not ({canonical_key(r['path']) for r in outside} & {canonical_key(r['path']) for r in rows})
    with warnings.catch_warnings():
        warnings.simplefilter('error', InconsistentVersionWarning)
        baseline = joblib.load(run / 'baseline_model.joblib')
        improved = joblib.load(run / 'improved_model.joblib')
        deployed = joblib.load(model_path)
        holdout, hp = evaluate_rows(test, baseline, improved, repeats)
        public, ep = evaluate_rows(outside, baseline, improved, repeats)
        current_prediction = deployed.predict(np.asarray([extract_features(r['path']) for r in test]))
    checks['baseline_reproduced'] = holdout['models']['logistic_regression'] == result['logistic_regression']
    checks['improved_reproduced'] = holdout['models']['improved_logistic_regression'] == result['improved_logistic_regression']
    checks['external_metrics_reproduced'] = public['models'] == result['datasets']['external_public']['models']
    checks['deployed_matches_v1_scores'] = scores([int(r['label']) for r in test], current_prediction) == result['logistic_regression']
    db_path = ROOT / 'instance/events.sqlite3'
    db_hash = sha256(db_path)
    with closing(sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        integrity = db.execute('PRAGMA integrity_check').fetchall()
        database = {'integrity_check': integrity, 'row_count': db.execute('SELECT COUNT(*) FROM access_logs').fetchone()[0],
                    'columns': [r[1] for r in db.execute('PRAGMA table_info(access_logs)')],
                    'action_http_counts': db.execute('SELECT action,http_status,COUNT(*) FROM access_logs GROUP BY action,http_status').fetchall()}
    checks['user_sqlite_intact'] = integrity == [('ok',)] and sha256(db_path) == db_hash
    checks['protected_data_and_model_unchanged'] = protected == {'dataset': sha256(data_path), 'deployed_model': sha256(model_path)}
    if before:
        preserved = {name: sha256(ROOT / name) == digest for name, digest in before.items()
                     if name.startswith(('docs/evaluations/', 'artifacts/')) or name in ('data/paths_synthetic.csv', 'instance/events.sqlite3')}
        checks['all_preexisting_protected_artifacts_preserved'] = all(preserved.values())
    else:
        preserved = {}
    report = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
              'platform': platform.platform(), 'versions': {name: importlib.metadata.version(name) for name in ('Flask', 'scikit-learn', 'numpy', 'joblib', 'pytest', 'matplotlib')},
              'python_files_parsed': len(sources), 'source_sha256': sources, 'protected_sha256': protected,
              'dataset_audit': data_audit, 'split': check,
              'canonical_train_test_overlap_count': len({canonical_key(r['path']) for r in train} & {canonical_key(r['path']) for r in test}),
              'models': {'deployed_features': int(deployed.n_features_in_), 'v1_features': int(baseline.n_features_in_),
                         'v2_features': int(improved.n_features_in_), 'selected_C': improved.named_steps['model'].C},
              'fresh_measurements': {'frozen_holdout': holdout, 'external_public': public},
              'database_read_only': database, 'archived_manifest_checks': manifest_results,
              'preexisting_protected_checks': preserved, 'checks': checks,
              'passed': sum(checks.values()), 'failed': sum(not v for v in checks.values()),
              'limitations': 'No refit or tuning. Existing test was disclosed; external labels are lexical and source-correlated. External selected set lacks double-decode-only examples.'}
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print('Audit:', target)
    print(f"{report['passed']} checks PASS; {report['failed']} FAIL; {len(sources)} Python files parsed")
    print(json.dumps({k: v['models'] for k, v in report['fresh_measurements'].items()}, indent=2))
    methodology(output, repeats)
    return int(report['failed'] > 0)


def methodology(output, repeats=7):
    """Post-audit sensitivity analysis, no fit and no label-based filtering.

    Keep the locked benchmark intact. Report a separate subset excluding
    cross-partition lexical equivalents, never silently replace the test.
    """
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'methodology.json'
    if target.exists():
        raise FileExistsError('Do not overwrite a prior methodology audit')
    rows = read_csv(ROOT / 'docs/evaluations/20261116T153450Z_e5b13b/split.csv')
    train = [r for r in rows if r['partition'] == 'train']
    test = [r for r in rows if r['partition'] == 'test']
    equivalents = {}
    for row in train:
        equivalents.setdefault(canonical_key(row['path']), []).append(row)
    overlap = [r for r in test if canonical_key(r['path']) in equivalents]
    clean = [r for r in test if canonical_key(r['path']) not in equivalents]
    pairs = []
    for row in overlap:
        for matching in equivalents[canonical_key(row['path'])]:
            pairs.append({'test_path': row['path'], 'test_family': row['family'],
                          'train_path': matching['path'], 'train_family': matching['family'],
                          'canonical_key': canonical_key(row['path'])})
    write_csv(output / 'canonical_overlap.csv', pairs,
              ['test_path', 'test_family', 'train_path', 'train_family', 'canonical_key'])
    run = ROOT / 'docs/evaluations/20261116T154448Z_7a27a7'
    with warnings.catch_warnings():
        warnings.simplefilter('error', InconsistentVersionWarning)
        baseline = joblib.load(run / 'baseline_model.joblib')
        improved = joblib.load(run / 'improved_model.joblib')
        measured, predictions = evaluate_rows(clean, baseline, improved, repeats)
    write_csv(output / 'sensitivity_predictions.csv', predictions, list(predictions[0]))
    data = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'canonical_definition': 'Unicode NFC, exactly two URL decode views, backslash->slash, casefold; no filesystem resolution',
            'locked_test_samples': len(test),
            'overlapping_canonical_keys': len({canonical_key(r['path']) for r in overlap}),
            'excluded_test_rows': len(overlap), 'remaining_test_rows': len(clean),
            'frozen_test_canonical_disjoint': not overlap,
            'remaining_canonical_disjoint': not ({canonical_key(r['path']) for r in clean} & set(equivalents)),
            'selection_uses_test_labels_or_predictions': False,
            'models_refitted': False,
            'sensitivity_results': measured,
            'interpretation': 'Post-hoc sensitivity subset, not a new blind benchmark. Original locked test, models and dashboard scores are unchanged. Family-generator correlation and prior disclosure remain.'}
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Methodology:', target)
    print('Canonical-equivalent test rows excluded:', len(overlap), '; remaining:', len(clean))
    print(json.dumps(measured['models'], indent=2))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repeats', type=int, default=7)
    parser.add_argument('--methodology-only', action='store_true')
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error('repeats must be >= 3')
    if args.methodology_only:
        if args.output is None:
            parser.error('--methodology-only requires --output')
        raise SystemExit(methodology(args.output, args.repeats))
    raise SystemExit(audit(args.output, args.repeats))
