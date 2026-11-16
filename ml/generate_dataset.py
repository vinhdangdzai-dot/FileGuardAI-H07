"""Deterministic, explicitly SYNTHETIC labelled examples for learning exercises.

'1' means suspicious syntax, NOT proven filesystem escape. Dataset contains
encodings that Flask will intentionally NOT decode a second time.
"""
import argparse
import csv
import random
from pathlib import Path

BENIGN_PATTERNS = [
    '{f}', 'tailieu/{f}', 'tai_lieu/{f}', 'bai_giang/{f}',
    'bao_cao/{f}', 'thuc_hanh/{f}', 'hoc_ky_1/{f}',
    'photos/{f}', 'videos/{f}', 'khoa_luan/{f}',
    'nam_2026/{f}', 'tai_lieu/chuong_1/{f}',
    'tài liệu/{f}', 'báo cáo/{f}', 'nghiên cứu/{f}',
]
ATTACK_PATTERNS = [
    '../{f}', '../../{f}', '../../../{f}',
    'tailieu/../../{f}', 'tailieu/../../../{f}',
    '..\\{f}', '..\\..\\{f}', 'tailieu\\..\\..\\{f}',
    '/etc/{f}', '/home/user/{f}', 'C:\\Windows\\{f}',
    'D:\\private\\{f}', '\\\\server\\share\\{f}',
    '%2e%2e%2f{f}', '..%2F{f}', '%2E%2E%5C{f}',
    '%252e%252e%252f{f}', '%2e%2e/{f}',
    'tailieu/..%5c..%5c{f}', 'tailieu/..//..//{f}',
]
FILES_OK = [
    'baocao_{i}.pdf', 'báo cáo tốt nghiệp {i}.pdf',
    'chuong_{i}.pdf', 'tai lieu {i}.txt', 'slide_{i}.pptx',
    'mau_{i}.csv', 'ghi_chu_{i}.txt', 'ket_qua_{i}.xlsx',
]
FILES_SENSITIVE = [
    'secret_{i}.txt', 'config_{i}.env', 'private_{i}.key',
    'password_{i}.txt', 'settings_{i}.ini', 'db_{i}.sqlite3',
]


def create_rows(n=10000, seed=2026):
    if n < 60:
        raise ValueError('Use at least 60 examples for group holdout')
    rng = random.Random(seed)
    rows = []
    seen_paths = set()  # Avoid exact duplicate input paths
    for label, patterns, files in ((0, BENIGN_PATTERNS, FILES_OK),
                                   (1, ATTACK_PATTERNS, FILES_SENSITIVE)):
        for j in range(n // 2):
            k = j % len(patterns)
            while True:
                stem = rng.choice(files).format(i=rng.randint(1, 9999))
                candidate = patterns[k].format(f=stem)
                if candidate not in seen_paths:
                    break
            seen_paths.add(candidate)
            rows.append({'path': candidate,
                         'label': label, 'family': f'{label}-{k:02d}'})
    rng.shuffle(rows)
    return rows


def write_dataset(path: Path, n=10000, seed=2026):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = create_rows(n=n, seed=seed)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'label', 'family'])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate synthetic path dataset')
    parser.add_argument('--output', default='data/paths_synthetic.csv')
    parser.add_argument('--n', type=int, default=10000)
    args = parser.parse_args()
    print('Generated', write_dataset(Path(args.output), n=args.n), 'synthetic examples')
