# Đối chứng lỗi Gemini 404 — 18/11/2026

## Bằng chứng và giới hạn kết luận

Nguồn: docs/h07/evidence/gemini_live_20261118T111736Z_59c64d/report.json.
SHA-256 được lưu trong source_audit.json; không sửa kết quả cũ.

Model gemini-2.5-flash-lite có trong model_discovery của OpenAI-compatible,
nhưng cả probe và pipeline đều HTTP 404/model_unavailable. Endpoint là
https://generativelanguage.googleapis.com/v1beta/openai/chat/completions,
timeout 20 giây, max_tokens 2048. BLOCK/403, SQLite, Alert và Dashboard vẫn
hoạt động. Bằng chứng này chưa có lời gọi Native generateContent cùng key;
catalog PASS không chứng minh quyền/phương thức generate khả dụng.

Không thể xác định từ run cũ liệu lỗi nằm ở tầng tương thích, model ngừng
hoạt động, API version hay quyền truy cập. Không khẳng định đã sửa thành công
kết nối Google bằng cách chỉ sửa code hoặc chạy mock.

## Thay đổi trực tiếp

- Tái sử dụng GeminiNativeProvider sẵn có; không xây lại dịch vụ. Native dùng
  x-goog-api-key và generateContent; compatible dùng Bearer và Chat Completions.
- Bổ sung probe tạo nội dung tối giản cho cả hai adapter, cùng câu yêu cầu
  `Reply with OK.`, cùng key/model và giới hạn 256 output token; không JSON
  mode/system prompt trong phép thử tối giản.
- Bổ sung GET metadata đúng model Native, ghi supportedGenerationMethods
  được Google trả về, thay vì suy khả năng generate từ catalog tên model.
- Dùng chung hàm xử lý HTTPError: lưu HTTP status, RPC status theo allowlist,
  diagnostic/category/retryable và dạng error body. Không lưu message/body
  lỗi, headers hoặc key. HTTP 404 vẫn FAIL, không auto retry.
- Công cụ tools/compare_gemini_apis.py nhận key ẩn một lần và tạo hai provider
  với cùng chuỗi key/model trong bộ nhớ, không lưu key hay hash key.
- Giới hạn cứng 5 lần open HTTP cho cả hai transport, có khóa giữa thread.
  Request lỗi cũng tiêu tốn ngân sách; request thứ sáu bị chặn trước mạng.
- 2 request generate tối giản + 1 request metadata. Khi có endpoint thành
  công, thêm 2 request probe JSON và pipeline production-format trong Flask
  fixture. Không thay config triển khai; không tự đổi model.
- Nếu Native thành công thì chọn Native cho fixture. Nếu chỉ compatible
  thành công thì chọn compatible. Nếu cả hai fail thì pipeline NOT_RUN,
  không gọi lặp lại model đã lỗi để tiết kiệm quota.
- Nếu cả hai 404 thì conclusion=both_404_model_endpoint_or_access_unavailable,
  status=FAIL, không tuyên bố kết nối generate thành công.
- Tách status toàn phép đối chứng khỏi integration_status của adapter đã
  chọn. Native pipeline PASS nhưng compatible 404 vẫn giữ comparison FAIL;
  không che nhánh lỗi. Probe JSON trong pipeline vẫn bắt buộc PASS.

Không sửa Logistic Regression, dataset, schema SQLite, Security Alerts hay
chính sách ALLOW/BLOCK/MISS. Chỉ dữ liệu fixture được tạo trong các test.

## Kiểm thử đã chạy, chưa dùng API thật

- Mock provider/protocol hồi quy ban đầu: 91 PASS, 0 FAIL, 29,50 giây.
- Sau thêm request budget: 92 PASS, 0 FAIL, 30,75 giây.
- Bộ đối chứng cuối: 11 PASS, 0 FAIL, 7,44 giây. Bao gồm kiểm thử đầy đủ
  Native parser/request → Flask TCP → log/Alert SQLite → Gemini schema mock
  → Dashboard với compatible 404. Chính xác 5 request giả lập, không có
  Google network call, không dùng key thật.
