# Gemini trong CANH GÁC SỐ

## Kiến trúc và dữ liệu gửi đi

Tái sử dụng `ExplanationService`: sau khi quyết định và ghi nhật ký truy cập,
request chỉ đưa Event ID và các đặc trưng đã làm sạch vào hàng đợi có giới
hạn. Worker nền mới gọi API; timeout/lỗi API không đổi ALLOW/BLOCK/MISS và
không giữ request tải tệp chờ Gemini. Logistic Regression và chính sách
đường dẫn giữ nguyên.

Adapter `GeminiProvider` kế thừa adapter Chat Completions hiện có, dùng endpoint
Google cố định `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`.
Dùng Bearer header, `max_tokens` mặc định 2048 (cấu hình được), `response_format=json_object`; bỏ tham
số `store` của adapter OpenAI. Yêu cầu trả tiếng Việt, chỉ chấp nhận đúng bốn
trường `why`, `traversal_type`, `risk`, `recommendations`, kiểm tra kiểu/độ dài,
giá trị risk, phản hồi bị cắt và phản hồi có chứa key. Không nhận markdown
thay cho JSON, không render HTML do API cung cấp.

Dữ liệu sự kiện gửi ra chỉ có: decision, ml_alert, parent_components (0–4),
absolute_style, backslash, structural_encoding, remaining_decode_changes
(0–2), length_bucket. Không gửi Event ID, IP người dùng, đường dẫn gốc, tên
tệp, nội dung tệp, mật khẩu hay token người dùng. Header Authorization chỉ
chứa key dịch vụ đúng mục đích xác thực. Google vẫn thấy IP mạng của máy chủ.
Không suy ra thoát symlink hoặc khai thác thành công từ các cờ cấu trúc.

## Cấu hình phía máy chủ

Đặt trong môi trường của tiến trình chạy Flask/Gunicorn:

```text
AI_EXPLANATION_PROVIDER=gemini
AI_EXPLANATION_MODEL=<model Gemini đang được cấp quyền trong Google AI Studio>
AI_EXPLANATION_API_KEY=<key riêng của bạn>
AI_EXPLANATION_TIMEOUT=20
AI_EXPLANATION_MAX_TOKENS=2048
AI_EXPLANATION_HOURLY_LIMIT=20
```

Không nhập key vào HTML/JavaScript hay cuộc trò chuyện; không commit key.
Ứng dụng đọc môi trường, không tự nạp `.env`; `.env.example` chỉ là hướng dẫn.
`AI_EXPLANATION_ENDPOINT` chỉ áp dụng adapter `openai-compatible`, không thay
endpoint Google của adapter `gemini`. Không tự chọn/thay model khi API từ chối.
Gemini dùng timeout mặc định 20 giây, giới hạn 0,1–60 giây; adapter
OpenAI-compatible chung vẫn giới hạn tối đa 10 giây. Gemini max_tokens cấu
hình được từ 256 đến 8192, mặc định 2048. Model suy luận lâu có thể timeout hoặc hết
token, được báo lỗi thay vì lưu kết quả thiếu. Không có key/model hợp lệ thì
chạy offline. Khởi động lại tiến trình sau khi thay cấu hình môi trường.

Sau khi đăng nhập Admin, mở Dashboard → Phân tích AI → Bật → Lưu cấu hình.
Thiết lập bật/tắt có CSRF và audit; mặc định tắt. “Đã cấu hình” chỉ xác nhận
adapter được tạo, không khẳng định key hợp lệ hay API kết nối thành công.
Xem trạng thái từng kết quả để biết success/cached, pending, quota,
authentication, network, timeout, invalid_response, rate_limited hoặc interrupted.

Giới hạn giờ được đếm chung trong SQLite sidecar; cache thành công 24 giờ,
cache lỗi ngắn 60 giây, hàng đợi mặc định 16 tác vụ. Khi đầy có thể bỏ tác vụ;
không đảm bảo mọi cảnh báo đều có giải thích. Tắt API không xóa kết quả cũ;
lời gọi đã bắt đầu có thể hoàn tất. Quyền tải tệp luôn do chính sách cục bộ.

## Lưu trữ và trang sự kiện

Tiếp tục dùng `instance/ai_explanations.sqlite3` tách khỏi SQLite nghiệp vụ.
`analyses.event_id` liên kết logic với `access_logs.id` (khác file SQLite nên
không có foreign key liên cơ sở dữ liệu). Thêm bảng `provenance` bằng
`CREATE TABLE IF NOT EXISTS` để lưu provider/model thực tế của từng phân tích
mới, giữ nguyên các bảng và dữ liệu cũ. Kết quả cũ chưa có nguồn được ghi rõ
“không được ghi ở phiên bản cũ”, không tự nhận là Gemini.

Nhấn Event ID trong bảng Dashboard hoặc liên kết trong Phân tích AI để mở
`/dashboard/events/<id>`. Chỉ Admin được xem; Guest chuyển tới đăng nhập,
Auditor bị từ chối. Trang hiển thị LR, chính sách, dữ liệu cục bộ, các chỉ dấu
được tính lại từ đường dẫn đã lưu, trạng thái API và giải thích tiếng Việt
nếu có. Không tự tạo kết quả thay thế khi API thiếu hoặc lỗi; nút tải lại
cho phép cập nhật trạng thái nền. Dùng layout, theme và cỡ chữ hiện có.

## Kiểm thử và thử kết nối thật

```text
python -m pytest -q -rs
python tools/run_h07_acceptance.py
python tools/check_gemini_connection.py
python tools/verify_ui_browser.py --software-rendering
```

Probe kết nối chỉ gửi đặc trưng của payload tổng hợp, có thể tiêu tốn một
lượt API; không khởi tạo Flask hay truy cập SQLite nghiệp vụ, không bật API
cho ứng dụng. Chỉ in trạng thái/schema, không in key hoặc nội dung phản hồi.
Exit 0 = phản hồi hợp lệ; 1 = lỗi thật; 2 = NOT_RUN vì thiếu cấu hình. Không
đổi NOT_RUN thành PASS hoặc đưa probe mạng vào bộ pytest mặc định.

Mock chứng minh hợp đồng request, dữ liệu làm sạch, timeout/mạng/401/403/429,
phản hồi lỗi/bị cắt/echo key, liên kết đúng Event ID ngoài 20 dòng gần nhất,
phân quyền, CSRF và escape XSS. Mock không chứng minh khả năng kết nối Google
hoặc chất lượng diễn giải tiếng Việt của model thật.

Log và báo cáo chạy thực tế: `docs/h07/evidence/gemini_20261118/`.
Không push GitHub hoặc triển khai VPS trong đợt nâng cấp này.

Cách nhập key ẩn trong Terminal, chạy probe + pipeline TCP thật và đọc thời
gian phân tích: [GEMINI_LIVE_VERIFICATION.md](GEMINI_LIVE_VERIFICATION.md).

Nguồn hợp đồng API: [Google Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai).
