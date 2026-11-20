# Đối chứng Native và OpenAI-compatible cùng key/model

Báo cáo gemini_live_20261118T111736Z_59c64d xác nhận model có trong catalog
OpenAI-compatible nhưng probe và pipeline đều HTTP 404. Catalog không chứng
minh model hỗ trợ/được cấp quyền tạo nội dung qua endpoint đó. Báo cáo cũ
chưa thử generateContent native; không đủ dữ liệu khẳng định quyền model
hay tầng tương thích là nguyên nhân. Không sửa kết quả run cũ.

## Lệnh chạy có giới hạn

Sau khi mock tests PASS, tại thư mục FileGuardAI_H07 trong Terminal VS Code:

```powershell
..\.venv\Scripts\python.exe tools/compare_gemini_apis.py --prompt-key --model gemini-2.5-flash-lite
```

Key nhập ẩn một lần, chỉ trong môi trường/bộ nhớ tiến trình. Không nhập key
vào tham số, chat hoặc file Git. Nếu môi trường tiến trình đã có key đúng,
có thể bỏ --prompt-key. Không dùng lại key từng lộ qua chat. Không có key
thì NOT_RUN/exit 2; không thử mạng hoặc tự tìm key trong lịch sử người dùng.

Thử nghiệm sử dụng cùng một giá trị key/model cho hai provider, không lưu
key hoặc hash key để chứng minh. Công cụ kiểm tra hai giá trị bằng nhau
trong bộ nhớ trước mọi request. Không tự đổi model, key hay retry.

## Ngân sách tối đa 5 request

1. Native POST /v1beta/models/{model}:generateContent, x-goog-api-key.
2. Compatible POST /v1beta/openai/chat/completions, Authorization Bearer.
3. Native GET /v1beta/models/{model}, x-goog-api-key: lấy metadata đúng model
   gồm supportedGenerationMethods, không suy từ catalog tên chung.
4. Nếu một endpoint tạo nội dung thành công: thêm probe JSON và request
   traversal chạy qua pipeline thật trong Flask fixture bằng adapter đó.

Hai phép thử tối giản đều yêu cầu `Reply with OK.`, tối đa 256 output token,
không JSON mode hoặc system prompt để tách lỗi generate cơ bản khỏi schema.
Chỉ ghi content_nonempty, status, thời gian/số byte; không lưu nguyên text.
Response bị cắt/lỗi định dạng vẫn FAIL, kể cả HTTP 200; không coi reachable
là bằng chứng hoàn thành tạo nội dung hoặc pipeline thành công.

Nếu Native thành công, chọn Native cho **fixture kiểm thử**, không sửa
cấu hình runtime website hoặc tự triển khai. Native adapter đã có và được
tái sử dụng, vẫn dùng hàng đợi, feature allowlist, cache, rate limit và
SQLite analysis theo Event ID như cũ. Nếu chỉ compatible thành công thì dùng
compatible cho fixture. Không tự thử model khác hoặc downgrade bảo mật.

Nếu cả hai fail, không lặp lại request generate trong pipeline: ghi
pipeline NOT_RUN cùng lý do. Đặc biệt nếu cả hai 404: kết luận
`both_404_model_endpoint_or_access_unavailable`; tổng FAIL và không khẳng
định kết nối tạo nội dung thành công. 404 không đủ phân biệt model đã ngừng,
API version/endpoint, quyền truy cập hoặc cơ chế che tài nguyên của dự án.

## Ý nghĩa kết quả

Report mới: docs/h07/evidence/gemini_compare_<UTC>_<id>/report.json.

- status: kết quả toàn phép đối chứng. Một endpoint còn lỗi thì vẫn FAIL.
- integration_status: kết quả probe JSON + LR/BLOCK/SQLite/Alerts/Gemini/
  Dashboard trên adapter được chọn trong fixture. Có thể PASS trong khi
  status tổng FAIL vì endpoint còn lại 404; không che mất lỗi đó.
- native_model_metadata: tên model, các phương thức được Google trả về và
  generate_content_supported; metadata không thay thế phép gọi generate.
- HTTP error: http_status, upstream_status theo allowlist (NOT_FOUND,
  PERMISSION_DENIED, INTERNAL...), error_format, diagnostic/category và
  retryable. Không lưu thông báo lỗi gốc, header, key hoặc body lỗi.
- Pipeline giữ quy tắc probe phải PASS và tất cả kiểm tra phải PASS; không
  bỏ probe để chuyển FAIL sang PASS. Cảnh báo và BLOCK/403 không phụ thuộc AI.

Fixture dùng port localhost ngẫu nhiên, SQLite và credentials riêng. Model
LR, dataset, SQLite nghiệp vụ chỉ đọc/kiểm tra SHA, không thay thế. Hàng đợi
AI tắt trước kiểm tra tệp benign để không phát sinh lời gọi thứ sáu ngoài
ngân sách. Không gọi Telegram/email, không tự push/merge/deploy.

Chỉ khi integration_status PASS mới có bằng chứng pipeline giải thích hoàn
chỉnh ở run đó. Nội dung AI trên dữ liệu giả lập vẫn cần xem ngữ nghĩa và
không được coi là quyết định bảo vệ hoặc xác nhận khai thác thành công.

Nguồn: [Google model metadata](https://ai.google.dev/api/models),
[generateContent](https://ai.google.dev/api/generate-content),
[OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai).
