# Light / Dark / Theo hệ thống — FileGuardAI-H07

Nhánh `h07/cybersecurity-ui`, PR#2; tiếp nối32dbe34. Không thay backend/endpoints, Path Traversal, ALLOW/BLOCK/MISS, CSRF/session/role, dữ liệu hoặc models. Kết quả cũ giữ nguyên, chỉ thêm bằng chứng mới.

## Sử dụng và thiết kế

Thanh điều hướng có nút mặt trời/mặt trăng **Giao diện**, với3 lựa chọn Sáng/Tối/Theo hệ thống. Mặc định Theo hệ thống. Chuyển ngay trong cùng document, không tải lại hoặc gọi API. Lưu key `fg-theme` trong localStorage cùng origin; không lưu credential hoặc session. Khi chọn Theo hệ thống, giao diện theo thay đổi OS trực tiếp; lựa chọn Sáng/Tối ghi đè OS. Đồng bộ các tab bằng storage event.

Script `theme.js` đồng bộ trước các stylesheet: lựa chọn đã lưu được áp dụng trước CSS/paint; không đợi DOMContentLoaded mới chọn màu. Loader có fallback khi storage bị chặn hoặc giá trị không hợp lệ; khi storage bị chặn chỉ đổi trong trang và trang mới trở lại Theo hệ thống, không hứa lưu được trạng thái. Tắt JS vẫn dùng giao diện dark và native forms/links, không để nút theme chết hiện ra.

Màu tập trung ở CSS variables: một palette dark giữ navy/cyan/tím, một palette light với nền trắng/xám nhạt, navy text và cyan đậm. Cùng HTML/Jinja cho cả hai. Áp dụng sidebar/navbar/card/table/status/input/select/notice/alert, login, ba khung AI Evaluation, glossary và các trang403/404/503. CSS modal/tooltip/dropdown Bootstrap cũng dùng tokens; không thêm modal nghiệp vụ mới.

Biểu đồ tương tác đổi palette, grid/ticks/legend/tooltip và vẽ lại canvas; giữ nguyên instance, giá trị, nguồn run và trạng thái dữ liệu. Ngừng animation cũ khi đổi màu để tránh canvas rỗng tạm thời. Test có kiểm pixel canvas đã được vẽ trước khi chụp, không chỉ so mảng số. Ảnh PNG thực nghiệm đã lưu được giữ nguyên màu/byte, không invert hoặc chỉnh artifact để hợp theme.

Nút/menu có aria-label, aria-haspopup, aria-checked, focus ring; hỗ trợ Enter/Space, mũi tên, Home/End, Escape và Tab. Menu không thuộc form login/logout/export. Giữ password toggle/loading/failure, run selector đã validate, cảnh báo khoa học và các trường metadata thiếu “Không được cung cấp”. Không trộn run hoặc suy Validation/C/canonical overlap mới.

## Kết quả thực tế và giới hạn môi trường

| Kiểm thử | Kết quả |
|---|---|
| `python -m pytest -q -rs` |143 PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS;64.68s |
| `python tools/run_h07_acceptance.py` |6 bước exit0;pytest143 PASS/3 SKIP |
| Dashboard/auth/filter/CSV TCP |41 PASS,0 FAIL |
| Download TCP/security |33 PASS,0 FAIL,3 symlink SKIP |
| Performance |144 request/144 SQLite rows,0 lỗi |
| Edge/Chromium local, bản cuối |241 PASS,0 FAIL;0 JavaScript/static errors |
| Chrome cài sẵn và portable local |FAIL do browser bị đóng/crash; không đổi thành SKIP/PASS |
| Chrome Windows CI |Workflow đã bổ sung bước browser bắt buộc; xem kết quả cụ thể trên PR, không dùng Edge local thay cho Chrome |

[Pytest stdout](pytest_20261117T070856Z/stdout.txt) · [command/exit](pytest_20261117T070856Z/command.json) · [Acceptance summary](../bao_cao_h07/evidence/20261117T070909Z_14fe5a/summary.json) · [JUnit](../bao_cao_h07/evidence/20261117T070909Z_14fe5a/pytest.xml) · [HTTP từng TC](../bao_cao_h07/evidence/20261117T070909Z_14fe5a/http_test_cases.csv).

[Browser241 checks cuối](browser_20261117T070418Z_61843f/results.json) và [manifest ảnh](browser_20261117T070418Z_61843f/manifest.json). Cả5 trang được kiểm ở1440/768/390px trong **cả hai theme**. Kiểm thêm đổi mode không reload, dữ liệu/instance chart không đổi, palette cập nhật, theme đã lưu áp dụng trước CSS dù OS ngược lại, keyboard menu, OS light/dark live, cross-tab và đóng/mở lại browser thực với profile fixture riêng. Storage-denied được fault-inject trong context riêng. Các403/404 thật và503 từ lỗi ghi log fixture được render cả light/dark, không giả status hoặc động vào DB nghiệp vụ.

Bộ browser giữ các kiểm tra login đúng/sai/CSRF, password reveal, filter/export, metadata đúng run, khoa học100%, download Unicode, encoded traversal403 và missing404 của đợt trước. Thêm8 SSR regression cases cho loader sớm/không async, controls dùng chung và không làm đổi fields auth. Ba SKIP vẫn do quyền symlink Windows11; không tăng mức nghiệm thu PI3.1.

