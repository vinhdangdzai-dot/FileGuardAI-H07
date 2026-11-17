# Tích hợp 10.000 mẫu vào AI Training — 17/11/2026

Nhánh `h07/cybersecurity-ui`, PR #2. Không đổi dataset, nhãn, mô hình triển khai, chính sách Path Traversal, CSRF/session/phân quyền hoặc SQLite nghiệp vụ. Không merge main.

## Dữ liệu xác nhận

File `data/paths_synthetic.csv` đã tồn tại nên không sinh lại hoặc ghi đè. [Audit thực tế](audit_20261117T081413Z_b9cdfa/audit.json):

| Tiêu chí | Kết quả |
|---|---|
| Dòng dữ liệu (không tính header) | 10.000 |
| Nhãn 0 / nhãn 1 | 5.000 / 5.000 |
| Family | 35 |
| Cột | path, label, family |
| Trùng chuỗi nguyên bản | 0 dòng dư |
| Trùng canonical | 32 nhóm, 32 dòng dư; 0 nhóm xung đột nhãn |
| Tái tạo trong RAM bằng seed 2026 | Khớp từng byte qua SHA-256 |

SHA-256 CSV gốc và bản tái tạo trong RAM đều là:

`2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0`

Khóa canonical audit: Unicode NFC → đúng hai lượt URL unquote → backslash thành slash → casefold. Không loại bỏ dot-segment, không resolve filesystem. Đây là phép so sánh dữ liệu, không dùng để mở file hoặc cấp quyền. Không xóa 32 dòng dư, không sửa nhãn để làm đẹp số liệu. Split strict gộp family có chung khóa canonical vào cùng component.

CSV vẫn bị `.gitignore` loại trừ. Khôi phục **chỉ khi file chưa có**, từ thư mục gốc dự án và đúng môi trường Python:

```powershell
python -m ml.generate_dataset --output data/paths_synthetic.csv --n 10000
python tools/audit_training_dataset.py
```

Generator hiện có mặc định seed 2026; chế độ mở `x` từ chối ghi đè. Audit chỉ đọc CSV, sinh bản so sánh trong RAM và ghi report mới; không cần commit CSV gốc. Không chạy lệnh xóa CSV để khôi phục khi đã có dữ liệu.

## Xem / tìm / xuất toàn bộ mẫu

Đăng nhập **Admin** → **AI Training** → **Tra cứu toàn bộ dữ liệu**. Mặc định 50 mẫu/trang (200 trang); chọn 100 mẫu/trang (100 trang). STT là vị trí 1-based trong CSV gốc, không đánh số lại khi lọc. Trang trước/sau giữ tìm kiếm, nhãn, family, kích thước trang và run. Tìm literal substring không phân biệt hoa thường, hỗ trợ Unicode; không chạy regex hoặc diễn giải wildcard. Đổi bộ lọc bắt đầu từ trang 1. Trang vượt cuối được đưa về trang cuối; tham số không hợp lệ trả 400, run không được backend liệt kê trả 404.

Chỉ tối đa 50/100 mẫu được đưa vào HTML, không nhúng 10.000 dòng vào JavaScript. Backend đọc CSV trong giới hạn 32 MiB hiện có và lọc/cắt trang trong RAM; với quy mô lớn hơn nên cân nhắc chỉ mục/persistent data store. Không đưa dữ liệu huấn luyện vào SQLite nghiệp vụ.

Nút **Tải CSV dữ liệu** gửi POST kèm CSRF hiện có và luôn xuất đủ 10.000 dòng, kể cả đang lọc hoặc không có kết quả. Export giữ chống spreadsheet formula injection hiện có; vì vậy CSV xuất là bản an toàn để xem, không thay cho CSV gốc dùng kiểm hash. Guest bị chuyển đăng nhập; Auditor bị 403 cho cả trang và export khi có CSRF hợp lệ. HTML/Jinja autoescape bảo vệ path/family/query có markup.

## Thực nghiệm tái lập, tách bạch mô hình

Đã chạy `python tools/evaluate_strict_groups.py`, tạo mới [run 20261117T081416Z_5cb7da](../evaluations/20261117T081416Z_5cb7da/results.json). Không ghi đè run cũ, không cập nhật `latest.json`, không thay `artifacts/model.joblib`. Trang Training ưu tiên run strict hợp lệ mới nhất trong danh sách backend; bộ chọn cho phép xem run lịch sử. Metadata và metrics dùng cùng một results.json. Không điền Validation hoặc tham số còn thiếu từ run khác.

| Phân hoạch | Mẫu | Nhãn 0 | Nhãn 1 |
|---|---:|---:|---:|
| Train fit chọn C v2 | 6.500 | 3.000 | 3.500 |
| Validation chọn C v2 | 1.999 | 999 | 1.000 |
| Test | 1.501 | 1.001 | 500 |
| Development/refit = Train + Validation | 8.499 | 3.999 | 4.500 |

35 family được gộp thành 26 component. Family overlap, exact path overlap và canonical overlap đều rỗng giữa các phân hoạch. Seed 2026; threshold 0,5. Chọn C từ 0,1 / 1 / 10 bằng F1 validation, hòa chọn C nhỏ nhất: C v2 = 0,1. Scaler/model refit bằng development sau chọn C, không dùng Test. Đây là protocol có sẵn được chạy lại, không chỉnh thuật toán từ kết quả Test.

| Tập / phương pháp | Accuracy | Precision | Recall | F1 | [[TN, FP], [FN, TP]] |
|---|---:|---:|---:|---:|---|
| Test · LR v1 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | [[1001, 0], [0, 500]] |
| Test · LR v2 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | [[1001, 0], [0, 500]] |
| Test · Regex | 1,0000 | 1,0000 | 1,0000 | 1,0000 | [[1001, 0], [0, 500]] |
| Ngoài · LR v1 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | [[118, 0], [0, 118]] |
| Ngoài · LR v2 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | [[118, 0], [0, 118]] |
| Ngoài · Regex | 1,0000 | 1,0000 | 1,0000 | 1,0000 | [[118, 0], [0, 118]] |

