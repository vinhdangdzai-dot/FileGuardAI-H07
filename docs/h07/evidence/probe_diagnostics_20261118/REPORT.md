# Probe FAIL và pipeline thành công: đối chiếu bằng chứng

Nguồn bất biến: docs/h07/evidence/gemini_live_20261118T105847Z_e2e2e8/report.json.
Không sửa hoặc chuyển kết quả của run cũ sang PASS. SHA-256 và kiểm tra
encoding của file gốc nằm trong source_audit.json.

## Kết luận từ run thật hiện có

Model thực tế là **gemini-3.5-flash-lite**, adapter **gemini** (OpenAI-compatible),
không phải gemini-2.5-flash hay native. Discovery và 10 kiểm tra chức năng PASS.
Probe FAIL/provider_error sau 6540,8564 ms; pipeline success sau 3241,9548 ms;
download BLOCK 403 sau 83,6870 ms. Tổng thể FAIL là đúng vì probe bắt buộc.

Hai lần gọi dùng cùng đối tượng provider, HTTPS endpoint
https://generativelanguage.googleapis.com/v1beta/openai/chat/completions,
model, timeout 20 giây, max_tokens 2048, prompt, JSON object mode và credential.
Probe gọi trực tiếp; pipeline gọi từ worker qua RecordingProvider và cùng
GeminiProvider.analyze. Không có nhánh tự đổi endpoint/model/token/timeout
giữa hai lần gọi. Pipeline là lời gọi thật, không lấy cache: sidecar fixture mới.

Khác nhau ở bộ đặc trưng giả lập:

| Trường | Probe | Pipeline |
|---|---|---|
| structural_encoding | false | true |
| remaining_decode_changes | 0 | 1 |

Các trường còn lại giống nhau: BLOCK, ml_alert=true, parent_components=1,
absolute_style=false, backslash=false, length_bucket=short. Đây là hai phép
thử khác nhau có chủ ý, không cần ép thành payload giống nhau để đạt PASS.

**Không đủ bằng chứng xác định HTTP status chính xác hoặc nguyên nhân gốc
của lỗi probe cũ.** Code cũ gộp các HTTPError không thuộc 400/401/403/404/429
vào provider_error, rồi bỏ HTTP status/body. Lỗi JSON/schema thông thường
được phân loại invalid_response, không phải provider_error. Lỗi HTTP tạm
thời là một khả năng nhưng không được khẳng định là 500/503, quota, timeout
hay cấu hình sai chỉ vì lần gọi sau thành công. Gọi lại bây giờ cũng không
khôi phục được status của lời gọi lịch sử.

## Sửa chẩn đoán, không hạ tiêu chí nghiệm thu

- ProviderError mang http_status, category và retryable bên cạnh code và
  diagnostic đã làm sạch. Các nhóm: temporary_api, configuration,
  response_processing, unknown_provider. Chỉ gợi ý có thể thử lại, không tự
  gọi lại hoặc xóa kết quả lỗi.
- 408/429/500/502/503/504 và timeout/network được đánh dấu retryable;
  400/401/403/404 phân loại cấu hình theo code; invalid_response thuộc xử lý
  phản hồi. Retryable không chứng minh chính xác nguyên nhân sự cố Google.
- RecordingProvider lưu phase=probe/pipeline, endpoint, model, timeout,
  max_tokens, đặc trưng allowlist, hash body request không chứa key, thời
  gian và metadata phản hồi (status/số byte, không lưu body/header lỗi).
- Probe lỗi có metadata riêng trong report. Mỗi lần gọi có request_attempts
  tương ứng; không dùng lỗi của pipeline để giải thích nhầm probe.
- Không lưu Authorization/x-goog-api-key, exception text hay dữ liệu gốc.
  Không sửa schema SQLite, model, dataset, Security Alerts hoặc quyết định
  chính sách. Các thông tin chẩn đoán mới nằm trong bộ nhớ/report verifier.
- Điều kiện tổng thể vẫn bắt buộc probe PASS, toàn bộ checks PASS và dữ liệu
  được bảo toàn; test riêng chứng minh probe 503 + pipeline success vẫn FAIL.

## Tiếng Việt và ngữ nghĩa

File gốc đọc strict UTF-8 thành công, không BOM, không U+FFFD; các chuỗi
tiếng Việt đúng Unicode và không có các dấu hiệu mojibake đã kiểm tra.
JSON Unicode escapes là cú pháp hợp lệ, không phải lỗi mất dấu. Nếu Terminal
Windows hiển thị sai, đọc bằng `Get-Content -Encoding UTF8 <đường dẫn>` hoặc
mở file bằng VS Code UTF-8. Không sửa/ghi đè file bằng giải mã ngược phỏng đoán.

Nội dung thực: risk=high là nhận định tham khảo; nhận diện mã hóa cấu trúc
và thay đổi giải mã có dữ liệu hỗ trợ. Khuyến nghị kiểm tra/giám sát mang tính
chung, không chứng minh tính đầy đủ. Câu why nối cảnh báo ML với quyết định
chặn có thể gây hiểu nhầm: BLOCK được quyết định bởi chính sách độc lập.
Không đánh dấu lời giải thích là đúng ngữ nghĩa chỉ vì có dấu tiếng Việt.

Prompt mới nêu rõ ML không gây BLOCK/cấp quyền và không khuyến nghị giải mã
URL lặp không kiểm soát. Cache identity chuyển gemini-json-v3 để không dùng
lại giải thích từ prompt cũ. Không sửa kết quả AI lịch sử; vẫn cần đọc và
đánh giá thủ công phản hồi mới, không có bảo đảm LLM luôn diễn giải đúng.

## Kiểm thử và quota

82 mock tests PASS ở mock.stdout.txt, gồm HTTP metadata/ẩn key, UTF-8,
phân loại lỗi response và probe 503/pipeline thành công nhưng tổng thể FAIL.
Pytest toàn bộ: **318 PASS, 0 FAIL, 0 ERROR, 3 SKIP**, 15 subtest PASS;
199,35 giây, exit 0. Log pytest.stdout.txt và pytest.stderr.txt.
Ba SKIP là symlink Windows thiếu quyền ở tests/test_app.py:49,
tests/test_security.py:54 và :66; không chuyển thành PASS.

Không gọi Gemini thật trong đợt sửa này: bằng chứng cũ đã chứng minh pipeline
hoạt động; gọi lại chỉ để đoán nguyên nhân lỗi cũ sẽ tốn quota mà không thể
khôi phục HTTP status đã bỏ. Nếu cần tái hiện, người vận hành dùng verifier
đã cập nhật với key nhập ẩn; vẫn tối đa hai lượt phân tích, hoặc thêm một
metadata request nếu dùng --choose-model. Không bỏ qua probe, không auto retry.

File sửa: app/ai_explanations.py, tools/verify_gemini_live.py.
File mới: tests/test_probe_diagnostics.py, báo cáo này, source_audit.json
và các log/manifest trong thư mục bằng chứng này.
Không commit, push, merge hoặc triển khai VPS.
