# Kết quả thực nghiệm khởi đầu (không phải kết quả cuối đồ án)

Kết quả này thuộc lần đóng gói ban đầu. Kết quả Windows, Flask TCP,
SQLite và model huấn luyện lại mới nhất nằm ở
[CHUONG_4_KIEM_THU_TCP.md](CHUONG_4_KIEM_THU_TCP.md).

Thời điểm chạy bộ sinh dữ liệu: 16/11/2026. Môi trường cài sẵn NumPy, Scikit-learn và Pytest. Chưa chạy thử Flask HTTP trong môi trường tạo gói do Flask không có sẵn và môi trường không thể tải package qua mạng.

## Kết quả huấn luyện trên dữ liệu **tổng hợp**

Nguồn: `artifacts/training_results.json` sau lệnh `python -m ml.train_model --n 10000`.

- Tổng dữ liệu giả lập: 10.000 đường dẫn có nhãn (5.000 hợp lệ, 5.000 nghi vấn).
- Huấn luyện: 7.999 mẫu. Kiểm thử: 2.001 mẫu.
- Nhóm họ mẫu đường dẫn (*template family*) không trùng giữa train và test.
- Logistic Regression: Accuracy = **0,8751**, Precision = **1,0000**, Recall = **0,7500**, F1 = **0,8571**.
- Ma trận nhầm lẫn `[TN, FP; FN, TP]` = `[[1001, 0], [250, 750]]`.
- Baseline regex đơn giản đạt kết quả giống trên tập này. **Chưa chứng minh AI ưu việt hơn baseline**; đây là vấn đề cần giải quyết bằng dữ liệu đa dạng và thí nghiệm độc lập.

Nhận xét: còn **250 mẫu nghi vấn bị bỏ sót** trên tập kiểm thử tổng hợp. Vì vậy hệ thống phải giữ nguyên cơ chế kiểm soát đường dẫn độc lập với AI. Giá trị Recall 75% chưa đạt chỉ tiêu dự kiến 95% trong đề cương. Không được viết là đã đạt 95%.

## Những kiểm thử đã thực hiện được

- Pytest cho `app/security.py`, dữ liệu và đặc trưng ML: **9 tests passed, 1 test module skipped** (bộ kiểm thử tích hợp Flask bị bỏ qua vì chưa cài Flask trong môi trường đóng gói).
- Unittest bảo mật: **6 tests passed**.
- Phân tích cú pháp: đã kiểm tra các mô-đun Python và 5 mẫu HTML/Jinja2.
- Tệp PDF mẫu: đã kiểm tra đều mở được như PDF 1 trang.

## Việc phải làm trước khi viết Chương 4

1. Trên Windows 11: chạy `START_WINDOWS.bat`, kiểm tra website `http://127.0.0.1:5000`.
2. Chạy `TEST_WINDOWS.bat`; chạy `python tools/smoke_http.py` trong terminal khác khi Flask đang hoạt động.
3. Chụp ảnh trang tải tệp, trang 403, trang 404, đăng nhập, dashboard và nhật ký.
4. Lập bảng Pass/Fail có thời gian, dữ liệu đầu vào, kết quả thực tế và bằng chứng; không viết dữ liệu dự kiến thành kết quả.
5. Bổ sung dữ liệu ngoài họ mẫu nhân tạo, đánh giá tỷ lệ bỏ sót và false positives; đối chiếu mô hình AI với baseline regex và cơ chế ngăn chặn độc lập.
