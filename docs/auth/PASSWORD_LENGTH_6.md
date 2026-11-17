# Chính sách mật khẩu demo 6–128 ký tự — 17/11/2026

Nhánh `h07/cybersecurity-ui`, tiếp nối41373af. Chỉ đổi giới hạn đặt/đổi mật khẩu; không áp thêm yêu cầu ký tự đặc biệt hoặc chữ hoa. Không tạo/reset mật khẩu thật, không thay hash có sẵn, dataset, model hoặc SQLite nghiệp vụ.

Đã đồng bộ `tools/manage_credentials.py` (Admin/Auditor + prompt getpass), `app/auth.py` (bootstrap khi chưa có hash), `app/web.py` (đổi mật khẩu), `app/templates/change_password.html` (hai trường mới/xác nhận minlength6, maxlength128 và hướng dẫn). Hash đã có luôn được ưu tiên; khởi động lại không tạo hash/password mới. Quy trình CLI nhập/xác nhận kín, Werkzeug hash, atomic write, CSRF, throttling, phân quyền, kiểm mật khẩu hiện tại và server-side session revocation giữ nguyên.

| Độ dài | Mong đợi khi đặt/đổi | CLI Admin | CLI Auditor | Bootstrap Admin | Web đổi mật khẩu |
|---|---|---|---|---|---|
| 5 | Từ chối | PASS | PASS | PASS | PASS |
| 6 | Chấp nhận | PASS | PASS | PASS | PASS |
| 8 | Chấp nhận | PASS | PASS | PASS | PASS |
| 12 | Chấp nhận | PASS | PASS | PASS | PASS |
| 128 | Chấp nhận | PASS | PASS | PASS | PASS |
| 129 | Từ chối | PASS | PASS | PASS | PASS |

Không kiểm tra ngược độ dài plaintext từ hash cũ và không sửa cơ chế login. Password đã lưu hợp lệ vẫn dùng được; chính sách này áp dụng lúc đặt/đổi. Đổi mật khẩu trên web vẫn yêu cầu khác mật khẩu hiện tại, xác nhận trùng và đúng mật khẩu hiện tại. Mật khẩu sai, xác nhận khác, CSRF/Guest/Auditor, write failure, rate limit, cookie cũ và concurrent change vẫn nằm trong bộ test hiện hữu.

Bổ sung21 cases:12 tham số CLI (6 độ dài ×2 role),6 bootstrap,2 mốc web6/8 và1 kiểm web6 ký tự/persistence/form attributes. Tests dùng chuỗi chữ thường hoặc fixture ngẫu nhiên, không đưa password thật vào Git. Browser và tool restart đổi sang tạo password fixture đúng6 ký tự trong RAM, không in/lưu plaintext.

## Kết quả chạy local

- Pytest: **205 PASS,0 FAIL,0 ERROR,3 SKIP**,15 subtests PASS;60,33s. [Stdout](../ui/pytest_20261117T122216Z/stdout.txt).
- Acceptance: **6/6 bước exit0**, pytest205 PASS/3 SKIP;dashboard TCP41 PASS;download33 PASS/3 symlink SKIP;hiệu năng144 request/144 log rows/0 lỗi. [Summary/JUnit](../bao_cao_h07/evidence/20261117T122057Z_16e451/summary.json).
- Hai OS subprocess Flask thật qua TCP: **20 assertions PASS,0 FAIL**. Process đầu đổi sang password6 ký tự; process sau chấp nhận mới, từ chối cũ, dashboard200, download200 và traversal403. [Kết quả](evidence/restart_20261117T122142Z_65253e/results.json).
- Browser cuối: **402 PASS,0 FAIL**, không lỗi JavaScript/static assets; xem [results.json](../ui/browser_20261117T122115Z_b675a3/results.json), ảnh account Light/Dark và manifest trong cùng thư mục. Đây là lượt mới với password fixture đúng6 ký tự.

Các SKIP giữ nguyên do quyền symlink Windows, không biến FAIL thành SKIP. Bộ browser vẫn kiểm Light/Dark, cỡ chữ, AI Training10.000 mẫu, login/CSRF, account/revocation và bố cục1440/768/390. Zoom vẫn là CDP reflow emulation, không phải xác nhận native zoom. Chrome local vẫn có giới hạn môi trường đã ghi; Chrome CI tách riêng với artifact theo commit.

Hash được bảo vệ trong acceptance và TCP trước/sau không đổi. Không có hash mật khẩu/secret/SQLite nghiệp vụ được thêm vào commit. Không chạy CLI đặt mật khẩu thật trong workspace. Khi chưa có hash, người dùng chạy `python tools/manage_credentials.py --role admin` để nhập kín một lần rồi `python run.py`; không chạy CLI lại mỗi lần restart.

File: `app/auth.py`, `app/web.py`, `app/templates/change_password.html`, `tools/manage_credentials.py`, `tests/test_password_change.py`, `tools/ui_password_checks.py`, `tools/verify_credentials_tcp.py`, `docs/auth/PASSWORDS.md`, `docs/h07/USE_CASES.md`, UI PR description và báo cáo này/evidence mới. Không thay password hash/SECRET_KEY/session logic hoặc chính sách download. Commit/push nhánh review và cập nhật PR#2; không merge main.
