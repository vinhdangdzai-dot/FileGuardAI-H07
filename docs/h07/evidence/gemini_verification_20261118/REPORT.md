# Xác minh Gemini thật — 18/11/2026

## Phạm vi đã sửa

- Rà soát Gemini OpenAI-compatible adapter, giữ endpoint Google cố định và
  Bearer header, không dùng key trong URL, không theo redirect.
- Thêm allowlist/kiểu/miền giá trị ngay trước HTTP; không nhận thêm path,
  IP, tên tệp, token hoặc dữ liệu nhạy cảm từ caller.
- Gemini timeout mặc định 20 giây, cấu hình tối đa 60 giây; max_tokens
  256–8192, mặc định 2048; giữ JSON object và schema validator. Không tự
  đổi model, retry vô hạn hoặc khôi phục JSON bị cắt.
- Kiểm tra key không xuất hiện trong model/endpoint để tránh nhập nhầm key
  vào trường model rồi lưu vào provenance/report. Không log giá trị key.
- Phân loại HTTP 400/404 và mã lỗi Google an toàn: authentication, quota,
  invalid_request, model_unavailable, timeout, network, invalid_response.
  Chỉ lưu mã chẩn đoán cố định, không lưu body lỗi/headers/exception text.
- Thêm analysis_timings trong SQLite sidecar, không ALTER/xóa bảng cũ;
  lưu started/completed/duration_ms đo bằng perf_counter quanh provider.
  Dashboard/Event Detail hiển thị thời gian tách khỏi HTTP download.
  Cache/dữ liệu cũ không được tự gán số đo mới.
- Pending TTL tính theo timeout để không gọi trùng hoặc báo interrupted
  quá sớm với Gemini xử lý dài hơn 30 giây.
- Thêm verifier nhập key ẩn bằng getpass, không fallback echo; key chỉ trong
  môi trường tiến trình. Tạo SQLite/credentials/server TCP riêng, không
  dùng SQLite nghiệp vụ. Launcher nhập ẩn chạy run.py hiện có khi người dùng
  chủ động gọi, không tự bật AI, không tự deploy.
- Thêm --choose-model: một metadata GET từ Google, cho người vận hành chọn
  ID thật bằng số, không tự đoán/thay thế model khi gặp 404.

## Phân biệt bằng chứng thật và mock

### API thật: đã nhận phản hồi lỗi, chưa có giải thích thành công

Các run do người vận hành nhập key trong Terminal, không gửi key qua chat:

| Run | Kết quả thực tế |
|---|---|
| gemini_live_20261118T101714Z_62190e | NOT_RUN: chưa có key/model; không gọi Google |
| gemini_live_20261118T102131Z_fc7a35 | NOT_RUN: cấu hình hoặc Terminal chưa hợp lệ |
| gemini_live_20261118T102236Z_e1640d | FAIL: probe và pipeline nhận HTTP 400 / invalid_request, model gemini-2.5-flash |
| gemini_live_20261118T102729Z_1c938c | FAIL: probe và pipeline nhận HTTP 404 / model_unavailable, model gemini-2.5-flash |
| gemini_live_20261118T102804Z_6f3837 | NOT_RUN: invalid_api_key_format; không gọi API |
| gemini_live_20261118T102847Z_0940fc | FAIL: model_unavailable ở probe và pipeline |

Run gemini_live_20261118T103037Z_ddcfb2 được tạo nhưng chưa có report.json ở
thời điểm ghi bảng này: chưa được đánh dấu PASS/FAIL hoặc xem là thành công.
Cần người vận hành hoàn tất Terminal và kiểm tra báo cáo của chính run đó.
Nếu có run mới hơn, lấy kết quả trực tiếp trong report.json, không suy diễn.

Ở các run API lỗi đã hoàn tất, các kiểm tra thực tế vẫn PASS:

- Admin fixture đăng nhập qua TCP localhost.
- Traversal mã hóa trả BLOCK/403; access_logs và Security Alert đã lưu.
- Thời gian provider (kể cả lời gọi lỗi) được lưu ở sidecar.
- Dashboard và Event Detail vẫn trả 200 khi API lỗi.
- Quyết định BLOCK và Alert giữ nguyên; tệp hợp lệ vẫn tải HTTP 200.
- Chỉ allowlisted coarse features đi tới provider.
- Dataset, model triển khai và SQLite nghiệp vụ giữ SHA-256 trước/sau.

Không có bằng chứng thành công về nội dung tiếng Việt, mức rủi ro hoặc
khuyến nghị từ Google ở các run trên. Không dùng mock thay cho phần còn
thiếu này. Các lỗi 400/404 ban đầu không đủ để suy ra key sai: adapter đã
được bổ sung phân loại metadata an toàn để phân biệt lỗi key và request ở
lượt chạy mới, không tự gán nguyên nhân cho dữ liệu lỗi cũ đã bỏ body.

