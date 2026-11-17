## Giao diện Cybersecurity Dashboard — nhánh review

Đợt hoàn thiện mới: [Login, chọn run và giải thích kết quả AI](docs/ui/REFINEMENT_LOGIN_AI.md). Pytest135 PASS/0 FAIL/0 ERROR/3 SKIP;Chrome85 PASS ở1440/768/390px;acceptance6 bước exit0. Giữ nguyên auth/policy/model/dữ liệu; ảnh trước/sau và trường metadata thiếu được ghi rõ.

[Bàn giao giao diện, ảnh thật và bằng chứng](docs/ui/README.md): dark theme, sidebar responsive, tìm kiếm tệp, biểu đồ dữ liệu thật và các trang AI chỉ đọc. Nhánh `h07/cybersecurity-ui` dựa trên `bb87b23`; không đổi backend hoặc mô hình. Kiểm thử đợt UI:127 pytest PASS/3 SKIP,42 browser checks PASS,acceptance6 bước exit0. Phần hồ sơ bên dưới giữ các số baseline trước nâng cấp UI theo mốc lịch sử.

## Hồ sơ nghiệm thu H07 hiện hành — 17/11/2026

[12 tài liệu và ma trận nghiệm thu](docs/bao_cao_h07/12_MA_TRAN_NGHIEM_THU.md):[bản sửa temp Windows](docs/bao_cao_h07/13_SUA_LOI_PYTEST_WINDOWS11.md) đạt116 pytest PASS,0 FAIL,0 ERROR,3 SKIP trong môi trường Codex; cần chạy lại bằng tài khoản người dùng. TCP dashboard41 PASS,download33 PASS/3 SKIP;144 request hiệu năng không lỗi. Chính sách: chỉ admin xem dashboard/log/AI/CSV; auditor chỉ kho công khai. AI Training chỉ đọc, không tự fit/deploy. 11/12 PI PASS,PI3.1 PARTIAL do symlink thật thiếu quyền Windows11 cục bộ. Các số/quyền ở phần lịch sử bên dưới cần đọc theo mốc thời gian.

# H07 – FileGuard AI: Path Traversal Detection & Prevention (MVP)

**Đề tài:** Xây dựng hệ thống phát hiện và ngăn chặn tấn công Path Traversal trên ứng dụng web sử dụng thuật toán Logistic Regression.

**Trạng thái:** Phiên bản khởi đầu dành cho đồ án tốt nghiệp. Không phải một sản phẩm bảo mật production.

**Hồ sơ H07 mới nhất (17/11/2026):** [ma trận 12 PI](docs/MA_TRAN_H07.md),
[tài liệu bốn chương](docs/h07/CHUONG_1.md),
[runbook quyền/mật khẩu/log](docs/h07/AN_NINH_VAN_HANH.md),
[kết quả thực nghiệm](docs/h07/CHUONG_4.md).
Tự đánh giá minimum: 11/12 Đạt, mục chứng minh symlink Windows còn Chưa đạt.
Clone mới: cài `requirements-ci.txt`, chạy `python tools/prepare_workspace.py`
trước pytest để khôi phục input bị gitignore mà không thay model có sẵn.

**Kết quả rà soát tổng hợp mới nhất:** [docs/BAO_CAO_TONG_HOP.md](docs/BAO_CAO_TONG_HOP.md).
Bao gồm các bản sửa ổn định/bảo mật, kiểm thử TCP, tính lại metrics và
phát hiện 15 đường dẫn train/test tương đương sau chuẩn hóa encoding.

## 1. Tính năng có trong mã nguồn

- Website Flask liệt kê/tải tệp trong `shared_files/`, hỗ trợ tên Unicode, dấu cách và thư mục con.
- Phân tích chuỗi đường dẫn bằng Logistic Regression, ghi xác suất nghi vấn. AI **không cấp quyền truy cập**.
- Lớp phòng vệ độc lập (`app/security.py`) từ chối đường dẫn vượt thư mục, đường dẫn tuyệt đối, đường dẫn Windows và liên kết tượng trưng. Trên Linux/POSIX dùng mở từng thành phần bằng directory fd và `O_NOFOLLOW`.
- Ghi SQLite thời gian UTC, IP, đường dẫn, điểm AI, trạng thái, HTTP code, lý do, độ trễ.
- Dashboard có đăng nhập bằng mật khẩu và biểu đồ Chart.js, frontend Bootstrap (có CSS dự phòng khi mất mạng).
- Sinh dữ liệu mẫu có nhãn (`ml/generate_dataset.py`), huấn luyện Logistic Regression và so sánh với bộ quy tắc (`ml/train_model.py`).
- Bài kiểm thử bằng Pytest và unittest, kể cả trường hợp **AI dự đoán sai lành tính nhưng yêu cầu vẫn phải bị chặn**.

## 2. Cài đặt trên Windows 11 (PowerShell)

