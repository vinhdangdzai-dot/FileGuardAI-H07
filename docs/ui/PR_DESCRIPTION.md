Nâng cấp presentation FileGuardAI-H07 thành dashboard dark navy/cyan/tím trên nhánh riêng, giữ nguyên backend/routes/contracts, role admin/auditor, CSRF/session, dữ liệu và models.

Kho tệp có tìm kiếm Unicode và filter đuôi tệp, native download và trạng thái gửi yêu cầu trung thực. Dashboard có sidebar thu gọn/mobile, thẻ ALLOW/BLOCK/MISS, biểu đồ số liệu thật, bảng cuộn và filter/export giữ nguyên. AI Evaluation/Training phân biệt deployed/experimental, hiển thị metrics/weights/label charts/history từ artifacts và các giới hạn100% synthetic. Login/error/empty/no-JS states đồng bộ theme.

Bootstrap5.3.3 và Chart.js4.4.7 đúng phiên bản cũ được đóng gói local với MIT licenses/URL/SHA256; không cần CDN. Không thêm dependency Python runtime; Playwright tùy chọn chỉ phục vụ screenshots/test riêng.

Validation thực tế:

- python -m pytest -q -rs:127 PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS. Baseline116 PASS/3 SKIP;thêm11 UI regression cases.
- Acceptance:cả6 bước exit0;dashboard TCP41 PASS;download33 PASS/3 symlink SKIP;144 request/144 log rows,0 lỗi. Không đổi các3 SKIP thành PASS.
- Chrome headless/TCP:42 PASS,0 FAIL;không lỗi JS/static assets;1440/768/390px;native download/traversal403/missing404, Unicode, login/CSRF, filters/CSV, chart equality, responsive/sidebar/no-JS.
- Dataset,deployed v1,frozen v2 và SQLite nghiệp vụ giữ nguyên hash trước/sau. Ảnh dùng DB/tệp fixture tách riêng, không nhận là nhật ký sản xuất.
- Browser lần đầu35 PASS/1 FAIL được giữ nguyên trong evidence; lỗi syntax JS và missing static đã sửa và kiểm thử lại, không che FAIL.

docs/ui/README.md có bảng trước/sau, từng file thay đổi, ảnh thực tế desktop/mobile và đường dẫn log/manifest. PI3.1 vẫn PARTIAL do đặc quyền symlink Windows11;không tuyên bố an toàn/tổng quát hóa100%. Browser ngoài Chrome/thiết bị vật lý/WCAG audit chưa kiểm.

PR stacked lên h07/complete-minimum-requirements để review riêng UI và không trộn diff backend của PR#1. Không ghi đè branch cũ hoặc merge main.