- Acceptance: cả sáu bước exit 0 tại
  docs/bao_cao_h07/evidence/20261118T112851Z_1548a5/summary.json.
  Pytest trong acceptance: 327 PASS, 0 FAIL, 0 ERROR, 3 SKIP; 15 subtest
  PASS; 193,18 giây. Các testcase budget/TCP cuối được bổ sung sau lượt này.
- Protected SHA-256 trong acceptance đều không đổi: dataset, model triển
  khai, model thử nghiệm cũ và SQLite nghiệp vụ. Không huấn luyện lại model.
- Lượt Pytest cuối: **329 PASS, 0 FAIL, 0 ERROR, 3 SKIP**, 15 subtest PASS;
  197,15 giây, exit 0. Log pytest-final.stdout.txt và pytest-final.stderr.txt.

Ba SKIP trong acceptance là symlink Windows thiếu quyền ở tests/test_app.py:49,
tests/test_security.py:54 và :66. Không đổi SKIP thành PASS hoặc FAIL thành SKIP.

Môi trường Codex chưa có AI_EXPLANATION_API_KEY. Lệnh không prompt đã chạy
thử và ghi NOT_RUN/exit 2 (gemini_compare_20261118T112857Z_5f3d44), không gọi
Google. Chưa có bằng chứng Native thật cùng key cho run 404 trong đợt này.
Không dùng lại credential từng gửi qua chat hoặc tự tìm key ngoài cấu hình.

## Phép thử thật cần người vận hành nhập key

Tại thư mục FileGuardAI_H07 trong Terminal VS Code:

```powershell
..\.venv\Scripts\python.exe tools/compare_gemini_apis.py --prompt-key --model gemini-2.5-flash-lite
```

Key nhập ẩn, không xuất ra chat. Lệnh tối đa 5 request, nếu cả hai generate
404 thì chỉ 3 request và dừng. Report mới ở docs/h07/evidence/gemini_compare_*.
Chỉ đọc kết quả thật trong report để kết luận nhánh nào hoạt động. Đầu ra
generate tối giản không được lưu; pipeline chỉ lưu giải thích trên đặc trưng
giả lập đã được kiểm tra schema, không có dữ liệu cá nhân gửi đi.

Nếu Native JSON pipeline thật PASS, người vận hành có thể cấu hình
AI_EXPLANATION_PROVIDER=gemini-native và dùng launcher hiện có; đợt sửa này
không tự chạy production app hoặc thay cấu hình đó. Nếu Native cũng 404,
cần kiểm tra model/API version/quyền dự án ở Google; code không vượt được
quyền truy cập hoặc phục hồi model đã ngừng.

## File tạo/sửa

| File | Nội dung |
|---|---|
| app/ai_explanations.py | Minimal probes, model metadata và HTTP/RPC diagnostics đã làm sạch |
| tools/compare_gemini_apis.py | Công cụ đối chứng key/model và hard request budget |
| tests/test_gemini_comparison.py | 11 regression tests, gồm pipeline TCP Native |
| docs/h07/GEMINI_ENDPOINT_COMPARISON.md | Hướng dẫn và cách đọc kết quả |
| docs/h07/evidence/gemini_compare_fix_20261118/ | Báo cáo, audit, request profiles và logs |

tools/verify_gemini_live.py, app/web.py và Native adapter hiện có được tái
sử dụng; không thay cơ chế đăng nhập, CSRF, phân quyền hay quyết định tải.
Các sửa đổi chưa commit từ các đợt trước giữ nguyên. Không commit, push,
merge hoặc deploy VPS.

Nguồn: [Model metadata](https://ai.google.dev/api/models),
[Native generateContent](https://ai.google.dev/api/generate-content),
[OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai).
