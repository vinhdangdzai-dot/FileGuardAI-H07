# Nâng cấp giao diện FileGuardAI-H07

> Bản hoàn thiện tiếp theo: [Login + AI Evaluation theo run](REFINEMENT_LOGIN_AI.md),135 pytest PASS/3 SKIP và85 browser checks PASS, kèm ảnh trước/sau. Các số và ảnh bên dưới là đợt baseline5866eb8, giữ để đối chiếu.

Nhánh `h07/cybersecurity-ui`, phát triển từ `bb87b23` của `h07/complete-minimum-requirements`. Phạm vi là presentation và kiểm thử; không thay Flask routes, API/data contracts, phân quyền, AI, dataset hoặc SQLite nghiệp vụ. Báo cáo ngày17/11/2026; thư mục evidence dùng UTC.

## Giao diện đã hoàn thành

- Theme dark navy/cyan/tím bằng CSS riêng, dùng Bootstrap5.3.3 hiện có. Sidebar desktop thu gọn và drawer mobile, Escape/focus keyboard, skip link, trạng thái active và nhãn truy cập khi thu gọn.
- Kho tệp có tìm kiếm Unicode NFC và lọc đuôi tệp trong danh sách backend đã cung cấp. Không gọi download khi tìm kiếm. Native form GET và liên kết tải vẫn dùng endpoint `/download`; không có bộ kiểm tra quyền mới ở JavaScript.
- Trạng thái tải chỉ báo đã gửi yêu cầu, không báo thành công từ timer. HTTP403/404/503 hiển thị trang lỗi thật của backend. Có empty state và fallback khi tắt JavaScript.
- Dashboard có thẻ tổng request/ALLOW/BLOCK/MISS, AI cảnh báo riêng, doughnut quyết định và xu hướng theo phút UTC. Xu hướng chỉ từ tối đa100 log trong bảng đã lọc, không giả là toàn bộ lịch sử. Một mốc thời gian chỉ hiện một điểm; không thêm mẫu để làm đẹp đường biểu diễn.
- Tất cả bộ lọc action/AI/HTTP/start/end và hidden fields export được giữ. Form CSV và logout giữ POST/CSRF. Security logs có đủ IP/UTC/path/score/label/action/HTTP/reason/duration; bảng cuộn ngang trong vùng riêng trên mobile.
- AI Evaluation hiển thị bốn chỉ số của LR v1 trong run, bảng LR v1/v2/Regex, biểu đồ so sánh, ảnh confusion matrix/metrics/latency có sẵn. Ghi rõ model thực nghiệm, deployed v1, frozen v2 và giới hạn kết quả100% trên tập hữu hạn.
- AI Training có thống kê CSV, phân bố nhãn thật,18/30 đặc trưng và hệ số từ artifact, scaler, lịch sử, CSV. Không có chức năng fit/deploy hoặc nhãn từ dự đoán.
- Login responsive và thống nhất theme; không còn chỉ dẫn sai về mật khẩu demo trong Terminal. Giữ nguyên role/password/CSRF/session/throttle của backend.

Bootstrap và Chart.js4.4.7 được lưu tại [static/vendor](../../app/static/vendor) đúng phiên bản cũ, kèm MIT licenses và manifest URL/SHA256. Không cần CDN để hiển thị theme hoặc biểu đồ. Đây là tài nguyên giao diện, không phải artifact AI. Không thay dependencies Python của ứng dụng; Playwright chỉ được cài cô lập trong `.verification` bị Git ignore.

## Kết quả thực tế trước / sau

| Bộ kiểm thử | Baseline bb87b23 | UI hiện hành |
|---|---|---|
| Pytest cục bộ |116 PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS |127 PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS |
| HTTP dashboard/auth/CSRF/CSV |41 PASS,0 FAIL |41 PASS,0 FAIL |
| HTTP download/security |33 PASS,0 FAIL,3 SKIP |33 PASS,0 FAIL,3 SKIP |
| Acceptance process steps |6 exit0 |6 exit0 |
| Hiệu năng TCP |144 request/144 rows SQLite,0 lỗi |144 request/144 rows SQLite,0 lỗi |
| Browser UI mới |Không có bộ này |42 PASS,0 FAIL;không lỗi JS/static assets |

Baseline: [acceptance trước UI](../bao_cao_h07/evidence/20261116T185722Z_cc572a/summary.json). Sau:

- Lệnh `python -m pytest -q -rs`: [stdout](pytest_20261117T035136Z/stdout.txt), [stderr](pytest_20261117T035136Z/stderr.txt), [command/exitcode](pytest_20261117T035136Z/command.json),43.90s.
- Lệnh `python tools/run_h07_acceptance.py`: [summary](../bao_cao_h07/evidence/20261117T035036Z_57acc3/summary.json), [JUnit](../bao_cao_h07/evidence/20261117T035036Z_57acc3/pytest.xml), [HTTP từng TC](../bao_cao_h07/evidence/20261117T035036Z_57acc3/http_test_cases.csv), stdout/stderr/hash cùng thư mục.
- Chrome thật qua TCP: [42 checks + browser version + hashes](browser_20261117T035025Z_1e4a53/results.json), [manifest ảnh](browser_20261117T035025Z_1e4a53/manifest.json). Độ rộng1440/768/390, cả5 trang; không tràn document ở tablet/mobile. Bảng dài cuộn bên trong.
- Bộ render pytest có11 cases mới: actual chart JSON, CSV labels, escape XSS, guest/auditor denied, login CSRF, native Unicode download/traversal, empty state và mọi script/style phải là static local trả200.

