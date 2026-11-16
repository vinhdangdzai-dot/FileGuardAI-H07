# Thực nghiệm HTTP qua TCP và mô hình sau huấn luyện lại

Ngày thực nghiệm: **16/11/2026**, khoảng **22:24–22:27, Asia/Saigon (UTC+7)**.
Đây là số liệu đã chạy trên máy, không phải kết quả dự kiến.

## 1. Môi trường và phương pháp

- Windows 11 build 26200, Python 3.12.10, scikit-learn 1.9.1, NumPy 2.5.5.
- Khởi tạo ứng dụng Flask thực bằng `create_app`, phục vụ bằng Werkzeug WSGI
  tại `127.0.0.1:5000`; gửi yêu cầu bằng `http.client.HTTPConnection` qua TCP.
  Không dùng Flask test client cho các ca TCP.
- Dùng đúng `shared_files` và `artifacts/model.joblib` của dự án.
- Dùng database SQLite riêng trong thư mục bằng chứng để không trộn kết quả
  với nhật ký demo cũ. Code/schema/luồng ghi SQLite của ứng dụng giữ nguyên.
- Tạo tệp kiểm chứng chứa marker ngẫu nhiên ở **ngoài** `shared_files`.
  Kiểm tra marker không xuất hiện trong response của mỗi ca TCP chi tiết;
  các ca 200 phải trả đúng từng byte của tệp công khai được yêu cầu.
- Không thay đổi giao diện hoặc chức năng ứng dụng. Server được tắt sau
  kiểm thử; chỉ xóa các link/junction do công cụ kiểm thử vừa tạo. Tệp bằng
  chứng và database kiểm thử được giữ lại.

Nguồn bằng chứng chính:
[summary.json](evidence/tcp_20261116T152600Z_66df95/summary.json),
[môi trường thư viện](evidence/2026-11-16/environment.txt).

## 2. Khắc phục không tương thích model

Sao lưu model cũ và kết quả cũ trong `docs/evidence/2026-11-16/`, sau đó chạy:

```powershell
..\.venv\Scripts\python.exe -m ml.train_model --n 10000
```

Đã lưu lại model bằng scikit-learn **1.9.1**. `ml/train_model.py` bổ sung
metadata thời điểm UTC và phiên bản Python/scikit-learn/NumPy trong JSON
để truy vết môi trường huấn luyện. Không thay đổi thuật toán, đặc trưng,
tham số hoặc cách chia train/test theo family.

Kết quả trên 10.000 mẫu tổng hợp, train 7.999 và test 2.001:

| Chỉ số | Logistic Regression | Baseline regex |
|---|---:|---:|
| Accuracy | 0,8751 | 0,8751 |
| Precision | 1,0000 | 1,0000 |
| Recall | 0,7500 | 0,7500 |
| F1 | 0,8571 | 0,8571 |

Ma trận `[TN, FP; FN, TP]`: `[[1001, 0], [250, 750]]`.
Đây là kết quả dữ liệu tổng hợp; không suy rộng thành hiệu quả ngoài thực tế.
Recall chưa đạt 95%; chưa có bằng chứng AI tốt hơn baseline trên tập này.

Đã kiểm tra load và predict với `InconsistentVersionWarning` được nâng
thành exception; không có lỗi. Bộ pytest cũng chạy với chính sách này.
Model SHA-256:
`4d7324aa302ecb3d1b731561210a0041e4aef3f740cc68d9187097a80e5a6322`.

Bằng chứng:
[kết quả sau huấn luyện](evidence/2026-11-16/training_results_after.json),
[kết quả trước huấn luyện](evidence/2026-11-16/training_results_before.json).
Model cũ được giữ để đối chiếu, không dùng để chạy ứng dụng.

## 3. Smoke test TCP và bảng test case

`tools/verify_tcp.py` khởi động server rồi gọi smoke script qua process riêng.
Smoke script: **10/10 PASS**, exit code 0.
[Đầu ra smoke HTTP](evidence/tcp_20261116T152600Z_66df95/smoke_http.txt).

Bộ chi tiết: **24 ca: 21 PASS, 0 FAIL, 3 SKIP**.

