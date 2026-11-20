"""Harmless localhost HTTP verification for H07 application-layer IPS."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-root', type=Path, default=ROOT/'docs/h07/evidence')
    args = parser.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=args.evidence_root/f'ips_pi31_{stamp}'
    files=out/'fixtures/shared_files';files.mkdir(parents=True)
    (files/'ok.txt').write_bytes(b'HARMLESS-PUBLIC-FIXTURE')
    outside=out/'fixtures/outside.txt';outside.write_bytes(b'OUTSIDE-SENTINEL-NEVER-RETURN')
    from app import create_app
    from app.database import ips_statistics
    app=create_app({'TESTING':True,'SECRET_KEY':'ips-http-fixture-only','CSRF_ENABLED':True,
                    'FILES_ROOT':files,'DATABASE':out/'events.sqlite3',
                    'MODEL_PATH':ROOT/'artifacts/model.joblib','ADMIN_PASSWORD':'fixture-password'})
    server=make_server('127.0.0.1',0,app,threaded=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    cases=[('valid','ok.txt',200),('missing','not-found.txt',404),('parent','../outside.txt',403),
           ('windows','..\\outside.txt',403),('absolute','C:/Windows/win.ini',403),
           ('encoded','%2e%2e%2foutside.txt',403),('double_encoded','%252e%252e%252foutside.txt',403)]
    rows=[]
    try:
        for code,path,expected in cases:
            connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
            # Keep percent sequences verbatim; quote all other structural input.
            target='/download?path='+quote(path,safe='%')
            connection.request('GET',target)
            response=connection.getresponse();body=response.read();connection.close()
            rows.append({'case':code,'input':path,'expected':expected,'actual':response.status,
                         'outside_exposed':b'OUTSIDE-SENTINEL' in body,
                         'pass':response.status==expected and b'OUTSIDE-SENTINEL' not in body})
    finally:
        server.shutdown();thread.join(timeout=5)
        app.extensions['recovery_mail'].close();app.extensions['ai_explanations'].close()
    stats=ips_statistics(app.config['DATABASE'])
    report={'generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'bind':'127.0.0.1','real_model_sha256':hashlib.sha256((ROOT/'artifacts/model.joblib').read_bytes()).hexdigest(),
            'cases':rows,'statistics':stats,'pass':all(row['pass'] for row in rows)}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':str(out),'pass':report['pass'],'passed':sum(r['pass'] for r in rows),
                      'failed':sum(not r['pass'] for r in rows)},ensure_ascii=True))
    return 0 if report['pass'] else 1


if __name__=='__main__':
    raise SystemExit(main())
