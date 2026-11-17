# CANH GÁC SỐ — by HuuVinh

Khẩu hiệu: **Giám sát thông minh – Bảo vệ dữ liệu an toàn.**

Hệ thống phát hiện, cảnh báo và ngăn chặn tấn công Path Traversal trong ứng dụng web với sự hỗ trợ của trí tuệ nhân tạo Logistic Regression.

## Phạm vi đổi thương hiệu

Tên sản phẩm hiển thị trên website đổi từ FileGuard AI sang CANH GÁC SỐ, với dòng by HuuVinh đúng chữ hoa/thường. `_brand.html` dùng chung cho navbar và sidebar; tên nổi bật, tác giả nhỏ hơn và in nghiêng. Logo SVG chiếc khiên kết hợp mắt giám sát dùng chung cho favicon và nhận diện navbar/sidebar, không dùng ảnh mockup. Sidebar thu gọn chỉ hiện logo; mở rộng có tên và tác giả. Footer, tiêu đề tab, Login, kho tệp, Dashboard, AI Training/Evaluation, tài khoản và các lỗi403/404/503 đều dùng tên mới. Khẩu hiệu/mô tả chính xác được đặt ở Login và phần giới thiệu kho tệp.

Đây là thương hiệu giao diện, không phải đổi tên repo/package/thư mục, route/API, khóa localStorage, window.FileGuardTheme, schema SQLite hoặc đề tài khóa luận. Không sửa data10.000 mẫu, models/artifacts, policy Path Traversal, session/CSRF/quyền, mật khẩu6–128 hoặc các kết quả thực nghiệm. Terminal banner kỹ thuật và tài liệu/bằng chứng lịch sử không bị thay thế máy móc. Các ảnh/biểu đồ thực nghiệm lưu trữ giữ nguyên.

Logo vector dùng nền navy, viền cyan, mắt sáng và chi tiết tím, nhìn được ở cả Light/Dark. Không animation mới. CSS rem và các chức năng Light/Dark/System, A−/A/A+, sidebar và responsive được giữ.

## Kết quả thực chạy local

| Kiểm thử | Kết quả |
|---|---|
| `python -m pytest -q -rs` | **214 PASS,0 FAIL,0 ERROR,3 SKIP**,15 subtests PASS;68,54s |
| `python tools/run_h07_acceptance.py` | **6/6 bước exit0**,pytest214 PASS/3 SKIP |
| Dashboard TCP/auth/filter/CSV |41 PASS,0 FAIL |
| Download TCP/security |33 PASS,0 FAIL,3 symlink SKIP |
| Hiệu năng |144 request/144 dòng SQLite fixture,0 lỗi |
| Edge browser cuối |**439 PASS,0 FAIL**,0 JS/static errors |

[Pytest stdout](pytest_20261117T124908Z/stdout.txt) · [Acceptance summary/JUnit](../bao_cao_h07/evidence/20261117T124452Z_982d20/summary.json) · [Browser từng check](browser_20261117T124911Z_c0c6a8/results.json).

Bổ sung9 SSR cases:6 trang cùng403/404 và503 fixture thật, kiểm UTF-8/name/byline/title/favicon; không cập nhật kỳ vọng của test cũ để che lỗi. Browser thêm36 tổ hợp identity (6 trang ×3 độ rộng1440/768/390 ×2 màu) và1 check sidebar thu gọn. Kiểm tên/tác giả hiển thị, title và bounding rect trong viewport, chờ transition hoàn tất. Giữ402 checks chức năng/typography/theme/data trước đây, gồm đăng nhập, đổi password6 ký tự và thu hồi phiên, Chart.js, Training phân trang/export10.000 mẫu, metadata/metrics/biểu đồ đúng run, tải hợp lệ và traversal403. System Mode và lưu lựa chọn được bộ theme hiện có kiểm.

Hash dataset/deployed v1/frozen v2/SQLite nghiệp vụ trước/sau acceptance và browser đều không đổi. Ba SKIP local vẫn do quyền symlink Windows; không tự gọi PASS. Chrome local vẫn có giới hạn môi trường đã ghi; Chrome CI chạy cùng bộ và đính artifact theo commit trên PR#2. Kiểm zoom125/150/200% của bộ typography vẫn là reflow mô phỏng CDP, không tuyên bố đã xác minh zoom native hoặc máy chiếu vật lý.

Lượt browser [124442Z](browser_20261117T124442Z_a0b8fa/results.json) có423 PASS/16 FAIL: công cụ đo sidebar mobile ngay sau click lúc animation150ms chưa đưa sidebar vào viewport (left=-314). Đã thêm chờ bounding rect đến đúng vị trí trước kiểm, giữ nguyên assertion tên/UTF-8/bounds và thêm ảnh sidebar mở. Không sửa CSS để che chữ, không đổi FAIL thành SKIP. Lượt cuối439 PASS nằm thư mục khác; cả hai được giữ với manifest.

## Ảnh trước/sau thực tế

Ảnh sử dụng fixture UI riêng, không chụp dữ liệu nghiệp vụ. Trước: [Login thương hiệu cũ](browser_20261117T122115Z_b675a3/03_login_desktop.png). Sau:

| Trang | Light1440 | Dark1440 | Light390 | Dark390 |
|---|---|---|---|---|
| Login |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_light_login_1440.png) |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_dark_login_1440.png) |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_light_login_390.png) |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_dark_login_390.png) |
| Kho tệp |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_light_public_1440.png) |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_dark_public_1440.png) |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_light_public_390.png) |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_dark_public_390.png) |
| Dashboard |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_light_dashboard_1440.png) |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_dark_dashboard_1440.png) |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_light_dashboard_390.png) |[Ảnh](browser_20261117T124911Z_c0c6a8/brand_dark_dashboard_390.png) |

Ảnh Training/Evaluation/Account cả hai màu và1440/390 cùng thư mục, tiền tố `brand_`. Sidebar mở mobile: [Light](browser_20261117T124911Z_c0c6a8/brand_light_sidebar_390.png) · [Dark](browser_20261117T124911Z_c0c6a8/brand_dark_sidebar_390.png). Có26 ảnh thương hiệu mới cộng các ảnh kiểm thử chức năng trước.

## File thay đổi và bàn giao

- `app/templates/_brand.html` mới; `base.html`, `login.html`, `index.html`, `dashboard.html`, `ai_training.html`, `ai_evaluation.html`, `change_password.html`, `error.html`: thay nhận diện và title/intro, giữ form/route/dữ liệu.
- `app/static/favicon.svg`: khiên/mắt vector mới; `app/static/style.css`: thang nhận diện rem và layout logo/author/compact sidebar.
- `tests/test_branding_ui.py` mới; `tools/ui_brand_checks.py` mới; `tools/verify_ui_browser.py` tích hợp kiểm và ảnh thật.
- `README.md`, `docs/ui/README.md`, `docs/ui/PR_DESCRIPTION.md`, báo cáo này và snapshots mới. Không sửa Python backend, schema, policy, credentials, ML hoặc dữ liệu. Bốn thư mục/file evidence025117Z có sẵn không thuộc commit.

Nhánh `h07/cybersecurity-ui`, PR#2 giữ draft, commit/push để review, không merge main. Chạy Flask theo hướng dẫn hiện có; hash Admin nếu chưa có vẫn cần CLI nhập kín một lần, không sinh credential mặc định theo tên thương hiệu.
