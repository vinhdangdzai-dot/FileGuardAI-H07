"""Two-stage experiment: select on training-family validation, then test.

prepare freezes v2/C/model before any new external evaluation. evaluate never
fits a model. Existing data/models/results are never overwritten.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
from time import perf_counter_ns
import uuid

import joblib
import numpy as np
import sklearn

from app.ml_features import FEATURE_NAMES_V2, extract_features, extract_features_v2, simple_rule
from ml.evaluate import benchmark, partition, scores, sha256, write_csv
from ml.train_model import PROJECT_ROOT, build_model

REFERENCE = PROJECT_ROOT / 'docs/evaluations/20261116T153450Z_e5b13b'
METHODS = [('logistic_regression', 'LR v1'), ('improved_logistic_regression', 'LR v2'), ('regex', 'Regex')]
SELECTION = {'validation_seed': 1701, 'candidate_C': [0.1, 1.0, 10.0],
             'threshold': 0.5, 'selection_rule': 'highest validation F1, ties choose smallest C',
             'feature_design': 'fixed raw/decode1/decode2 views; aggregate path structure; preserve v1 features'}


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def json_write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def select_model(training_rows):
    """This API accepts only original TRAIN rows. No test/external labels."""
    fit, validation, check = partition(training_rows, SELECTION['validation_seed'])
    x = np.asarray([extract_features_v2(r['path']) for r in fit])
    y = [int(r['label']) for r in fit]
    xv = np.asarray([extract_features_v2(r['path']) for r in validation])
    yv = [int(r['label']) for r in validation]
    candidates = []
    for c in SELECTION['candidate_C']:
        model = build_model()
        model.set_params(model__C=c)
        model.fit(x, y)
        pred = (model.predict_proba(xv)[:, 1] >= SELECTION['threshold']).astype(int)
        candidates.append({'C': c, 'validation': scores(yv, pred)})
    winner = max(candidates, key=lambda r: (r['validation']['f1'], -r['C']))
    return winner['C'], candidates, fit, validation, check


def prepare(reference=REFERENCE, output_root=None):
    output_root = output_root or PROJECT_ROOT / 'docs/evaluations'
    ref = json.loads((reference / 'results.json').read_text(encoding='utf-8'))
    data_path = PROJECT_ROOT / 'data/paths_synthetic.csv'
    if sha256(data_path) != ref['data_sha256']:
        raise ValueError('Dataset differs from fixed reference')
    manifest = json.loads((reference / 'manifest.json').read_text())
    for name in ('model.joblib', 'split.csv', 'predictions.csv', 'results.json'):
        if sha256(reference / name) != manifest[name]:
            raise ValueError('Reference integrity failure: ' + name)
    split = read_csv(reference / 'split.csv')
    training = [{k: r[k] for k in ('path', 'label', 'family')} for r in split if r['partition'] == 'train']
    if len(training) != ref['train_samples']:
        raise ValueError('Reference train membership mismatch')
    now = datetime.now(timezone.utc)
    out = output_root / (now.strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:6])
    out.mkdir(parents=True, exist_ok=False)
    # Persist design and input hashes before selection. This file is immutable.
    protocol = dict(SELECTION, created_at_utc=now.isoformat(), reference=str(reference.resolve()),
                    reference_results_sha256=sha256(reference / 'results.json'),
                    reference_split_sha256=sha256(reference / 'split.csv'),
                    data_sha256=sha256(data_path),
                    deployed_model_sha256=sha256(PROJECT_ROOT / 'artifacts/model.joblib'),
                    feature_source_sha256=sha256(PROJECT_ROOT / 'app/ml_features.py'),
                    experiment_source_sha256=sha256(Path(__file__)),
                    external_policy='Public SecLists lexical attacks plus Flask repository relative-path controls; never used to fit/select',
                    external_cap_per_class=200,
                    caveat='Reference test outcomes were disclosed before feature design; this is a reused benchmark, not a pristine blind test.')
    json_write(out / 'protocol.json', protocol)
    c, candidates, fit, validation, check = select_model(training)
    val_membership = {r['path'] for r in validation}
    write_csv(out / 'development_split.csv', [dict(r, partition='validation' if r['path'] in val_membership else 'fit') for r in training],
              ['path', 'label', 'family', 'partition'])
    model = build_model()
    model.set_params(model__C=c)
    start = perf_counter_ns()
    model.fit(np.asarray([extract_features_v2(r['path']) for r in training]), [int(r['label']) for r in training])
    fit_ms = (perf_counter_ns() - start) / 1e6
    joblib.dump(model, out / 'improved_model.joblib')
    shutil.copy2(reference / 'model.joblib', out / 'baseline_model.joblib')
    selection = {'selected_C': c, 'candidates': candidates, 'validation_split': check,
                 'fit_samples': len(fit), 'validation_samples': len(validation), 'refit_samples': len(training),
                 'fit_families': sorted({r['family'] for r in fit}),
                 'validation_families': sorted({r['family'] for r in validation}),
                 'refit_ms': fit_ms, 'feature_names_v2': FEATURE_NAMES_V2,
                 'protocol_sha256': sha256(out / 'protocol.json'),
                 'baseline_model_sha256': sha256(out / 'baseline_model.joblib'),
                 'improved_model_sha256': sha256(out / 'improved_model.joblib'),
                 'frozen_at_utc': datetime.now(timezone.utc).isoformat()}
    json_write(out / 'selection.json', selection)
    print('Frozen experiment:', out)
    print('Selected C from training validation:', c)
    print(json.dumps(candidates, indent=2))
    return out


def evaluate_rows(rows, baseline, improved, repeats):
    truth = [int(r['label']) for r in rows]
    x1 = np.asarray([extract_features(r['path']) for r in rows])
    x2 = np.asarray([extract_features_v2(r['path']) for r in rows])
    p1, p2 = baseline.predict_proba(x1)[:, 1], improved.predict_proba(x2)[:, 1]
    predictions = {'logistic_regression': (p1 >= .5).astype(int),
                   'improved_logistic_regression': (p2 >= .5).astype(int),
                   'regex': np.array([simple_rule(r['path']) for r in rows])}
    timing = {
        'lr_inference_only': benchmark(lambda: baseline.predict_proba(x1)[:, 1] >= .5, len(rows), repeats),
        'lr_end_to_end': benchmark(lambda: baseline.predict_proba(np.asarray([extract_features(r['path']) for r in rows]))[:, 1] >= .5, len(rows), repeats),
        'improved_inference_only': benchmark(lambda: improved.predict_proba(x2)[:, 1] >= .5, len(rows), repeats),
        'improved_end_to_end': benchmark(lambda: improved.predict_proba(np.asarray([extract_features_v2(r['path']) for r in rows]))[:, 1] >= .5, len(rows), repeats),
        'regex_end_to_end': benchmark(lambda: [simple_rule(r['path']) for r in rows], len(rows), repeats),
    }
    output = []
    for i, row in enumerate(rows):
        output.append(dict(row, lr_v1_probability=float(p1[i]), lr_v2_probability=float(p2[i]),
                           lr_v1_prediction=int(predictions['logistic_regression'][i]),
                           lr_v2_prediction=int(predictions['improved_logistic_regression'][i]),
                           regex_prediction=int(predictions['regex'][i])))
    return {'samples': len(rows), 'label_counts': {str(k): truth.count(k) for k in (0, 1)},
            'models': {key: scores(truth, value) for key, value in predictions.items()}, 'timing': timing}, output


def plots(result, out):
    os.environ.setdefault('MPLCONFIGDIR', str(out / '.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    datasets = list(result['datasets'].items())
    fig, axes = plt.subplots(len(datasets), 3, figsize=(14, 4.3 * len(datasets)), squeeze=False, constrained_layout=True)
    for row, (name, data) in enumerate(datasets):
        for col, (key, label) in enumerate(METHODS):
            ax = axes[row, col]
            matrix = np.array(data['models'][key]['confusion_matrix'])
            ax.imshow(matrix, cmap='Blues', vmin=0, vmax=max(1, matrix.max()))
            for (i, j), value in np.ndenumerate(matrix):
                ax.text(j, i, str(value), ha='center', va='center', fontsize=15,
                        color='white' if value > matrix.max() / 2 else 'black')
            ax.set(title=f'{label} — {name}', xticks=[0, 1], yticks=[0, 1],
                   xticklabels=['benign', 'suspicious'], yticklabels=['benign', 'suspicious'],
                   xlabel='Predicted', ylabel='True')
    fig.savefig(out / 'confusion_matrix.png', dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, len(datasets), figsize=(14, 5), squeeze=False, constrained_layout=True)
    names = ['accuracy', 'precision', 'recall', 'f1']
    for ax, (name, data) in zip(axes[0], datasets):
        x = np.arange(len(names))
        for i, (key, label) in enumerate(METHODS):
            ax.bar(x + (i - 1) * .25, [data['models'][key][n] for n in names], .25, label=label)
        ax.set(title=name, xticks=x, xticklabels=names, ylim=(0, 1.1), ylabel='Score')
        ax.legend(loc='lower right')
    fig.savefig(out / 'metrics.png', dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, len(datasets), figsize=(12, 4.5), squeeze=False, constrained_layout=True)
    for ax, (name, data) in zip(axes[0], datasets):
        values = [data['timing'][key]['amortized_us_per_path'] for key in ('lr_end_to_end', 'improved_end_to_end', 'regex_end_to_end')]
        bars = ax.bar(['LR v1', 'LR v2', 'Regex'], values)
        ax.bar_label(bars, fmt='%.3f', padding=3)
        ax.set(title=name, ylabel='Warm batch microseconds/path (amortized)', ylim=(0, max(values) * 1.2))
    fig.savefig(out / 'latency.png', dpi=160)
    plt.close(fig)


def write_report(result, out):
    s = result['selection']
    lines = ['# Thực nghiệm LR v1 / LR v2 / Regex', '',
             f"UTC: {result['created_at_utc']}. Reference test cố định: {result['reference_run']}.", '',
             '## Quy trình và giới hạn độc lập', '',
             result['protocol']['caveat'],
             'Không dùng nhãn test để chọn cấu hình. Bộ đặc trưng v2 cố định trước lựa chọn C. '
             'Chỉ validation từ original train được dùng chọn C; sau đó refit trên toàn bộ original train. '
             'Giai đoạn evaluate không có lệnh fit. Tập ngoài thu thập sau khi đóng băng model, '
             'không dùng để sửa đặc trưng hoặc chọn C. Không thay model đang triển khai.',
             f"Fit/validation: {s['fit_samples']}/{s['validation_samples']}; refit {s['refit_samples']}. "
             f"C được chọn: {s['selected_C']}; ngưỡng 0,5 cố định.",
             'Candidate C = 0,1; 1; 10. Quy tắc chọn: validation F1 cao nhất, hòa chọn C nhỏ nhất.', '',
             '| C | Validation Accuracy | Precision | Recall | F1 |', '|---|---:|---:|---:|---:|']
    for c in s['candidates']:
        m = c['validation']
        lines.append(f"| {c['C']} | {m['accuracy']:.6f} | {m['precision']:.6f} | {m['recall']:.6f} | {m['f1']:.6f} |")
    for name, data in result['datasets'].items():
        lines += ['', '## ' + name, '', f"N={data['samples']}; nhãn: {data['label_counts']}.", '',
                  '| Method | Accuracy | Precision | Recall | F1 | TN | FP | FN | TP |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for key, label in METHODS:
            m = data['models'][key]
            (tn, fp), (fn, tp) = m['confusion_matrix']
            lines.append(f"| {label} | {m['accuracy']:.6f} | {m['precision']:.6f} | {m['recall']:.6f} | {m['f1']:.6f} | {tn} | {fp} | {fn} | {tp} |")
        lines += ['', '| Timing | Median batch ms | P95 batch ms | Amortized µs/path |', '|---|---:|---:|---:|']
        for key, t in data['timing'].items():
            lines.append(f"| {key} | {t['median_batch_ms']:.6f} | {t['p95_batch_ms']:.6f} | {t['amortized_us_per_path']:.6f} |")
    lines += ['', '![Confusion matrices](confusion_matrix.png)', '![Metrics](metrics.png)', '![Latency](latency.png)', '',
              '## Phân tích FN và đặc trưng', '',
              'V1 chỉ nhìn một lớp unquote khi đếm traversal; các cờ encoded_dot/slash/backslash '
              'chỉ tìm escape một lớp trong chuỗi gốc. `%252e%252e%252f` chưa xuất hiện dưới dạng '
              '`../` trong các tín hiệu này. Regex v1 cũng chỉ kiểm tra marker một lớp. '
              'V2 giữ 18 đặc trưng v1 và thêm 12 tín hiệu cấu trúc tổng hợp trên raw/decode1/decode2: '
              'parent component, tỷ lệ parent, absolute/drive/UNC, separator, mixed separator, '
              'escape depth, dot component, null, structural escape và số lượt decode làm thay đổi chuỗi. '
              'Các tín hiệu dùng chung giữa mức mã hóa giúp học từ raw/single encoding trong train; '
              'không biến quy tắc thành nhãn hay quyết định truy cập.',
              'Giải mã tối đa đúng hai lần, chỉ trong ML; không unquote_plus, không chuyển kết quả '
              'này tới open_authorized. security.py và extract_features v1 giữ nguyên hành vi.', '',
              '## Tập ngoài và gắn nhãn', '',
              'Chi tiết nguồn, commit, snapshot hash, lọc, duplicate và provenance từng dòng: '
              'external_manifest.json, external_cases.csv và README.md trong data/external/<snapshot>. '
              'Nhãn được gắn bằng chính sách lexical, không dùng dự đoán LR/regex. '
              'Đây là corpus công khai có chọn lọc, không phải traffic thực tế hoặc bộ chuẩn do bên thứ ba gán nhãn. '
              'Benign là tên file tương đối trong repo Flask, không phải benign HTTP traffic. '
              'Tương quan nguồn với nhãn và nhiều biến thể cùng payload làm giới hạn khả năng tổng quát hóa. '
              'Nhãn suspicious không khẳng định khai thác thành công trên FileGuardAI.', '',
              '## Diễn giải', '',
              'Chỉ kết luận theo từng tập và từng chỉ số, không tự khẳng định v2 tốt hơn. '
              'Nếu recall tăng nhưng false positives tăng phải báo cả hai. '
              'Tập test cũ từng được công bố nên chỉ là reused benchmark; cần test tương lai được '
              'bên độc lập thu thập và khóa trước khi tiếp tục nghiên cứu. '
              'Thời gian là warm batch chia số mẫu, không phải độ trễ HTTP; raw timings lưu JSON. '
              'Không có dữ liệu mới được đưa vào model triển khai.', '',
              '## Bằng chứng', '',
              '- protocol.json + selection.json: kế hoạch, validation, model freeze.',
              '- development_split.csv: fit/validation từ original train.',
              '- holdout_predictions.csv / external_predictions.csv: từng nhãn, xác suất, dự đoán.',
              '- baseline_model.joblib / improved_model.joblib: model so sánh lưu riêng.',
              '- results.json / manifest.json: chỉ số, timings, hash.', '']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def evaluate(out, external, repeats=15):
    if repeats < 3 or (out / 'results.json').exists():
        raise ValueError('Use repeats >= 3 and a prepared run not yet evaluated')
    protocol = json.loads((out / 'protocol.json').read_text(encoding='utf-8'))
    selection = json.loads((out / 'selection.json').read_text(encoding='utf-8'))
    checks = [(out / 'protocol.json', selection['protocol_sha256']),
              (PROJECT_ROOT / 'app/ml_features.py', protocol['feature_source_sha256']),
              (Path(__file__), protocol['experiment_source_sha256']),
              (PROJECT_ROOT / 'artifacts/model.joblib', protocol['deployed_model_sha256']),
              (PROJECT_ROOT / 'data/paths_synthetic.csv', protocol['data_sha256']),
              (out / 'baseline_model.joblib', selection['baseline_model_sha256']),
              (out / 'improved_model.joblib', selection['improved_model_sha256'])]
    if any(sha256(p) != digest for p, digest in checks):
        raise ValueError('Frozen experiment input/model/source changed')
    reference = Path(protocol['reference'])
    if sha256(reference / 'split.csv') != protocol['reference_split_sha256'] or sha256(reference / 'results.json') != protocol['reference_results_sha256']:
        raise ValueError('Reference changed')
    ref = json.loads((reference / 'results.json').read_text(encoding='utf-8'))
    split = read_csv(reference / 'split.csv')
    test = [{k: r[k] for k in ('path', 'label', 'family')} for r in split if r['partition'] == 'test']
    outside = read_csv(external / 'external_cases.csv')
    manifest = json.loads((external / 'external_manifest.json').read_text(encoding='utf-8'))
    if sha256(external / 'external_cases.csv') != manifest['external_cases_sha256']:
        raise ValueError('External corpus hash mismatch')
    if manifest['frozen_selection_sha256'] != sha256(out / 'selection.json'):
        raise ValueError('External corpus is not tied to this frozen selection')
    if {r['path'] for r in outside} & {r['path'] for r in split}:
        raise ValueError('External path overlap with original data')
    baseline, improved = joblib.load(out / 'baseline_model.joblib'), joblib.load(out / 'improved_model.joblib')
    holdout, hp = evaluate_rows(test, baseline, improved, repeats)
    public, ep = evaluate_rows(outside, baseline, improved, repeats)
    if holdout['models']['logistic_regression'] != ref['logistic_regression']:
        raise ValueError('Baseline does not reproduce reference test results')
    result = {k: ref[k] for k in ('audit', 'train_samples', 'test_samples', 'train_families', 'test_families', 'split')}
    result.update(created_at_utc=datetime.now(timezone.utc).isoformat(), schema_version=2, seed=2026, threshold=.5,
                  python_version=platform.python_version(), sklearn_version=sklearn.__version__,
                  reference_run=reference.name, protocol=protocol, selection=selection,
                  external_source_manifest=manifest, preservation_verified=True,
                  datasets={'frozen_holdout': holdout, 'external_public': public},
                  timing=holdout['timing'], **holdout['models'])
    write_csv(out / 'holdout_predictions.csv', hp, list(hp[0]))
    write_csv(out / 'external_predictions.csv', ep, list(ep[0]))
    json_write(out / 'results.json', result)
    shutil.copy2(external / 'external_manifest.json', out / 'external_manifest.json')
    plots(result, out)
    write_report(result, out)
    json_write(out / 'manifest.json', {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()})
    temp = out.parent / ('latest_' + uuid.uuid4().hex + '.tmp')
    json_write(temp, {'run': out.name})
    temp.replace(out.parent / 'latest.json')
    print(json.dumps({k: v['models'] for k, v in result['datasets'].items()}, indent=2))
    print('Evaluation:', out)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--reference', type=Path, default=REFERENCE)
    p.add_argument('--output-root', type=Path)
    p = sub.add_parser('evaluate')
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--external', type=Path, required=True)
    p.add_argument('--repeats', type=int, default=15)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.reference, args.output_root)
    else:
        evaluate(args.run, args.external, args.repeats)