### Kiểm thử tự động không gọi Gemini thật

- Lượt acceptance: 298 PASS, 0 FAIL, 0 ERROR, 3 SKIP; 15 subtest PASS;
  184,72 giây. Cả sáu bước pytest/dashboard_tcp/download_tcp/performance/
  symlinks/audit exit 0. Bằng chứng:
  docs/bao_cao_h07/evidence/20261118T101812Z_b148f0/.
- Lượt Pytest sau bổ sung guard/Google error parsing: 302 PASS, 3 SKIP,
  15 subtest PASS; 98,81 giây, xem pytest-final.stdout.txt.
- Provider/CLI regression sau bổ sung model discovery: 69 PASS, 0 FAIL,
  xem focused-models.stdout.txt. Gồm transport mock, nhập ẩn, key không
  xuất hiện trong report, error mapping, timing, đọc sidecar cũ và ba luồng
  TCP success/quota/network với provider fixture.
- Chrome: 475 PASS, 0 FAIL, không JavaScript/static error. Bằng chứng:
  docs/ui/browser_20261118T101828Z_524cf5/results.json. Giải thích trong ảnh
  là fixture đã ghi rõ, không phải Google Gemini thật. Layout Light/Dark,
  responsive, thông báo, CSRF và phân quyền tiếp tục được kiểm tra.

Ba SKIP pytest là symlink Windows thiếu quyền, không đổi FAIL thành SKIP
hoặc ghi PASS cho trường hợp chưa chạy. Số liệu từng lượt không cộng gộp.
Lượt Pytest đầy đủ sau cùng: **305 PASS, 0 FAIL, 0 ERROR, 3 SKIP**, cùng
15 subtest PASS, 213,27 giây; log pytest-models-final.stdout.txt. Đây là kết
quả hoàn tất sau khi bổ sung ba testcase discovery/nhập key đè môi trường.

## Cách tiếp tục trên máy người vận hành

Trong Terminal VS Code tại thư mục FileGuardAI_H07:

```powershell
..\.venv\Scripts\python.exe tools/verify_gemini_live.py --prompt-key --choose-model
```

Nhập key ở prompt ẩn, không nhìn thấy ký tự là bình thường. Chọn số của một
model text/chat Google thực sự trả về. Cờ này gọi thêm một request metadata,
ngoài tối đa hai request sinh giải thích. Nếu Google từ chối key/quota/model,
báo cáo phải FAIL, không tự retry liên tục hoặc loại bỏ chính sách bảo vệ.
Nếu cần tăng ngân sách cho model suy luận, cấu hình timeout/max_tokens qua
môi trường theo hướng dẫn; không tự thay model triển khai LR.

Sau khi verifier thành công, launcher cho website local:

```powershell
..\.venv\Scripts\python.exe tools/run_with_gemini.py
```

Admin bật giải thích riêng trên Dashboard. Launcher không lưu key cho lần
chạy sau, không thay password/SECRET_KEY, không tự push/deploy VPS.

Hướng dẫn chi tiết: docs/h07/GEMINI_LIVE_VERIFICATION.md.

## File tạo/sửa trong đợt xác minh

| File | Thay đổi |
|---|---|
| app/ai_explanations.py | Feature validation, Gemini limits, model metadata, sanitized errors, timing/pending TTL |
| app/web.py | Đọc timeout/max_tokens Gemini từ môi trường |
| app/templates/_ai_analysis.html | Hiển thị thời gian provider trên Dashboard |
| app/templates/event_detail.html | Thời gian và hướng dẫn lỗi request/model |
| .env.example | Tham số token, không chứa key |
| tools/verify_gemini_live.py | Nhập ẩn, discovery, probe thật + pipeline TCP tách dữ liệu, report |
| tools/run_with_gemini.py | Launcher nhập key ẩn, dùng run.py sẵn có |
| tests/test_gemini_live.py | Regression privacy, errors, timing, CLI và TCP mock |
| docs/h07/GEMINI_LIVE_VERIFICATION.md | Các bước an toàn và phạm vi xác minh |
| docs/h07/GEMINI_INTEGRATION.md | Đồng bộ timeout/token và link hướng dẫn |
| docs/h07/AUTOMATIC_ALERTS.md | Đồng bộ giới hạn Gemini mới |
| docs/h07/evidence/gemini_verification_20261118/ | Log và báo cáo đợt này |

Các thay đổi Alerts/Gemini chưa commit từ đợt trước được giữ nguyên. Không
push/merge, không triển khai VPS, không sửa dataset/model hoặc xóa bằng chứng.

Nguồn: [Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai),
[Google API errors](https://ai.google.dev/gemini-api/docs/api-errors).
