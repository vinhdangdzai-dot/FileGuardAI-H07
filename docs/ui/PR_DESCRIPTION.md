Hoàn thiện giao diện FileGuardAI-H07 trên h07/cybersecurity-ui: dark navy/cyan/tím, responsive cho5 trang, tập trung Login dễ trình chiếu và AI Evaluation giải thích đúng dữ liệu từng run. Giữ nguyên auth/session/CSRF, role admin/auditor, policy Path Traversal, ALLOW/BLOCK/MISS, dataset/models/SQLite và kết quả thực nghiệm đã lưu.

Login:navbar wrap thay vì cắt mép, hai cột desktop và bố cục tablet/mobile cân đối, giảm khoảng trống trên, tăng chữ mô tả/nhãn/phụ. Có hiện/ẩn mật khẩu bằng keyboard/ARIA, loading đúng nút submit, che lại khi pageshow, thông báo thất bại rõ và không phản chiếu mật khẩu. Request/login controls của Flask không đổi.

AI Evaluation:ba khu vực dữ liệu/cấu hình/độ tin cậy, cảnh báo nguyên văn về100% không chứng minh phát hiện/ngăn chặn100% thực tế, glossary8 thuật ngữ có thể thu gọn. Run selector dùng GET ?run hiện có và danh sách backend đã validate; phân biệt family lịch sử và strict canonical. Không đoán Validation/C v1/canonical overlap còn thiếu. Phân biệt Train fit, Validation, Test và Development/refit; metadata/metrics/chart/ảnh đều cùng run. Chỉ thay backend tối thiểu để truyền history và experiment_type vào selector; không thêm endpoint hoặc đổi hợp đồng route.

Giữ chức năng kho tệp/tìm Unicode/native download, dashboard/filter/export, AI Training chỉ đọc, sidebar, loading/empty/error/no-JS. Bootstrap5.3.3/Chart.js4.4.7 local với giấy phép/hash vẫn giữ; không đổi dependencies ứng dụng.

Bootstrap5.3.3 và Chart.js4.4.7 đúng phiên bản cũ được đóng gói local với MIT licenses/URL/SHA256; không cần CDN. Không thêm dependency Python runtime; Playwright tùy chọn chỉ phục vụ screenshots/test riêng.

Validation thực tế:

- python -m pytest -q -rs:135 PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS. Baseline5866eb8 là127 PASS/3 SKIP;thêm8 regression cases của đợt hoàn thiện.
- Acceptance:cả6 bước exit0;dashboard TCP41 PASS;download33 PASS/3 symlink SKIP;144 request/144 log rows,0 lỗi. Không đổi các3 SKIP thành PASS.
- Chrome headless/TCP:85 PASS,0 FAIL;không lỗi JS/static assets;1440/768/390px cho5 trang, thêm navbar guest Login cả3 kích thước. Kiểm hiện/ẩn bằng Space/Enter, loading submit thật, login sai/đúng, CSRF, run metadata/metrics/chart/ảnh đúng nguồn, sidebar/Escape, filter/export, download/traversal403/missing404 và no-JS. Đo computed contrast và cỡ chữ, không tuyên bố audit WCAG đầy đủ.
- Dataset,deployed v1,frozen v2 và SQLite nghiệp vụ giữ nguyên hash trước/sau. Ảnh dùng DB/tệp fixture tách riêng, không nhận là nhật ký sản xuất.
- Giữ ảnh trước/sau và mọi đợt thử. Lần công cụ chặn navigation timeout16 PASS/1 FAIL được giữ; sửa thành quan sát thụ động submit, không giả phản hồi hoặc hạ điều kiện PASS. Lần82 PASS và cuối85 PASS lưu riêng. Không đổi FAIL thành SKIP.

docs/ui/REFINEMENT_LOGIN_AI.md có file thay đổi, nguồn số từng run, ảnh trước/sau, logs và giới hạn. docs/ui/README.md giữ bằng chứng đợt nền. PI3.1 vẫn PARTIAL do đặc quyền symlink Windows11;không tuyên bố an toàn/tổng quát hóa100%. Browser ngoài Chrome/thiết bị vật lý/WCAG audit đầy đủ chưa kiểm.

PR stacked lên h07/complete-minimum-requirements để review riêng UI và không trộn diff backend của PR#1. Không ghi đè branch cũ hoặc merge main.
