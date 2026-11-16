"""Audit existing CSV and evaluate fixed, family-disjoint holdouts.

python -m ml.evaluate --repeats 15
Never generates/replaces data or overwrites deployed models. Output is a new
docs/evaluations/<timestamp_uuid> directory; latest.json is only a UI pointer.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
from time import perf_counter_ns
import uuid

import joblib
import numpy as np
import sklearn
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

from app.ml_features import FEATURE_NAMES, extract_features, simple_rule
from ml.train_model import PROJECT_ROOT, build_model, split_by_family


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit_dataset(rows):
    if not rows or any(not {'path', 'label', 'family'} <= r.keys() for r in rows):
        raise ValueError('CSV requires nonempty path,label,family rows')
    if any(r['label'] not in ('0', '1') or not r['path'] or not r['family'] for r in rows):
        raise ValueError('Invalid labels, empty paths or empty families')
    labels_by_path, labels_by_family = defaultdict(set), defaultdict(set)
    for r in rows:
        labels_by_path[r['path']].add(r['label'])
        labels_by_family[r['family']].add(r['label'])
    counts = Counter(r['path'] for r in rows)
    result = {
        'rows': len(rows), 'unique_paths': len(counts),
        'duplicate_excess_rows': sum(n - 1 for n in counts.values()),
        'duplicate_path_groups': sum(n > 1 for n in counts.values()),
        'label_counts': dict(sorted(Counter(r['label'] for r in rows).items())),
        'conflicting_path_labels': sum(len(v) > 1 for v in labels_by_path.values()),
        'mixed_label_families': sum(len(v) > 1 for v in labels_by_family.values()),
        'family_counts': dict(sorted(Counter(r['family'] for r in rows).items())),
    }
    if result['duplicate_excess_rows'] or result['conflicting_path_labels'] or result['mixed_label_families']:
        raise ValueError('Resolve duplicate/conflicting paths or mixed-label families before evaluation: ' + str(result))
    if set(result['label_counts']) != {'0', '1'}:
        raise ValueError('Both classes required')
    return result


def partition(rows, seed):
    train, test = split_by_family(rows, seed)
    groups_overlap = sorted({r['family'] for r in train} & {r['family'] for r in test})
    paths_overlap = sorted({r['path'] for r in train} & {r['path'] for r in test})
    if groups_overlap or paths_overlap or any({r['label'] for r in part} != {'0', '1'} for part in (train, test)):
        raise ValueError('Unsafe train/test partition')
    return train, test, {'family_overlap': groups_overlap, 'path_overlap': paths_overlap,
                         'train_label_counts': dict(Counter(r['label'] for r in train)),
                         'test_label_counts': dict(Counter(r['label'] for r in test))}


def scores(y, pred):
    return {'accuracy': float(accuracy_score(y, pred)),
            'precision': float(precision_score(y, pred, zero_division=0)),
            'recall': float(recall_score(y, pred, zero_division=0)),
            'f1': float(f1_score(y, pred, zero_division=0)),
            'confusion_matrix': confusion_matrix(y, pred, labels=[0, 1]).tolist()}


def benchmark(fn, count, repeats):
    fn()  # warmup excluded from measurements, no fitting/tuning here
    samples = []
    for _ in range(repeats):
        start = perf_counter_ns()
        fn()
        samples.append((perf_counter_ns() - start) / 1e6)
    return {'repeats': repeats, 'samples_per_batch': count, 'batch_ms': samples,
            'median_batch_ms': float(np.median(samples)),
            'p95_batch_ms': float(np.percentile(samples, 95)),
            'amortized_us_per_path': float(np.median(samples) * 1000 / count)}


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_results(result, out):
    # Keep matplotlib cache inside the new run rather than the user profile.
    os.environ.setdefault('MPLCONFIGDIR', str(out / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), constrained_layout=True)
    for ax, key, title in zip(axes, ('logistic_regression', 'regex'), ('Logistic Regression', 'Regex baseline')):
        matrix = np.array(result[key]['confusion_matrix'])
        ax.imshow(matrix, cmap='Blues', vmin=0, vmax=result['test_samples'])
        for (i, j), value in np.ndenumerate(matrix):
            ax.text(j, i, str(value), ha='center', va='center', fontsize=16)
        ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=['benign (0)', 'suspicious (1)'],
               yticklabels=['benign (0)', 'suspicious (1)'], xlabel='Predicted', ylabel='True', title=title)
    fig.savefig(out / 'confusion_matrix.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    names = ['accuracy', 'precision', 'recall', 'f1']
    x = np.arange(4)
    for offset, key, title in [(-.18, 'logistic_regression', 'Logistic Regression'), (.18, 'regex', 'Regex')]:
        bars = ax.bar(x + offset, [result[key][n] for n in names], .36, label=title)
        ax.bar_label(bars, fmt='%.4f', padding=3, fontsize=9)
    ax.set(xticks=x, xticklabels=['Accuracy', 'Precision', 'Recall', 'F1'], ylim=(0, 1.16), ylabel='Score',
           title='Family-disjoint holdout (seed 2026)')
    ax.legend(loc='lower right')
    fig.savefig(out / 'metrics.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    values = [result['timing'][k]['amortized_us_per_path'] for k in ('lr_end_to_end', 'regex_end_to_end')]
    bars = ax.bar(['LR: features + predict', 'Regex: rule'], values)
    ax.bar_label(bars, fmt='%.3f', padding=3)
    ax.set(ylabel='Median batch time / paths (microseconds)', title='Warm batch latency; not request latency')
    ax.set_ylim(0, max(values) * 1.2)
    fig.savefig(out / 'latency.png', dpi=180)
    plt.close(fig)


def report(result, out):
    audit = result['audit']
    lines = ['# Đánh giá thực nghiệm Logistic Regression — Chương 4', '',
             f"Thời điểm UTC: {result['created_at_utc']}. Seed chính: 2026. Ngưỡng AI cố định 0,5.", '',
             '## Dữ liệu và chống rò rỉ', '',
             f"CSV có {audit['rows']} mẫu, {audit['unique_paths']} đường dẫn duy nhất, "
             f"{audit['duplicate_excess_rows']} dòng trùng dư, {audit['duplicate_path_groups']} nhóm đường dẫn trùng; "
             f"{audit['conflicting_path_labels']} đường dẫn xung đột nhãn.",
             f"Nhãn: {audit['label_counts']}. Có {len(audit['family_counts'])} family.",
             f"Train {result['train_samples']}, test {result['test_samples']}; "
             f"train {len(result['train_families'])} family, test {len(result['test_families'])} family.",
             f"Family giao nhau: {result['split']['family_overlap']}; đường dẫn giao nhau: {result['split']['path_overlap']}.",
             'Split stratify theo nhãn ở cấp family, xấp xỉ 20% số family mỗi nhãn làm test; '
             'không hứa chính xác 20% số dòng. StandardScaler và LR chỉ fit train. '
             'Không chọn ngưỡng/đặc trưng/siêu tham số theo test, không dùng test để huấn luyện.',
             'Nhãn 1 là cú pháp nghi vấn, không phải bằng chứng đã đọc được tệp ngoài kho. '
             'Đầu vào CSV là chuỗi lexical, không phải toàn bộ HTTP query đã qua Flask decode.', '',
             '| Phương pháp | Accuracy | Precision | Recall | F1 | TN | FP | FN | TP |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for key in ('logistic_regression', 'regex'):
        m = result[key]
        (tn, fp), (fn, tp) = m['confusion_matrix']
        lines.append(f"| {key} | {m['accuracy']:.6f} | {m['precision']:.6f} | {m['recall']:.6f} | {m['f1']:.6f} | {tn} | {fp} | {fn} | {tp} |")
    lines += ['', '![Confusion matrices](confusion_matrix.png)', '![Metrics](metrics.png)', '',
              '## Thời gian dự đoán', '',
              f"Fit model chính: {result['fit_ms']:.3f} ms (không bao gồm trích đặc trưng). "
              'Benchmark warm batch, perf_counter_ns; có warmup, không gồm đọc CSV, I/O hay HTTP. '
              'So sánh đầu cuối LR gồm extract_features + predict_proba + ngưỡng; regex gồm simple_rule. '
              'LR inference-only dùng đặc trưng tính sẵn được báo riêng. Giá trị mỗi đường dẫn là '
              'thời gian batch chia số mẫu, không phải p95 latency của từng request.', '',
              '| Phép đo | Số lượt | Median batch ms | P95 batch ms | Median µs/path (amortized) |',
              '|---|---:|---:|---:|---:|']
    for key, value in result['timing'].items():
        lines.append(f"| {key} | {value['repeats']} | {value['median_batch_ms']:.6f} | {value['p95_batch_ms']:.6f} | {value['amortized_us_per_path']:.6f} |")
    lines += ['', '![Latency](latency.png)', '', '## Độ nhạy với cách chọn family', '',
              'Năm seed cố định được khai báo trước; mỗi lượt fit pipeline mới chỉ bằng train của lượt đó. '
              'Không chọn seed/model tốt nhất để triển khai. Các lượt có thể dùng lại mẫu ở vai trò '
              'train/test khác nhau nên không phải năm tập kiểm thử độc lập. Không dùng để tuning.', '',
              '| Seed | Test rows | LR F1 | LR Recall | Regex F1 | Regex Recall |',
              '|---|---:|---:|---:|---:|---:|']
    for r in result['robustness']:
        lines.append(f"| {r['seed']} | {r['test_samples']} | {r['logistic_regression']['f1']:.6f} | {r['logistic_regression']['recall']:.6f} | {r['regex']['f1']:.6f} | {r['regex']['recall']:.6f} |")
    lines += ['', '## Phân tích lỗi theo family', '',
              '| Family test | N | Nhãn | LR sai | Regex sai | Ví dụ |', '|---|---:|---:|---:|---:|---|']
    for r in result['family_results']:
        example = r['example'].replace('|', '&#124;')
        lines.append(f"| {r['family']} | {r['samples']} | {r['label']} | {r['lr_errors']} | {r['regex_errors']} | `{example}` |")
    lines += ['', '## Hạn chế và khả năng tổng quát hóa', '',
              '- Dữ liệu tổng hợp từ số template hữu hạn, cân bằng 50/50; tên tệp và nhãn có thể '
              'tương quan do bộ sinh (ví dụ tên sensitive). Không đại diện phân bố traffic thực tế.',
              '- Family holdout giảm ghi nhớ template giống hệt nhưng các family vẫn dùng chung '
              'cấu trúc, từ vựng và số ngẫu nhiên. Không có giao nhau chuỗi không có nghĩa các mẫu '
              'độc lập về ngữ nghĩa. Chưa có test thực địa hoặc nguồn ngoài bộ sinh.',
              '- Đặc trưng trùng nhau giữa train/test có thể hợp lệ vì mô hình nén nhiều chuỗi '
              'thành cùng vector; đây không phải bằng chứng độc lập. Số vector giao nhau được '
              'ghi trong results.json để công khai mức độ tương đồng.',
              '- Phân tích family và các seed cho biết khả năng nhận dạng template chưa gặp '
              'trong cùng bộ sinh; không đủ kết luận tổng quát hóa sang obfuscation mới, '
              'Unicode normalization, proxy decoding khác hoặc tác nhân tấn công thích nghi.',
              '- Nếu LR và regex có chỉ số giống nhau, không có bằng chứng LR tốt hơn baseline '
              'ở phép thử này. Recall dưới 95% không được trình bày là đạt mục tiêu 95%.',
              '- Cần tập test độc lập từ hệ thống được phép kiểm thử, gán nhãn có kiểm tra, '
              'chia theo nguồn/thời gian và khóa lại trước tuning; thêm benign khó và malicious '
              'chưa có trong generator. Báo cáo false positives, false negatives và tải thực tế.',
              '- Kết quả dashboard thuộc model đánh giá lưu riêng, không thay model download. '
              'Điểm AI chỉ phục vụ phát hiện; security.py vẫn quyết định quyền truy cập.', '',
              '## Thống kê family toàn bộ dữ liệu', '', '| Family | Số mẫu |', '|---|---:|']
    lines += [f'| {k} | {v} |' for k, v in audit['family_counts'].items()]
    lines += ['', '## Bằng chứng và tái lập', '',
              '`python -m ml.evaluate --repeats 15` tạo lần chạy mới, không ghi đè dữ liệu/model cũ.',
              '- results.json: chỉ số đầy đủ, seed, phiên bản, hash, thời gian thô và kiểm tra split.',
              '- split.csv: mọi dòng được phân train/test, nhãn và family.',
              '- predictions.csv: dự đoán và xác suất của từng mẫu test để tính lại metrics.',
              '- model.joblib: pipeline đánh giá chính; không dùng trong download.',
              '- environment.txt: phiên bản package; manifest.json: SHA-256 các file bằng chứng.',
              '- Ba PNG là hình xuất bằng matplotlib, dùng trực tiếp trong báo cáo khóa luận.', '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def evaluate(csv_path, output_root, repeats=15):
    if repeats < 3:
        raise ValueError('Use at least 3 timing repeats')
    started = datetime.now(timezone.utc)
    data_hash = sha256(csv_path)
    deployed_hash = sha256(PROJECT_ROOT / 'artifacts/model.joblib')
    with csv_path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    audit = audit_dataset(rows)
    train, test, split = partition(rows, 2026)
    x_train = np.asarray([extract_features(r['path']) for r in train])
    x_test = np.asarray([extract_features(r['path']) for r in test])
    y_train, y_test = [int(r['label']) for r in train], [int(r['label']) for r in test]
    model = build_model()
    t0 = perf_counter_ns()
    model.fit(x_train, y_train)
    fit_ms = (perf_counter_ns() - t0) / 1e6
    probability = model.predict_proba(x_test)[:, 1]
    pred = (probability >= .5).astype(int)
    regex = [simple_rule(r['path']) for r in test]
    out = output_root / (started.strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6])
    out.mkdir(parents=True, exist_ok=False)
    family_results = []
    for family in sorted({r['family'] for r in test}):
        indices = [i for i, r in enumerate(test) if r['family'] == family]
        family_results.append({'family': family, 'samples': len(indices), 'label': test[indices[0]]['label'],
                               'example': test[indices[0]]['path'],
                               'lr_errors': sum(int(pred[i] != y_test[i]) for i in indices),
                               'regex_errors': sum(int(regex[i] != y_test[i]) for i in indices)})
    result = {'created_at_utc': started.isoformat(), 'seed': 2026, 'threshold': .5,
              'python_version': platform.python_version(), 'sklearn_version': sklearn.__version__,
              'numpy_version': np.__version__, 'platform': platform.platform(),
              'data_path': str(csv_path.resolve()), 'data_sha256': data_hash, 'audit': audit,
              'feature_names': FEATURE_NAMES, 'train_samples': len(train), 'test_samples': len(test),
              'train_families': sorted({r['family'] for r in train}),
              'test_families': sorted({r['family'] for r in test}), 'split': split,
              'shared_unique_feature_vectors': len(set(map(tuple, x_train)) & set(map(tuple, x_test))),
              'fit_ms': fit_ms, 'logistic_regression': scores(y_test, pred), 'regex': scores(y_test, regex),
              'family_results': family_results, 'deployed_model_sha256': deployed_hash,
              'timing': {
                  'lr_inference_only': benchmark(lambda: model.predict_proba(x_test)[:, 1] >= .5, len(test), repeats),
                  'lr_end_to_end': benchmark(lambda: model.predict_proba(np.asarray([extract_features(r['path']) for r in test]))[:, 1] >= .5, len(test), repeats),
                  'regex_end_to_end': benchmark(lambda: [simple_rule(r['path']) for r in test], len(test), repeats),
              }, 'robustness': []}
    for seed in (2026, 7, 42, 123, 2025):
        tr, te, check = partition(rows, seed)
        if seed == 2026:
            lr_score, rule_score = result['logistic_regression'], result['regex']
        else:
            other = build_model(seed)
            other.fit([extract_features(r['path']) for r in tr], [int(r['label']) for r in tr])
            truth = [int(r['label']) for r in te]
            lr_score = scores(truth, other.predict([extract_features(r['path']) for r in te]))
            rule_score = scores(truth, [simple_rule(r['path']) for r in te])
        result['robustness'].append({'seed': seed, 'test_samples': len(te), 'split': check,
                                     'test_families': sorted({r['family'] for r in te}),
                                     'logistic_regression': lr_score, 'regex': rule_score})
    write_csv(out / 'split.csv', [dict(r, partition=part) for part, subset in [('train', train), ('test', test)] for r in subset],
              ['path', 'label', 'family', 'partition'])
    write_csv(out / 'predictions.csv', [dict(r, probability=float(probability[i]), lr_prediction=int(pred[i]), regex_prediction=regex[i]) for i, r in enumerate(test)],
              ['path', 'label', 'family', 'probability', 'lr_prediction', 'regex_prediction'])
    joblib.dump(model, out / 'model.joblib')
    result['evaluation_model_sha256'] = sha256(out / 'model.joblib')
    if sha256(csv_path) != data_hash or sha256(PROJECT_ROOT / 'artifacts/model.joblib') != deployed_hash:
        raise RuntimeError('Input data or deployed model changed during evaluation')
    result['preservation_verified'] = True
    result['source_hashes'] = {name: sha256(PROJECT_ROOT / name) for name in ('ml/evaluate.py', 'ml/train_model.py', 'app/ml_features.py', 'ml/generate_dataset.py')}
    (out / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    import subprocess
    env = subprocess.run([__import__('sys').executable, '-m', 'pip', 'freeze'], capture_output=True, text=True, check=True)
    (out / 'environment.txt').write_text(env.stdout, encoding='utf-8')
    plot_results(result, out)
    report(result, out)
    manifest = {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    pointer = output_root / 'latest.json'
    temporary = output_root / ('latest_' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps({'run': out.name}), encoding='utf-8')
    temporary.replace(pointer)
    print(json.dumps({k: result[k] for k in ('audit', 'logistic_regression', 'regex', 'timing')}, indent=2))
    print('Output:', out)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=PROJECT_ROOT / 'data/paths_synthetic.csv')
    parser.add_argument('--output-root', type=Path, default=PROJECT_ROOT / 'docs/evaluations')
    parser.add_argument('--repeats', type=int, default=15)
    args = parser.parse_args()
    evaluate(args.csv, args.output_root, args.repeats)