| Mã TC | Nhóm đầu vào | Mong đợi | Thực tế | Kết quả |
|---|---|---|---|---|
| TC01–TC03 | Tệp hợp lệ, Unicode/dấu cách, thư mục con | 200, đúng byte | 200, đúng byte | PASS |
| TC04 | `../` tới tệp kiểm chứng ngoài kho | 403, không có marker | Đúng | PASS |
| TC05 | `..` | 403 | 403 | PASS |
| TC06 | `..\` tới tệp ngoài kho | 403, không có marker | Đúng | PASS |
| TC07–TC10 | Absolute tới tệp ngoài kho, POSIX, Windows, UNC | 403 | 403 | PASS |
| TC11 | URL-encoded traversal tới tệp ngoài kho | 403, không có marker | Đúng | PASS |
| TC12–TC14 | Double/triple encoding, separator Windows mã hóa | 403 | 403 | PASS |
| TC15–TC16 | Tệp thiếu, gồm tên Unicode trong thư mục con | 404/MISS | Đúng | PASS |
| TC17–TC19 | Traversal giữa đường dẫn, NUL, yêu cầu thư mục | 403 | 403 | PASS |
| TC20–TC22 | Ba trường hợp symlink cần kiểm tra lại | Tạo link rồi kiểm tra 403 | Tạo link thất bại, WinError 1314 | SKIP |
| TC23–TC24 | Junction tới ngoài kho, tệp tồn tại/không tồn tại | 403, không có marker | Đúng | PASS |

Bảng đầy đủ có **mã TC, đầu vào URL chính xác, mong đợi, thực tế,
PASS/FAIL/SKIP và link bằng chứng từng ca**:

- [Bảng Markdown](evidence/tcp_20261116T152600Z_66df95/test_cases.md).
- [Bảng CSV UTF-8 BOM dùng trong Excel](evidence/tcp_20261116T152600Z_66df95/test_cases.csv).

Mỗi JSON `TCxx.json` ghi URL gửi, đường dẫn sau giải mã, HTTP thực tế,
response headers, độ dài và SHA-256 response, từng phép kiểm tra boolean,
thời gian bắt đầu/kết thúc UTC và bản ghi SQLite liên quan.

Không ca TCP đã thực hiện nào trả về marker của tệp ngoài kho. Kết quả
này xác nhận các trường hợp đã kiểm thử; không phải chứng minh an toàn
cho mọi payload hoặc mọi điều kiện tranh chấp đồng thời.

## 4. Đối chiếu SQLite

Database bằng chứng:
[events.sqlite3](evidence/tcp_20261116T152600Z_66df95/events.sqlite3).

Mỗi ca chi tiết đã xác minh:

1. Chính xác một bản ghi mới cho một yêu cầu download.
2. IP bằng `127.0.0.1`.
3. Đường dẫn bằng giá trị sau một lần giải mã query của Flask.
4. Điểm AI bằng kết quả tính lại bằng model mới, sai số dưới `1e-12`;
   nhãn đúng theo ngưỡng 0,5.
5. ALLOW/BLOCK/MISS tương ứng 200/403/404; HTTP trong log khớp response.
6. `created_at` là UTC và thuộc khoảng thời gian yêu cầu, dung sai một giây
   do log chỉ lưu đến giây; `duration_ms` hữu hạn và không âm; lý do không rỗng.

Tổng cả smoke và bộ chi tiết: **31 bản ghi**, gồm **6 HTTP 200,
22 HTTP 403, 3 HTTP 404**. IP duy nhất là `127.0.0.1`.
Thời gian xử lý ghi trong log: min **0,5693 ms**, trung bình **2,9663 ms**,
max **16,2228 ms**. Đây là đo một lượt local, không phải benchmark tải;
`duration_ms` được ghi trước khi truyền hết response và không phải độ trễ
tải tệp đầu cuối qua mạng.

[Bằng chứng tổng hợp SQLite](evidence/tcp_20261116T152600Z_66df95/sqlite_audit.json).

## 5. Pytest và symlink

```powershell
..\.venv\Scripts\python.exe -m pytest -q -rs -W error::sklearn.exceptions.InconsistentVersionWarning --junitxml=docs/evidence/2026-11-16/pytest.xml
```

Thực tế: **35 passed, 3 skipped, 15 subtests passed**, không có cảnh báo
lệch phiên bản. Bao gồm hồi quy dashboard/đăng nhập, log, tên đặc biệt,
AI false negative và false positive không thay thế quyết định an toàn.

[Đầu ra pytest](evidence/2026-11-16/pytest.txt),
[JUnit XML](evidence/2026-11-16/pytest.xml).

Ba test symlink cũ vẫn SKIP. Công cụ TCP cũng thử lại ba tình huống tương
ứng và ghi được `WinError 1314: A required privilege is not held by the client`.
Không giả lập để đánh dấu PASS; không tự thay đổi Developer Mode hay quyền
Windows. Cần chạy lại với quyền tạo symlink phù hợp để bổ sung kết quả.
Junction Windows đã tạo thành công và cả hai ca escape đều PASS.

## 6. Cách tái lập và giới hạn

Từ thư mục `FileGuardAI_H07`, dùng môi trường đã cài thư viện:

```powershell
..\.venv\Scripts\python.exe tools/verify_tcp.py
```

Cổng 5000 phải đang trống. Công cụ tự chạy/tắt Flask và tạo thư mục bằng
chứng mới theo timestamp/UUID, không ghi đè các lần kiểm thử trước.
Không cần khởi động `run.py` trước khi chạy công cụ này.
`tools/smoke_http.py` vẫn dùng riêng được nếu server localhost đã khởi động.

Các giới hạn còn lại: chưa kiểm thử nhánh POSIX trên máy này; Windows
vẫn yêu cầu kho không bị người không tin cậy sửa đồng thời để tránh TOCTOU;
ba ca symlink chưa thể thực hiện; chưa thử tải đồng thời hoặc triển khai
production. Chính sách từ chối escape cấu trúc còn sót lại vẫn áp dụng,
kể cả tên literal chứa các escape đã dành riêng. Không thay đổi các giới
hạn bảo mật production khác trong README.