Cài **Python 3.11 hoặc 3.12**, xác nhận bằng `py -V`. Giải nén file ZIP vào thư mục ngắn không có ký tự lạ, ví dụ `D:\DoAn\FileGuardAI`.

Mở PowerShell trong thư mục dự án và chạy từng lệnh:

```powershell
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m ml.train_model
python -m pytest -q
python run.py
```

Cách đơn giản hơn: **nhấp đúp `START_WINDOWS.bat`** để tự cài phụ thuộc, huấn luyện nếu chưa có model và khởi chạy website.

Sau đó mở trình duyệt: **http://127.0.0.1:5000**. Khi `python run.py` chạy, mật khẩu quản trị được in ngay trên màn hình Terminal. Truy cập `http://127.0.0.1:5000/login` để mở trang thống kê.

Có thể đặt mật khẩu cố định bằng biến môi trường trước khi chạy (chỉ để demo local):

```powershell
$env:ADMIN_PASSWORD = "Thay-Bang-Mat-Khau-Rieng"
python run.py
```

Khi server đang chạy, mở cửa sổ Terminal thứ hai và gõ `python tools/smoke_http.py` để thực hiện các ca kiểm thử HTTP tự động. Có thể chạy `TEST_WINDOWS.bat` để thử Pytest.

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m ml.train_model
pytest -q
python run.py
```

## 3. Cấu trúc mã nguồn

```text
path_traversal_h07_mvp/
├── run.py                   # Khởi động máy chủ localhost
├── START_WINDOWS.bat        # Tự thiết lập và khởi động trên Windows
├── TEST_WINDOWS.bat         # Chạy kiểm thử trên Windows
├── tools/smoke_http.py      # Kiểm thử HTTP mẫu (chỉ localhost)
├── app/
│   ├── __init__.py           # Ứng dụng Flask factory (lazy import)
│   ├── web.py                # Download, login và dashboard
│   ├── security.py           # Phòng ngừa Path Traversal độc lập AI
│   ├── ml_features.py        # Trích xuất đặc trưng cho Logistic Regression
│   ├── database.py           # SQLite logs
│   ├── templates/            # Giao diện Jinja2/HTML/Bootstrap
│   └── static/               # CSS, Chart.js init
├── ml/
│   ├── generate_dataset.py   # Sinh dữ liệu giả lập, có nhãn
│   └── train_model.py        # Huấn luyện, nhóm train/test, đánh giá
├── tests/                   # Kiểm thử Pytest / unittest
├── shared_files/             # Tài liệu công khai được phép tải
├── artifacts/                # Model .joblib, kết quả .json
├── instance/                 # SQLite log khi chạy (tự tạo)
├── docs/                     # Ma trận H07 và kế hoạch
└── requirements.txt
```

## 4. Thực nghiệm trên hệ thống **do bạn tự quản lý**

Chi tiết bản sửa mã hóa URL, chính sách và kết quả kiểm thử mới:
[docs/SUA_PATH_TRAVERSAL.md](docs/SUA_PATH_TRAVERSAL.md).
Thực nghiệm TCP, bảng test case và bằng chứng SQLite sau huấn luyện lại:
[docs/CHUONG_4_KIEM_THU_TCP.md](docs/CHUONG_4_KIEM_THU_TCP.md).
Flask giải mã query đúng một lần; lớp truy cập tệp từ chối các escape cấu
trúc còn sót lại (`%2e`, `%2f`, `%5c`, `%00`, `%3a`, `%25`) mà không giải
mã thêm. Vì vậy payload mã hóa nhập qua form cũng trả 403; tệp không tồn
tại có cú pháp hợp lệ vẫn trả 404 bất kể điểm AI.

| Yêu cầu | Kết quả mong đợi |
|---|---|
| `baocao.pdf` | HTTP 200, tải tệp thành công |
| `báo cáo tốt nghiệp.pdf` | HTTP 200, hỗ trợ Unicode và dấu cách |
| `tailieu/chuong1.pdf` | HTTP 200, hỗ trợ thư mục con |
| `../secret.txt` | HTTP 403 |
| `../../config.txt` | HTTP 403 |
| `..%2Fsecret.txt` (gửi trong URL) | HTTP 403 khi Flask đã giải mã query |
| Symlink bên trong trỏ đến bên ngoài | HTTP 403 |
| `khong_co.txt` | HTTP 404 |

**Lưu ý:** Dự án đã cung cấp 3 tệp PDF mẫu thực tế theo đúng tên trong H07. Có thể thay bằng tài liệu riêng để trình diễn; chỉ đặt tài liệu công khai, không đặt thông tin nhạy cảm trong `shared_files/`.

## 5. Kết quả AI và cách viết báo cáo

Đánh giá dữ liệu **hiện có**, tạo artifact riêng và không thay model triển khai:

```powershell
python -m ml.evaluate --repeats 15
```

Xem [báo cáo thực nghiệm AI mới](docs/CHUONG_4_DANH_GIA_AI.md).
So sánh LR v1, LR v2 và regex với test cố định, validation theo nhóm và
corpus ngoài có nguồn: [docs/CAI_TIEN_LR_V2.md](docs/CAI_TIEN_LR_V2.md).
Model v2 chỉ là artifact thực nghiệm, không tự thay model đang triển khai.
Sau đăng nhập, dashboard có nút **Kết quả đánh giá AI** để xem metrics,
confusion matrix, thời gian dự đoán và biểu đồ của lần đánh giá mới nhất.
Các lần đánh giá được lưu riêng trong `docs/evaluations/`.

Chạy `python -m ml.train_model`. Kết quả nằm ở `artifacts/training_results.json`:

Lệnh huấn luyện giữ CSV hiện có, sao lưu model/results cũ vào
`artifacts/history/` trước khi lưu output mới. Bộ sinh dữ liệu từ chối
ghi đè file đã tồn tại; hãy chọn tên output mới cho một dataset mới.

- Số mẫu trong train/test và các *template families* dành riêng cho kiểm thử.
- Accuracy, Precision, Recall, F1, Confusion Matrix.
- So sánh Logistic Regression với baseline regex giản lược.

**Không được trình bày kết quả trên dữ liệu tự sinh như bằng chứng mô hình hiệu quả ngoài thực tế.** Cần bổ sung tập dữ liệu độc lập, thử trên biến thể chưa có trong quá trình sinh dữ liệu; ghi các hạn chế và phân tích false positives / false negatives.

**So sánh ba phương án:** (A) Logistic Regression dùng cho phát hiện; (B) regex đơn giản dùng cho phát hiện; (C) kiểm tra đường dẫn thực tế, làm chuẩn an toàn độc lập. C không phải classifier có thể thay bằng AI, mà là tầng quyết định cho phép/từ chối.

## 6. Giới hạn bảo mật cần nêu trong đồ án

- Chỉ chạy trên **localhost**, không công khai Internet; `debug=False`.
- **Không** để người khác có quyền ghi trực tiếp vào `shared_files/`. Trên Windows, rủi ro race condition do symlink/reparse point vẫn có nếu thư mục bị người không tin cậy sửa trong lúc hệ thống hoạt động. Trên POSIX có biện pháp `O_NOFOLLOW` nhưng không thay thế kiểm soát quyền hệ điều hành.
- Mật khẩu quản trị được sinh ngẫu nhiên mỗi lần chạy nếu không đặt `ADMIN_PASSWORD`, phiên đăng nhập hết hiệu lực khi chạy lại. Ở production phải có HTTPS, quản trị người dùng, CSRF, giới hạn thử mật khẩu, phân quyền và lưu secret lâu dài; demo này **chưa** có đầy đủ các biện pháp đó.
- Đừng giải mã URL nhiều lần ở tầng truy cập tệp. Flask đọc `request.args` đã giải mã URL query; bộ đặc trưng AI có thể phân tích biểu diễn khác nhưng chỉ cho mục đích cảnh báo.
- Không tải các tệp mã nguồn/model `.joblib` không tin cậy. `joblib.load` có thể thực thi mã khi tải tệp độc hại.
- Trong thực tế nên sử dụng **ID tệp do máy chủ phát sinh** thay vì cho phép nhập trực tiếp đường dẫn, nếu yêu cầu nghiệp vụ cho phép.
- Phụ thuộc Bootstrap và Chart.js qua CDN, biểu đồ có thể không hiển thị khi máy hoàn toàn ngoại tuyến; danh sách và thống kê vẫn đọc được.

Kết quả chạy bước đầu được ghi trung thực trong [docs/KET_QUA_BAN_DAU.md](docs/KET_QUA_BAN_DAU.md).

## 7. Nguồn tham khảo và bản quyền

Mã nguồn MVP trong ZIP được viết mới để phù hợp đề cương H07; không chép nguyên dự án GitHub.

- [OWASP Path Traversal Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Path_Traversal_Prevention_Cheat_Sheet.html)
- [MITRE CWE-22](https://cwe.mitre.org/data/definitions/22.html)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [ML-based-WAF (tham khảo quy trình ML)](https://github.com/vladan-stojnic/ML-based-WAF)
- [Path Traversal secure.py (tham khảo kiểm tra đường dẫn)](https://github.com/talkpython/python-web-owasp-top-10-with-agentic-ai-course/blob/main/examples/01-broken-access-control/ex2-path-traversal/secure.py)
- [SecLists (tham khảo lựa chọn payload kiểm thử)](https://github.com/danielmiessler/SecLists)

Không sao chép dữ liệu, giấy phép hoặc tuyên bố tác quyền của repository bên ngoài mà chưa kiểm tra điều kiện sử dụng.
