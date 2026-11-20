# Báo cáo tích hợp Gemini — 18/11/2026

## Kết quả thực hiện

Tích hợp adapter Gemini thực thi HTTP tới endpoint Google, tái sử dụng hàng
đợi nền, timeout, rate limit, cache, SQLite và định dạng kết quả của dịch vụ
hiện có. Chưa khẳng định kết nối Gemini thành công: môi trường không có
AI_EXPLANATION_API_KEY; workspace không có `.env`. Probe báo NOT_RUN và exit 2.
Không in, lưu hay yêu cầu gửi API key trong cuộc trò chuyện.

Thêm trang chi tiết sự kiện có phân quyền Admin, link từ Event ID Dashboard,
phân tách LR/chính sách/API, cảnh báo giới hạn, chỉ dấu cấu trúc, mức rủi ro
tham khảo có nguồn và khuyến nghị. Trang kế thừa Light/Dark Mode, cỡ chữ và
sidebar hiện có. Nguồn provider/model được lưu cho từng phân tích mới trong
bảng provenance của SQLite sidecar; kết quả lịch sử không có nguồn không
được tự gán sang Gemini. Không xóa dữ liệu hoặc thay mô hình/chính sách.

## Kiểm thử thực tế

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Pytest toàn bộ cuối, `-q -rs` | 267 PASS, 0 FAIL, 0 ERROR, 3 SKIP; 15 subtest PASS; 174,93 giây; exit 0 | pytest-final.stdout.txt / stderr.txt |
| Provider/Gemini regression cuối | 42 PASS, 0 FAIL; 14,32 giây; exit 0 | provider-final.stdout.txt / stderr.txt |
| Acceptance | Cả 6 bước exit 0 | acceptance.stdout.txt; `docs/bao_cao_h07/evidence/20261118T092951Z_401927/summary.json` |
| Pytest bên trong acceptance | 264 PASS, 3 SKIP; 15 subtest PASS; 164,78 giây | thư mục acceptance, pytest.stdout.txt |
| Dashboard TCP | 41 PASS, 0 FAIL | thư mục acceptance, dashboard_tcp.stdout.txt |
| Download TCP | 33 PASS, 0 FAIL, 3 SKIP | thư mục acceptance, download_tcp.stdout.txt |
| Chrome headless 157.0.8103.78 | 466 PASS, 0 FAIL; không JavaScript/static error | `docs/ui/browser_20261118T093224Z_3f9962/results.json` |
| Trang sự kiện 1440/768/390px × Light/Dark | 18 kiểm tra PASS về theme, giải thích fixture và không tràn ngang | cùng results.json; 6 ảnh event_detail_fixture_*.png |
| Gemini thật | **NOT_RUN**, thiếu key/model trong môi trường; không phải PASS | live-probe.stdout.txt; exit 2 |
| Bảo toàn dữ liệu | SHA-256 dataset, model triển khai, model thử nghiệm, SQLite nghiệp vụ đều không đổi | protected_unchanged trong summary.json và browser results.json |

Acceptance được chạy trước khi bổ sung ba trường hợp regression cho cấu hình
Gemini lúc tạo app; vì vậy số pytest trong acceptance là 264, lượt toàn bộ
cuối là 267. Không cộng gộp hai lượt chạy hoặc cộng subtest vào số testcase.

Ba SKIP pytest là các bài symlink sẵn có: tests/test_app.py:49,
tests/test_security.py:54 và :66, thiếu quyền tạo symlink trên Windows.
Symlink probe có exit 0 nhưng các trường hợp thiếu quyền vẫn là SKIP, không
đánh dấu PASS. Không biến FAIL thành SKIP.

Lượt trình duyệt ban đầu chưa chạy được do Playwright không import được;
log browser*.stderr.txt giữ nguyên. Cài Playwright vào thư mục kiểm thử riêng
`.verification/gemini_browser_lib` rồi chạy Chrome với quyền vượt sandbox đã
được công cụ chấp thuận; không sửa ACL hệ thống hoặc cài dependency vào
runtime ứng dụng. Lệnh browser cuối dùng Python thêm thư mục đó vào sys.path,
import playwright.sync_api trước khi chạy tools/verify_ui_browser.py với
`--software-rendering --browser .verification/chrome_for_testing/157.0.8103.78/chrome-win64/chrome.exe`.
Ảnh và phân tích trong browser dùng provider fixture được ghi rõ trong ảnh
và results.json, không phải phản hồi Gemini thật. Toàn bộ log cũ được giữ lại.

