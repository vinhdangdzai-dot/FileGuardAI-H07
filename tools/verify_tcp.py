"""Reproducible localhost TCP checks with SQLite and per-case evidence.

Run from project root: python tools/verify_tcp.py
Uses real shared_files and the shipped model; keeps test logs in docs/evidence.
Never opens the user's events database or changes existing public files.
"""
from __future__ import annotations

import csv
from contextlib import closing
import hashlib
import http.client
import json
import math
import platform
import sqlite3
import subprocess
import sys
import threading
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import sklearn
from sklearn.exceptions import InconsistentVersionWarning
from werkzeug.serving import make_server

from app import create_app
from app.ml_features import extract_features


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    evidence = ROOT / 'docs' / 'evidence' / ('tcp_' + stamp + '_' + uuid.uuid4().hex[:6])
    evidence.mkdir(parents=True)
    database = evidence / 'events.sqlite3'
    shared = ROOT / 'shared_files'
    sentinel = evidence / 'outside_secret.txt'
    secret = ('OUTSIDE-SECRET-' + uuid.uuid4().hex).encode()
    sentinel.write_bytes(secret)
    # Verify loading and actual inference with version warnings treated as errors.
    with warnings.catch_warnings():
        warnings.simplefilter('error', InconsistentVersionWarning)
        model = joblib.load(ROOT / 'artifacts/model.joblib')
        model.predict_proba([extract_features('baocao.pdf')])
    app = create_app({'FILES_ROOT': shared, 'DATABASE': database, 'ADMIN_HASH_FILE':database.parent/'admin_password.hash', 'AUDITOR_HASH_FILE':database.parent/'auditor_password.hash',
                      'ADMIN_PASSWORD': uuid.uuid4().hex})
    server = make_server('127.0.0.1', 5000, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    rows = []

    def run_case(code, name, query, expected, expected_bytes=None):
        uri = '/download?path=' + query
        decoded = parse_qs('path=' + query, keep_blank_values=True)['path'][0]
        with closing(sqlite3.connect(database)) as db:
            before = db.execute('SELECT COALESCE(MAX(id),0) FROM access_logs').fetchone()[0]
        con = http.client.HTTPConnection('127.0.0.1', 5000, timeout=10)
        started = datetime.now(timezone.utc)
        try:
            con.request('GET', uri)
            response = con.getresponse()
            body = response.read()
            status = response.status
            headers = dict(response.getheaders())
        finally:
            con.close()
        ended = datetime.now(timezone.utc)
        with closing(sqlite3.connect(database)) as db:
            db.row_factory = sqlite3.Row
            logs = [dict(r) for r in db.execute('SELECT * FROM access_logs WHERE id > ?', (before,))]
        checks = {'http': status == expected, 'no_external_secret': secret not in body,
                  'exact_content': expected_bytes is None or body == expected_bytes,
                  'one_sqlite_row': len(logs) == 1}
        if len(logs) == 1:
            log = logs[0]
            probability = (float(model.predict_proba([extract_features(decoded)])[0][1])
                           if len(decoded) <= 4096 else None)
            created = datetime.fromisoformat(log['created_at'])
            checks.update({
                'ip': log['client_ip'] == '127.0.0.1',
                'path': log['requested_path'] == decoded[:4096],
                'ml_score': (abs(log['ml_score'] - probability) < 1e-12 if probability is not None
                             else log['ml_score'] is None),
                'ml_label': log['ml_label'] == (('suspicious' if probability >= .5 else 'benign')
                                              if probability is not None else 'skipped'),
                'decision': log['action'] == {200: 'ALLOW', 403: 'BLOCK', 404: 'MISS'}[expected],
                'logged_http': log['http_status'] == status,
                'duration_ms': math.isfinite(log['duration_ms']) and log['duration_ms'] >= 0,
                'timestamp_utc': created.utcoffset().total_seconds() == 0
                    and started.timestamp() - 1 <= created.timestamp() <= ended.timestamp(),
                'reason': bool(log['reason']),
            })
        result = 'PASS' if all(checks.values()) else 'FAIL'
        detail = {'tc': code, 'name': name, 'uri': uri, 'framework_path': decoded,
                  'expected_http': expected, 'actual_http': status, 'result': result,
                  'checks': checks, 'headers': headers, 'response_length': len(body),
                  'response_sha256': hashlib.sha256(body).hexdigest(), 'sqlite_rows': logs,
                  'started_utc': started.isoformat(), 'ended_utc': ended.isoformat()}
        (evidence / (code + '.json')).write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding='utf-8')
        rows.append({'TC': code, 'Input': uri, 'Expected': f'HTTP {expected}; SQLite correct; no secret',
                     'Actual': f'HTTP {status}; ' + ('all checks true' if result == 'PASS' else str(checks)),
                     'Result': result, 'Evidence': code + '.json'})
        print(code, result, status, name)

    def skip(code, name, exc):
        reason = f'{type(exc).__name__}: {exc}'
        (evidence / (code + '.json')).write_text(json.dumps(
            {'tc': code, 'result': 'SKIP', 'reason': reason}, ensure_ascii=False, indent=2), encoding='utf-8')
        rows.append({'TC': code, 'Input': name, 'Expected': 'HTTP 403; no external content',
                     'Actual': reason, 'Result': 'SKIP', 'Evidence': code + '.json'})

    links = []
    try:
        smoke = subprocess.run([sys.executable, str(ROOT / 'tools/smoke_http.py')],
                               cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        (evidence / 'smoke_http.txt').write_text(smoke.stdout + smoke.stderr, encoding='utf-8')
        cases = [
            ('TC01', 'valid file', quote('baocao.pdf'), 200, (shared / 'baocao.pdf').read_bytes()),
            ('TC02', 'Unicode and spaces', quote('báo cáo tốt nghiệp.pdf'), 200,
             (shared / 'báo cáo tốt nghiệp.pdf').read_bytes()),
            ('TC03', 'subdirectory', quote('tailieu/chuong1.pdf'), 200,
             (shared / 'tailieu/chuong1.pdf').read_bytes()),
            ('TC04', 'parent directory', '../' + quote(sentinel.relative_to(ROOT).as_posix()), 403, None),
            ('TC05', 'parent component alone', '..', 403, None),
            ('TC06', 'Windows parent separator', quote('..\\' + str(sentinel.relative_to(ROOT))), 403, None),
            ('TC07', 'absolute existing external file', quote(str(sentinel)), 403, None),
            ('TC08', 'POSIX absolute', '/etc/passwd', 403, None),
            ('TC09', 'Windows absolute', quote('C:\\Windows\\win.ini'), 403, None),
            ('TC10', 'UNC', quote('\\\\server\\share\\secret.txt'), 403, None),
            ('TC11', 'URL encoding', '%2e%2e%2f' + quote(sentinel.relative_to(ROOT).as_posix()), 403, None),
            ('TC12', 'double encoding / form encoded payload', '%252e%252e%252fsecret.txt', 403, None),
            ('TC13', 'triple encoding', '%25252e%25252e%25252fsecret.txt', 403, None),
            ('TC14', 'encoded Windows separator', '%2e%2e%5csecret.txt', 403, None),
            ('TC15', 'missing file', 'h07_missing_' + uuid.uuid4().hex + '.txt', 404, None),
            ('TC16', 'encoded missing Unicode', quote('tailieu/không tồn tại ' + uuid.uuid4().hex + '.txt'), 404, None),
            ('TC17', 'traversal in subdirectory', 'tailieu/../../secret.txt', 403, None),
            ('TC18', 'null encoding', '%00secret.txt', 403, None),
            ('TC19', 'directory is not a file', 'tailieu', 403, None),
            ('TC25', 'Windows superscript device', quote('COM¹.txt'), 403, None),
            ('TC26', 'Windows console device', quote('CONIN$'), 403, None),
            ('TC27', 'duplicate path parameters', 'baocao.pdf&path=../secret.txt', 403, None),
            ('TC28', 'oversized path skips advisory scoring', 'x' * 5000, 403, None),
            ('TC29', 'alternate data stream', quote('baocao.pdf:stream'), 403, None),
            ('TC30', 'trailing space component', quote('.. /secret.txt'), 403, None),
            ('TC31', 'control character', '%0asecret.txt', 403, None),
            ('TC32', 'encoded absolute slash', '%2fsecret.txt', 403, None),
            ('TC33', 'current directory component', './baocao.pdf', 403, None),
            ('TC34', 'mixed separators', quote('tailieu/..\\secret.txt'), 403, None),
            ('TC35', 'missing nested file', 'tailieu/missing/subdir.txt', 404, None),
            ('TC36', 'regular file used as parent', 'baocao.pdf/child.txt', 404, None),
        ]
        for case in cases:
            run_case(*case)
        # Recheck all three previously skipped symlink scenarios via real TCP.
        token = '__tcp_' + uuid.uuid4().hex
        for code, directory in [('TC20', False), ('TC21', False), ('TC22', True)]:
            link = shared / (token + code)
            try:
                link.symlink_to(sentinel.parent if directory else sentinel, target_is_directory=directory)
            except (OSError, NotImplementedError) as exc:
                skip(code, 'symlink directory' if directory else 'symlink file', exc)
                continue
            links.append(link)
            run_case(code, 'symlink escape', quote(link.name + ('/outside_secret.txt' if directory else '')), 403)
        junction = shared / (token + '_junction')
        process = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(sentinel.parent)], capture_output=True)
        if process.returncode:
            skip('TC23', 'Windows junction', OSError(repr(process.stderr)))
        else:
            links.append(junction)
            run_case('TC23', 'junction existing external file', quote(junction.name + '/outside_secret.txt'), 403)
            run_case('TC24', 'junction missing external file', quote(junction.name + '/missing.txt'), 403)
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
        # Only remove links created here, after validating their exact parent.
        for link in links:
            assert link.parent.resolve() == shared.resolve()
            if link.is_symlink():
                link.unlink()
            else:
                link.rmdir()
    with (evidence / 'test_cases.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['TC', 'Input', 'Expected', 'Actual', 'Result', 'Evidence'])
        writer.writeheader()
        writer.writerows(rows)
    table = ['# TCP test cases', '', '| TC | Input | Expected | Actual | Result | Evidence |',
             '|---|---|---|---|---|---|']
    for row in rows:
        cells = [str(row[k]).replace('|', '&#124;').replace('\n', ' ') for k in ['TC', 'Input', 'Expected', 'Actual', 'Result']]
        table.append('| ' + ' | '.join(cells) + f" | [{row['Evidence']}]({row['Evidence']}) |")
    (evidence / 'test_cases.md').write_text('\n'.join(table) + '\n', encoding='utf-8')
    summary = {'started_run_utc': stamp, 'host': '127.0.0.1', 'port': 5000,
               'transport': 'http.client -> TCP -> Werkzeug WSGI -> Flask',
               'python': platform.python_version(), 'platform': platform.platform(),
               'sklearn': sklearn.__version__, 'shared_files': str(shared), 'database': str(database),
               'model_sha256': hashlib.sha256((ROOT / 'artifacts/model.joblib').read_bytes()).hexdigest(),
               'model_load_InconsistentVersionWarning': False,
               'smoke_exit_code': smoke.returncode,
               'totals': {key: sum(r['Result'] == key for r in rows) for key in ['PASS', 'FAIL', 'SKIP']}}
    (evidence / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    print('Evidence:', evidence)
    return int(smoke.returncode != 0 or summary['totals']['FAIL'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
