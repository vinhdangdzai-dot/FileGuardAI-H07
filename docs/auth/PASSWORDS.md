# Mật khẩu bền vững, đổi mật khẩu Admin và thu hồi phiên — 17/11/2026

> Chính sách hiện hành: [6–128 ký tự và kiểm thử đầy đủ các mốc](PASSWORD_LENGTH_6.md). Các kết quả184 PASS bên dưới là mốc41373af trước cập nhật này, được giữ nguyên để đối chiếu.

Nhánh `h07/cybersecurity-ui`, PR #2. Không đổi mô hình/dataset/Path Traversal hoặc dữ liệu SQLite nghiệp vụ. Tests dùng hash và SQLite fixture riêng; không đặt mật khẩu thật thay người dùng.

## Thiết lập và sử dụng

Workspace lúc kiểm tra chưa có `instance/admin_password.hash`. Không tạo mật khẩu mặc định hoặc dùng mật khẩu fixture cho cài đặt thật. Trong terminal tương tác, từ thư mục dự án, kích hoạt Python venv rồi chạy **một lần khi chưa có hash**:

```powershell
python tools/manage_credentials.py --role admin
python run.py
```

CLI dùng getpass để nhập và xác nhận kín; không nhận password trong command line. START_WINDOWS.bat cũng hỏi qua CLI lần đầu nếu chưa có hash. Những lần mở server sau chỉ chạy run.py, không chạy lại CLI trừ khi chủ động reset. File hợp lệ tồn tại được đọc nguyên trạng, kể cả cấu hình bootstrap/env đã thay đổi; không tự tạo salt/hash hoặc mật khẩu khác. Hash hỏng làm startup báo lỗi, không âm thầm ghi đè. Giữ hỗ trợ Werkzeug scrypt và PBKDF2 hợp lệ; mật khẩu mới dùng mặc định Werkzeug scrypt.

Không còn in mật khẩu tạm trong run.py. Không còn tự phát sinh Admin password khi production chưa được cấu hình. ADMIN_PASSWORD_HASH hoặc ADMIN_PASSWORD từ environment chỉ là bootstrap tương thích lần đầu khi file chưa tồn tại; khuyến nghị CLI để tránh shell history. Plaintext bootstrap được loại khỏi Flask config sau khởi tạo. Hash, history, khóa cập nhật, temp credential và database được gitignore; không đặt các file này trong shared_files.

Admin đăng nhập → **Tài khoản · Đổi mật khẩu**. Nhập hiện tại, mới6–128 ký tự, xác nhận trùng; mật khẩu mới phải khác hiện tại. Ba ô có hiện/ẩn qua keyboard/ARIA; không điền lại giá trị sau lỗi. Thành công xóa cả phiên đang dùng, chuyển về Login với thông báo rõ và yêu cầu đăng nhập lại. Guest bị chuyển Login; Auditor403. Light/Dark/System, A−/A/A+ và thang chữ18px mặc định vẫn dùng chung. GET không thay đổi hash, POST cần CSRF.

## Cơ chế và lý do thay đổi

Trước sửa: app đã ưu tiên file hash khi có, nhưng khi chưa có thì tạo mật khẩu tạm trong RAM mỗi startup và in ra console; session cookie chỉ kiểm role, chưa có server-side credential version. CLI ghi hash qua temp/replace, nhưng server đang chạy chỉ giữ bản hash cũ trong config đến restart.

Sau sửa:

- `app/credential_store.py`: đọc file có giới hạn4KiB và validate định dạng hash; lock RLock trong process và msvcrt/fcntl qua file chung để phối hợp giữa các process; file tạm tạo độc quyền, mode0600 trên nền tảng hỗ trợ, flush/fsync rồi os.replace cùng thư mục. Không truncate hash đang hoạt động. Chỉ dọn đúng temp do thao tác tạo, không xóa dữ liệu/người dùng/temp toàn hệ thống.
- `app/auth.py`: khởi tạo hash một lần dưới lock, ưu tiên file đã có; mỗi request có role so sánh opaque HMAC version của role + hash hiện tại với version trong cookie đã ký. Không đưa password hash vào cookie. Phiên legacy không có version phải đăng nhập lại. File hash đọc lỗi thì fail closed.
- Login đọc hash hiện tại từ filesystem, phiên được gắn version của **chính hash đã xác minh**, tránh cấp version mới cho một lần login dùng password cũ trùng lúc thay đổi. Đổi mật khẩu recheck password dưới cross-process lock, nên hai request cũ không cùng ghi đè.
- POST `/account/password`: Admin-only, CSRF,5 lần lỗi/IP/300 giây qua security_events (chia sẻ giữa worker/restart); vượt ngưỡng trả429 và Retry-After300. Lỗi hiện tại403; độ dài/xác nhận/giống cũ400; lỗi ghi503. Không ghi giá trị password, confirmation, hash hay request body vào event.
- Events cố định: password_change_requested / password_change_failed / password_change_throttled / password_change_write_failed / password_change_success. SQLite và append-only triggers giữ nguyên, chỉ thêm query đếm thất bại theo thời gian/IP. Các event fixture không đi vào database nghiệp vụ.
- CLI dùng cùng writer/lock, giữ backup hash cũ trong credential_history như trước. CLI đổi hash có hiệu lực ngay trên request sau và thu hồi session role tương ứng, không cần restart để nạp hash.