## Phạm vi kiểm thử mock

Kiểm tra endpoint/header/body Gemini, prompt tiếng Việt, không gửi đường dẫn,
IP, token hoặc key trong body; lỗi timeout, mất mạng, 401/403, 429, JSON lỗi,
phản hồi bị cắt và echo key. Kiểm tra cấu hình môi trường, offline khi thiếu
key/model, SQLite Event ID, sự kiện ngoài 20 dòng gần nhất, CSRF bật/tắt,
Guest/Auditor bị từ chối, XSS được escape, HTTP 200/403/404 và API không sửa
quyết định bảo vệ. Bộ test dịch vụ hiện có tiếp tục kiểm tra giới hạn, cache,
sidecar outage và tác vụ nền không giữ request tải tệp chờ API.

## File tạo hoặc sửa

| File | Thay đổi |
|---|---|
| app/ai_explanations.py | GeminiProvider; validate finish_reason; chuẩn hóa lỗi; provenance; snapshot theo Event ID |
| app/web.py | Chọn adapter qua môi trường; route chi tiết sự kiện chỉ Admin |
| app/templates/event_detail.html | Trang phân tích sự kiện mới |
| app/templates/dashboard.html | Liên kết Event ID |
| app/templates/_ai_analysis.html | Provider/model và liên kết chi tiết |
| app/templates/base.html | Trang chi tiết dùng sidebar quản trị |
| .env.example | Hướng dẫn cấu hình Gemini, không chứa key thật |
| tests/test_gemini.py | 15 testcase mới, mock và tích hợp Flask |
| tools/check_gemini_connection.py | Probe thật chủ động, đầu ra đã giới hạn, không chạm SQLite |
| tools/ui_ai_analysis_checks.py | 18 kiểm tra trang chi tiết và 6 ảnh responsive/theme |
| docs/h07/GEMINI_INTEGRATION.md | Cấu hình, kiến trúc, quyền, dữ liệu và hướng dẫn vận hành |
| docs/h07/evidence/gemini_20261118/ | Báo cáo này, log kiểm thử và manifest |

Các thư mục bằng chứng được tạo thêm bởi công cụ có sẵn:

- docs/bao_cao_h07/evidence/20261118T092951Z_401927/
- docs/evidence/tcp_20261118T093248Z_19b7d5/
- docs/h07/evidence/20261118T093254Z_0f7705/
- docs/ui/browser_20261118T093224Z_3f9962/
- docs/evaluations/dashboard_http_20261116T172733Z_800c38_http_6f822fa988ea.json

Thư mục evidence/proxy_fix_20261117 đã tồn tại trước đợt này, không phải
bằng chứng Gemini. Không commit, push, merge hoặc triển khai VPS.

## Cách chạy và giới hạn

Xem `docs/h07/GEMINI_INTEGRATION.md`: cấu hình môi trường, chạy `python run.py`,
đăng nhập Admin, bật Phân tích AI, nhấn Event ID. Sau khi cấu hình key/model,
chạy `python tools/check_gemini_connection.py` để kiểm chứng kết nối Google.
Model phải được cấp quyền trong dự án Google của người vận hành.

Chưa đo chất lượng giải thích tiếng Việt hoặc khả năng tương thích với một
model Gemini cụ thể bằng API thật. Mock chỉ chứng minh hợp đồng và xử lý lỗi.
Timeout tối đa 10 giây, giới hạn output 2048 token có thể không phù hợp model
suy luận lâu; phản hồi thiếu bị từ chối. Coarse features không đủ kết luận
xâm nhập, thoát symlink hoặc ngữ nghĩa đường dẫn. API có thể thiếu/sai; không
quyết định quyền tải. Probe live chủ động có thể tính phí một lượt API và
không dùng quota tracker SQLite của ứng dụng.
