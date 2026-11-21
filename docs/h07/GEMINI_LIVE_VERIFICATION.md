# Nhập key an toàn và xác minh Gemini thật

## Adapter native bổ sung

Ngoài OpenAI-compatible, có adapter `gemini-native` dùng API chính thức
`POST /v1beta/models/{model}:generateContent`, xác thực bằng header
`x-goog-api-key` (không đặt key trong URL). Dùng JSON MIME, maxOutputTokens,
kiểm tra finishReason=STOP và bỏ các phần thought trước khi kiểm tra schema.
Không tự fallback hoặc thay model.

Với key mới đã thay thế key từng gửi qua chat, kiểm tra native trong Terminal:

```powershell
$env:AI_EXPLANATION_MODEL = 'gemini-2.5-flash'
..\.venv\Scripts\python.exe tools/verify_gemini_live.py --prompt-key --native
```

Nếu model trả 404, dùng thêm `--choose-model` để chọn từ danh sách native
Google trả về (chỉ liệt kê model có generateContent trên trang metadata đầu).
Không khẳng định gemini-2.5-flash còn khả dụng cho mọi dự án.
Để launcher local dùng native, đặt `$env:AI_EXPLANATION_PROVIDER = 'gemini-native'`
trước khi chạy tools/run_with_gemini.py. Không dùng lại key đã lộ trong chat;
thu hồi và tạo key mới trong Google AI Studio. Không có key thật trong source.