Vô hiệu hóa là phía server trên mỗi request; cookie cũ không được chấp nhận dù cookie chưa hết hạn hoặc được replay, kể cả worker khác đọc cùng hash. Các request đã được xác thực và bắt đầu xử lý trước thời điểm commit không thể bị hủy hồi tố. Admin đổi mật khẩu không đổi quyền hoặc mật khẩu Auditor riêng.

### SECRET_KEY và restart

Mật khẩu được giữ qua restart **độc lập với session**. Mặc định SECRET_KEY ngẫu nhiên mỗi process: restart làm session hết hiệu lực, phải login lại bằng mật khẩu đã lưu. Nếu cần giữ session qua restart hoặc dùng nhiều worker, cung cấp cùng SECRET_KEY ngẫu nhiên đủ mạnh (ít nhất32 byte entropy) từ secret manager/environment riêng. Không hardcode, không commit .env/secret, không gửi secret qua Git hoặc thông báo. Không ghi SECRET_KEY thật trong đợt sửa này. Khóa ổn định không bỏ kiểm tra version: thay mật khẩu vẫn thu hồi cookie cũ. Cookie HttpOnly/SameSite, TTL15 phút, CSRF và thiết lập HTTPS/COOKIE_SECURE hiện tại giữ nguyên.

### Lỗi ghi và giới hạn audit

Trước khi thay hash, app phải ghi được event requested; audit lỗi lúc này thì503 và không thay mật khẩu. Nếu tạo/ghi/flush/replace thất bại trước commit, hash cũ, session và khả năng login cũ giữ nguyên; có regression test PermissionError. Sau khi replace đã thành công, không thông báo sai rằng password cũ còn dùng được và không rollback âm thầm. Nếu ghi success event sau commit thất bại, app vẫn thu hồi phiên và yêu cầu login bằng password mới, đồng thời ghi server error cố định không chứa secret. Hai tài nguyên filesystem/SQLite không có transaction chung; crash/audit outage sau commit có thể để lại requested nhưng thiếu success. Không tuyên bố đảm bảo audit exactly-once hoặc độ bền trước mọi sự cố nguồn điện.

Windows file mới kế thừa quyền thư mục instance; mode0600 không tương đương chứng nhận ACL Windows. Không thay ACL toàn hệ thống hoặc đòi Administrator. OS operator có quyền đọc/ghi hash/SECRET_KEY vẫn là đối tượng tin cậy; shared filesystem/network lock chưa được chứng nhận. Throttling theo IP còn hạn chế NAT/proxy/DoS; không phải hệ IAM production.

## Kiểm thử thực tế

| Bộ kiểm thử | Kết quả thực chạy |
|---|---|
| Pytest mới nhất | **184 PASS,0 FAIL,0 ERROR,3 SKIP**,15 subtests PASS;53,00s |
| Acceptance cuối | **6/6 bước exit0**,pytest184 PASS/3 SKIP |
| Dashboard TCP |41 PASS,0 FAIL |
| Download TCP |33 PASS,0 FAIL,3 symlink SKIP |
| Hiệu năng |144 request/144 dòng SQLite fixture,0 lỗi |
| Restart TCP hai OS processes thật |**20 assertions PASS,0 FAIL**,TESTING=False |
| Edge browser cuối |**402 PASS,0 FAIL**,0 JS/static errors |

[Pytest](../ui/pytest_20261117T110403Z/stdout.txt) · [Acceptance](../bao_cao_h07/evidence/20261117T110327Z_f3d237/summary.json) · [Restart TCP](evidence/restart_20261117T105734Z_64a69b/results.json) · [Browser](../ui/browser_20261117T105955Z_7ac63b/results.json).

19 regression cases mới kiểm restart/stable SECRET_KEY, restart/random SECRET_KEY, thu hồi worker/cookie replay, CLI cập nhật live, validation/current/mismatch, các biên12/128, lỗi atomic replace, audit outage trước/sau commit, rate limit chia sẻ, CSRF/Guest/Auditor, session thiếu version, concurrent changes, hash lỗi không ghi đè, bootstrap production và hash PBKDF2 cũ được giữ nguyên. Fixtures UI cũ tạo session thủ công được bổ sung version hợp lệ từ server; không thêm bypass TESTING cho kiểm tra phiên production.

