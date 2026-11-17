# Đánh giá rủi ro Path Traversal / CWE-22

## Phạm vi và cơ sở

Tài sản: file ngoài kho, thông tin đăng nhập, model pickle, log IP/path,
tính toàn vẹn nhật ký, tính sẵn sàng Flask. Tác nhân: khách web chưa đăng
nhập, người có quyền xem dashboard, người có quyền ghi filesystem. Trust
boundary: query HTTP -> policy -> filesystem; session -> trang quản trị;
operator OS -> credential/model/database. Chỉ thử trên localhost do chủ
dự án quản lý, không tấn công host nguồn công khai.

[CWE-22](https://cwe.mitre.org/data/definitions/22.html) mô tả việc đường
dẫn từ bên ngoài không bị giới hạn đúng vào thư mục được phép. `../` và
absolute path là hai biểu diễn điển hình; encoded path cần xét nhất quán
với tầng HTTP. Tham khảo [OWASP Path Traversal](https://community.owasp.org/attacks/Path_Traversal).

Thang L (khả năng) và I (tác động) 1–5, điểm R=L×I: thấp 1–4, trung bình
5–9, cao 10–16, rất cao 17–25. Đây là **nhận định thiết kế**, không phải
số liệu đo xác suất tấn công. Điểm sau kiểm soát chỉ đúng với giả định
kho không bị người không tin cậy sửa đồng thời.

| ID | Kịch bản | Trước L/I/R | Kiểm soát và bằng chứng | Sau L/I/R |
|---|---|---|---|---|
| R01 | `../` đọc config/secret ngoài kho | 5/5/25 | validate component, containment, tests/security + TCP | 1/5/5 |
| R02 | Absolute/drive/UNC/ADS hoặc device Windows | 4/5/20 | cấm cú pháp và thiết bị; chỉ regular file | 1/5/5 |
| R03 | Encoded/double encoded traversal | 5/5/25 | một decode transport; residual escape bị từ chối; không lặp decode ở file access | 1/5/5 |
| R04 | Symlink/junction thoát kho | 3/5/15 | lstat/reparse, không duyệt link; test junction PASS, symlink còn phụ thuộc quyền | 2/5/10 |
| R05 | Đổi junction giữa check và open (TOCTOU) | 3/5/15 | ACL kho, tài khoản OS tối thiểu; Windows chưa có handle-based proof | 2/5/10 |
| R06 | AI false negative cấp quyền sai | 4/5/20 | AI không cấp quyền; model benign vẫn bị security chặn | 1/5/5 |
| R07 | Đọc/xóa/sửa log qua web | 4/4/16 | roles, thư mục private, append-only triggers, không API DELETE/UPDATE | 1/4/4 |
| R08 | Đoán mật khẩu/CSRF/chiếm phiên | 4/4/16 | scrypt hash, CSRF, 5 lỗi/300s/IP, phiên 15 phút, cookie HttpOnly/SameSite | 2/4/8 |
| R09 | Cạn tài nguyên do input/log/request | 4/3/12 | path <=4096, payload body <=32KiB, giới hạn listing; chưa có quota log/global rate limit | 3/3/9 |
| R10 | Load joblib không tin cậy thực thi code | 3/5/15 | chỉ artifact nội bộ, hash đối chiếu; không upload/deploy qua web | 1/5/5 |
| R11 | Đăng dữ liệu/log/credential vào Git | 3/4/12 | gitignore private files, kiểm tra staged diff, PR không chứa DB/hash mật khẩu thật | 1/4/4 |

Không xóa rủi ro còn lại chỉ vì một tập payload đạt 100% block. Tài khoản
có quyền sửa DB có thể gỡ trigger; operator có quyền ghi kho có thể chép
hoặc hardlink tệp nhạy cảm vào đó. Đây là ranh giới tin cậy OS, không có
cam kết ngăn được bằng mô hình ML. 403 nghĩa vi phạm policy, 404 nghĩa
path hợp lệ nhưng không có file; score cao không tự động tạo 403.
