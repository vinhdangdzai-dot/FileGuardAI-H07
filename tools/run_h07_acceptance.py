"""Run feasible acceptance suites, preserving real stdout/exit codes/evidence."""
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.evaluate import sha256
from tools.pytest_runtime import create_runtime, runtime_environment
from xml.etree import ElementTree


def pytest_counts(path):
    """Count serialized testcase nodes; report ERROR independently of FAIL."""
    root = ElementTree.parse(path).getroot()
    counts = dict(PASS=0, FAIL=0, ERROR=0, SKIP=0)
    for case in root.iter('testcase'):
        status = ('ERROR' if case.find('error') is not None else
                  'FAIL' if case.find('failure') is not None else
                  'SKIP' if case.find('skipped') is not None else 'PASS')
        counts[status] += 1
    return counts


def main():
    out = ROOT/'docs/bao_cao_h07/evidence'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6])
    out.mkdir(parents=True)
    protected = {str(p.relative_to(ROOT)): sha256(p) for p in [ROOT/'data/paths_synthetic.csv', ROOT/'artifacts/model.joblib',
                 ROOT/'docs/evaluations/20261116T154448Z_7a27a7/improved_model.joblib', ROOT/'instance/events.sqlite3'] if p.is_file()}
    runtime = create_runtime(ROOT, 'acceptance')
    env = runtime_environment(runtime)
    steps = [('pytest', ['-m', 'pytest', '-q', '-rs', '-W', 'error::sklearn.exceptions.InconsistentVersionWarning',
                        '-p', 'no:cacheprovider', '--basetemp='+str(runtime['basetemp']),
                        '--junitxml='+str(out/'pytest.xml')]),
             ('dashboard_tcp', ['tools/verify_evaluation_http.py']),
             ('download_tcp', ['tools/verify_tcp.py']),
             ('performance', ['tools/h07_acceptance.py']),
             ('symlinks', ['tools/check_symlinks.py']),
             ('audit', ['tools/audit_project.py', '--output', str(out/'audit'), '--repeats', '7'])]
    results = {}
    for name, args in steps:
        completed = subprocess.run([sys.executable, *args], cwd=ROOT, env=env, capture_output=True,
                                   text=True, encoding='utf-8', errors='replace', timeout=240)
        (out/(name+'.stdout.txt')).write_text(completed.stdout, encoding='utf-8')
        (out/(name+'.stderr.txt')).write_text(completed.stderr, encoding='utf-8')
        results[name] = {'returncode': completed.returncode, 'command': [sys.executable, *args]}
        print(name, 'exit', completed.returncode, flush=True)
    if (out/'pytest.xml').is_file():
        results['pytest']['junit_counts'] = pytest_counts(out/'pytest.xml')
        results['pytest']['counting_note'] = 'Serialized JUnit testcase nodes only; console subtest totals are retained separately and not added here.'
    cases = []
    def locate(step):
        text = (out/(step+'.stdout.txt')).read_text(encoding='utf-8')
        found = re.findall(r'^Evidence:\s*(.+)$', text, re.M)
        if not found:
            return None
        path = Path(found[-1].strip().replace('\\', '/'))
        return path if path.is_absolute() else ROOT/path
    download = locate('download_tcp')
    if download:
        results['download_tcp']['evidence'] = str(download.relative_to(ROOT))
        results['download_tcp']['counts'] = json.loads((download/'summary.json').read_text())['totals']
        for file in sorted(download.glob('TC*.json')):
            row = json.loads(file.read_text(encoding='utf-8'))
            cases.append({'TC': row['tc'], 'suite': 'download_tcp', 'input': row.get('uri', 'symlink fixture'),
                          'expected_http': row.get('expected_http', 403), 'actual_http': row.get('actual_http'),
                          'result': row['result'], 'evidence': str(file.relative_to(ROOT))})
    dashboard = locate('dashboard_tcp')
    if dashboard:
        proof = json.loads(dashboard.read_text(encoding='utf-8'))
        results['dashboard_tcp'].update(evidence=str(dashboard.relative_to(ROOT)), passed=proof['passed'], failed=proof['failed'])
        for i, check in enumerate(proof['checks'], 1):
            cases.append({'TC': f'WEB{i:02}', 'suite': 'dashboard_tcp',
                          'input': check['method']+' '+check['path']+' '+json.dumps(check.get('public_form_fields', {})),
                          'expected_http': check['expected_http'], 'actual_http': check['actual_http'],
                          'result': 'PASS' if check['pass'] else 'FAIL', 'evidence': str(dashboard.relative_to(ROOT))+f'#check-{i}'})
    performance = locate('performance')
    if performance:
        results['performance']['evidence'] = str(performance.relative_to(ROOT))
        data = json.loads((performance/'performance.json').read_text())
        results['performance'].update(requests=data['http_requests'], failures=data['failures'], sqlite_rows=data['sqlite_rows'])
    summary = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'steps': results,
               'test_runtime': {k: str(v.relative_to(ROOT)) for k, v in runtime.items()},
               'protected_sha256_before': protected,
               'protected_unchanged': {p: sha256(ROOT/p) == digest for p, digest in protected.items()},
               'note': 'Zero process exit for symlink probe does not mean PASS: inspect per-case SKIP/1314. No model deployment or merging.'}
    (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    with (out/'http_test_cases.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['TC','suite','input','expected_http','actual_http','result','evidence'])
        writer.writeheader()
        writer.writerows(cases)
    (out/'manifest.json').write_text(json.dumps({p.relative_to(out).as_posix(): sha256(p) for p in out.rglob('*') if p.is_file()}, indent=2), encoding='utf-8')
    print('Acceptance evidence:', out.relative_to(ROOT), flush=True)
    return int(any(r['returncode'] for r in results.values()) or not all(summary['protected_unchanged'].values()))


if __name__ == '__main__':
    raise SystemExit(main())