Restart TCP dùng hai subprocess Flask nối tiếp trên localhost, cùng hash fixture/SQLite và SECRET_KEY fixture ngẫu nhiên: tiến trình đầu đổi mật khẩu, dừng; tiến trình sau từ chối cũ/chấp nhận mới, dashboard200, download200 và traversal403, kiểm không phản chiếu password hoặc ghi password trong SQL event. Không dùng hoặc đổi hash Admin thật.

Browser giữ toàn bộ385 checks trước, thêm17 checks account:6 bố cục Light/Dark ở1440/768/390,3 hiện/ẩn keyboard, CSRF, current sai, thành công/relogin, phiên khác bị thu hồi và password cũ/mới. Có6 ảnh form blank không có secret. Chrome local vẫn có giới hạn crash đã ghi; Chrome CI chạy riêng cùng suite, kết quả theo commit và artifacts được cập nhật trên PR #2. Zoom125–200% của bộ typography vẫn chỉ là reflow mô phỏng CDP, chưa xác minh native Ctrl+plus.

Ba SKIP local giữ lý do quyền symlink Windows, không đổi thành PASS. Hash dataset/deployed v1/frozen v2/SQLite nghiệp vụ trước/sau acceptance và browser không đổi. Không commit hash credentials, SQLite nghiệp vụ, plaintext, cookie storage state hoặc SECRET_KEY. Các SQL fixture đã tồn tại trong lịch sử Git không bị xóa để giữ bằng chứng.

## Bằng chứng lỗi/trung gian được giữ

- [Pytest ban đầu](../ui/password_initial_checks/result.json):13 PASS/1 FAIL do test guard bootstrap vô tình dùng TESTING=True, vốn cung cấp credential fixture. Sửa test sang production mode, giữ assertion phải từ chối thiếu credential; không nới production.
- [Browser101925Z](../ui/browser_20261117T101925Z_2189b2/results.json):324 PASS/1 FAIL do popup theme khi nút tài khoản wrap. Sửa vị trí popup trong viewport.
- [Browser105655Z](../ui/browser_20261117T105655Z_b52f3f/results.json):394 PASS/1 FAIL vì selector CSRF không scope form, trùng field logout. Scope vào form đổi password, không bypass CSRF.
- [Acceptance101936Z](../bao_cao_h07/evidence/20261117T101936Z_acdc03/interrupted.json):ERROR thực thi do subprocess TimeoutExpired báo thời lượng âm (-577,704s); chưa có final summary, không coi PASS. Lượt chạy lại105540Z đạt6 bước trước bổ sung case PBKDF2; lượt cuối110327Z ghi184 PASS.
- Tool restart lần thử đầu dùng tên purpose chưa được allocator hỗ trợ, dừng trước test; sửa dùng runtime pytest có sẵn, không giảm kiểm tra. Kết quả20 PASS là lượt chạy thực sau sửa.
- Pytest183 PASS của lượt101923Z giữ riêng, không ghi đè thành184; các con số trong bảng là mốc cuối.

## File và hướng dẫn xác minh

Source: `app/credential_store.py` (mới), `app/auth.py`, `app/web.py`, `app/database.py`, `run.py`, `START_WINDOWS.bat`, `tools/manage_credentials.py`, `app/templates/base.html`, `app/templates/change_password.html` (mới), `app/static/password-change.js` (mới), `app/static/style.css`, `app/static/theme.js`.

Tests/tools: `tests/test_password_change.py` (mới), session fixture trong `test_ui.py`, `test_ui_refinement.py`, `test_training_dataset.py`, `test_text_size_ui.py`; `tools/ui_password_checks.py` (mới), `tools/verify_credentials_tcp.py` (mới), `tools/verify_ui_browser.py`, và cấu hình hash fixture tách riêng trong `verify_evaluation_http.py`, `verify_tcp.py`, `h07_acceptance.py`.

Docs/config: `.gitignore`, `.gitattributes`, `README.md`, runbook `docs/h07/AN_NINH_VAN_HANH.md`, `docs/h07/CHUONG_3.md`, UI README/PR description, báo cáo này và evidence mới. Không sửa nhãn data, model, tests Path Traversal hoặc API download hiện hữu.

Chạy `python -m pytest -q -rs`, `python tools/run_h07_acceptance.py`, `python tools/verify_credentials_tcp.py`; browser tùy chọn `python tools/verify_ui_browser.py --browser "đường dẫn Chrome/Edge.exe"`. Mỗi lượt dùng fixture riêng, không cần nhập password thật. [Form Dark mobile](../ui/browser_20261117T105955Z_7ac63b/password_dark_390.png) · [Form Light desktop](../ui/browser_20261117T105955Z_7ac63b/password_light_1440.png). Commit/push nhánh review, PR #2 giữ draft, không merge main.
