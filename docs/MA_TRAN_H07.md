# Đối chiếu mã nguồn với yêu cầu H07

Mẫu H07: 4 CLO, 12 PI; báo cáo gồm Giới thiệu, 4 chương, Kết luận, TLTK và phụ lục. Các phần cần hoàn thiện thêm được đánh dấu **CẦN LÀM**.

| PI | Minh chứng trong MVP | Còn phải hoàn thiện khi làm đồ án |
|---|---|---|
| 1.1 | `app/security.py`, README §6 | Bảng đánh giá rủi ro và ví dụ CWE-22 |
| 1.2 | `app/ml_features.py`, `ml/train_model.py` | Sơ đồ quy trình phát hiện và cơ sở lý luận |
| 1.3 | `app/__init__.py`, `app/security.py` | UML Activity Diagram và luồng xử lý lỗi |
| 2.1 | Flask app + cấu trúc thư mục | Sơ đồ kiến trúc chi tiết, mô tả các module |
| 2.2 | `app/database.py`, `/dashboard` | ERD, bảng mô tả trường dữ liệu, chính sách log |
| 2.3 | `tests/test_security.py`, `tests/test_app.py` | Bảng kịch bản thực nghiệm và ảnh chụp |
| 3.1 | `open_authorized` tách rời AI | Phân tích giới hạn, đo tỷ lệ chặn, minh chứng cấu hình |
| 3.2 | SQLite tạo tự động, log từng yêu cầu | Chứng minh truy vấn/lọc, sao lưu và bảo vệ nhật ký |
| 3.3 | Xem/tải tệp, phân tích, ngăn chặn, nhật ký | Use Case Diagram và đặc tả 5 Use Case |
| 3.4 | HTML/Bootstrap, login, Chart.js | Bổ sung phân quyền người dùng và hardening nếu công khai |
| 4.1 | Pytest, thống kê, thời gian xử lý | Benchmark nhiều lần; phân tích false positive/negative |
| 4.2 | Dữ liệu synthetic 10.000 đường dẫn mặc định | Thu thập nguồn độc lập, kiểm tra nhãn và bias |

## Dàn ý báo cáo bắt buộc theo H07

- Giới thiệu đề tài
- Chương 1. Cơ sở lý thuyết
- Chương 2. Phân tích yêu cầu hệ thống
- Chương 3. Thiết kế và triển khai hệ thống
- Chương 4. Kết quả kiểm thử hoạt động (Hoạt động thử nghiệm, phân tích kết quả đạt được, logs, tài liệu hướng dẫn)
- Kết luận
- Tài liệu tham khảo
- Phụ lục (nếu có)

## Lưu ý triển khai và đánh giá

- Các **Lưu ý** trong mẫu H07 Word là chỉ dẫn của giảng viên và nhà trường, cần giữ nguyên trên đề cương, không xóa.
- Không thay đổi CLO–PI cố định nếu chưa có chấp thuận.
- Không tự ghi số liệu thực nghiệm chưa đo được.
- Không đăng nguồn dữ liệu cá nhân hoặc mật khẩu quản trị lên GitHub.
