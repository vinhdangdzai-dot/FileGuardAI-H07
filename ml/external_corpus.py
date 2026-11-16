"""Collect a version-pinned public test corpus AFTER model selection freeze.

This module never imports ML features or models. Labels describe path syntax,
not exploit success. No payload is sent to a remote application.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote
from urllib.request import Request, urlopen
import uuid

from ml.evaluate import sha256, write_csv
from ml.train_model import PROJECT_ROOT


def views(path):
    raw = unicodedata.normalize('NFC', path)
    once = unquote(raw, errors='replace')
    return raw, once, unquote(once, errors='replace')


def canonical_key(path):
    return views(path)[-1].replace('\\', '/').casefold()


def label_reason(path):
    """Independent annotation policy: parent segment or absolute/drive path."""
    for depth, text in enumerate(views(path)):
        normalized = text.replace('\\', '/')
        if '..' in normalized.split('/'):
            return f'parent_component_at_decode_{depth}'
        if normalized.startswith('/'):
            return f'absolute_or_unc_at_decode_{depth}'
        if re.match(r'^[A-Za-z]:', normalized):
            return f'windows_drive_at_decode_{depth}'
    return None


def collect(run, output_root=None):
    selection = json.loads((run / 'selection.json').read_text(encoding='utf-8'))
    protocol = json.loads((run / 'protocol.json').read_text(encoding='utf-8'))
    if sha256(run / 'protocol.json') != selection['protocol_sha256']:
        raise ValueError('Protocol changed')
    now = datetime.now(timezone.utc)
    root = output_root or PROJECT_ROOT / 'data/external'
    out = root / (now.strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6])
    out.mkdir(parents=True, exist_ok=False)
    sources = []

    def download(url, name):
        req = Request(url, headers={'User-Agent': 'FileGuardAI-H07-research', 'Accept': 'application/vnd.github+json' if 'api.github.com' in url else '*/*'})
        with urlopen(req, timeout=30) as response:
            data = response.read()
        dest = out / name
        dest.write_bytes(data)
        sources.append({'url': url, 'file': name, 'sha256': sha256(dest),
                        'retrieved_at_utc': datetime.now(timezone.utc).isoformat()})
        return data

    sec_commit = json.loads(download('https://api.github.com/repos/danielmiessler/SecLists/commits/master', 'seclists_commit.json'))['sha']
    payload_url = f'https://raw.githubusercontent.com/danielmiessler/SecLists/{sec_commit}/Fuzzing/LFI/LFI-Jhaddix.txt'
    payloads = download(payload_url, 'LFI-Jhaddix.txt').decode('utf-8-sig')
    download(f'https://raw.githubusercontent.com/danielmiessler/SecLists/{sec_commit}/LICENSE', 'SecLists_LICENSE.txt')
    flask_commit = json.loads(download('https://api.github.com/repos/pallets/flask/commits/3.1.2', 'flask_commit.json'))['sha']
    tree_url = f'https://api.github.com/repos/pallets/flask/git/trees/{flask_commit}?recursive=1'
    tree = json.loads(download(tree_url, 'flask_tree.json'))
    if tree.get('truncated'):
        raise ValueError('Truncated public tree; cannot use incomplete snapshot')
    download(f'https://raw.githubusercontent.com/pallets/flask/{flask_commit}/LICENSE.txt', 'Flask_LICENSE.txt')
    import csv
    with (PROJECT_ROOT / 'data/paths_synthetic.csv').open(encoding='utf-8-sig', newline='') as f:
        original = list(csv.DictReader(f))
    raw_original = {r['path'] for r in original}
    canonical_original = {canonical_key(r['path']) for r in original}
    positives, negatives, rejected = {}, {}, Counter()
    for line_number, line in enumerate(payloads.splitlines(), 1):
        # Remove only surrounding whitespace and normalize Unicode NFC; never
        # decode or rewrite separators in the model input persisted in CSV.
        path = unicodedata.normalize('NFC', line.strip())
        reason = label_reason(path)
        if not path or path.startswith('#') or len(path) > 4096 or not reason:
            rejected['public_payload_not_in_annotation_scope'] += 1
            continue
        if path in raw_original or canonical_key(path) in canonical_original:
            rejected['payload_overlap_original'] += 1
            continue
        if path in positives:
            rejected['payload_exact_duplicate'] += 1
            continue
        positives[path] = {'path': path, 'label': '1', 'family': 'public_seclists',
                           'source_url': payload_url, 'source_line': str(line_number),
                           'source_revision': sec_commit, 'label_reason': reason,
                           'source_original': line}
    for item in tree['tree']:
        if item['type'] != 'blob':
            continue
        path = unicodedata.normalize('NFC', item['path'])
        if label_reason(path) or path in raw_original or canonical_key(path) in canonical_original:
            rejected['control_ineligible_or_overlap'] += 1
            continue
        negatives[path] = {'path': path, 'label': '0', 'family': 'public_flask_relative_path',
                           'source_url': f'https://github.com/pallets/flask/blob/{flask_commit}/{item["path"]}',
                           'source_line': '', 'source_revision': flask_commit,
                           'label_reason': 'relative_repository_file_path_without_parent_or_absolute_syntax',
                           'source_original': item['path']}
    cap = protocol['external_cap_per_class']
    count = min(cap, len(positives), len(negatives))
    if count < 10:
        raise ValueError('Insufficient public rows; no fabricated fallback')
    import hashlib
    order = lambda p: hashlib.sha256(p.encode('utf-8')).hexdigest()
    rows = [positives[p] for p in sorted(positives, key=order)[:count]]
    rows += [negatives[p] for p in sorted(negatives, key=order)[:count]]
    rows.sort(key=lambda r: order(r['path']))
    write_csv(out / 'external_cases.csv', rows,
              ['path', 'label', 'family', 'source_url', 'source_line', 'source_revision', 'label_reason', 'source_original'])
    info = {'created_at_utc': now.isoformat(), 'frozen_at_utc': selection['frozen_at_utc'],
            'frozen_selection_sha256': sha256(run / 'selection.json'),
            'protocol_sha256': sha256(run / 'protocol.json'),
            'external_cases_sha256': sha256(out / 'external_cases.csv'),
            'dataset_path': str(out.resolve()), 'rows': len(rows), 'label_counts': dict(Counter(r['label'] for r in rows)),
            'public_eligible_positive': len(positives), 'public_eligible_negative': len(negatives),
            'excluded_counts': dict(rejected), 'raw_overlap_original': 0, 'canonical_overlap_original': 0,
            'within_external_duplicate_excess': len(rows) - len({r['path'] for r in rows}),
            'within_external_canonical_duplicate_excess': len(rows) - len({canonical_key(r['path']) for r in rows}),
            'selection': 'first min(200, eligible_per_class) by SHA256(path); no model predictions used',
            'sources': sources,
            'normalization': 'strip surrounding whitespace for payload lines; Unicode NFC; preserve case/percent escapes/separators in model inputs',
            'annotation': '1 iff raw/decode1/decode2 has parent component, rooted/UNC path or Windows drive; 0 iff public Flask blob path lacks these; no model-based labels',
            'limitations': 'Weak lexical annotation, source/label confounding; not real traffic or exploit success. Public payload examples may already be familiar to researcher. Variants can be canonically correlated.'}
    (out / 'external_manifest.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    text = f'''# Public-source external lexical corpus

Collected UTC: {now.isoformat()}. Models frozen UTC: {selection['frozen_at_utc']}.
{len(rows)} rows; {count} suspicious + {count} benign controls.

## Sources

- SecLists LFI-Jhaddix: {payload_url} (MIT, license preserved).
- Flask 3.1.2 repository tree: {tree_url} (BSD-3-Clause, license preserved).
- Background on percent/double encoding: https://community.owasp.org/Double_Encoding

## Annotation and normalization

Positive candidates are public payload lines having a parent component or
absolute/UNC/drive syntax in raw or at most two URL-decode views. Negative
controls are actual relative Flask repository filenames without those markers.
These labels express lexical intent, not filesystem access or exploit success.
Out-of-scope LFI wrappers/relative sensitive names without traversal evidence
are excluded rather than automatically called malicious or benign.

Payload whitespace is stripped and Unicode normalized NFC. Model input keeps
percent escapes, case and separators. No URL decoding of the persisted input.
CSV keeps source_original, URL, revision, line and label_reason per sample.
Exclude exact and two-decode/slash/casefold-equivalent matches to all original
10,000 rows. De-duplicate exact public strings. Canonically related external
variants may remain; their count is in external_manifest.json.

Select up to 200 per class by SHA256(path), with no model-dependent filtering.
Neither model nor validation selection reads this corpus; it is evaluation-only.
No attack requests are sent to public hosts; network use only downloads sources.

This is a source-derived, weakly annotated lexical corpus, not a representative
real-world benchmark. Public file paths are benign syntax controls, not normal
web traffic. Source and label are correlated. No claim of fully blind research
or proven real-world generalization is justified.
'''
    (out / 'README.md').write_text(text, encoding='utf-8')
    print('External corpus:', out)
    print('Rows:', len(rows), 'labels:', info['label_counts'])
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--output-root', type=Path)
    args = p.parse_args()
    collect(args.run, args.output_root)
