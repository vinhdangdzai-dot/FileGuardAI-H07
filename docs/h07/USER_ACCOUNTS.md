# Tài khoản CANH GÁC SỐ

Bản nâng cấp hiện hành: xem [Argon2id và TOTP Admin](MFA_SECURITY.md).
Admin bắt buộc hoàn tất TOTP trước khi vào Dashboard; không có cờ bỏ MFA
cho TESTING. Luồng SMTP/hồ sơ bên dưới tiếp tục được dùng.

## Tương thích và migration

Giữ nguyên Admin/Auditor truyền thống trong instance/*.hash, cơ chế đổi hash
nguyên tử và thu hồi phiên theo credential version. Không nhập email giả,
không chép/đổi hash cũ vào SQLite hoặc tự thay mật khẩu khi khởi động.

Tài khoản mới lưu trong SQLite nghiệp vụ bằng migration cộng thêm của
app/account_store.py. Khi create_app khởi động, init_db tạo bảng nếu chưa có:
auth_schema_versions (version 2), auth_users, auth_reset_tokens, auth_rate_limits;
thêm auth_mfa, auth_mfa_challenges, auth_backup_codes, auth_sessions.
Migration chạy trong transaction BEGIN IMMEDIATE; kiểm tra phiên bản/cột,
rollback nếu schema không tương thích, không DROP/DELETE dữ liệu hay ALTER
các bảng Security Alerts/log cũ. Chạy lại không tạo lại tài khoản/mật khẩu.

Trước khi người vận hành cập nhật bản đang chạy, sao lưu SQLite bằng công cụ
SQLite backup có sẵn, giữ riêng hash Admin/Auditor và secret môi trường. Không
thay DB nghiệp vụ bằng DB fixture. Đợt kiểm thử chỉ dùng DB/hash tạm riêng.

Admin/Auditor truyền thống đăng nhập /login bằng cách **để trống username**,
chọn loại tài khoản và nhập mật khẩu hiện có. Đường POST cũ được giữ để các
công cụ acceptance và quản trị tiếp tục dùng được. Admin truyền thống không
có dòng auth_users nên không thể bị khóa/hạ quyền qua quản lý tài khoản.
Đây là đường khôi phục quyền quản trị có chủ đích, cần bảo vệ hash file/CLI.

Muốn chuyển sang Admin định danh: đăng ký User với email mình sở hữu, đăng
nhập Admin truyền thống, xác minh người/địa chỉ email, rồi cấp quyền Admin
trong /admin/accounts sau khi nhập lại mật khẩu Admin. Không xóa hash cũ.
Tài khoản mới không được tự đăng ký Admin hoặc chọn quyền khi đăng nhập.

## Quyền và các trang

| Chức năng | Guest | User | Auditor SQLite | Admin |
|---|---|---|---|---|
| Kho tệp công khai / tải tệp theo policy | Có | Có | Có | Có |
| Đăng ký / yêu cầu reset | Có, có rate limit | Có | Có | Có |
| Hồ sơ /account | Không | Chỉ bản thân | Chỉ bản thân | Chỉ bản thân hoặc hồ sơ legacy |
| Đổi mật khẩu /account/password | Không | Mật khẩu bản thân | Mật khẩu bản thân | Mật khẩu bản thân |
| Dashboard / nhật ký / AI / dataset / Alerts | Không | Không | Không, giữ chính sách Auditor hiện có | Có |
| /admin/accounts: lọc/phân trang/khóa/quyền | Không | Không | Không | Có và xác minh lại mật khẩu |

Auditor legacy vẫn bị từ chối chức năng đổi mật khẩu Admin cũ; người vận hành
dùng CLI --role auditor để đổi hash Auditor. Auditor định danh có thể tự đổi
mật khẩu SQLite của mình. Khóa tài khoản dừng đăng nhập và thu hồi phiên,
không thay chính sách kho tệp công khai đối với Guest.

Profile cho phép đổi display_name; username/email chỉ đọc. Không đổi địa chỉ
khôi phục khi chưa có quy trình xác minh email mới. Mọi trang có Light/Dark,
font controls và form CSRF; trường mật khẩu có hiện/ẩn, thông báo/loading.
Quyền được kiểm tra tại backend, không dựa vào nút ẩn hoặc role gửi từ form.

Admin có thể khóa/mở, gán role admin/auditor/user. Cần mật khẩu Admin hiện
tại, rate limit và CSRF. Không tự khóa/đổi quyền mình hoặc vô hiệu hóa Admin
SQLite hoạt động cuối. Kiểm tra lại role/version của Admin SQLite ngay trong
transaction để không dùng một phiên đã bị đổi quyền đồng thời.

## Mật khẩu và session

Hash mới dùng **Argon2id, 64 MiB, 3 vòng, parallelism=1**, salt 16 byte
ngẫu nhiên riêng từ argon2-cffi. Hash Werkzeug PBKDF2/scrypt cũ vẫn xác minh
được; login hợp lệ mới nâng thuật toán, không đổi password. Hash file được
sao lưu trước ghi nguyên tử; restart đơn thuần không thay hash/password.
Các lần tạo/đổi password qua website/CLI đều dùng Argon2id.

Giữ chính sách demo 6–128 ký tự đã được người dùng yêu cầu trước đó; khuyến
nghị dùng cụm mật khẩu dài, riêng biệt. Không ép ký tự hoa/đặc biệt. Không
lưu plaintext trong DB/log; không gửi password/token/API key tới Gemini.

Mỗi auth_users có session_version ngẫu nhiên. Cookie có SID ngẫu nhiên đã ký;
SQLite chỉ lưu digest SID. before_request kiểm tra active/role/version và
session server chưa thu hồi, idle/absolute timeout, cùng phiên bản MFA cho
Admin. Đổi/reset password, khóa/mở hoặc đổi quyền thu hồi phiên/challenge
và token reset cũ. Login xoay cookie/CSRF. Logout POST có CSRF thu hồi SID
trên server, từ chối cả bản cookie đã sao chép.

Cookie HttpOnly và SameSite=Lax. Secure tự bật cho request HTTPS hoặc khi
COOKIE_SECURE=1. HTTP chỉ phục vụ tài khoản ở demo loopback (127.0.0.1/
localhost); production public yêu cầu HTTPS và COOKIE_SECURE=1. Cấu hình
Nginx chuyển HTTP sang HTTPS, Gunicorn bind loopback, TRUST_PROXY theo hướng
dẫn hiện có; không tin X-Forwarded-* từ client công khai. Giữ SECRET_KEY ổn
định bằng môi trường an toàn để các worker cùng xác minh cookie; không ghi
secret vào repository. Thay secret vẫn thu hồi mọi phiên theo thiết kế Flask.

Khi chạy Gunicorn, khởi tạo application trong từng worker, không dùng
`--preload`: mailer nền và dịch vụ AI hiện tại dùng thread trong tiến trình.
Chưa kiểm chứng gửi SMTP thật hoặc vận hành nhiều worker trên VPS trong đợt này.

## Khôi phục và SMTP

Người vận hành đã chọn tự cấu hình SMTP qua môi trường tiến trình:

```text
ACCOUNT_RESET_ORIGIN=https://your-domain.example
ACCOUNT_SMTP_HOST=smtp.your-provider.example
ACCOUNT_SMTP_PORT=587
ACCOUNT_SMTP_SSL=0
ACCOUNT_SMTP_FROM=noreply@your-domain.example
ACCOUNT_SMTP_USERNAME=<tài khoản SMTP>
ACCOUNT_SMTP_PASSWORD=<secret trong môi trường, không commit>
```

Port 587 dùng STARTTLS bắt buộc; SSL=1 dùng TLS ngay từ đầu, thường port 465.
Certificate được xác minh bằng ssl.create_default_context, timeout 5 giây
cho thao tác socket, không fallback plaintext. Trường host/from/origin thiếu
thì không gửi, không in token ra console hoặc trả token trong HTML. .env.example
chỉ là hướng dẫn; ứng dụng đọc môi trường, không tự nạp file .env.

ACCOUNT_RESET_ORIGIN là URL HTTPS tin cậy do vận hành đặt, không lấy từ
Host/X-Forwarded-Host. Origin không được chứa userinfo, query hoặc fragment.
Test mode cho phép origin loopback HTTP và sender giả được inject rõ ràng;
không tự gửi SMTP thật khi TESTING. Admin thấy trạng thái cấu hình tại profile,
nhưng configured không có nghĩa kiểm thử gửi mail thật đã thành công.

POST /forgot-password có cùng status/message cho tồn tại, không tồn tại,
khóa hoặc rate limited; tra cứu/queue cục bộ, không chờ SMTP. Không cam kết
constant-time tuyệt đối cho mọi thao tác DB; rate limit hạn chế lấy mẫu.
Link không xuất hiện ở response. Mailer nền có hàng đợi 16, không retry vô
hạn; gửi thất bại sẽ vô hiệu token và ghi mã sự kiện chung không có địa chỉ,
body, password hoặc token. Queue đầy cũng vô hiệu token vừa cấp.

Token là secrets.token_urlsafe(32), 256 bit ngẫu nhiên. SQLite chỉ lưu SHA-256
của **token ngẫu nhiên** (khác với password KDF), hạn 15 phút, gắn với user ID
và version credential. Token cũ bị vô hiệu khi cấp token mới. Consume token,
đổi hash, thay session_version và audit cùng transaction BEGIN IMMEDIATE;
hai yêu cầu reset đồng thời chỉ một yêu cầu thành công.

Link dạng /reset-password#token=...: fragment không được gửi vào request
HTTP/access log hoặc Referer. JS điền mã vào ô password rồi xóa fragment khỏi
URL hiện tại bằng history.replaceState. JS tắt thì người dùng tự dán phần mã
từ email vào form POST. Server không đưa token vào query/path hoặc phản hồi
lỗi, không lưu request body. Người vận hành không bật middleware/proxy ghi
body hoặc ghi toàn bộ email/SMTP debug; không dùng script ngoài trên trang reset.

Reset thành công không tự đăng nhập. Thông báo lỗi token hết hạn/đã dùng/
không hợp lệ giống nhau. Legacy file Admin/Auditor chưa có email đã xác minh
nên không dùng reset email; khôi phục qua tools/manage_credentials.py.

## Giới hạn tần suất và audit

- Login: giới hạn lỗi theo IP hiện có; thêm 5 lần thử/5 phút cho định danh
  tài khoản, gộp username/email về cùng username. Login đúng xóa bộ đếm
  định danh; bộ đếm lỗi IP theo cửa sổ hiện có vẫn giữ.
- Đăng ký: 5 request/IP/giờ mặc định, thêm trần 200 request/giờ toàn hệ thống.
- Quên mật khẩu: 5/IP và 3/định danh/15 phút, 60 request/giờ toàn hệ thống.
- Nộp token reset: 10/IP/15 phút. Đổi mật khẩu: 5/tài khoản+IP/5 phút.
- Admin quản lý: 10 request/IP/phút; mỗi mutation xác minh lại password.

Các limiter lưu SQLite để tồn tại qua restart và dùng chung nhiều worker.
Không coi đây là thay thế rate limit Nginx/CAPTCHA cho Internet hoặc bảo đảm
chống DoS phân tán. Dummy password verification giảm khác biệt thời gian
username không tồn tại; thông báo login sai không phân biệt khóa/sai mật khẩu.

security_events tiếp tục append-only: signup/login/logout, cập nhật profile,
đổi/reset mật khẩu, SMTP delivery và thay đổi quyền/khóa. Ghi user ID khi có,
không ghi password, reset token, nội dung email hay secret SMTP. Admin đọc
audit như trước; User/Auditor không được xem security logs, AI config hoặc CSV.

## Kiểm thử và giới hạn đã biết

Pytest và acceptance hiện có, cộng tests/test_accounts.py kiểm tra migration,
hash/salt, login/email, fixation, revocation, reset hết hạn/dùng lại/đồng thời,
SMTP lỗi/thiếu cấu hình, XSS/SQLi/CSRF/role escalation và khóa/mở tài khoản.
tests/test_account_mail.py kiểm tra TLS trước AUTH/gửi thư và từ chối gửi khi
STARTTLS lỗi. Đây là mock transport, không phải chứng nhận SMTP thật hoạt động.
tests/test_acceptance_timeout.py kiểm tra timeout giữ stdout/stderr, ghi ERROR
và không làm acceptance thành công; các suite còn lại vẫn được thực hiện.
tools/verify_accounts_browser.py chạy Chrome/TCP với mailbox giả, ảnh ở
1440/768/390px, Light/Dark cho bảy trang tài khoản; không dùng SMTP thật.

Đã có TOTP bắt buộc cho Admin, mã dự phòng và giới hạn 5 phiên song song.
Chưa có email verification đầu vào/đổi email hoặc trang liệt kê thiết bị.
Không hỗ trợ email quốc tế Unicode ở local-part/domain; display_name
Unicode được hỗ trợ. Chưa có durable email outbox: restart có thể mất email
chưa gửi, token tự hết hạn và không đổi password nếu chưa consume. SMTP thật
cần người vận hành cấu hình/xác minh riêng; không ghi PASS thay cho test đó.

Không xóa dữ liệu cũ, thay LR/dataset/Gemini/path policy hoặc deploy. Không
commit/push/merge. Log giai đoạn đầu ở docs/h07/evidence/accounts_20261118/;
bản Argon2id/TOTP và kiểm chứng cuối ở docs/h07/evidence/accounts_mfa_20261119/.

Nguồn: [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[OWASP Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