Tập ngoài là snapshot 236 mẫu LFISuite + Starlette hiện có, không thu thập nguồn mới hay coi là test mù. Không gộp chỉ số ngoài vào Test. Median warm-batch Test 1.501 mẫu, 7 lượt, gồm trích đặc trưng + suy luận: LR v1 51,9815 ms, LR v2 112,2732 ms, Regex 2,7178 ms. Số này là độ trễ batch tại máy chạy, không phải HTTP hoặc cam kết hiệu năng. [Split](../evaluations/20261117T081416Z_5cb7da/split.csv), [cấu hình trước fit](../evaluations/20261117T081416Z_5cb7da/plan_before_fit.json), [lựa chọn/freeze trước test](../evaluations/20261117T081416Z_5cb7da/models_frozen_before_test.json), dự đoán, biểu đồ và manifest nằm trong cùng thư mục run.

Các bảng 18 đặc trưng v1, 30 đặc trưng v2 và hệ số vẫn thuộc model triển khai v1 / frozen reference v2; giao diện ghi rõ chúng khác model thực nghiệm của run. Link Evaluation giữ nguyên run để xem biểu đồ, confusion matrix và tập ngoài. LR chỉ hỗ trợ cảnh báo, kiểm tra phạm vi đường dẫn độc lập quyết định quyền tải.

**Kết quả 100% trên tập dữ liệu kiểm thử không chứng minh hệ thống phát hiện hoặc ngăn chặn 100% các cuộc tấn công Path Traversal trong thực tế.** Nguồn tổng hợp đã được xem từ trước, cùng pattern/generator và nhãn lexical có thể tạo source bias. Canonical split chỉ loại giao nhau theo phép chuẩn hóa công bố, không loại mọi tương đồng ngữ nghĩa. Không có bằng chứng LR v2 tốt hơn LR v1/Regex trong lần chạy này.

## Kiểm thử và file thay đổi

- [Pytest stdout](../ui/pytest_20261117T081620Z/stdout.txt): **158 PASS, 0 FAIL, 0 ERROR, 3 SKIP**, 15 subtests PASS, 74,68 s. Baseline 143 PASS/3 SKIP; thêm 15 regression cases. SKIP giữ nguyên lý do quyền symlink Windows.
- [Edge TCP/browser](../ui/browser_20261117T081653Z_148fdc/results.json): **248 PASS, 0 FAIL**, không lỗi JavaScript/static. Thêm 7 checks cho dataset, giữ kiểm tra auth/download/traversal và Light/Dark tại 1440/768/390px. [Ảnh Training](../ui/browser_20261117T081653Z_148fdc/06_training_desktop.png).
- Acceptance: xem [summary](../bao_cao_h07/evidence/20261117T081743Z_92c28e/summary.json) và stdout/JUnit/HTTP test cases cùng thư mục. Hoàn tất **6/6 bước exit 0**; pytest 158 PASS/3 SKIP; dashboard TCP 41 PASS; download 33 PASS/3 symlink SKIP; hiệu năng 144 request, 144 dòng SQLite fixture, 0 lỗi. Hash CSV/deployed v1/frozen v2/SQLite nghiệp vụ trước và sau đều không đổi. Probe symlink exit 0 không biến các ca thiếu quyền thành PASS.
- Chrome local vẫn có giới hạn crash môi trường đã ghi ở [báo cáo theme](../ui/LIGHT_DARK_MODE.md). Workflow Chrome bắt buộc trên Windows CI chạy cùng suite; trạng thái và artifact của commit xem trên PR #2, không lấy kết quả Edge làm Chrome PASS.

| TC | Nội dung | Kết quả / minh chứng |
|---|---|---|
| DS01 | 10.000 dòng, cân bằng nhãn, 35 family, cột/hash/seed | 7 điều kiện audit PASS |
| DS02 | Trang đầu/cuối 50/100, vượt cuối | 4 tham số test PASS |
| DS03 | Tìm Unicode/literal, label/family kết hợp, giữ bộ lọc | Regression và TCP PASS |
| DS04 | Tham số sai | 6 tham số test trả 400 PASS |
| DS05 | XSS path/family/query | Escape HTML PASS |
| DS06 | Export đủ 10.000, CSRF, Guest/Auditor | Regression và TCP PASS |
| DS07 | Strict mặc định, run lịch sử không trộn số liệu | Regression và TCP PASS |
| DS08 | Flask, Path Traversal, auth hiện hữu | Toàn bộ pytest không FAIL/ERROR |

File code: `app/training_view.py` (phân trang, bỏ preview cố định), `app/web.py` (GET filters + chọn run đã validate), `app/templates/ai_training.html`, hai partial mới `_training_dataset.html` và `_training_results.html`, `tools/audit_training_dataset.py` (mới), `tools/verify_ui_browser.py`, `tests/test_training_dataset.py` (mới), `tests/test_ui.py`. Assertion form cũ được cập nhật để kiểm rõ hai GET form mới; POST export/logout vẫn giữ nguyên. Không nới auth hoặc đổi FAIL thành SKIP.

Tài liệu/evidence: báo cáo này, audit JSON, run strict mới (hai model **thực nghiệm** riêng), pytest/browser/acceptance snapshots mới, các liên kết README và ma trận kiểm thử. Không commit dataset bị ignore, mật khẩu, profile browser hoặc SQLite nghiệp vụ. Chứng cứ có sẵn từ 025117Z không thuộc thay đổi này.
