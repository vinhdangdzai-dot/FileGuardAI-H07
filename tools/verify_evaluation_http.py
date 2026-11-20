"""Verify the latest real evaluation page and plots over localhost TCP."""
import hashlib
from contextlib import nullcontext
import http.client
import json
from pathlib import Path
import secrets
import re
import sys
import threading
from urllib.parse import urlencode, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from werkzeug.serving import make_server
from werkzeug.security import generate_password_hash
from app import create_app
from tools.mfa_fixture import Authenticator


def main():
    root = ROOT / 'docs/evaluations'
    run = json.loads((root / 'latest.json').read_text())['run']
    results = json.loads((root / run / 'results.json').read_text(encoding='utf-8'))
    evidence = {'run': run, 'transport': 'TCP localhost', 'checks': []}
    # Preserve the test database as evidence, avoiding Windows cleanup of a
    # SQLite connection that may remain alive until Python garbage collection.
    database_folder = root / ('http_' + secrets.token_hex(6))
    database_folder.mkdir()
    evidence['database'] = str(database_folder / 'events.sqlite3')
    with nullcontext(database_folder) as tmp:
        password = secrets.token_hex(16)
        auditor_password = secrets.token_hex(16)
        app = create_app({'TESTING':True,'CSRF_ENABLED':True,'SECRET_KEY':secrets.token_hex(32),
                          'DATABASE': Path(tmp) / 'events.sqlite3', 'ADMIN_HASH_FILE':Path(tmp)/'admin_password.hash', 'AUDITOR_HASH_FILE':Path(tmp)/'auditor_password.hash', 'ADMIN_PASSWORD': password,
                          'AUDITOR_PASSWORD_HASH': generate_password_hash(auditor_password)})
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
                if body:
                    public = parse_qs(body)
                    check['public_form_fields'] = {k: v for k, v in public.items()
                                                   if k in {'kind', 'role', 'action', 'ml_label', 'http_status', 'start', 'end'}}
                evidence['checks'].append(check)
                return content, dict(response.getheaders()), check
            finally:
                connection.close()

        try:
            request('/dashboard/ai-evaluation', 302)
            request('/dashboard/ai-evaluation/chart/metrics.png?run=' + run, 302)
            request('/login', 403, 'POST', urlencode({'password': password}))
            form, _, _ = request('/login', 200)
            token = re.search(rb'name="csrf_token" value="([^"]+)"', form).group(1).decode()
            _, headers, _ = request('/login', 302, 'POST', urlencode({'password': password, 'csrf_token': token}))
            cookie = headers['Set-Cookie'].split(';', 1)[0]
            mfa_form, _, _ = request('/login/mfa', 200)
            mfa_form=mfa_form.decode('utf-8')
            authenticator=Authenticator()
            mfa_token=re.search(r'name="csrf_token" value="([^"]+)"',mfa_form)[1]
            codes, _, _=request('/login/mfa',200,'POST',urlencode({'csrf_token':mfa_token,'code':authenticator.factor(mfa_form)}))
            authenticator.remember(codes.decode('utf-8'))
            body, _, check = request('/dashboard/ai-evaluation', 200)
            token = re.search(rb'name="csrf_token" value="([^"]+)"', body).group(1).decode()
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
            training, _, training_check = request('/dashboard/ai-training', 200)
            training_check['metadata_present'] = b'view_max_parent_components' in training and b'10000' in training
            training_check['pass'] &= training_check['metadata_present']
            for kind in ('dataset', 'v1', 'v2'):
                csv_data, _, check = request('/dashboard/ai-training/export', 200, 'POST', urlencode({'kind': kind, 'csrf_token': token}))
                check['csv_header_present'] = (b'path,label,family' in csv_data if kind == 'dataset' else b'feature,coefficient,train_mean,train_scale' in csv_data)
                check['pass'] &= check['csv_header_present']
            request('/dashboard/ai-training/export', 403, 'POST', urlencode({'kind': 'dataset'}))
            request('/dashboard/ai-training/export', 400, 'POST', urlencode({'kind': '../../secret', 'csrf_token': token}))
            body, _, check = request('/download?path=baocao.pdf', 200)
            check['exact_file'] = body == (ROOT / 'shared_files/baocao.pdf').read_bytes()
            check['pass'] &= check['exact_file']
            request('/download?path=..%2fsecret.txt', 403)
            request('/download?path=__evaluation_missing__.txt', 404)
            request('/dashboard?action=BLOCK', 200)
            request('/dashboard?action=invalid', 400)
            request('/dashboard?ml_label=suspicious&http_status=403', 200)
            request('/dashboard?start=2026-01-01T00:00:00Z&end=2027-01-01T00:00:00Z', 200)
            request('/dashboard?ml_label=invalid', 400)
            request('/dashboard?http_status=999', 400)
            request('/dashboard?start=2027-01-01&end=2026-01-01', 400)
            request('/dashboard/logs/export', 403, 'POST', '')
            exported, _, exported_check = request('/dashboard/logs/export', 200, 'POST', urlencode({'csrf_token': token}))
            exported_check['csv_header_present'] = b'requested_path' in exported and exported.startswith(b'\xef\xbb\xbf')
            exported_check['pass'] &= exported_check['csv_header_present']
            request('/logout', 403, 'POST', '')
            request('/logout', 302, 'POST', urlencode({'csrf_token': token}))
            request('/dashboard/ai-evaluation', 302)
            form, _, _ = request('/login', 200)
            token = re.search(rb'name="csrf_token" value="([^"]+)"', form).group(1).decode()
            request('/login', 302, 'POST', urlencode({'role': 'auditor', 'password': auditor_password, 'csrf_token': token}))
            request('/dashboard', 403)
            form, _, _ = request('/', 200)
            token = re.search(rb'name="csrf_token" value="([^"]+)"', form).group(1).decode()
            request('/dashboard/logs/export', 403, 'POST', urlencode({'csrf_token': token}))
            request('/dashboard/ai-evaluation', 403)
            request('/dashboard/ai-training', 403)
            request('/dashboard/ai-training/export', 403, 'POST', urlencode({'kind': 'dataset', 'csrf_token': token}))
            request('/logout', 302, 'POST', urlencode({'csrf_token': token}))
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()
    evidence['passed'] = sum(c['pass'] for c in evidence['checks'])
    evidence['failed'] = sum(not c['pass'] for c in evidence['checks'])
    # Preserve every prior TCP evidence file, even for the same frozen run.
    target = root / ('dashboard_http_' + run + '_' + database_folder.name + '.json')
    target.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(f"TCP dashboard: {evidence['passed']} PASS, {evidence['failed']} FAIL")
    print('Evidence:', target)
    return int(evidence['failed'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