Nguồn: [Google API keys](https://ai.google.dev/gemini-api/docs/api-key),
[GenerateContent](https://ai.google.dev/api/generate-content).

## Nhập trong Terminal VS Code

Mở Terminal tương tác ở thư mục `FileGuardAI_H07`, chạy:

```powershell
..\.venv\Scripts\python.exe tools/verify_gemini_live.py --prompt-key
```

Nếu chưa có biến môi trường, chương trình hỏi API key bằng `getpass` (ẩn
hoàn toàn, không hiện dấu sao), sau đó hỏi model ID được dự án Google của bạn
cấp quyền. Không nhập key vào tham số lệnh, chat, source code, `.env.example`
hoặc Git. Không có fallback đọc hiện rõ: nếu Terminal không hỗ trợ nhập ẩn,
chương trình từ chối chạy. Không chạy qua Output panel/pipe hay ghi phiên
terminal bằng công cụ bên ngoài khi nhập bí mật.

Key được đặt tạm trong môi trường tiến trình verifier, không lưu vào file,
không cập nhật biến môi trường Windows toàn hệ thống và được bỏ khỏi môi
trường khi kết thúc nếu do chương trình vừa nhập. Đây không phải cơ chế bảo
đảm xóa byte trong bộ nhớ Python; các tiến trình/công cụ có đặc quyền đọc bộ
nhớ vẫn nằm ngoài phạm vi bảo vệ. Không thay mật khẩu/SECRET_KEY của website.

Chọn đúng ID text model trong Google AI Studio; không tự chọn model thay
thế khi API từ chối. Không cần dán key vào chat. Khi hoàn tất chỉ gửi lại
đường dẫn `Evidence` hoặc thông báo đã chạy để đọc báo cáo trong workspace.

Nếu đã cấu hình môi trường ở tiến trình hiện tại, có thể bỏ `--prompt-key`.
Thiếu key/model sẽ tạo báo cáo **NOT_RUN**, exit 2, không gọi mạng Google.

## Verifier thực hiện những gì

Nếu model cũ trả 404, có thể lấy danh sách từ chính Google và chọn bằng số:

```powershell
..\.venv\Scripts\python.exe tools/verify_gemini_live.py --prompt-key --choose-model
```

Cờ này thêm **một request metadata GET /v1beta/openai/models** (không gửi dữ
liệu sự kiện), rồi cho người vận hành chọn model text/chat trong danh sách.
Tổng tối đa ba request Google khi dùng cờ, trong đó tối đa hai request sinh
giải thích. Không tự chọn model thay thế hoặc thử hàng loạt. Danh sách trả
về không bảo đảm mọi model đều hỗ trợ Chat Completions/quota của dự án; lỗi
thật vẫn phải ghi FAIL. `--prompt-key` yêu cầu nhập lại key ẩn, thay vì vô
tình dùng một key cũ đã có trong môi trường của Terminal.

Tối đa **hai lời gọi Gemini**: probe đặc trưng giả lập và một phân tích nền
từ request traversal giả lập trong ứng dụng fixture. Thao tác này có thể
tính quota/chi phí API thật. Không retry vô hạn, không thử hàng loạt model.
Probe không dùng quota tracker của ứng dụng; lần phân tích nền dùng tracker
SQLite fixture. Ngay cả khi probe báo lỗi, verifier kiểm tra thêm luồng nền
để ghi nhận BLOCK/cảnh báo vẫn được giữ khi API lỗi.

1. Gửi probe HTTPS tới endpoint OpenAI-compatible cố định của Google.
2. Tạo Flask/SQLite/hash đăng nhập tạm trong `.test_runtime_*`, không chạy
   production app hay sử dụng SQLite nghiệp vụ. Đọc model LR triển khai ở
   chế độ read-only, không huấn luyện hoặc thay artifact.
3. Đăng nhập Admin fixture qua TCP localhost với mật khẩu ngẫu nhiên chỉ
   trong bộ nhớ; kiểm tra CSRF/session thực tế.
4. Gửi traversal mã hóa tổng hợp, kiểm tra HTTP 403, access_logs BLOCK và
   Security Alert đã được commit trước khi chờ phân tích API.
5. Chờ tác vụ Gemini, đọc analysis/provenance/timing theo đúng Event ID.
6. Đọc lại Dashboard/Event Detail qua TCP, kiểm tra render lời giải thích và
   thời gian; xác minh AI không sửa BLOCK/403, tệp hợp lệ vẫn tải 200.
7. So sánh SHA-256 dataset/model/SQLite nghiệp vụ trước và sau.

Chỉ decision, ml_alert, số thành phần cha, cờ absolute/backslash/encoding,
số lớp decode và length_bucket ra Google. Adapter kiểm tra allowlist, kiểu
và miền giá trị ngay trước HTTP; trường path/IP/token hoặc chuỗi ngoài enum
bị từ chối. Không gửi Event ID, IP client, tên tệp, raw path, mật khẩu, token
người dùng hay nội dung tệp. Authorization header chỉ chứa API key dịch vụ
để xác thực. Google vẫn thấy IP mạng của máy chủ gửi request.

## Hợp đồng và cấu hình Gemini

Endpoint: `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`.
Key đọc từ `AI_EXPLANATION_API_KEY`, model từ `AI_EXPLANATION_MODEL`.
Không đặt key trong URL/query. Không theo HTTP redirect sang host khác.

- `AI_EXPLANATION_TIMEOUT`: Gemini mặc định 20 giây, giới hạn 0,1–60 giây;
  adapter OpenAI-compatible chung giữ giới hạn 10 giây cũ. Đây là socket
  timeout cho thao tác mạng, không cam kết deadline cứng cho mọi kiểu stream.
- `AI_EXPLANATION_MAX_TOKENS`: 256–8192, mặc định 2048. Một số model dùng
  ngân sách suy luận trước khi tạo JSON; nếu bị cắt thì bị từ chối, không
  cố sửa JSON thiếu. Có thể điều chỉnh trong Terminal (không phải key):

  ```powershell
  $env:AI_EXPLANATION_TIMEOUT = '45'
  $env:AI_EXPLANATION_MAX_TOKENS = '4096'
  ```

- `response_format={type:json_object}`, prompt yêu cầu các trường
  why/traversal_type/risk/recommendations bằng tiếng Việt (risk dùng enum
  low/medium/high/unknown). Bỏ `store` của adapter OpenAI chung.
- Chỉ chấp nhận object JSON đúng schema/kiểu/độ dài, finish_reason=stop;
  không nhận markdown, JSON thiếu hoặc nội dung chứa key dịch vụ.
- 400 → invalid_request, 404 → model_unavailable; 401/403 → authentication,
  429 → quota; timeout/network/invalid_response/provider_error tách riêng.
  Không lưu exception text, error body, request headers hoặc key vào log.
- Cache identity có version và giới hạn token, tránh dùng nhầm kết quả từ
  cấu hình Gemini cũ. Pending TTL tính theo timeout để không gọi trùng hoặc
  báo interrupted sớm khi model còn đang xử lý bình thường.

Nguồn: [Google OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai).
Hỗ trợ của model/quyền/quota thực tế chỉ được xác minh khi gọi API với cấu
hình dự án của người vận hành; đọc tài liệu hoặc mock không chứng minh được.

## Kết quả và giới hạn đánh giá nội dung

Mỗi lần verifier tạo thư mục `docs/h07/evidence/gemini_live_<UTC>_<id>/`
với report.json. Không ghi đè run cũ. Report gồm chế độ LIVE_GOOGLE_API,
PASS/FAIL/NOT_RUN, checks riêng, hai kết quả phân tích trên dữ liệu giả lập,
HTTP/Alert/Event ID, thời gian, đặc trưng đã gửi và hash bảo toàn.

- Exit 0: probe, API nền, SQLite, render và bất biến bảo vệ đều PASS.
- Exit 1: ít nhất một kiểm tra FAIL; ví dụ quota vẫn có BLOCK/cảnh báo PASS
  nhưng kiểm tra Gemini phải FAIL, không che thành SKIP.
- Exit 2: chưa chạy do thiếu cấu hình/Terminal an toàn hoặc người dùng ngắt.

Heuristic dấu tiếng Việt chỉ là quan sát từng trường, không phải kiểm chứng
ngôn ngữ/ngữ nghĩa. `human_review_required=true` luôn được ghi để người đọc
xem nguyên nhân, dấu hiệu, mức rủi ro và khuyến nghị; không suy ra khai thác
thành công/thoát symlink từ cờ cấu trúc. Các báo cáo mock trong Pytest mang
mode MOCK_ONLY và không được dùng để tuyên bố kết nối Google thành công.

Thời gian API lưu ở bảng analysis_timings của sidecar, dùng perf_counter
cho duration_ms, tách thời gian HTTP và thời gian chờ hàng đợi. Dashboard và
Event Detail hiển thị số đo khi có; cache/dữ liệu cũ không được tự điền số.
Trang lấy snapshot khi tải lại; Security Alerts polling vẫn hoạt động riêng.

## Chạy website với key nhập ẩn

Sau khi verifier thành công, nếu muốn chạy bản local với cùng cách nhập ẩn:

```powershell
..\.venv\Scripts\python.exe tools/run_with_gemini.py
```

Launcher dùng `run.py` hiện có, bind localhost như cũ; không auto bật giải
thích hoặc deploy. Admin vào Dashboard → Phân tích AI → Bật để cho phép gửi
đặc trưng. Sau khi đóng launcher, key không được lưu cho phiên Terminal sau;
phải nhập lại hoặc dùng biến môi trường do người vận hành quản lý.

Không tự push GitHub, thay SQLite nghiệp vụ bằng fixture hoặc triển khai VPS.