Hash dataset/deployed v1/frozen v2/SQLite nghiệp vụ trước/sau cả acceptance và browser đều không đổi. Bằng chứng trung gian được giữ riêng, không ghi đè: pytest065401Z;acceptance065636Z;browser070133Z241 PASS trước khi thêm kiểm pixel.

**Chrome local chưa được xác nhận thành công.** Hai lần [064542Z](browser_20261117T064542Z_eddacf/results.json)/[064658Z](browser_20261117T064658Z_f62496/results.json) có11 PASS/1 FAIL do Page crashed. [064943Z](browser_20261117T064943Z_5a808f/results.json) thử GPU disabled vẫn0 PASS/1 FAIL. Chẩn đoán trang trắng không tải app cũng bị Chrome đóng, có log GPU/network service exit; chưa xác định nguyên nhân OS/chính sách cụ thể. Không sửa ACL, antivirus hoặc profile Chrome người dùng.

Đã thử [Chrome for Testing chính thức](https://googlechromelabs.github.io/chrome-for-testing/)157.0.8103.78 portable trong `.verification`, không cài hệ thống, nhưng [065630Z](browser_20261117T065630Z_49a82b/results.json) cũng bị đóng trước khi mở app. Không ghi kết quả này thành PASS. Binary/profile/download không commit. Để kiểm Chrome độc lập, CI cài Playwright riêng và chạy cùng suite trên Chrome runner Windows; upload evidence cho review.

Lần Edge [065837Z](browser_20261117T065837Z_670481/results.json)226 PASS/1 FAIL do công cụ dùng predicate dạng expression làm vướng CSP cấm unsafe-eval. Đã đổi predicate sang function, không nới CSP hoặc đổi điều kiện kỳ vọng. Lần [070133Z](browser_20261117T070133Z_60b146/results.json)241 PASS và lần cuối thêm chờ pixel đều giữ riêng. Các kiểm tra tương phản ở những phần chữ quan trọng không thay cho audit WCAG toàn diện. Chưa chứng nhận Safari/Firefox hoặc thiết bị cảm ứng vật lý.

## Ảnh thực tế Light / Dark

Ảnh dùng localhost, DB/tệp fixture riêng và model/metadata thật đọc từ artifact; không phải dữ liệu sản xuất hoặc ảnh tạo bằng AI.

| Trang | Light1440 | Dark1440 | Light390 | Dark390 |
|---|---|---|---|---|
| Kho tệp |[Ảnh](browser_20261117T070418Z_61843f/theme_light_public_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_public_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_light_public_390.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_public_390.png) |
| Login |[Ảnh](browser_20261117T070418Z_61843f/theme_light_login_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_login_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_light_login_390.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_login_390.png) |
| Dashboard |[Ảnh](browser_20261117T070418Z_61843f/theme_light_dashboard_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_dashboard_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_light_dashboard_390.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_dashboard_390.png) |
| Evaluation |[Ảnh](browser_20261117T070418Z_61843f/theme_light_evaluation_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_evaluation_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_light_evaluation_390.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_evaluation_390.png) |
| Training |[Ảnh](browser_20261117T070418Z_61843f/theme_light_training_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_training_1440.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_light_training_390.png) |[Ảnh](browser_20261117T070418Z_61843f/theme_dark_training_390.png) |

Ảnh403/404/503 của mỗi theme nằm cùng thư mục, tiền tố `theme_light_error_`/`theme_dark_error_`.

## File thay đổi và tái lập

- `app/static/theme.js` (mới): bootstrap preference trước CSS, storage/system events, menu keyboard/ARIA.
- `app/static/style.css`: palette semantic light/dark dùng chung, màu controls/alerts/status/menu/modal/tooltip, giữ layout responsive.
- `app/static/dashboard.js`: đọc palette CSS và redraw cùng chart khi theme đổi, không sửa data.
- `app/templates/base.html`: loader sớm và một menu theme dùng chung, không nhân bản HTML.
- `tests/test_theme_ui.py` (mới):8 cases; `tools/ui_theme_checks.py` (mới): runtime browser theme checks.
- `tools/verify_ui_browser.py`: tích hợp checks, ghi browser/launch args, hỗ trợ flag chẩn đoán software rendering (không tự đổi cấu hình browser hệ thống).
- `.github/workflows/tests.yml`: cài Playwright1.65.2 trong thư mục test riêng, chạy Chrome và upload ảnh/JSON/JUnit. Requirements Python runtime không đổi.
- `README.md`, `docs/ui/README.md`, `docs/ui/PR_DESCRIPTION.md`, báo cáo này và các evidence mới nêu trên. Chứng cứ025117Z có sẵn vẫn giữ nguyên ngoài commit.

Chạy app như cũ bằng `python run.py`, mở **Giao diện** trên navbar. Kiểm thử hai lệnh trong bảng; browser tùy chọn `python tools/verify_ui_browser.py --browser "đường dẫn Chrome hoặc Edge.exe"`. Chỉ dùng profile fixture do tool tạo, không cần huấn luyện/deploy model. PR#2 giữ draft để review; không merge main.
