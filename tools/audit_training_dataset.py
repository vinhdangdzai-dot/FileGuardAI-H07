"""Read-only CSV audit; deterministic recovery check without overwriting data."""
from collections import defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.training_view import read_dataset, dataset_stats
from ml.external_corpus import canonical_key
from ml.generate_dataset import create_rows

EXPECTED = '2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0'


def main():
    path = ROOT/'data/paths_synthetic.csv'
    rows = read_dataset(path)
    stats = dataset_stats(rows, path)
    groups = defaultdict(list)
    for row in rows:
        groups[canonical_key(row['path'])].append(row)
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=['path', 'label', 'family'])
    writer.writeheader()
    writer.writerows(create_rows(n=10000, seed=2026))
    recovered_sha = hashlib.sha256(buffer.getvalue().encode('utf-8-sig')).hexdigest()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        columns = csv.DictReader(stream).fieldnames
    checks = {'rows_10000': stats['rows'] == 10000,
              'balanced_labels': stats['label_counts'] == {'0':5000, '1':5000},
              'families_35': len(stats['family_counts']) == 35,
              'columns': columns == ['path', 'label', 'family'],
              'no_exact_duplicates': stats['exact_duplicate_excess'] == 0,
              'original_sha_matches': stats['sha256'] == EXPECTED,
              'deterministic_seed_2026_matches': recovered_sha == stats['sha256']}
    report = {**stats, 'columns':columns, 'expected_sha256':EXPECTED,
              'seed_2026_regenerated_in_memory_sha256': recovered_sha,
              'canonical_method':'NFC, exactly two URL unquote passes, backslash to slash, casefold; audit only, no dot-segment collapse or filesystem resolution',
              'canonical_duplicate_groups':sum(len(g)>1 for g in groups.values()),
              'canonical_conflicting_labels':sum(len({r['label'] for r in g})>1 for g in groups.values()),
              'checks':{k:'PASS' if v else 'FAIL' for k,v in checks.items()}}
    folder = ROOT/'docs/datasets'/('audit_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    (folder/'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print('Evidence:',folder.relative_to(ROOT))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
