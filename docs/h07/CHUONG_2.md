# Chương 2 — Phân tích yêu cầu và thiết kế

## 1. Các yêu cầu chức năng

F01 liệt kê tài liệu được phép; F02 tải tệp với Unicode, khoảng trắng và
thư mục con; F03 trả 403 cho vi phạm policy, 404 cho file thiếu, 200 cho
file hợp lệ; F04 chấm điểm AI advisory; F05 lưu event SQLite; F06 đăng
nhập/đăng xuất theo role; F07 xem/lọc log và biểu đồ; F08 admin xuất CSV;
F09 operator quản lý hash và backup; F10 nghiên cứu model offline, giữ
artifact/model cũ. Mỗi tính năng có use case, route/CLI và test tương ứng.

## 2. Yêu cầu phi chức năng

N01 không đọc ngoài shared_files với mô hình đe dọa đã nêu; N02 không
dùng AI làm lớp cấp quyền; N03 mật khẩu không ghi plaintext xuống DB/Git;
N04 quyền truy cập log được kiểm tra server-side; N05 chống CSRF POST,
throttle login; N06 log append-only ở lớp ứng dụng và OS private; N07
không tự xóa bằng chứng; N08 báo số đo thực, ghi SKIP/giới hạn; N09 có
hướng dẫn tái lập ở clone mới; N10 không tự merge main.

Phạm vi localhost, Python 3.12/Flask/sklearn/SQLite/Windows. Chưa có cam
kết production multiuser, HTTPS infrastructure, OS-level tamper resistance
hoặc Windows TOCTOU-proof. Việc chưa chạy được symlink thật là mục chưa
đạt về minh chứng, không được che bằng test giả.

## 3. Actor và Use Case

[USE_CASES.md](USE_CASES.md) đặc tả 10 use case với actor, điều kiện,
luồng chính, ngoại lệ và hậu điều kiện. Admin/auditor là role web; operator
là quyền OS riêng. Không có đường nâng quyền qua query hoặc tự đăng ký.
Public file vẫn tải được khi chưa login, nhưng private artifact luôn ở
ngoài kho và ngoài các route public.

## 4. Thiết kế tổng thể

[THIET_KE.md](THIET_KE.md) có kiến trúc, Activity, Sequence, ERD thực tế
và định nghĩa field/index/trigger. Activity UML có source PlantUML riêng.
ERD không bịa bảng users hay FK; credential nằm trong cấu hình/hash file.

Ranh giới và phân tích rủi ro xem [RUI_RO_CWE22.md](RUI_RO_CWE22.md).
Thiết kế chọn cấm các component/escape mơ hồ thay vì sanitize/decode lặp
đến một path khác; tên bị dành riêng có thể bị từ chối dù file nằm trong
kho. Đây là policy đã công bố, không đồng nghĩa mọi từ chối là khai thác.

## 5. Tiêu chí nghiệm thu

Mỗi PI trong MA_TRAN_H07 có trạng thái Đạt/Chưa đạt, phạm vi, file và test
thực. Đạt chỉ là tự đánh giá kỹ thuật theo minimum MVP, không phải xác
nhận chấm điểm của trường. Các CLO–PI gốc không bị đổi; nội dung mẫu Word
và yêu cầu riêng của giảng viên cần được đối chiếu ngoài tài liệu kỹ thuật.
