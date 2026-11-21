# Phân quyền, mật khẩu và bảo vệ nhật ký

## Ma trận quyền

| Tài nguyên | Guest | Auditor | Admin | OS Operator |
|---|---|---|---|---|
| Kho public/download qua policy | Có | Có | Có | Qua OS theo ACL |
| Dashboard/AI plots/security events | Không | Không | Đọc | Không tự có cookie |
| Filter log | Không | Không | Có | CLI SQL read-only nếu có ACL |
| Export CSV | Không | Không | Có, POST + CSRF | Có qua công cụ local |
| UPDATE/DELETE event qua app | Không | Không | Không | Trigger có thể bị operator có quyền DB gỡ: rủi ro còn lại |
| Đổi mật khẩu Admin hiện tại | Không | Không | Có, xác minh mật khẩu + CSRF | CLI có quyền filesystem |
| Đặt hash Auditor/backup/deploy model | Không | Không | Không qua web | Có, bằng CLI/OS |

## Cấu hình tài khoản

Chỉ dùng CLI để thiết lập lần đầu hoặc chủ động đặt lại mật khẩu; không chạy lại CLI ở mỗi lần mở server. Chạy trong project bằng đúng Python venv đang dùng:

```powershell
python tools/manage_credentials.py --role admin
python tools/manage_credentials.py --role auditor
python run.py
```

Password nhập bằng getpass, không qua command-line/history. Chỉ scrypt
hash Werkzeug được lưu trong `instance/admin_password.hash` hoặc
`auditor_password.hash`; hash cũ vào credential_history, không xóa.
Hash Admin hợp lệ đã có luôn được ưu tiên và không ghi lại khi startup.
CLI và website đổi hash có hiệu lực ngay; phiên Admin cũ bị thu hồi bằng
kiểm tra phiên bản hash phía server. Không còn in mật khẩu tạm. Khi chưa
có hash, dùng CLI nhập kín. Biến môi trường chỉ còn là bootstrap tương thích
lần đầu, không ghi đè file có sẵn. Chi tiết và giới hạn: [PASSWORDS](../auth/PASSWORDS.md).

Session 15 phút, HttpOnly + SameSite=Lax. HTTPS thực tế cần đặt
COOKIE_SECURE=1 và secret bền vững trong secret manager/env. Demo mặc định
secret random sau restart làm mất hiệu lực session cũ. CSRF bật trong
chạy bình thường; TESTING mặc định tắt để giữ bộ test cũ, nhưng tests/auth
và TCP kiểm tra rõ chế độ CSRF bật. Không dùng TESTING cho triển khai.
Throttling theo IP là kiểm soát MVP, có rủi ro NAT/DoS; không phải hệ IAM.

## Log và backup

DB, model, credential không được nằm trong FILES_ROOT; startup từ chối
misconfiguration. Không có endpoint trả DB trực tiếp. Triggers append-only
bảo vệ khỏi sửa/xóa bằng query ứng dụng; không chống attacker có OS write.
SQL tham số hóa, log request raw-after-Flask-decode, không password/token.
CSV thêm dấu nháy trước các giá trị có thể thành công thức spreadsheet.

```powershell
python tools/backup_logs.py instance/backups/events-20261117.sqlite3
```

Backup online không ghi đè, source read-only, kiểm tra integrity. Bản sao
chứa IP/path nhạy cảm: giới hạn người đọc bằng Windows ACL, mã hóa ổ đĩa
và lưu ngoài Git/public. Chính sách đồ án: không tự purge bằng chứng;
operator chịu trách nhiệm retention và nơi lưu được phép. Không tự áp
ACL hệ thống trong phiên làm việc để tránh khóa người dùng khỏi workspace.

Khuyến nghị ACL: chỉ tài khoản chạy Flask và operator được đọc/ghi
instance; kho public không cho khách web/tài khoản không tin cậy ghi;
model chỉ operator cập nhật. Xác minh bằng Properties -> Security hoặc
`icacls instance`, `icacls shared_files` tại máy triển khai. Chưa đo một
chính sách ACL domain/production, không tự tuyên bố đã harden OS.

## Giới hạn

Windows TOCTOU chưa có Win32 handle-based authorization; symlink thật
cần quyền OS, chưa tự bật Developer Mode. Chưa có MFA, multi-user DB,
remote log collector, log HMAC chain, log quota hoặc rate limit download.
SQLite triggers không phải tamper-proof storage. Không load pickle/joblib
không tin cậy. Khuyến nghị gắn với
[OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
