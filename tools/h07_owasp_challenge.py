"""Small public OWASP challenge set; models and threshold remain frozen.

Separate from LFISuite corpus. Correlated public variants, not real traffic.
"""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.request import Request, urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import joblib
from ml.evaluate import sha256, write_csv
from ml.improve import evaluate_rows, plots, read_csv, json_write
from ml.external_corpus import canonical_key


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6]
    source = ROOT / 'data/external' / ('owasp_' + stamp)
    source.mkdir(parents=True)
    url = 'https://community.owasp.org/attacks/Path_Traversal'
    # Public examples, fixed BEFORE HTTP fetch or prediction. No transformations.
    public = ['%2e%2e%2f', '%2e%2e/', '..%2f', '%2e%2e%5c', '%2e%2e\\',
              '..%5c', '%252e%252e%255c', '..%255c', '..%c0%af', '..%c1%9c']
    origin = ROOT / 'docs/evaluations/20261116T154448Z_7a27a7'
    baseline_hash = sha256(origin / 'baseline_model.joblib')
    improved_hash = sha256(origin / 'improved_model.joblib')
    json_write(source / 'protocol.json', {'payloads': public, 'threshold': .5,
               'baseline_sha256': baseline_hash, 'improved_sha256': improved_hash,
               'labels': '1 for verbatim OWASP attack-intent examples (legacy overlong included, not exploit success); 0 for first ten SHA-ordered real Starlette paths from new corpus; no prediction-based selection',
               'created_at_utc': datetime.now(timezone.utc).isoformat()})
    with urlopen(Request(url, headers={'User-Agent': 'FileGuardAI-H07-research'}), timeout=20) as r:
        body = r.read()
    visible = html.unescape(re.sub('<[^>]+>', '', body.decode('utf-8'))).lower()
    if any(value.lower() not in visible for value in public):
        raise ValueError('Public source no longer contains every predeclared example')
    # Store only the short cited examples, source URL and page hash, not a copy
    # of the entire copyrighted article.
    rows = [dict(path=p, label='1', family='owasp_attack_examples', source_url=url,
                 label_reason='verbatim_public_attack_intent_example') for p in public]
    previous = ROOT / 'data/external/h07_20261116T171550Z_5b8ba9/cases.csv'
    controls = sorted((r for r in read_csv(previous) if r['label'] == '0'),
                      key=lambda r: hashlib.sha256(r['path'].encode()).hexdigest())[:10]
    rows += [dict(path=r['path'], label='0', family='starlette_control', source_url=r['source_url'],
                  label_reason='relative_public_repository_path') for r in controls]
    original = read_csv(ROOT / 'data/paths_synthetic.csv')
    overlap = {canonical_key(r['path']) for r in rows} & {canonical_key(r['path']) for r in original}
    if overlap:
        raise ValueError('Challenge overlaps original training/test corpus')
    write_csv(source / 'cases.csv', rows, ['path', 'label', 'family', 'source_url', 'label_reason'])
    metadata = {'source_url': url, 'source_page_sha256': hashlib.sha256(body).hexdigest(),
                'cases_sha256': sha256(source / 'cases.csv'), 'rows': len(rows),
                'canonical_overlap_original': len(overlap),
                'coverage': '6 single-encoding, 2 double-encoding, 2 legacy overlong attack examples; 10 shared Starlette controls',
                'limitations': 'Twenty illustrative lexical examples, related variants, shared controls; legacy overlong is attack intent, not valid modern UTF-8 traversal. Not a blind real-world benchmark.'}
    json_write(source / 'manifest.json', metadata)
    model1, model2 = joblib.load(origin / 'baseline_model.joblib'), joblib.load(origin / 'improved_model.joblib')
    measured, predictions = evaluate_rows(rows, model1, model2, 15)
    latest = ROOT / 'docs/evaluations/latest.json'
    old = json.loads(latest.read_text())['run']
    result = json.loads((ROOT / 'docs/evaluations' / old / 'results.json').read_text(encoding='utf-8'))
    result['created_at_utc'] = datetime.now(timezone.utc).isoformat()
    result['datasets']['owasp_challenge'] = measured
    result['owasp_challenge_manifest'] = metadata
    result.setdefault('dataset_descriptions', {})['owasp_challenge'] = 'OWASP public examples + Starlette controls; challenge minh họa, không traffic thực'
    out = ROOT / 'docs/evaluations' / stamp
    out.mkdir()
    json_write(out / 'results.json', result)
    write_csv(out / 'owasp_predictions.csv', predictions, list(predictions[0]))
    plots(result, out)
    shutil.copy2(latest, out / 'previous_latest.json')
    json_write(out / 'manifest.json', {p.name: sha256(p) for p in out.iterdir() if p.is_file()})
    if sha256(origin / 'baseline_model.joblib') != baseline_hash or sha256(origin / 'improved_model.joblib') != improved_hash:
        raise RuntimeError('Frozen models changed')
    temporary = latest.with_suffix('.' + uuid.uuid4().hex + '.tmp')
    json_write(temporary, {'run': out.name})
    temporary.replace(latest)
    print('Source:', source.relative_to(ROOT))
    print('Evaluation:', out.relative_to(ROOT))
    print(json.dumps(measured['models'], indent=2))


if __name__ == '__main__':
    main()
