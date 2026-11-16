"""Repeated TCP performance and prevention measurements on owned fixtures."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from contextlib import closing
import http.client
import json
from pathlib import Path
import sqlite3
import sys
import threading
import time
from urllib.parse import quote
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from werkzeug.serving import make_server, WSGIRequestHandler
from app import create_app


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


def main():
    out = ROOT / 'docs/h07/evidence' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6])
    base = out / 'fixtures/shared_files'
    (base / 'tài liệu').mkdir(parents=True)
    (base / 'ok.txt').write_bytes(b'PUBLIC')
    (base / 'tài liệu/báo cáo.txt').write_bytes(b'UNICODE-CONTENT')
    secret = ('OUTSIDE-' + uuid.uuid4().hex).encode()
    outside = out / 'fixtures/secret.txt'
    outside.write_bytes(secret)
    db = out / 'events.sqlite3'
    app = create_app({'FILES_ROOT': base, 'DATABASE': db, 'ADMIN_PASSWORD': uuid.uuid4().hex})
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    cases = [('ok.txt', 200, b'PUBLIC'), (quote('tài liệu/báo cáo.txt'), 200, b'UNICODE-CONTENT'),
             ('missing.txt', 404, None), ('../secret.txt', 403, None),
             ('%252e%252e%252fsecret.txt', 403, None),
             (quote(str(outside.resolve())), 403, None), ('%00secret.txt', 403, None),
             ('..%5csecret.txt', 403, None)]

    def probe(case):
        query, expected, content = case
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=15)
        start = time.perf_counter()
        try:
            connection.request('GET', '/download?path=' + query)
            response = connection.getresponse()
            body = response.read()
            return {'query': query, 'expected': expected, 'actual': response.status,
                    'latency_ms': (time.perf_counter() - start) * 1000,
                    'no_leak': secret not in body, 'exact_public_content': content is None or body == content}
        finally:
            connection.close()

    trials = []
    try:
        for trial in range(3):
            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=4) as pool:
                rows = list(pool.map(probe, cases * 6))
            elapsed = time.perf_counter() - start
            malicious = [r for r in rows if r['expected'] == 403]
            latency = [r['latency_ms'] for r in rows]
            trials.append({'trial': trial + 1, 'requests': rows, 'wall_seconds': elapsed,
                           'throughput_rps': len(rows) / elapsed,
                           'latency_ms_p50_p95_p99': [float(np.percentile(latency, p)) for p in (50, 95, 99)],
                           'policy_violations': len(malicious),
                           'blocked_violations': sum(r['actual'] == 403 for r in malicious),
                           'prevention_rate': sum(r['actual'] == 403 for r in malicious) / len(malicious),
                           'leaks': sum(not r['no_leak'] for r in rows),
                           'failures': sum(r['actual'] != r['expected'] or not r['exact_public_content'] or not r['no_leak'] for r in rows)})
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
    with closing(sqlite3.connect(db)) as con:
        log_count = con.execute('SELECT COUNT(*) FROM access_logs').fetchone()[0]
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
    result = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'workers': 4,
              'trials': trials, 'http_requests': sum(len(t['requests']) for t in trials),
              'sqlite_rows': log_count, 'sqlite_integrity': integrity,
              'failures': sum(t['failures'] for t in trials),
              'method': '3 trials x48 requests; 4 workers; TCP localhost; end-to-end body read; includes Flask, model and SQLite; no production throughput claim'}
    (out / 'performance.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('Evidence:', out.relative_to(ROOT))
    print(json.dumps({k: v for k, v in result.items() if k != 'trials'}, indent=2))
    for t in trials:
        print(t['trial'], 'RPS', round(t['throughput_rps'], 2), 'p50/p95/p99 ms', t['latency_ms_p50_p95_p99'],
              'blocked', t['blocked_violations'], '/', t['policy_violations'])
    return int(result['failures'] > 0 or result['http_requests'] != log_count or integrity != 'ok')


if __name__ == '__main__':
    raise SystemExit(main())
