# 09 — Dashboard, phân quyền và mật khẩu

Bản nghiệm thu ngày 17/11/2026 (giờ Việt Nam). Phạm vi: MVP localhost Windows 11; không phải chứng nhận triển khai Internet.

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

Kiểm chứng: [auth.py](../../app/auth.py), [training_view.py](../../app/training_view.py), [templates](../../app/templates), [test_auth.py](../../tests/test_auth.py), [TCP41checks](../evaluations/dashboard_http_20261116T172733Z_800c38_http_5badd2c18bb5.json). Chưa kiểm trình duyệt/thị giác thủ công; không chế ảnh screenshot.

**Trạng thái: PASS.** Đối chiếu [ma trận tổng hợp](12_MA_TRAN_NGHIEM_THU.md). Bằng chứng chạy thực tế: [summary](evidence/20261116T182248Z_5acba3/summary.json), [pytest](evidence/20261116T182248Z_5acba3/pytest.stdout.txt), [bảng HTTP](evidence/20261116T182248Z_5acba3/http_test_cases.csv).
