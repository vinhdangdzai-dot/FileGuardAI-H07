# Argon2id, TOTP Admin và phiên đăng nhập — CANH GÁC SỐ

Bản cập nhật ngày 19/11/2026 (Asia/Saigon). Tên thư mục evidence có timestamp
`...Z` dùng UTC. Không thay Logistic Regression, Gemini, dataset, Path Traversal
hoặc quyết định ALLOW/BLOCK/MISS. Không tự commit/push/deploy.

## Chính sách đã chốt và phạm vi OWASP

Hash mới dùng argon2-cffi **Argon2id v19, 64 MiB, time_cost=3, parallelism=1,
salt 16 byte ngẫu nhiên, hash 32 byte**. Không truyền salt cố định vào thư viện.
Hai phép tính Argon2 đồng thời tối đa mỗi tiến trình; quá tải trả 503, không
hạ thuật toán. Tham số này cao hơn mức tối thiểu 19 MiB/t=2/p=1 của
[OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

Theo lựa chọn rõ ràng của người dùng, demo tiếp tục nhận mật khẩu **6–128 ký
tự**, không ép chữ hoa/ký tự đặc biệt. Đây là giới hạn: chưa đáp ứng ASVS 5.0
6.2.1 (tối thiểu 8, khuyến nghị 15). Chưa có bộ đối chiếu 3.000 mật khẩu phổ
biến/breached passwords. Không tuyên bố chứng nhận hoặc đáp ứng đầy đủ ASVS L2/L3.

Tham chiếu [ASVS 5.0 V6](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x15-V6-Authentication.md),
[V7](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x16-V7-Session-Management.md)
và [OWASP MFA](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html):

| Nhóm đối chiếu | Cơ chế trong dự án | Phạm vi/giới hạn |
|---|---|---|
| 6.3: brute-force và nhiều đường xác thực | Limiter SQLite theo IP và định danh; Admin legacy/SQLite cùng phải TOTP | Không thay thế rate limit tại Nginx; User/Auditor vẫn một yếu tố |
| 6.4.3: recovery không bỏ MFA | Reset password giữ nguyên TOTP; đổi credential version, thu hồi phiên/challenge | Email legacy chưa có nên khôi phục password legacy qua CLI |
| 6.5.1/6.5.8: dùng một lần, giờ server | TOTP 30 giây, chỉ cửa sổ hiện tại; counter lưu và tiêu thụ atomic | Điện thoại/server cần đồng bộ giờ; không chống phishing như WebAuthn |
| 6.5.2/6.5.3: mã dự phòng | 8 mã CSPRNG, mỗi mã 128 bit; chỉ lưu SHA-256 gắn principal và cờ đã dùng | SHA-256 dành cho mã ngẫu nhiên đủ entropy, không dành cho password |
| 7.2/7.3: session reference/timeout | SID ngẫu nhiên 256 bit, DB chỉ lưu digest; idle tối đa 15 phút, absolute 8 giờ | Last-seen ghi theo nhịp 30 giây; timeout có thể sớm hơn tối đa 30 giây |
| 7.4: thu hồi phiên | Logout, khóa/quyền, đổi/reset password, thay TOTP đều vô hiệu hóa phiên tương ứng | Tối đa 5 phiên song song; cấp phiên thứ 6 thu hồi phiên cũ nhất |
| 7.5: thay yếu tố nhạy cảm | Đổi TOTP cần mật khẩu hiện tại và OTP/mã dự phòng chưa dùng | Không có nút tắt MFA trên web; recovery đặc quyền ở console |

## Luồng đăng nhập và phân quyền

1. Đăng ký mới luôn là User. Backend bỏ qua role gửi theo login định danh,
   từ chối mass assignment khi signup/profile. Username hoặc email đều dùng được.
2. Password đúng với Admin chỉ tạo challenge 5 phút trong SQLite. Cookie lúc
   này không có `role`, `user_id` hoặc quyền Dashboard; chỉ có reference ngẫu nhiên.
3. Admin chưa có TOTP nhận QR tạo tại localhost/server và khóa thiết lập.
   Không có dịch vụ QR bên ngoài. Phải nhập TOTP đúng mới kích hoạt.
4. Admin đã kích hoạt nhập TOTP hoặc mã dự phòng. Mã đã dùng/counter đã nhận
   bị từ chối trên mọi worker. Không chấp nhận cửa sổ trước/sau 30 giây.
5. Chỉ sau bước hai mới tạo session server và cấp quyền. Mã dự phòng mới chỉ
   xuất hiện trong phản hồi POST thành công, không đưa vào cookie/flash/log.
6. Đổi thiết bị cần xác minh lại cả hai yếu tố; thiết bị cũ vẫn hiệu lực đến
   khi thiết bị mới được xác nhận. Khi hoàn tất, phiên/mã dự phòng cũ bị thu hồi.

RBAC hiện có được giữ: Admin quản trị; User và Auditor không đọc Dashboard,
logs, dữ liệu AI/dataset hoặc cấu hình riêng tư. User/Auditor SQLite có hồ sơ
và đổi password của chính mình. Auditor hash file vẫn dùng CLI, không được
đổi password Admin. Gán quyền Admin chỉ từ Admin đã hoàn thành MFA và xác minh
lại password; phiên User cũ bị thu hồi, login tiếp theo bắt buộc thiết lập MFA.

## Migration không làm mất quyền quản trị

Schema version 2 cộng thêm `auth_mfa`, `auth_mfa_challenges`,
`auth_backup_codes`, `auth_sessions` vào bốn bảng tài khoản version 1. Chạy
transaction, kiểm tra cấu trúc, không DROP/DELETE bảng hoặc log hiện hữu.

Werkzeug PBKDF2/scrypt cũ vẫn xác minh được. Khởi động lại không thay password.
Login hợp lệ nâng hash sang Argon2id; SQLite dùng compare-and-swap để không
ghi đè password đổi đồng thời. Hash file cũ được sao lưu vào credential_history
trước ghi nguyên tử. Chỉ thay thuật toán, không thay password. Hash auditor chỉ
được cấu hình qua môi trường vẫn do người vận hành quản lý cho tới khi dùng CLI.
Hash Argon2 có chi phí cao hơn policy không bị tự giảm về policy thấp hơn.

Cookie cũ chưa có session reference/MFA không còn vào được trang quản trị;
người dùng đăng nhập lại và thiết lập TOTP. Đây là thu hồi phiên có chủ đích,
không phải mất tài khoản. Các backup hash cũng nhạy cảm: cần bảo vệ như hash
đang dùng và có kế hoạch lưu trữ riêng; hash cũ yếu có thể giảm lợi ích chống
crack offline nếu cùng bị lộ. Không tự xóa bằng chứng/backup cũ.

## Khóa mã hóa TOTP và sao lưu

TOTP seed dùng **AES-256-GCM**, nonce ngẫu nhiên 96 bit; AAD gắn principal
để ciphertext của tài khoản này không dùng cho tài khoản khác. Khóa không
được dẫn xuất từ SECRET_KEY. Ciphertext ghi kèm key ID để đọc được các phiên
bản khóa còn giữ trong keyring.

Hai cách cấu hình qua môi trường tiến trình:

- `ACCOUNT_MFA_KEYS`: JSON keyring từ secret manager/env, không in giá trị.
- `ACCOUNT_MFA_KEY_FILE`: đường dẫn file JSON riêng, nằm ngoài shared_files.

Để trống cả hai ở demo: tạo `instance/mfa_keys.json` **một lần**, ghi nguyên
tử, giữ lại qua restart. File/key tạm đã bị Git ignore. POSIX tạo mode 0600
và từ chối key file có quyền group/other; trên Windows cần kiểm tra NTFS ACL
cho tài khoản chạy Flask. Chưa chứng nhận ACL Windows tự động. Trên VPS ưu
tiên file ngoài thư mục dự án hoặc secret manager, tách backup DB và key.

Cấu trúc keyring version 1 gồm `active` (key ID) và `keys` (key ID → base64url
32 byte). Không chép key thật vào tài liệu, Git hay chat. Khi xoay khóa, thêm
ID mới và đổi active, vẫn giữ ID cũ để giải mã seed hiện có; restart các worker
trong thời gian bảo trì. Chưa có tự động re-encrypt toàn bộ seed/retire khóa.
Không đổi active bằng một key khác có cùng ID. Mất/sai key khi đang có MFA
hoạt động: startup từ chối, không tự sinh key thay thế; phục hồi backup riêng.

SECRET_KEY ký cookie vẫn do cấu hình hiện hành quản lý. Production nhiều
worker cần cùng SECRET_KEY ổn định; thay SECRET_KEY sẽ thu hồi cookie nhưng
không thay khóa MFA/password. Không dùng Gunicorn --preload vì các thread
mailer/AI hiện tại phải khởi tạo trong worker.

## Triển khai và khôi phục

Không có deploy tự động. Trước khi người vận hành áp dụng: sao lưu SQLite
bằng SQLite backup, hash/history, keyring và cấu hình secret riêng; cài
`python -m pip install -r requirements.txt`, restart Flask và đăng nhập.
Admin legacy tiếp tục để trống username, chọn Admin và dùng password cũ;
quét QR rồi lưu 8 mã dự phòng ngoài điện thoại. Admin SQLite dùng username/email.

Production public bắt buộc HTTPS, COOKIE_SECURE=1; cookie HttpOnly/SameSite=Lax.
Demo HTTP chỉ cho loopback. Giữ cấu hình TRUST_PROXY hiện hành: chỉ bật sau
Nginx tin cậy, Gunicorn bind loopback và Nginx ghi đè forwarded headers.
Password reset qua SMTP cấu hình theo USER_ACCOUNTS.md; không tự tắt TOTP.

Mất điện thoại: password + một mã dự phòng, sau đó đổi thiết bị trong
`/account/mfa`. Mất cả mã dự phòng: người vận hành xác minh danh tính ngoài
website, có quyền console máy chủ và nhập password Admin ở lời nhắc ẩn:

```text
python tools/manage_mfa.py
python tools/manage_mfa.py --account <username-hoặc-email-Admin-SQLite>
```

CLI yêu cầu xác nhận `RESET MFA`, giới hạn thử và ghi audit; thu hồi yếu tố/
phiên/challenge/mã cũ, giữ account/password/log và **bắt buộc đăng ký TOTP mới**.
User không dùng được quy trình Admin này. CLI không bỏ yêu cầu MFA và không
cho đăng nhập web khi chưa thiết lập lại. Khóa mã hóa mất/hỏng phải được phục
hồi; CLI không tự xóa/ghi đè key hoặc bỏ MFA của Admin khác.

## Kiểm thử và giới hạn thực nghiệm

`tests/test_mfa.py` dùng raw requests để thử thiếu yếu tố, replay, race OTP,
brute-force đổi IP, backup dùng lại, session copy/logout/expiry, mất key,
recovery, reset password không bỏ MFA và writer SQLite không bị giữ trong lúc
băm password. Các test chức năng cũ đã dùng password + authenticator fixture
thay vì tự chèn role vào cookie; không có cờ tắt MFA khi TESTING.

`tools/mfa_fixture.py` là authenticator trong bộ nhớ cho fixture localhost,
không tích hợp vào runtime, không cấp quyền trực tiếp trong DB. Chrome/TCP
dùng TOTP theo giờ thật; một số unit test điều khiển thời gian để kiểm tra
counter, race, hết hạn và nhiều lần login. Ảnh setup che seed và QR.

Kết quả/chỉ số thực tế, inventory file và CSV từng test ở
`docs/h07/evidence/accounts_mfa_20261119/`. SMTP/Gemini thật không được gọi
trong đợt này; các lỗi API được test bằng mock. Symlink Windows thiếu quyền
vẫn được ghi SKIP. Chưa kiểm chứng triển khai VPS/nhiều worker thực, thiết bị
Authenticator vật lý, SMTP thật, WebAuthn, email verification hoặc MFA toàn vai trò.
