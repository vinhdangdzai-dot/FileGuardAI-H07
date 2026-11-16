"""Collect another source-disjoint corpus AFTER v2 freeze; evaluate only.

No fitting or model-dependent selection. This is a source-derived lexical
benchmark, not an independently human-labelled real traffic dataset.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from urllib.request import Request, urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import joblib
from ml.external_corpus import canonical_key, label_reason
from ml.improve import evaluate_rows, plots, read_csv, json_write
from ml.evaluate import sha256, write_csv


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6]
    source = ROOT / 'data/external' / ('h07_' + stamp)
    source.mkdir(parents=True)
    origin = ROOT / 'docs/evaluations/20261116T154448Z_7a27a7'
    model_hashes = {name: sha256(origin / name) for name in ('baseline_model.joblib', 'improved_model.joblib')}
    frozen = {'models': model_hashes, 'selection_sha256': sha256(origin / 'selection.json'),
              'policy': 'max 200/class; canonical disjoint from original 10000 and previous external 400; public syntactic positives; Starlette relative-path controls; prefer deepest encoding per canonical group; round-robin raw/one/two decode buckets by SHA256 order; no predictions or labels from original test used for selection'}
    json_write(source / 'protocol_before_fetch.json', frozen)
    snapshots = []

    def fetch(url, name):
        with urlopen(Request(url, headers={'User-Agent': 'FileGuardAI-H07-thesis'}), timeout=20) as r:
            data = r.read()
        (source / name).write_bytes(data)
        snapshots.append({'url': url, 'file': name, 'sha256': sha256(source / name)})
        return data

    revision = '4d5e414c9631f3c12ee1ac86ff7234d848391fd3'
    url = f'https://raw.githubusercontent.com/danielmiessler/SecLists/{revision}/Fuzzing/LFI/LFI-LFISuite-pathtotest.txt'
    payloads = fetch(url, 'payloads.txt').decode('utf-8-sig')
    shutil.copy2(ROOT / 'data/external/20261116T154731Z_66a7c6/SecLists_LICENSE.txt', source / 'SecLists_LICENSE.txt')
    commit = json.loads(fetch('https://api.github.com/repos/encode/starlette/commits/0.48.0', 'starlette_commit.json'))['sha']
    tree = json.loads(fetch(f'https://api.github.com/repos/encode/starlette/git/trees/{commit}?recursive=1', 'starlette_tree.json'))
    if tree.get('truncated'):
        raise ValueError('Incomplete source tree')
    fetch(f'https://raw.githubusercontent.com/encode/starlette/{commit}/LICENSE.md', 'Starlette_LICENSE.md')
    originals = read_csv(ROOT / 'data/paths_synthetic.csv') + read_csv(ROOT / 'data/external/20261116T154731Z_66a7c6/external_cases.csv')
    excluded_keys = {canonical_key(r['path']) for r in originals}
    positives = {}
    rejected = Counter()
    for line, text in enumerate(payloads.splitlines(), 1):
        path = text.strip()
        reason = label_reason(path)
        if not reason or not path or len(path) > 4096 or canonical_key(path) in excluded_keys:
            rejected['out_of_scope_or_previously_seen'] += 1
            continue
        depth = int(reason.rsplit('_', 1)[-1])
        row = dict(path=path, label='1', family=f'public_depth_{depth}', source_url=url,
                   source_line=line, revision=revision, label_reason=reason, depth=depth)
        key = canonical_key(path)
        previous = positives.get(key)
        if previous is None or (depth, path) > (previous['depth'], previous['path']):
            positives[key] = row
    ordering = lambda r: hashlib.sha256(r['path'].encode()).hexdigest()
    buckets = {n: sorted((r for r in positives.values() if r['depth'] == n), key=ordering) for n in (0, 1, 2)}
    selected = []
    while len(selected) < 200 and any(buckets.values()):
        for n in (0, 1, 2):
            if buckets[n] and len(selected) < 200:
                selected.append(buckets[n].pop(0))
    controls = [dict(path=r['path'], label='0', family='starlette_relative',
                     source_url=f'https://github.com/encode/starlette/blob/{commit}/{r["path"]}',
                     source_line='', revision=commit, label_reason='relative_repository_path', depth=0)
                for r in tree['tree'] if r['type'] == 'blob' and not label_reason(r['path']) and canonical_key(r['path']) not in excluded_keys]
    controls = sorted(controls, key=ordering)
    n = min(len(selected), len(controls))
    if n < 10:
        raise ValueError('Insufficient independently sourced rows; no fabricated fallback')
    rows = selected[:n] + controls[:n]
    rows.sort(key=ordering)
    write_csv(source / 'cases.csv', rows, ['path', 'label', 'family', 'source_url', 'source_line', 'revision', 'label_reason', 'depth'])
    metadata = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'rows': len(rows),
                'label_counts': dict(Counter(r['label'] for r in rows)),
                'positive_decode_depth_counts': dict(Counter(r['depth'] for r in selected[:n])),
                'previous_canonical_overlap': len({canonical_key(r['path']) for r in rows} & excluded_keys),
                'internal_canonical_duplicates': len(rows) - len({canonical_key(r['path']) for r in rows}),
                'cases_sha256': sha256(source / 'cases.csv'), 'snapshots': snapshots,
                'models_frozen_before_fetch': frozen, 'source_directory': str(source.relative_to(ROOT)),
                'limitations': 'New public source, weak lexical annotation with source/label confounding; not blind human-reviewed real traffic. No model or threshold modified.'}
    json_write(source / 'manifest.json', metadata)
    baseline = joblib.load(origin / 'baseline_model.joblib')
    improved = joblib.load(origin / 'improved_model.joblib')
    measured, predictions = evaluate_rows(rows, baseline, improved, 15)
    result = json.loads((origin / 'results.json').read_text(encoding='utf-8'))
    result['created_at_utc'] = datetime.now(timezone.utc).isoformat()
    result['datasets']['external_h07'] = measured
    result['h07_source_manifest'] = metadata
    result['dataset_descriptions'] = {'external_public': 'SecLists Jhaddix + Flask (lần trước)',
                                      'external_h07': 'SecLists LFISuite + Starlette (nguồn ngoài mới)'}
    out = ROOT / 'docs/evaluations' / stamp
    out.mkdir()
    json_write(out / 'results.json', result)
    write_csv(out / 'external_h07_predictions.csv', predictions, list(predictions[0]))
    json_write(out / 'external_h07_manifest.json', metadata)
    plots(result, out)
    for name, digest in model_hashes.items():
        if sha256(origin / name) != digest:
            raise RuntimeError('Frozen model changed')
    json_write(out / 'manifest.json', {p.name: sha256(p) for p in out.iterdir() if p.is_file()})
    pointer = ROOT / 'docs/evaluations/latest.json'
    shutil.copy2(pointer, out / 'previous_latest.json')
    temporary = pointer.with_suffix('.' + uuid.uuid4().hex + '.tmp')
    json_write(temporary, {'run': out.name})
    temporary.replace(pointer)
    print('New corpus:', source.relative_to(ROOT))
    print('New evaluation:', out.relative_to(ROOT))
    print(json.dumps({'metadata': metadata, 'metrics': measured['models']}, indent=2))


if __name__ == '__main__':
    main()
