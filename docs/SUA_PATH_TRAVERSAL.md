# Sửa xử lý Path Traversal — 16/11/2026

**Cập nhật tiếp theo:** Đã hoàn tất thực nghiệm TCP và huấn luyện lại model.
Xem [kết quả Chương 4](CHUONG_4_KIEM_THU_TCP.md). Các mục bên dưới ghi lại
trạng thái ở lần sửa ban đầu; cảnh báo model và việc chưa chạy TCP đã được
xử lý trong lần thực nghiệm tiếp theo, ba ca symlink vẫn SKIP.

## Nguyên nhân

Form GET mã hóa dấu `%` người dùng nhập thành `%25`. Khi nhập
`%2e%2e%2fsecret.txt`, query truyền trên mạng là
`path=%252e%252e%252fsecret.txt`. Flask giải mã query một lần, trả lại
`%2e%2e%2fsecret.txt` trong `request.args`. Trước bản sửa, security coi đây
là tên literal trong kho và trả MISS/404 khi không tồn tại. AI dùng thêm
một biểu diễn `unquote` để trích đặc trưng nên vẫn có thể chấm suspicious.
404 này không chứng minh đã đọc được tệp ngoài kho.

Gửi trực tiếp `?path=%2e%2e%2fsecret.txt` khác với nhập vào form: Flask
chuyển thành `../secret.txt`, và bộ kiểm tra cũ đã từ chối thành phần `..`.

## Chính sách sau sửa

1. Flask là nơi duy nhất giải mã URL transport cho luồng truy cập tệp.
   Không thêm `unquote`, không giải mã lặp và không dùng chuỗi AI đã giải mã
   để mở tệp.
2. `validate_relative_path` từ chối escape cấu trúc còn sót lại, không phân
   biệt hoa thường: `%2e`, `%2f`, `%5c`, `%00`, `%3a`, `%25`.
   `%25` được dành riêng để từ chối cả các lớp mã hóa lồng nhau mà không
   cần vòng lặp giải mã. Đây là vi phạm chính sách cú pháp, không phải
   kết luận rằng hệ điều hành đã diễn giải chuỗi đó thành traversal.
3. Giữ kiểm tra thành phần đường dẫn: cấm `..`, `.`, slash đầu, backslash,
   drive Windows, UNC, ADS, tên thiết bị và tên có hậu tố không hợp lệ.
   Bổ sung từ chối ký tự điều khiển ASCII.
4. `safe_path` dùng `lstat` kiểm tra từng thành phần, cấm symlink và Windows
   reparse point (bao gồm junction), sau đó resolve và kiểm tra containment
   bằng thành phần đường dẫn. Không mở tệp ngoài kho.
5. Chỉ mở regular file; bổ sung kiểm tra thư mục trước nhánh mở Windows.
   POSIX vẫn dùng directory fd và `O_NOFOLLOW` như trước.
6. `web.py` và `ml_features.py` bổ sung chú thích về ranh giới giải mã.
   Cách tính điểm AI, model, giao diện, schema SQLite và dashboard giữ nguyên.
   Log vẫn lưu chuỗi sau Flask decode cùng điểm AI, quyết định và lý do.
7. Bổ sung test form, raw URL, nội dung tệp chính xác, junction, AI false
   positive và tích hợp artifact Logistic Regression thực tế; cập nhật
   smoke script với các mức mã hóa.

Tên tiếng Việt, dấu cách, dấu `+`, phần trăm thông thường và thư mục con
vẫn được hỗ trợ. Ví dụ tên literal `literal%20name.txt` được tải đúng tệp,
không bị giải mã thêm thành `literal name.txt`. Nếu muốn truy cập tên có
dấu cách bằng URL, hãy URL-encode tên một lần; form tự thực hiện bước này.

## Kết quả kiểm thử thực tế

Môi trường: Windows, Python 3.12.10, scikit-learn 1.9.1.
Chạy từ thư mục `FileGuardAI_H07`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q -rs
```

Kết quả: **35 passed, 3 skipped, 0 failed; 15 subtests passed; 3 warnings**.
Các kiểm tra HTTP sử dụng Flask test client, không cần chạy server hay
ghi vào database thật. Dữ liệu kiểm thử và log được tạo trong thư mục tạm.

| Nhóm | Thực tế | Kết quả |
|---|---|---|
| Tệp hợp lệ, Unicode, dấu cách, thư mục con | HTTP 200, đúng nội dung | PASS |
| Dấu `+`, `%` và tên literal `%20` | HTTP 200, không giải mã thêm | PASS |
| `../`, `..\`, absolute, drive Windows, UNC | HTTP 403 | PASS |
| `%2e%2e%2fsecret.txt` nhập qua form | HTTP 403/BLOCK | PASS |
| URL mã hóa trực tiếp, hai và nhiều lớp | HTTP 403 | PASS |
| Tệp hợp lệ về cú pháp nhưng không tồn tại | HTTP 404/MISS | PASS |
| Junction Windows tới ngoài kho, cả tệp tồn tại và thiếu | HTTP 403, không trả nội dung secret | PASS |
| AI luôn benign với traversal | HTTP 403/BLOCK | PASS |
| AI luôn suspicious, score 1.000 | Tệp hợp lệ 200, thiếu 404, traversal 403 | PASS |
| Artifact Logistic Regression thực tế | Điểm AI hợp lệ, HTTP 200/404/403 | PASS |
| Đăng nhập, dashboard, logout, SQLite log | Các test hồi quy pass | PASS |
| Symlink tệp/thư mục thực tế | Thiếu quyền tạo symlink Windows | SKIP (3) |

`tools/smoke_http.py` đã bổ sung payload nhưng chưa chạy với server đang
lắng nghe TCP; không coi kết quả test client là thực nghiệm trình duyệt.

## Hạn chế

- Windows vẫn có TOCTOU giữa kiểm tra và mở nếu người không tin cậy có
  quyền sửa kho đồng thời. Kho phải được bảo vệ bằng quyền hệ điều hành;
  bản sửa này không triển khai Win32 handle-based authorization.
- Chính sách cố ý không hỗ trợ tên literal chứa các escape cấu trúc đã
  dành riêng, kể cả nếu tên đó nằm trong kho. `%25` luôn bị từ chối.
  Những escape không thuộc tập dành riêng được coi là ký tự literal;
  không có bộ giải mã thứ hai ở tầng tệp.
- Ba test symlink cần chạy lại khi Windows có quyền tạo symlink hoặc
  Developer Mode. Junction đã được kiểm tra thành công trên môi trường này.
- Nhánh POSIX chưa chạy trên hệ điều hành này.
- Model artifact được tạo bằng scikit-learn 1.8.0, môi trường hiện dùng
  1.9.1 nên có ba `InconsistentVersionWarning`. Test suy luận đã pass,
  nhưng nên đồng bộ phiên bản hoặc huấn luyện lại trong môi trường cố định
  trước thực nghiệm chính thức. Không tự ghi đè artifact trong lần sửa này.
- Chưa thay đổi các giới hạn production và dữ liệu AI tổng hợp được nêu
  trong README; score AI không phải bằng chứng vi phạm chính sách tệp.
