# Bổ sung Gemini native

Thêm GeminiNativeProvider dùng generateContent và x-goog-api-key; không
đưa key vào URL, source, HTML hoặc JavaScript. Giữ GeminiProvider OpenAI-
compatible; không tự chuyển adapter hay đổi model khi lỗi. Cấu hình model
gemini-2.5-flash được giữ theo lựa chọn người vận hành, không khẳng định còn
khả dụng cho dự án này khi chưa kiểm chứng bằng một lời gọi thành công.

Model/feature allowlist, timeout, token budget, NoRedirect, schema validation,
key echo rejection và xử lý lỗi dùng lại dịch vụ hiện có. Native kiểm tra
finishReason STOP, bỏ phần thought và yêu cầu JSON đúng bốn trường. Native
model discovery dùng GET models với x-goog-api-key và chỉ lấy các mục hỗ trợ
generateContent trên trang metadata đầu; không gửi dữ liệu sự kiện.

Không lưu hoặc sử dụng lại credential được gửi trong chat. Credential đó
cần được thu hồi và thay mới ở Google AI Studio. Không có lượt gọi native
thật được thực hiện trong đợt bổ sung này; kết quả native bên dưới là mock.

File sửa: app/ai_explanations.py, app/web.py, tools/verify_gemini_live.py,
tools/run_with_gemini.py, docs/h07/GEMINI_LIVE_VERIFICATION.md.
File mới: tests/test_gemini_native.py và báo cáo này.

Mock provider/Gemini/native: 75 PASS, 0 FAIL (native.stdout.txt).
Regression native/live helper cuối: 33 PASS, 0 FAIL (native-final.stdout.txt).
Pytest toàn bộ: 311 PASS, 0 FAIL, 0 ERROR, 3 SKIP; 15 subtest PASS;
180,23 giây. Log pytest-native.stdout.txt và pytest-native.stderr.txt.
Ba SKIP là các bài symlink Windows thiếu quyền, không được đổi thành PASS.

Lệnh người vận hành chạy với key mới trong Terminal VS Code:

```powershell
$env:AI_EXPLANATION_MODEL = 'gemini-2.5-flash'
..\.venv\Scripts\python.exe tools/verify_gemini_live.py --prompt-key --native
```

Nếu model trả 404, người vận hành có thể dùng --choose-model để chọn từ
danh sách Google thực sự trả về. Không sửa ALLOW/BLOCK/MISS, không thay LR,
dataset hoặc SQLite nghiệp vụ, không push/merge/deploy.

Nguồn chính thức: [API keys](https://ai.google.dev/gemini-api/docs/api-key),
[GenerateContent](https://ai.google.dev/api/generate-content).
