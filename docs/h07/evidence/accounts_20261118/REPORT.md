# Kết quả nâng cấp tài khoản — 18/11/2026

## Phạm vi

Thêm đăng ký username/email, đăng nhập bằng một trong hai định danh, đăng xuất
POST, hồ sơ cá nhân, đổi mật khẩu, khôi phục qua email và quản lý tài khoản
Admin. User đăng ký mới luôn có role `user`; role từ form login không được dùng
để cấp quyền. Admin/Auditor hash file hiện có tiếp tục hoạt động.

Migration chỉ cộng thêm bốn bảng tài khoản trong SQLite, version 1. Không sửa
Logistic Regression, dataset, chính sách Path Traversal hoặc quyết định
ALLOW/BLOCK/MISS. Các đợt kiểm thử dùng SQLite/hash/mailbox fixture riêng.

Hash mới: Werkzeug PBKDF2-HMAC-SHA256 600.000 vòng và salt ngẫu nhiên riêng.
Giữ quy định demo 6–128 ký tự đã được yêu cầu trước đó. Token reset ngẫu nhiên
256 bit, DB chỉ chứa digest; hết hạn 15 phút, một lần sử dụng và ràng buộc
credential version. Đổi/reset mật khẩu, khóa/mở hoặc đổi quyền thu hồi phiên cũ.

CSRF, kiểm tra quyền ở backend, limiter SQLite và audit transaction được áp
dụng cho các thao tác. SMTP dùng TLS trước AUTH, không có fallback plaintext.
Cookie HttpOnly/SameSite=Lax; Secure cho HTTPS hoặc COOKIE_SECURE=1. HTTP chỉ
cho tài khoản trong demo loopback; production public yêu cầu HTTPS.

## Kiểm thử đã có bằng chứng

| Đợt | Kết quả thực tế | Bằng chứng |
|---|---|---|
| Focused auth/password trước sửa lỗi phát hiện trong test | 55 PASS, 2 FAIL | focused.stdout.txt |
| Focused sau sửa | 57 PASS, 0 FAIL | focused-final.stdout.txt |
| 15 test tài khoản đầu tiên | 15 PASS, 0 FAIL | accounts-final.stdout.txt |
| SMTP TLS và session không hợp lệ | 4 PASS, 0 FAIL | transport-session.stdout.txt |
| Pytest toàn dự án | 349 PASS, 0 FAIL, 0 ERROR, 3 SKIP; 15 subtest PASS | pytest-full.stdout.txt, pytest-full.xml |
| Chrome luồng tài khoản mới | 57 PASS, 0 FAIL | ../../../ui/accounts_20261118T154006Z_e34017/results.json |
| Chrome regression giao diện hiện có | 475 PASS, 0 FAIL | ../../../ui/browser_20261118T154914Z_a830e7/results.json |

Hai FAIL ban đầu: limiter định danh giữ cả lượt login thành công, và test so
sánh trang quên mật khẩu của hai client có CSRF token khác nhau. Đã xóa bucket
định danh khi login thành công và kiểm tra known/unknown bằng cùng anonymous
client. Giữ log gốc để đối chiếu, không đổi FAIL thành SKIP.

Lần acceptance đầu bị subprocess timeout sau 600 giây khi chạy song song
với Chrome; chưa hoàn thành, không được tính PASS/SKIP. Log vẫn ở
acceptance.stderr.txt. Runner đã có thời hạn Pytest 3.600 giây, giữ output khi
timeout, ghi ERROR/exit 124 và chạy tiếp các suite khác. Có regression test
cho việc timeout không làm acceptance thành công. Đợt cuối chạy tuần tự.

