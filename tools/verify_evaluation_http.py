"""Verify the latest real evaluation page and plots over localhost TCP."""
import hashlib
from contextlib import nullcontext
import http.client
import json
from pathlib import Path
import secrets
import sys
import threading
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from werkzeug.serving import make_server
from app import create_app


def main():
    root = ROOT / 'docs/evaluations'
    run = json.loads((root / 'latest.json').read_text())['run']
    results = json.loads((root / run / 'results.json').read_text())
    evidence = {'run': run, 'transport': 'TCP localhost', 'checks': []}
    # Preserve the test database as evidence, avoiding Windows cleanup of a
    # SQLite connection that may remain alive until Python garbage collection.
    database_folder = root / ('http_' + secrets.token_hex(6))
    database_folder.mkdir()
    evidence['database'] = str(database_folder / 'events.sqlite3')
    with nullcontext(database_folder) as tmp:
        password = secrets.token_hex(16)
        app = create_app({'DATABASE': Path(tmp) / 'events.sqlite3', 'ADMIN_PASSWORD': password})
        server = make_server('127.0.0.1', 0, app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        cookie = None

        def request(path, expected, method='GET', body=None):
            nonlocal cookie
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
            headers = {'Cookie': cookie} if cookie else {}
            if body is not None:
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
            try:
                connection.request(method, path, body=body, headers=headers)
                response = connection.getresponse()
                content = response.read()
                if response.getheader('Set-Cookie'):
                    cookie = response.getheader('Set-Cookie').split(';', 1)[0]
                check = {'path': path, 'method': method, 'expected_http': expected,
                         'actual_http': response.status, 'pass': response.status == expected,
                         'sha256': hashlib.sha256(content).hexdigest()}
                evidence['checks'].append(check)
                return content, dict(response.getheaders()), check
            finally:
                connection.close()

        try:
            request('/dashboard/ai-evaluation', 302)
            request('/dashboard/ai-evaluation/chart/metrics.png?run=' + run, 302)
            _, headers, _ = request('/login', 302, 'POST', urlencode({'password': password}))
            cookie = headers['Set-Cookie'].split(';', 1)[0]
            body, _, check = request('/dashboard/ai-evaluation', 200)
            check['run_present'] = run.encode() in body
            check['metrics_present'] = all(f'{results["logistic_regression"][k]:.4f}'.encode() in body
                                           for k in ('accuracy', 'precision', 'recall', 'f1'))
            check['pass'] &= check['run_present'] and check['metrics_present']
            if results.get('improved_logistic_regression'):
                check['comparison_metrics_present'] = all(
                    f'{metrics[k]:.4f}'.encode() in body
                    for dataset in results['datasets'].values()
                    for metrics in dataset['models'].values()
                    for k in ('accuracy', 'precision', 'recall', 'f1'))
                check['comparison_labels_present'] = b'LR v1' in body and b'LR v2' in body
                check['pass'] &= check['comparison_metrics_present'] and check['comparison_labels_present']
            for name in ('confusion_matrix.png', 'metrics.png', 'latency.png'):
                body, _, check = request('/dashboard/ai-evaluation/chart/' + name + '?run=' + run, 200)
                check['exact_png'] = body == (root / run / name).read_bytes()
                check['pass'] &= check['exact_png']
            request('/dashboard/ai-evaluation/chart/model.joblib?run=' + run, 404)
            request('/dashboard', 200)
            body, _, check = request('/download?path=baocao.pdf', 200)
            check['exact_file'] = body == (ROOT / 'shared_files/baocao.pdf').read_bytes()
            check['pass'] &= check['exact_file']
            request('/download?path=..%2fsecret.txt', 403)
            request('/download?path=__evaluation_missing__.txt', 404)
            request('/logout', 302, 'POST', '')
            request('/dashboard/ai-evaluation', 302)
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()
    evidence['passed'] = sum(c['pass'] for c in evidence['checks'])
    evidence['failed'] = sum(not c['pass'] for c in evidence['checks'])
    target = root / ('dashboard_http_' + run + '.json')
    target.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(f"TCP dashboard: {evidence['passed']} PASS, {evidence['failed']} FAIL")
    print('Evidence:', target)
    return int(evidence['failed'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
