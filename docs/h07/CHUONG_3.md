# Chương 3 — Triển khai và vận hành

## 1. Module và luồng xử lý

| Module | Trách nhiệm |
|---|---|
| app/web.py | factory, routes, download authorized handle, dashboard, CSV |
| app/security.py | validate/containment/link policy và bounded listing |
| app/auth.py | hash config, CSRF, role decorators; session 15 phút |
| app/database.py | schema/index/append-only triggers, bound queries, throttle events |
| app/evaluation_results.py | kiểm tra schema, counts/matrix/metric và timing trước render |
| app/ml_features.py | v1 18 đặc trưng tương thích model, v2 30 đặc trưng thử nghiệm |
| ml/train_model.py | pipeline, group split, sao lưu output khi huấn luyện có chủ đích |
| ml/evaluate.py / improve.py | đánh giá và train-family validation, freeze/test riêng |
| tools/h07_experiment.py | corpus nguồn mới, source snapshot, không fit |
| tools/h07_owasp_challenge.py | public encoding challenge cố định, không fit |
| tools/backup_logs.py / manage_credentials.py | vận hành OS không qua web |
| tools/h07_acceptance.py | hiệu năng và block rate qua TCP, fixture do chủ quản lý |

## 2. Cài đặt và tái lập

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ci.txt
.\.venv\Scripts\python.exe tools/prepare_workspace.py
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe tools/manage_credentials.py --role admin
.\.venv\Scripts\python.exe run.py
```

Workspace hiện tại dùng venv ở thư mục cha, tương ứng
`..\.venv\Scripts\python.exe`. requirements-ci pin đúng phiên bản thực
nghiệm để load artifact; requirements.txt là dải hỗ trợ, dùng dải khác
có thể có cảnh báo không tương thích pickle. Không load artifact lạ.
prepare_workspace chỉ khôi phục input bị gitignore khi chưa có, bằng
dataset seed cố định và baseline versioned đã xác minh hash; không ghi đè
model hiện có, không tự deploy v2. CI được thêm nhưng chỉ báo PASS khi
GitHub Actions thực sự chạy, không suy từ kết quả local.

## 3. Bảo mật và storage

[AN_NINH_VAN_HANH.md](AN_NINH_VAN_HANH.md) là runbook phân quyền,
mật khẩu, CSRF, throttling, cookie, OS ACL, backup và các giới hạn.
Migration lúc startup additive: tạo bảng/index/trigger thiếu, không xóa
event cũ. Xuất CSV chỉ admin, không export DB/password. SQL filter có
whitelist và bound params; export chống công thức spreadsheet.

Mật khẩu admin mặc định ngẫu nhiên chỉ bootstrap local. Khi dùng hash
persisted, terminal không in plaintext. Credential history và DB nằm
ngoài Git. Không đặt backup trong shared_files. Giữ bằng chứng cũ và
thực nghiệm mới trong thư mục timestamp riêng; không tự purge dữ liệu.

## 4. Tách phát hiện và ngăn chặn

Download vẫn dùng LR v1 và policy an toàn. V2 chỉ nằm trong thực nghiệm;
không có route triển khai model mới. AI error/skipped hoặc score cao
không thay đổi quyền filesystem. Các test cố ý mô phỏng false negative,
false positive và inference failure để xác minh điều này.

## 5. Quy trình quản lý thay đổi

Thay đổi được thực hiện trên nhánh `h07/complete-minimum-requirements`.
Đóng gói source, dữ liệu tổng hợp/public và bằng chứng đã kiểm tra;
không thêm local DB, credential thật hoặc token GitHub. Tạo PR để owner
review; không tự merge main. Các báo cáo cũ giữ nguyên theo lịch sử, báo
cáo mới không sửa ngược số liệu để làm đẹp kết quả.