Pytest trực tiếp hoàn tất trong 2.120,60 giây. Ba SKIP nằm ở
tests/test_app.py:49, tests/test_security.py:54 và :66 vì Windows không cho
tạo symlink khi thiếu quyền/Developer Mode. Không đổi lỗi thành SKIP.
Số subtest được giữ riêng, không cộng thêm vào số testcase JUnit.
Lượt acceptance này chưa có summary hoàn chỉnh khi yêu cầu được nâng lên
Argon2id/TOTP. Không dùng lượt chưa hoàn thành làm kết quả nghiệm thu.
Bản hiện hành và các lần chạy mới nằm ở ../accounts_mfa_20261119/;
thiết kế hiện hành ở ../../MFA_SECURITY.md. Phần mô tả PBKDF2 trong báo cáo
này là mốc trước yêu cầu MFA, không đại diện cho hash mới hiện nay.

Chrome chạy thực qua TCP, Light/Dark ở 1440/768/390px. Luồng mới gồm đăng ký,
login email, CSRF, đổi/reset mật khẩu, thu hồi phiên, khóa/mở và kiểm tra
file 200/traversal 403. Có 42 ảnh cho bảy trang tài khoản. Browser regression
giữ kiểm tra biểu đồ, bộ lọc, CSV, theme/font, AI explanations bằng fixture.
Zoom trong suite cũ là CDP emulation; không xác minh phím zoom native.
Không có lỗi runtime JavaScript hoặc lỗi tải static được suite ghi nhận.

Hai báo cáo Chrome đều ghi protected_unchanged=true cho dataset, model và
SQLite nghiệp vụ; suite tài khoản còn kiểm tra hash Admin thực không đổi.

## SMTP và giới hạn

Toàn bộ email trong test là mailbox/transport giả; chưa gửi SMTP thật và
không gọi Gemini thật trong đợt tài khoản. Người vận hành tự cấu hình các
biến ACCOUNT_RESET_ORIGIN, ACCOUNT_SMTP_HOST/PORT/SSL/FROM/USERNAME/PASSWORD
qua môi trường, sau đó xác minh delivery riêng. Không đưa secret vào chat,
repository hoặc log. Trang hồ sơ Admin phân biệt cấu hình transport với
việc đã xác minh gửi thành công.

Chưa có email verification/MFA. Hồ sơ chỉ đổi tên hiển thị; email/username
chỉ đọc. Chưa hỗ trợ email quốc tế Unicode. Mailqueue trong bộ nhớ không
bền qua restart; token chưa dùng sẽ tự hết hạn, password không đổi.
Không dùng Gunicorn --preload với thread mail/AI hiện tại. Chưa kiểm chứng
SMTP thật, nhiều worker hoặc triển khai VPS. Admin cần xác minh danh tính
trước khi nâng quyền một tài khoản mới.

Không commit, push, merge hoặc deploy. Các thay đổi Gemini/Alerts/UI có từ
trước trong working tree được giữ nguyên, không coi là phần mới của đợt này.

## File mã nguồn/tài liệu của đợt tài khoản

Tạo mới:

- app/account_store.py
- app/account_views.py
- app/account_mail.py
- app/static/account-reset.js
- app/templates/register.html
- app/templates/forgot_password.html
- app/templates/reset_password.html
- app/templates/account.html
- app/templates/accounts_manage.html
- tests/test_accounts.py
- tests/test_account_mail.py
- tests/test_acceptance_timeout.py
- tools/verify_accounts_browser.py
- docs/h07/USER_ACCOUNTS.md
- docs/h07/evidence/accounts_20261118/REPORT.md và log/evidence cùng thư mục
- docs/ui/accounts_20261118T154006Z_e34017/ (JSON, manifest, 42 PNG)
- docs/ui/browser_20261118T154914Z_a830e7/ (regression JSON/manifest/PNG)

Chỉnh sửa:

- app/auth.py
- app/web.py
- app/database.py
- app/templates/base.html
- app/templates/login.html
- app/templates/change_password.html
- tools/manage_credentials.py
- tools/run_h07_acceptance.py
- .env.example

Hướng dẫn vận hành và mô tả quyền chi tiết: ../../USER_ACCOUNTS.md.
