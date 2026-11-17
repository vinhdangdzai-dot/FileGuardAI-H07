# 06 — Ma trận kiểm thử thực tế

> C?p nh?t Dataset/UI: [b?o c?o t?ch h?p 10.000 m?u](../datasets/INTEGRATION_10000.md) ghi k?t qu? m?i v? b?ng ch?ng ri?ng; c?c m?c c? b?n d??i gi? nguy?n.

> **Cập nhật sửa quyền temp:** [báo cáo13](13_SUA_LOI_PYTEST_WINDOWS11.md). Lệnh pytest thông thường mới:116 PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS. Dùng runtime UUID riêng, không dùng pytest-of-user hoặc cache cũ. Kết quả109 PASS bên dưới là mốc nghiệm thu trước bản sửa, không phải lần chạy mới.

Bản nghiệm thu ngày 17/11/2026 (giờ Việt Nam). Phạm vi: MVP localhost Windows 11; không phải chứng nhận triển khai Internet.

Môi trường: Windows 11, Python venv hiện tại, scikit-learn1.9.1, Flask/SQLite; localhost qua TCP thật, không chỉ test_client. Lệnh và exit code nằm trong [summary](evidence/20261116T182248Z_5acba3/summary.json); stdout/stderr/JUnit được giữ cùng thư mục. Chạy bằng `python tools/run_h07_acceptance.py` tạo thư mục mới, không ghi đè bằng chứng cũ.

| Nhóm | Thực tế | Kết luận / bằng chứng |
|---|---|---|
| Pytest | 109 PASS, 3 SKIP, 15 subtests PASS; 22.66s | [stdout](evidence/20261116T182248Z_5acba3/pytest.stdout.txt), [JUnit](evidence/20261116T182248Z_5acba3/pytest.xml) |
| Checkout sạch ef545f2 + prepare_workspace | 109 PASS, 3 SKIP, 15 subtests PASS; 38.38s | [JUnit](evidence/clean_ef545f2.xml); cùng venv, không phải cài dependency mới |
| GitHub CI3839f3d Windows Server2025 | 112 PASS,0 SKIP,15 subtests PASS;40.91s | [bằng chứng](evidence/ci_3839f3d.json); dependencies cài mới;3 symlink thật chạy được |
| Dashboard/auth/CSV TCP | 41 PASS, 0 FAIL | [JSON](../evaluations/dashboard_http_20261116T172733Z_800c38_http_5badd2c18bb5.json) |
| Download TCP | 33 PASS, 0 FAIL, 3 SKIP | [summary](../evidence/tcp_20261116T182321Z_e9d112/summary.json) |
| Hiệu năng và SQLite | 144 request, 0 lỗi, 144 dòng; integrity ok | [performance](../h07/evidence/20261116T182323Z_0090f9/performance.json) |
| Symlink Windows | 3 SKIP; thiếu đặc quyền WinError1314 | [probe](evidence/20261116T182248Z_5acba3/symlinks.stdout.txt); không được tính PASS |
| Junction swap / handle Windows | 2 bài pytest PASS | [test_windows_handle.py](../../tests/test_windows_handle.py) |
| Audit dữ liệu/model | tiến trình exit0 | [audit](evidence/20261116T182248Z_5acba3/audit) |

Bảng máy đọc có từng mã TC, đầu vào, expected, actual, trạng thái và đường dẫn bằng chứng: **[http_test_cases.csv](evidence/20261116T182248Z_5acba3/http_test_cases.csv)**. Payload bao gồm tệp thật, Unicode/dấu cách/subdir, `../`, `..`, backslash, absolute/drive/UNC, đơn/hai/nhiều lớp URL encoding, NUL, tên không tồn tại. Body được đối chiếu tệp công khai và sentinel ngoài root; status đúng một mình chưa đủ để kết luận không rò rỉ.

Kiểm thử bổ sung: AI benign không vượt policy; AI suspicious không ép403; AI lỗi; log lỗi503 không đọc body; RBAC guest/auditor/admin; CSRF; mật khẩu; invalid time/status/probability; query thống kê và export cùng scope; CSV formula injection; model checksum trước unpickle; private storage startup guard; canonical split không giao nhau.

Chưa chạy: Python3.11 (đã chạy3.12.10), symlink thật với Developer Mode/SeCreateSymbolicLinkPrivilege, SMB/reparse provider khác, Linux runtime cho nhánh POSIX, kiểm thử mạng production và trình duyệt thủ công. Cần chạy lại trên môi trường tương ứng; không điền PASS trước khi có kết quả. Các fixture/bằng chứng cũ và DB người dùng được giữ nguyên SHA trong summary.

**Trạng thái: PARTIAL — symlink thật SKIP.** Đối chiếu [ma trận tổng hợp](12_MA_TRAN_NGHIEM_THU.md). Bằng chứng chạy thực tế: [summary](evidence/20261116T182248Z_5acba3/summary.json), [pytest](evidence/20261116T182248Z_5acba3/pytest.stdout.txt), [bảng HTTP](evidence/20261116T182248Z_5acba3/http_test_cases.csv).
