# 01 — Phân tích rủi ro Path Traversal / CWE-22

Bản nghiệm thu ngày 17/11/2026 (giờ Việt Nam). Phạm vi: MVP localhost Windows 11; không phải chứng nhận triển khai Internet.

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

**Trạng thái: PASS.** Đối chiếu [ma trận tổng hợp](12_MA_TRAN_NGHIEM_THU.md). Bằng chứng chạy thực tế: [summary](evidence/20261116T182248Z_5acba3/summary.json), [pytest](evidence/20261116T182248Z_5acba3/pytest.stdout.txt), [bảng HTTP](evidence/20261116T182248Z_5acba3/http_test_cases.csv).