Browser kiểm tra thêm tìm kiếm NFD→NFC, filter PDF, body tải Unicode chính xác, traversal single/double403 và missing404, login/CSRF, lọc BLOCK/export CSV, dữ liệu chart khớp backend, biểu đồ training khớp nhãn CSV, thu gọn sidebar, Escape trên mobile và native links khi tắt JS. Đây là request thực tạo lên **DB fixture riêng**, không phải số liệu giả đưa vào SQLite nghiệp vụ.

Lần browser đầu [35 PASS/1 FAIL](browser_20261117T034734Z_e24af1/results.json) giữ nguyên: phát hiện JS syntax error. Đồng thời thấy tham chiếu `ai-charts.js`404 ở Training. Đã sửa, thêm kiểm tra script/style và kiểm tra browser nghiêm ngặt; lần42 PASS có0 lỗi JS/0 static errors. Không chuyển FAIL thành SKIP. Lần pytest trung gian125 PASS ở034754Z giữ làm lịch sử, không thay số127 của bản cuối.

Ba SKIP vẫn là symlink Windows thiếu đặc quyền. PI3.1 trên Windows11 cục bộ vẫn PARTIAL như hồ sơ H07; nâng cấp giao diện không thay trạng thái này. Dataset/deployed v1/frozen v2/SQLite nghiệp vụ đều giữ nguyên SHA trước/sau acceptance và browser run. DB trước/sau **giữa các đợt khác nhau** có thể khác do người dùng vận hành; chỉ so cùng một đợt đo.

## Ảnh chụp thật

Các ảnh là Chrome headless render Flask localhost, không phải mockup/imagegen. Kho tệp screenshot dùng8 tệp fixture công khai; dashboard là5 yêu cầu fixture thực trong một phút; không mô tả như nhật ký sản xuất. Metadata huấn luyện và đánh giá đọc artifact thật hiện có, không fit lại.

| Trang | Desktop | Mobile |
|---|---|---|
| Kho tệp |[Ảnh](browser_20261117T035025Z_1e4a53/01_public_desktop.png) |[Ảnh](browser_20261117T035025Z_1e4a53/public_mobile.png) |
| Login |[Ảnh](browser_20261117T035025Z_1e4a53/03_login_desktop.png) |[Ảnh](browser_20261117T035025Z_1e4a53/login_mobile.png) |
| Dashboard |[Ảnh](browser_20261117T035025Z_1e4a53/04_dashboard_desktop.png) |[Ảnh](browser_20261117T035025Z_1e4a53/dashboard_mobile.png) |
| AI Evaluation |[Ảnh](browser_20261117T035025Z_1e4a53/05_evaluation_desktop.png) |[Ảnh](browser_20261117T035025Z_1e4a53/evaluation_mobile.png) |
| AI Training |[Ảnh](browser_20261117T035025Z_1e4a53/06_training_desktop.png) |[Ảnh](browser_20261117T035025Z_1e4a53/training_mobile.png) |

[Sidebar mobile](browser_20261117T035025Z_1e4a53/sidebar_mobile.png) · [HTTP403 thật](browser_20261117T035025Z_1e4a53/02_blocked_request.png).

## File tạo / sửa

| Loại | File |
|---|---|
| Sửa templates |app/templates/base.html;index.html;dashboard.html;ai_evaluation.html;ai_training.html;login.html;error.html |
| Sửa CSS/JS |app/static/style.css;app/static/dashboard.js |
| Tạo CSS/JS asset hỗ trợ |app/static/ui.js;app/static/favicon.svg |
| Tạo vendor |app/static/vendor/bootstrap.min.css;bootstrap.LICENSE;chart.umd.min.js;chart.LICENSE.md;manifest.json |
| Tạo tests/tool |tests/test_ui.py;tools/verify_ui_browser.py |
| Sửa Git metadata |.gitattributes giữ nguyên byte của vendor |
| Tài liệu |README.md;docs/ui/README.md;docs/ui/PR_DESCRIPTION.md |
| Evidence mới |docs/ui/browser_20261117T034734Z_e24af1/;browser_20261117T035025Z_1e4a53/;pytest_20261117T034754Z/;pytest_20261117T035136Z/;acceptance035036Z_57acc3 và các TCP/performance mà summary tham chiếu |

Bằng chứng025117Z_2e1b7c và các TCP/performance tương ứng đã có trước khi làm UI được để nguyên tại workspace, không gộp vào commit UI. Không chỉnh/xóa hoặc dùng để tạo số đẹp. Không commit credential, DB nghiệp vụ hoặc `.verification`.

## Tái lập và giới hạn

Chạy ứng dụng như trước bằng `python run.py`. Kiểm thử hai lệnh ở trên. Browser tùy chọn: cài Playwright trong môi trường kiểm thử riêng, dùng Chrome/Edge hiện có, rồi `python tools/verify_ui_browser.py --browser "đường dẫn browser.exe"`. Công cụ tạo runtime/DB riêng và thư mục evidence mới mỗi lần, không sửa DB nghiệp vụ. Không cài thêm dependency này vào requirements ứng dụng.

Trong phiên Codex này Playwright cài bằng tài khoản khác nên sandbox không đọc được module; browser được chạy ngoài sandbox sau phê duyệt, không đổi ACL và không yêu cầu VS Code chạy Administrator. Lỗi import là lỗi công cụ, không được ghi SKIP/PASS cho UI. Kết quả42 PASS chỉ thuộc Chrome và các kích thước đã đo, chưa chứng nhận Safari/Firefox, thiết bị cảm ứng vật lý hoặc audit WCAG đầy đủ. Không có cam kết hệ thống an toàn tuyệt đối từ thiết kế giao diện. PR chỉ để review, không merge main.
