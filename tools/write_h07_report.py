"""Render the dated H07 acceptance dossier from retained, actual evidence."""
import json
from pathlib import Path
from app.ml_features import FEATURE_NAMES, FEATURE_NAMES_V2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/bao_cao_h07'
E = 'evidence/20261116T182248Z_5acba3'
RUN = '20261116T181019Z_dea9ec'
P = '../h07/evidence/20261116T182323Z_0090f9/performance.json'


def write(name, title, content, status='PASS'):
    OUT.mkdir(parents=True, exist_ok=True)
    header = f'# {title}\n\nBản nghiệm thu ngày 17/11/2026 (giờ Việt Nam). Phạm vi: MVP localhost Windows 11; không phải chứng nhận triển khai Internet.\n\n'
    tail = f'\n\n**Trạng thái: {status}.** Đối chiếu [ma trận tổng hợp](12_MA_TRAN_NGHIEM_THU.md). '
    tail += f'Bằng chứng chạy thực tế: [summary]({E}/summary.json), [pytest]({E}/pytest.stdout.txt), [bảng HTTP]({E}/http_test_cases.csv).\n'
    (OUT / name).write_text(header + content.strip() + tail, encoding='utf-8')


def main():
    summary = json.loads((OUT / E / 'summary.json').read_text(encoding='utf-8'))
    assert all(step['returncode'] == 0 for step in summary['steps'].values())
    assert all(summary['protected_unchanged'].values())
    write('01_PHAN_TICH_RUI_RO.md', '01 — Phân tích rủi ro Path Traversal / CWE-22', r'''
Ứng dụng công khai danh sách và tải tệp bằng `GET /download?path=...`. Dữ liệu không tin cậy vượt từ query HTTP sang hệ thống tệp là ranh giới chính. Tài sản cần bảo vệ gồm tệp ngoài `shared_files`, SQLite, mật khẩu băm, mô hình và tính sẵn sàng. AI nhận diện ý định dạng chuỗi; kiểm soát truy cập là cơ chế độc lập.

Nguyên nhân lỗi ban đầu: chuỗi mã hóa còn nguyên có thể được coi là tên tệp không tồn tại nên trả MISS/404, trong khi mô hình vẫn nhận tín hiệu nguy hiểm. Không thể suy quyết định HTTP từ điểm 1.000: xác suất mô hình không chứng minh vi phạm quyền. Bản sửa thống nhất Flask giải mã query một lần, từ chối cấu trúc nguy hiểm hoặc escape cấu trúc còn sót; kiểm tra đường dẫn thực và handle trước khi phục vụ.

L và I dưới đây là **nhận định thiết kế**, thang 1–5; R=L×I, không phải thống kê sự cố thực tế.

| ID | Kịch bản / tài sản | L | I | R | Kiểm soát và rủi ro còn lại |
|---|---|---:|---:|---:|---|
| R01 | `../` đọc bí mật | 5 | 5 | 25 | Cấm thành phần cha; containment; HTTP403 |
| R02 | `..\` / dấu phân cách hỗn hợp | 5 | 5 | 25 | Nhận cả hai dấu phân cách trước kiểm tra |
| R03 | Đường dẫn tuyệt đối, ổ đĩa, UNC | 4 | 5 | 20 | Từ chối rooted/drive/colon; không nối trực tiếp với root |
| R04 | URL đơn/hai lớp | 5 | 5 | 25 | Một lần giải mã transport; reserved escapes còn sót bị chặn |
| R05 | Symlink / junction thoát root | 3 | 5 | 15 | Resolve containment + kiểm tra handle Windows; symlink thật còn SKIP |
| R06 | Đổi junction giữa check và open | 3 | 5 | 15 | GetFinalPathNameByHandleW; test hoán đổi junction PASS |
| R07 | Truy cập nhật ký / mô hình qua download | 3 | 5 | 15 | Startup guard không cho private storage nằm trong public root |
| R08 | SQL injection / sửa log | 3 | 4 | 12 | Bind tham số, admin-only, append-only triggers; OS writer vẫn có thể sửa DB |
| R09 | Brute force / CSRF / chiếm session | 3 | 4 | 12 | Hash mật khẩu, throttle, CSRF, expiry; TLS/secret/ACL phải cấu hình khi triển khai |
| R10 | AI false negative/positive | 4 | 4 | 16 | AI chỉ cảnh báo; không cấp quyền; đánh giá FP/FN riêng |
| R11 | DB lỗi / dữ liệu không hợp lệ / DoS | 3 | 3 | 9 | Giới hạn path, kiểm tra hữu hạn, lỗi503 không stream; chưa thử tải Internet |

Mã chứng minh: [security.py](../../app/security.py), [web.py](../../app/web.py), [auth.py](../../app/auth.py), [test handle Windows](../../tests/test_windows_handle.py). Ngoài phạm vi: đối thủ có quyền ghi OS vào root, hardlink, thay root/ACL, cấu hình proxy không tin cậy; xem tài liệu07.

Nguồn định nghĩa: [MITRE CWE-22](https://cwe.mitre.org/data/definitions/22.html), [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal). Không coi mọi dấu chấm hoặc điểm AI cao là tấn công thành công.
''')
    features = '\n'.join(f'| {i+1} | `{name}` | {"v1 + v2" if i < 18 else "v2 thử nghiệm"} |' for i, name in enumerate(FEATURE_NAMES_V2))
    write('02_QUY_TRINH_AI.md', '02 — Quy trình AI và đặc trưng', r'''
Logistic Regression: z=wᵀx+b, P(suspicious)=1/(1+exp(-z)); ngưỡng cố định0.5. Pipeline chuẩn hóa StandardScaler trước LR; chỉ fit trên phần development được phép. Đây là xác suất của nhãn tổng hợp trong phân phối huấn luyện, chưa được hiệu chỉnh thành xác suất khai thác thật.

```mermaid
flowchart LR
 D[CSV có nhãn và family] --> G[Gộp family chung canonical key]
 G --> T[Train / validation / test theo nhóm]
 T --> V[Chọn C chỉ trên validation]
 V --> F[Fit development; đóng băng model]
 F --> E[Đánh giá test và corpus công khai]
 R[Query đã được Flask decode một lần] --> X[Đặc trưng]
 X --> S[Scaler và LR triển khai v1]
 S --> A[Điểm và nhãn cảnh báo]
 R --> P[Kiểm tra quyền độc lập]
 P --> H[200 / 403 / 404]
 A --> L[SQLite và dashboard admin]
 H --> L
```

V1 có18 đặc trưng, giữ tương thích artifact đang triển khai. V2 thêm12 đặc trưng cực đại trên raw, decode1, decode2; chỉ tạo góc nhìn ML, không truyền chuỗi giải mã này tới filesystem. Không dùng `unquote_plus` ở bước ML, không lặp tới khi ổn định. Số thành phần cha và độ sâu thoát đo trên cả `/` và `\`; escape ký tự cấu trúc và số lần decode thay đổi giúp nhận double encoding.

| STT | Đặc trưng trong mã | Phạm vi |
|---|---|---|
''' + features + r'''

Length/count/entropy là tín hiệu thống kê, không phải bằng chứng quyền. Hệ số đọc từ artifact thật qua trang AI Training; hệ số trên không gian đã chuẩn hóa, không diễn giải thành quan hệ nhân quả. Không thay pipeline v1 tại runtime bằng v2.

Nguồn: [ml_features.py](../../app/ml_features.py), [strict_groups.py](../../ml/strict_groups.py), [script đánh giá](../../tools/evaluate_strict_groups.py), [đánh giá và giới hạn](10_DANH_GIA_MO_HINH.md).''')
    write('03_UML_ACTIVITY.md', '03 — UML Activity của yêu cầu tải tệp', r'''
```mermaid
flowchart TD
 S([Bắt đầu GET download]) --> Q[Flask đọc request.args: decode transport một lần]
 Q --> M{AI dự đoán được?}
 M -->|Có| C{Nhãn AI}
 C -->|benign| B[Ghi nhận điểm benign]
 C -->|suspicious| W[Ghi nhận điểm suspicious]
 M -->|Không| U[Ghi unavailable / error; không cấp quyền]
 B --> P[Kiểm tra policy và mở tệp an toàn]
 W --> P
 U --> P
 P --> J{Kết quả}
 J -->|Vi phạm cấu trúc hoặc containment| X[BLOCK 403]
 J -->|Đúng phạm vi, không tồn tại| N[MISS 404]
 J -->|Tệp thường, handle trong root| Y[ALLOW 200 dự kiến]
 X --> L[Ghi access_logs]
 N --> L
 Y --> L
 L --> K{Lưu thành công?}
 K -->|Không| Z[Đóng handle; HTTP503 không stream]
 K -->|Có| R[Trả status và body phù hợp]
 R --> E([Kết thúc])
 Z --> E
```

False negative AI vẫn403 nếu policy bị vi phạm; false positive với tệp hợp lệ vẫn200. Không tồn tại trong root vẫn404 kể cả điểm AI cao. Lỗi cơ sở dữ liệu không được báo nhầm404 và không stream tệp rồi mới thử ghi log. Không bảo đảm có bản ghi SQL trong thời gian SQLite không hoạt động: lỗi được ghi vào server logger, trả503.

Kiểm chứng [test_app.py](../../tests/test_app.py), [test_acceptance_extensions.py](../../tests/test_acceptance_extensions.py), và [TCP](06_MA_TRAN_KIEM_THU.md). Bản PlantUML lịch sử: [download_activity.puml](../h07/diagrams/download_activity.puml); sơ đồ ở đây bổ sung nhánh503 và là mô tả hiện hành.''')
    write('04_KIEN_TRUC_HE_THONG.md', '04 — Kiến trúc và ranh giới tin cậy', r'''
```mermaid
flowchart LR
 U[Trình duyệt / HTTP TCP] --> F[Flask web.py]
 F --> AU[auth.py: session / CSRF / RBAC]
 F --> ML[LR v1 + features + scaler]
 F --> IPS[security.py: policy / resolve / handle]
 IPS --> FS[shared_files chỉ đọc]
 F --> DB[database.py SQLite]
 AU --> DB
 DB --> UI[Dashboard admin + thống kê + CSV]
 TV[training_view.py chỉ đọc] --> UI
 DATA[CSV gốc + artifact cố định] --> TV
 OFF[CLI offline: strict split và đánh giá] --> EV[Artifact mới + biểu đồ + manifest]
 EV --> UI
```

| Module | Đầu vào | Đầu ra / trách nhiệm |
|---|---|---|
| web | Request đã parse | Điều phối tải tệp, đăng nhập, log, render; không fit model |
| security | Root tin cậy + đường dẫn | Handle tệp an toàn hoặc lỗi policy/missing |
| ml_features / predictor | Chuỗi | Vector18 / xác suất; v2 chỉ thử nghiệm |
| auth | Form/session/config hash | Role; CSRF; throttle; expiry |
| database / log_filters | Giá trị đã kiểm tra | INSERT và SELECT bind tham số; hai bảng append-only |
| training_view | CSV và artifact được cấu hình cố định | Thống kê, hệ số thật, lịch sử; không triển khai |
| tools / ml | CSV có nhãn gốc | Đánh giá offline, hình PNG, bằng chứng tái lập |

Đồng bộ theo từng request: AI/policy/SQLite xong trước response. Dashboard cập nhật khi tải lại trang, không khẳng định realtime cứng hoặc xử lý packet mạng. Public root tách DB, dữ liệu huấn luyện, credential, model và evaluation root; startup từ chối cấu hình đặt private storage trong root. SQLite phù hợp demo đơn máy; Flask localhost không chứng minh khả năng chịu tải production. Biến môi trường/secret và ACL do người vận hành quản lý.

Triển khai, rollback, backup và bốn chương đã có: [runbook](../h07/AN_NINH_VAN_HANH.md), [Chương1](../h07/CHUONG_1.md), [Chương2](../h07/CHUONG_2.md), [Chương3](../h07/CHUONG_3.md), [Chương4 lịch sử](../h07/CHUONG_4.md). Bổ sung thực nghiệm mới dùng tài liệu10–12 thay số cũ; không xóa các lần chạy trước.''')
    write('05_CO_SO_DU_LIEU.md', '05 — SQLite, ERD và bảo vệ nhật ký', r'''
```mermaid
erDiagram
 access_logs {
  INTEGER id PK
  TEXT created_at
  TEXT client_ip
  TEXT requested_path
  REAL ml_score
  TEXT ml_label
  TEXT action
  INTEGER http_status
  TEXT reason
  REAL duration_ms
 }
 security_events {
  INTEGER id PK
  TEXT created_at
  TEXT client_ip
  TEXT actor_role
  TEXT event
 }
```

Hai bảng độc lập, không có khóa ngoại giả định giữa request và session. ID tự tăng; các cột ngoài ml_score đều NOT NULL. Thời gian UTC ISO giây; score có thể NULL khi AI không khả dụng. ALLOW→200, BLOCK→403, MISS→404; kiểm tra cặp action/status, nhãn whitelist, probability hữu hạn0..1, duration hữu hạn không âm trước INSERT. Chuỗi path được giới hạn4096. IP lấy theo request, không tin tùy tiện X-Forwarded-For.

Index: `access_logs(created_at)` và `security_events(client_ip,created_at)`. Trigger chặn UPDATE/DELETE trên cả hai bảng. Không chống được chủ sở hữu file OS hoặc người gỡ trigger; DB/backup cần ACL riêng, không đặt trong root công khai. Không lưu mật khẩu, CSRF token hoặc session cookie trong bằng chứng.

Ví dụ truy vấn logic (giá trị dùng tham số, không nội suy):

```sql
SELECT * FROM access_logs
WHERE created_at >= ? AND created_at <= ?
  AND action = ? AND ml_label = ? AND http_status = ?
ORDER BY id DESC LIMIT ?;
```

Bộ lọc đồng thời thời gian UTC, quyết định, nhãn AI, HTTP áp dụng cùng điều kiện cho bảng, thẻ thống kê và export. Giới hạn bảng tối đa500; dashboard là mẫu gần nhất, số đếm là tập lọc. Input sai hoặc start>end trả400, không chạy câu SQL tự do. Trống trả0, không NULL.

`duration_ms` là thời gian xử lý đo trước INSERT/stream, không gồm tải body hoàn chỉnh. Latency TCP trong bài hiệu năng đo từ client đến nhận body xong, không so sánh như cùng đại lượng. Mất SQLite trả503 và giữ kín nội dung; login chỉ cấp session sau audit thành công; logout vẫn xóa session khi audit lỗi.

Đợt144 request có144 dòng, integrity_check=`ok`, trường IP/path/score/action/status/time được công cụ kiểm tra với request thực. Xem [hiệu năng](../h07/evidence/20261116T182323Z_0090f9/performance.json), [database.py](../../app/database.py), [tests mở rộng](../../tests/test_acceptance_extensions.py). Backup CLI [backup_logs.py](../../tools/backup_logs.py) dùng SQLite backup, không ghi đè bằng chứng cũ.''')
    write('06_MA_TRAN_KIEM_THU.md', '06 — Ma trận kiểm thử thực tế', f'''
Môi trường: Windows 11, Python venv hiện tại, scikit-learn1.9.1, Flask/SQLite; localhost qua TCP thật, không chỉ test_client. Lệnh và exit code nằm trong [summary]({E}/summary.json); stdout/stderr/JUnit được giữ cùng thư mục. Chạy bằng `python tools/run_h07_acceptance.py` tạo thư mục mới, không ghi đè bằng chứng cũ.

| Nhóm | Thực tế | Kết luận / bằng chứng |
|---|---|---|
| Pytest | 109 PASS, 3 SKIP, 15 subtests PASS; 22.66s | [stdout]({E}/pytest.stdout.txt), [JUnit]({E}/pytest.xml) |
| Checkout sạch ef545f2 + prepare_workspace | 109 PASS, 3 SKIP, 15 subtests PASS; 38.38s | [JUnit](evidence/clean_ef545f2.xml); cùng venv, không phải cài dependency mới |
| Dashboard/auth/CSV TCP | 41 PASS, 0 FAIL | [JSON](../evaluations/dashboard_http_20261116T172733Z_800c38_http_5badd2c18bb5.json) |
| Download TCP | 33 PASS, 0 FAIL, 3 SKIP | [summary](../evidence/tcp_20261116T182321Z_e9d112/summary.json) |
| Hiệu năng và SQLite | 144 request, 0 lỗi, 144 dòng; integrity ok | [performance]({P}) |
| Symlink Windows | 3 SKIP; thiếu đặc quyền WinError1314 | [probe]({E}/symlinks.stdout.txt); không được tính PASS |
| Junction swap / handle Windows | 2 bài pytest PASS | [test_windows_handle.py](../../tests/test_windows_handle.py) |
| Audit dữ liệu/model | tiến trình exit0 | [audit]({E}/audit) |

Bảng máy đọc có từng mã TC, đầu vào, expected, actual, trạng thái và đường dẫn bằng chứng: **[http_test_cases.csv]({E}/http_test_cases.csv)**. Payload bao gồm tệp thật, Unicode/dấu cách/subdir, `../`, `..`, backslash, absolute/drive/UNC, đơn/hai/nhiều lớp URL encoding, NUL, tên không tồn tại. Body được đối chiếu tệp công khai và sentinel ngoài root; status đúng một mình chưa đủ để kết luận không rò rỉ.

Kiểm thử bổ sung: AI benign không vượt policy; AI suspicious không ép403; AI lỗi; log lỗi503 không đọc body; RBAC guest/auditor/admin; CSRF; mật khẩu; invalid time/status/probability; query thống kê và export cùng scope; CSV formula injection; model checksum trước unpickle; private storage startup guard; canonical split không giao nhau.

Chưa chạy: Python3.11 (đã chạy3.12.10), symlink thật với Developer Mode/SeCreateSymbolicLinkPrivilege, SMB/reparse provider khác, Linux runtime cho nhánh POSIX, kiểm thử mạng production và trình duyệt thủ công. Cần chạy lại trên môi trường tương ứng; không điền PASS trước khi có kết quả. Các fixture/bằng chứng cũ và DB người dùng được giữ nguyên SHA trong summary.
''', 'PARTIAL — symlink thật SKIP')
    write('07_CO_CHE_IPS.md', '07 — Cơ chế ngăn chặn độc lập với AI', r'''
Đây là IPS tầng ứng dụng tại chức năng tải tệp, không phải firewall mạng. Quyết định policy không phụ thuộc probability hay nhãn LR. Thư mục `shared_files` là root cho phép, không phải mọi đường dẫn có cùng tiền tố chuỗi.

1. Flask giải mã query transport đúng một lần. `+` của query là dấu cách; muốn tên có dấu cộng phải gửi `%2B`. Mã tải tệp không gọi unquote lặp.
2. Từ chối đường dẫn rỗng/quá giới hạn/NUL, thành phần `..`, rooted/drive/UNC/colon và escape cấu trúc còn sót (kể cả chuỗi lồng `%25`). Chính sách nghiêm chấp nhận mất một số tên literal chứa escape nguy hiểm; không coi mọi `%` là độc hại.
3. Resolve đường dẫn trong root; kiểm tra containment bằng quan hệ đường dẫn, không startswith; symlink/junction resolve ra ngoài bị từ chối.
4. Chỉ mở tệp thường. POSIX dùng cơ chế không theo link khi có hỗ trợ; Windows lấy đường dẫn chuẩn của **handle đã mở** qua GetFinalPathNameByHandleW rồi kiểm tra với root đã ghim. Không dựa vào việc resolve lại chuỗi request sau open. Lỗi truy vấn handle đóng file và từ chối.
5. Trong phạm vi nhưng thiếu tệp→404; vi phạm policy→403; hợp lệ→200. Lỗi ghi log→503 trước stream.

Nguyên tắc giải mã để truy cập khác góc nhìn ML: ML v2 có raw+hai view hữu hạn để phát hiện, nhưng không được biến view thành đường dẫn tải. Ví dụ `%252e%252e%252f...` qua transport còn `%2e%2e%2f...` bị policy từ chối, không giải mã rồi mở lần nữa.

Test Windows hoán đổi junction sau check trước open chứng minh handle cuối cùng ra ngoài bị chặn; test lỗi API chứng minh đóng handle. Ba symlink thật vẫn SKIP vì quyền OS: không lấy kết quả junction thay thế bằng chứng symlink.

Giới hạn: không bảo vệ trước đối thủ có quyền thay public root/ACL, hardlink tới dữ liệu nhạy cảm, kernel/provider không tin cậy hoặc cấu hình filesystem mạng chưa kiểm thử. Cần root chỉ đọc với tài khoản phục vụ, cấm upload ghi tùy ý, tách private storage. Không tuyên bố hết mọi TOCTOU trên mọi nền tảng.

Mã: [security.py](../../app/security.py), [Windows tests](../../tests/test_windows_handle.py). API tham chiếu: [Microsoft GetFinalPathNameByHandleW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew).''', 'PARTIAL — chặn đã kiểm chứng; symlink thật còn SKIP')
    cases = [
        ('UC01', 'Xem danh sách tệp', 'Khách', 'Public root tồn tại', 'GET /', 'Hiển thị tên/link tệp công khai đã escape HTML', 'Không liệt kê DB/model/log; root lỗi hiển thị lỗi phù hợp', 'Không làm thay đổi tệp', 'tests/test_app.py; TCP public index'),
        ('UC02', 'Tải tệp hợp lệ', 'Khách', 'Tệp thường nằm trong root', 'GET /download?path=tên tương đối', 'Parse→AI→policy→mở an toàn→ghi ALLOW→200 đúng body', 'Thiếu tệp404; policy403; DB lỗi503', 'Không đọc ngoài root; ghi log nếu SQLite hoạt động', 'tests/test_app.py; verify_tcp valid/Unicode/subdir'),
        ('UC03', 'Phát hiện bằng AI', 'Hệ thống; admin xem', 'Artifact v1 tương thích hoặc chế độ unavailable', 'Chuỗi đường dẫn đã parse', 'Trích18 đặc trưng→scaler→LR→score/label→log', 'Model lỗi không cấp quyền; high score vẫn có thể200/404 theo policy', 'Có điểm thật hoặc trạng thái lỗi, không giả điểm', 'tests/test_app.py; test_evaluation.py'),
        ('UC04', 'Ngăn truy cập trái phép', 'Khách tạo request; hệ thống chặn', 'Có root tin cậy', '../, backslash, absolute, encoding, link ra ngoài', 'Policy xác nhận vi phạm→BLOCK403→không stream', 'AI benign vẫn chặn; symlink test thiếu quyền SKIP; lỗi audit503', 'Không lộ sentinel ngoài root trong các test đã chạy', 'tests/test_security.py; test_windows_handle.py; verify_tcp'),
        ('UC05', 'Quản trị nhật ký', 'Admin', 'Đăng nhập admin; SQLite hoạt động', 'GET dashboard và POST export có CSRF; filter UTC/action/AI/HTTP', 'Kiểm quyền→validate filter→query bind→thẻ/chart/bảng; export có audit', 'Guest chuyển login; auditor403; filter sai400; CSRF403; DB503', 'Không sửa/xóa log; export chỉ đúng scope', 'tests/test_auth.py; test_acceptance_extensions.py; dashboard TCP'),
    ]
    uc = '''Các ID sau là đặc tả hiện hành theo yêu cầu nghiệm thu; không dùng nhầm ID UC trong tài liệu lịch sử.

```mermaid
flowchart LR
 Guest["Actor: Khách"] --> UC01([UC01 Xem danh sách])
 Guest --> UC02([UC02 Tải tệp])
 Guest --> UC04([UC04 Ngăn truy cập trái phép])
 Admin["Actor: Admin"] --> UC05([UC05 Xem nhật ký và cảnh báo])
 subgraph FileGuardAI
 UC01
 UC02 -->|include| UC03([UC03 Phát hiện AI])
 UC02 -->|include| UC04
 UC05
 end
 UC03 -->|ghi cảnh báo| UC05
```

Đây là sơ đồ Use Case bằng Mermaid: các nút oval là chức năng trong boundary FileGuardAI; đường include thể hiện tải tệp luôn gọi AI và policy, không phải AI cấp quyền. Khách là tác nhân của yêu cầu, không có quyền cấu hình IPS.
'''
    for code, title, actor, pre, inp, flow, alt, post, test in cases:
        uc += f'\n## {code} — {title}\n\n| Thuộc tính | Đặc tả |\n|---|---|\n| Actor | {actor} |\n| Tiền điều kiện | {pre} |\n| Đầu vào | {inp} |\n| Luồng chính | {flow} |\n| Luồng thay thế / ngoại lệ | {alt} |\n| Hậu điều kiện | {post} |\n| Kiểm thử | {test} |\n'
    uc += '\nUC06 bổ sung: admin mở AI Training chỉ đọc dataset/model/history, export CSV với CSRF; không có endpoint fit/deploy. Thất bại checksum v2 hiển thị unavailable, không nạp pickle tùy ý. UC07: login kiểm hash + throttle + ghi audit trước session; logout luôn xóa session. [Mã routes](../../app/web.py), [test mở rộng](../../tests/test_acceptance_extensions.py).'
    write('08_USE_CASE.md', '08 — Đặc tả Use Case', uc)
    write('09_GIAO_DIEN_PHAN_QUYEN.md', '09 — Dashboard, phân quyền và mật khẩu', r'''
Chính sách hiện hành: chỉ admin được xem dữ liệu nhạy cảm; **auditor chỉ dùng kho công khai**, thay thế quyền đọc dashboard của bản cũ. Không xóa tài liệu lịch sử, nhưng quyền cũ không còn hiệu lực.

| Chức năng | Guest | Auditor đã đăng nhập | Admin |
|---|---|---|---|
| Danh sách / tải công khai | Có, vẫn policy | Có, vẫn policy | Có, vẫn policy |
| Dashboard / AI Evaluation / AI Training | 302 login | 403 | 200 |
| Export log / dataset / weights | 302 login khi token hợp lệ | 403 | POST + CSRF |
| Login | Form + CSRF | Theo luồng session | Theo luồng session |
| Logout | Không cấp quyền | Xóa session | Xóa session |

CSRF có thể403 trước kiểm role nếu token thiếu; đây không phải vượt quyền. Không có API sửa/xóa log từ dashboard. Sidebar, trang download và biểu đồ cũ giữ hoạt động; thêm link AI Training và bộ lọc nhật ký. Tất cả thống kê/export tuân cùng filter. Trang đánh giá chọn run lịch sử bằng ID whitelist/path containment, không đọc đường dẫn tùy ý.

AI Training: thống kê nhãn/family/raw và canonical duplicates, SHA dataset,18/30 feature, hệ số LR thật + scaler/intercept/C, lịch sử đánh giá, link biểu đồ và CSV. Đọc artifact v2 cố định với checksum trước unpickle; chỉ tải pickle tin cậy có nguồn cố định. Không nút tự huấn luyện, thay model hoặc ghi lại CSV. CSV chống công thức ở trường text.

Mật khẩu lưu hash Werkzeug, không plaintext; không hardcode mật khẩu mặc định; tạo hash bằng công cụ cấu hình được hướng dẫn trong runbook. Session có expiry; cookie HttpOnly/SameSite; Secure khi HTTPS phù hợp. Throttle login theo IP có audit; cookie secret cần cấu hình ổn định và riêng tư khi vận hành. Không ghi cookie/token vào bộ chứng cứ. Login audit thất bại không cấp session; logout audit thất bại vẫn xóa session.

Kiểm chứng: [auth.py](../../app/auth.py), [training_view.py](../../app/training_view.py), [templates](../../app/templates), [test_auth.py](../../tests/test_auth.py), [TCP41checks](../evaluations/dashboard_http_20261116T172733Z_800c38_http_5badd2c18bb5.json). Chưa kiểm trình duyệt/thị giác thủ công; không chế ảnh screenshot.''')
    results = json.loads((ROOT / f'docs/evaluations/{RUN}/results.json').read_text(encoding='utf-8'))
    timing_table = '\n| Phép đo strict1501,7 lượt | Median batch ms | Bình quân µs/path |\n|---|---:|---:|\n'
    for key, values in results['datasets']['frozen_holdout']['timing'].items():
        timing_table += f"| {key} | {values['median_batch_ms']:.4f} | {values['amortized_us_per_path']:.4f} |\n"
    performance = json.loads((OUT / P).read_text(encoding='utf-8'))
    requests = [r for trial in performance['trials'] for r in trial['requests']]
    valid = [r for r in requests if r['expected'] == 200]
    succeeded = sum(r['actual'] == 200 and r['exact_public_content'] for r in valid)
    perf_table = '\n| Trial,48 requests /4workers | p50 ms | p95 ms | p99 ms | Request/s |\n|---|---:|---:|---:|---:|\n'
    for trial in performance['trials']:
        a,b,c = trial['latency_ms_p50_p95_p99']
        perf_table += f"| {trial['trial']} | {a:.3f} | {b:.3f} | {c:.3f} | {trial['throughput_rps']:.3f} |\n"
    # Timing values come from the retained machine result, not estimates.
    metrics_link = f'../evaluations/{RUN}/results.json'
    write('10_DANH_GIA_MO_HINH.md', '10 — Báo cáo thực nghiệm Logistic Regression', f'''
Hai câu hỏi tách biệt: chất lượng phân loại chuỗi (LR/Regex) và hiệu quả policy ngăn đọc tệp (HTTP/body). Không dùng tỷ lệ chặn thay Recall của AI. Metrics: Accuracy=(TP+TN)/N; Precision=TP/(TP+FP); Recall=TP/(TP+FN); F1=2PR/(P+R). Confusion matrix theo thứ tự nhãn [benign,suspicious], dạng [[TN,FP],[FN,TP]].

| Tập / phương pháp | Accuracy | Precision | Recall | F1 | Confusion matrix |
|---|---:|---:|---:|---:|---|
| Holdout cũ2001 — LR v1 | 87.5062% | 100% | 75% | 85.7143% | [[1001,0],[250,750]] |
| Holdout cũ2001 — Regex | 87.5062% | 100% | 75% | 85.7143% | [[1001,0],[250,750]] |
| Holdout cũ2001 — v2 frozen | 100% | 100% | 100% | 100% | [[1001,0],[0,1000]] |
| Strict canonical holdout1501 — LR v1 mới fit development | 100% | 100% | 100% | 100% | [[1001,0],[0,500]] |
| Cùng strict1501 — LR v2 mới fit development | 100% | 100% | 100% | 100% | [[1001,0],[0,500]] |
| Cùng strict1501 — Regex | 100% | 100% | 100% | 100% | [[1001,0],[0,500]] |
| Public236 — cả ba strict model/Regex | 100% | 100% | 100% | 100% | [[118,0],[0,118]] |
| OWASP challenge20 — frozen v1/v2 | 100% | 100% | 100% | 100% | [[10,0],[0,10]] |
| Cùng challenge20 — Regex | 80% | 100% | 60% | 75% | [[10,0],[4,6]] |

250 FN cũ là family double encoding: tín hiệu v1/Regex không đủ trong cách chia family cũ; v2 bổ sung view hữu hạn và cấu trúc thành phần. Tuy nhiên holdout cũ đã công bố kết quả, có15 canonical equivalents vượt train/test; không thể gọi là blind independent. Tập dữ liệu toàn bộ có32 bản trùng canonical dù0 chuỗi trùng chính xác.

Thí nghiệm mới [{RUN}]({metrics_link}) gộp family chung canonical key thành26 connected components. Train6500, validation1999, test1501; chọn C trong[0.1,1,10] trên validation, chọn0.1 khi hòa; refit development8499, đóng băng rồi mới predict test. V1 giữ C1 làm đối chứng; scaler cũng chỉ fit development. Không thay deployed v1 hoặc frozen v2. Tập strict khác tập holdout cũ nên không so trực tiếp87.51→100 như mức cải thiện v2. Cả ba đều100 trên strict: **không chứng minh v2 ưu thế trên tập này**.

Artifacts: [plan trước fit](../evaluations/{RUN}/plan_before_fit.json), [kết quả và timing chính xác]({metrics_link}), [thư mục biểu đồ PNG và predictions](../evaluations/{RUN}), [mã đánh giá](../../tools/evaluate_strict_groups.py). Thời gian dự đoán là số đo perf_counter trong run, đọc trực tiếp JSON; không lấy latency HTTP làm inference time. Mỗi bảng so sánh chỉ dùng cùng tập trong cùng hàng nhóm. Dashboard lịch sử mở `?run={RUN}`; con trỏ latest cũ giữ nguyên để bảo toàn run tham chiếu.

Public236 chọn118 attack từ SecLists LFISuite và118 benign từ Starlette; canonical-disjoint với10k và tập public400 cũ. Challenge20 gồm10 ví dụ OWASP và10 controls; không khẳng định độc lập với236, vì có controls chia sẻ. Nguồn/commit/raw/license/nhãn ở [data/external](../../data/external). Nhãn theo intent/cấu trúc nguồn, chưa gán nhãn thủ công mù bởi nhiều chuyên gia; legacy overlong có thể chỉ là tên literal404 trên Flask hiện đại.

Thời gian thực tế từ run strict (inference_only không gồm features; end_to_end có features; µs/path là batch amortized, không phải latency request đơn):
{timing_table}

Hiệu năng IPS:3×48 request,4workers,TCP localhost,144 dòng SQLite,0 lỗi/0 sentinel leak,90/90 vi phạm policy bị chặn. Tải hợp lệ đúng body: **{succeeded}/{len(valid)} = {succeeded/len(valid):.2%}**. Đây là tỷ lệ trên bộ test đã đo, không phải100% mọi cuộc tấn công. Chi tiết [performance]({P}); không có cam kết throughput production.
{perf_table}

Giới hạn: dữ liệu tổng hợp cân bằng, nhóm lexical dễ phân biệt, biết trước test lịch sử, source bias trên corpus ngoài, không real traffic/blind site split; accuracy100 có thể phản ánh bài toán dễ. Cần corpus thực được phép, nhãn độc lập, temporal/source holdout, calibration, CI bootstrap theo nhóm và stress test nhiều môi trường trước kết luận tổng quát hóa.
''')
    write('11_DU_LIEU_HUAN_LUYEN.md', '11 — Dataset, nhãn và phòng chống leakage', r'''
CSV gốc [paths_synthetic.csv](../../data/paths_synthetic.csv) có10.000 dòng,5.000 benign/5.000 suspicious,35 family (15 benign/20 suspicious),0 dòng trùng chuỗi,0 conflicting raw labels. Các số được audit lại; không tạo lại dataset hay dùng AI đoán nhãn rồi coi là ground truth.

Canonical key phục vụ audit: Unicode NFC→unquote đúng hai lượt→backslash thành slash→casefold. Không resolve filesystem, không khẳng định đây là mọi quan hệ tương đương. Có9.968 key,32 duplicate excess rows. Không được báo “không trùng” nếu chỉ kiểm raw. Holdout lịch sử có15 giao canonical, đã ghi hạn chế.

Mới: union-find gộp toàn family nếu chia sẻ key;26 components; tách có phân tầng nhãn và seed2026 thành train6500 (3000/3500), validation1999 (999/1000), test1501 (1001/500). Không chia một component sang hai tập; ba cặp tập không giao family hoặc key. Nếu conflicting canonical labels hoặc không đủ component thì fail, không relabel hay random-row fallback. Sau chọn C ở validation, refit8499 development; test chỉ predict và tính metrics. Dữ liệu đã được xem trước trong lịch sử nên đây là cải thiện protocol trên nguồn đã biết, chưa blind evaluation.

Nguồn public236:118 LFISuite payload và118 Starlette path controls, snapshot/commit và license nằm [h07 corpus](../../data/external/h07_20261116T171550Z_5b8ba9). Nguồn challenge20: [OWASP corpus](../../data/external/owasp_20261116T172733Z_800c38). Attack label là ý định traversal của ví dụ, không chứng minh request khai thác được trên Flask hiện tại. Benign là control trong scope, không có nghĩa tệp tồn tại. Dedupe canonical đối với tập gốc và public400 được lưu manifest; không gộp challenge với236 để quảng cáo independence.

SHA256 dataset: `2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0`.
Model đang triển khai: `4d7324aa302ecb3d1b731561210a0041e4aef3f740cc68d9187097a80e5a6322`.
Frozen v2: `07e73c85cdbbd4a8acbc785565514a8330e3252483602c191c34208e04f8e368`.
Cả ba và DB người dùng giữ nguyên trước/sau acceptance. Models strict nằm trong run mới, không chép vào artifacts/model.joblib.

Kiểm chứng: [strict_groups.py](../../ml/strict_groups.py), [tests](../../tests/test_strict_groups.py), [split và manifest](../evaluations/20261116T181019Z_dea9ec). Hạn chế lớn nhất là đại diện tổng hợp, không phải chỉ số lượng10.000; cần thêm lỗi thực tế/benign phức tạp và nhãn được review độc lập.''')
    rows = [
        ('1.1','Rủi ro CWE-22','01_PHAN_TICH_RUI_RO.md','PASS','11 kịch bản, kiểm soát và giới hạn'),
        ('1.2','Quy trình AI','02_QUY_TRINH_AI.md','PASS','18/30 features, LR, scaler và không cấp quyền'),
        ('1.3','UML Activity','03_UML_ACTIVITY.md','PASS','200/403/404/503 và AI lỗi'),
        ('2.1','Kiến trúc','04_KIEN_TRUC_HE_THONG.md','PASS','Module/I/O và boundary'),
        ('2.2','SQLite / ERD','05_CO_SO_DU_LIEU.md','PASS','144/144 dòng; integrity ok; filter/error tests'),
        ('2.3','Kiểm thử','06_MA_TRAN_KIEM_THU.md','PASS','109 PASS +3 SKIP minh bạch; TCP74 PASS'),
        ('3.1','IPS / symlink','07_CO_CHE_IPS.md','PARTIAL','Traversal/junction/handle PASS; symlink thật3 SKIP'),
        ('3.2','Bảo vệ / truy vấn log','05_CO_SO_DU_LIEU.md','PASS','Admin, filters, triggers, backup; không OS tamper-proof'),
        ('3.3','Ít nhất5 Use Case','08_USE_CASE.md','PASS','UC01–UC05 đúng yêu cầu, đủ luồng/ngoại lệ/tests'),
        ('3.4','UI / phân quyền','09_GIAO_DIEN_PHAN_QUYEN.md','PASS','Admin-only; AI Training chỉ đọc; CSV/CSRF/RBAC'),
        ('4.1','Metrics / performance','10_DANH_GIA_MO_HINH.md','PASS','LR/Regex, confusion matrices; TCP144; không suy rộng'),
        ('4.2','Dữ liệu / independent protocol','11_DU_LIEU_HUAN_LUYEN.md','PASS','Canonical-group split, provenance public; không blind real-world'),
    ]
    source_map = {
        '1.1': ('app/security.py', 'tests/test_security.py'),
        '1.2': ('app/ml_features.py', 'tests/test_ml.py'),
        '1.3': ('app/web.py', 'tests/test_app.py'),
        '2.1': ('app/web.py', 'tests/test_review.py'),
        '2.2': ('app/database.py', 'tests/test_acceptance_extensions.py'),
        '2.3': ('tools/run_h07_acceptance.py', 'tests/test_app.py'),
        '3.1': ('app/security.py', 'tests/test_windows_handle.py'),
        '3.2': ('app/log_filters.py', 'tests/test_acceptance_extensions.py'),
        '3.3': ('app/web.py', 'tests/test_app.py'),
        '3.4': ('app/auth.py', 'tests/test_auth.py'),
        '4.1': ('tools/evaluate_strict_groups.py', 'tests/test_strict_groups.py'),
        '4.2': ('ml/strict_groups.py', 'tests/test_strict_groups.py'),
    }
    matrix = '| PI | Yêu cầu | Tài liệu | Mã / test / bằng chứng | Trạng thái | Kết quả thực tế |\n|---|---|---|---|---|---|\n'
    for code,title,file,status,detail in rows:
        src,test = source_map[code]
        proof = f'../evaluations/{RUN}/results.json' if code.startswith('4.') else f'{E}/pytest.xml'
        matrix += f'| {code} | {title} | [{file}]({file}) | [Mã](../../{src}) / [test](../../{test}) / [kết quả]({proof}) | {status} | {detail} |\n'
    write('12_MA_TRAN_NGHIEM_THU.md', '12 — Ma trận12 tiêu chí và hồ sơ bốn chương', matrix + f'''

**Tổng:11 PASS,1 PARTIAL,0 FAIL ở mức minimum MVP. Không xác nhận12/12 đã hoàn tất.** PI3.1 chỉ đổi PASS sau khi có bằng chứng chạy symlink thật; không tính SKIP thành PASS. PASS nghĩa có triển khai/bằng chứng trong phạm vi ghi rõ, không phải hội đồng đã chấm Đạt hoặc chất lượng production. Những tài liệu06/07 có PARTIAL chi tiết không phải hai PI khác nhau.

Hồ sơ khóa luận: Chương1 dùng01+02 (bài toán/rủi ro/cơ sở LR); Chương2 dùng03+04+05+08 (phân tích/thiết kế); Chương3 dùng07+09 và mã nguồn (cài đặt/bảo vệ); Chương4 dùng06+10+11+12 (thực nghiệm, tái lập, giới hạn). Bộ bốn chương trước tại [docs/h07](../h07) được giữ làm nền, các số/quyền hiện hành theo hồ sơ này.

Chạy lại từ root project với venv: `python -m pytest -q -rs`, `python tools/run_h07_acceptance.py`. Thí nghiệm mới chỉ đọc dữ liệu, lưu artifact thư mục duy nhất: `python tools/evaluate_strict_groups.py`. Không dùng train_model để khởi động demo hoặc tự thay deployed model.

Đợt chứng cứ [{E}]({E}/summary.json) giữ lệnh,exitcode,stdout,stderr,JUnit,bảng HTTP,hash bảo vệ. [Run strict](../evaluations/{RUN}) giữ split/plan/metrics/plots/predictions/model đóng băng. Thời gian UTC trong tên run là16/11, tương ứng rạng sáng17/11 Việt Nam; không sửa timestamp thành giờ giả.

Việc còn lại: chạy3symlink trên máy có đặc quyền, thử POSIX/SMB, review ACL/secret/TLS theo môi trường triển khai, corpus traffic thực và blind labels, kiểm UI thủ công, định dạng bản Word theo mẫu trường. Không xóa dữ liệu, model hoặc bằng chứng cũ; không merge main. PR chỉ phục vụ review.
''', 'PARTIAL — 11/12 PASS, 1/12 PARTIAL')
    print('Wrote 12 H07 acceptance documents from retained evidence.')
    for path, notice in [
        (ROOT / 'README.md', '## Hồ sơ nghiệm thu H07 hiện hành — 17/11/2026\n\n[12 tài liệu và ma trận nghiệm thu](docs/bao_cao_h07/12_MA_TRAN_NGHIEM_THU.md):109 pytest PASS,3 SKIP; TCP dashboard41 PASS,download33 PASS/3 SKIP;144 request hiệu năng không lỗi. Chính sách mới: chỉ admin xem dashboard/log/AI/CSV; auditor chỉ kho công khai. AI Training chỉ đọc, không tự fit/deploy. 11/12 PI PASS,PI3.1 PARTIAL do symlink thật thiếu quyền Windows. Các số/quyền ở phần lịch sử bên dưới cần đọc theo mốc thời gian.\n\n'),
        (ROOT / 'docs/MA_TRAN_H07.md', '> **Bản hiện hành:** [12_MA_TRAN_NGHIEM_THU](bao_cao_h07/12_MA_TRAN_NGHIEM_THU.md),17/11/2026. 11 PASS,1 PARTIAL;109 pytest PASS/3 SKIP. Chỉ admin đọc dữ liệu quản trị. Nội dung dưới đây giữ làm lịch sử, không thay bằng chứng mới.\n\n'),
    ]:
        original = path.read_text(encoding='utf-8')
        if notice not in original:
            path.write_text(notice + original, encoding='utf-8')


if __name__ == '__main__':
    main()
