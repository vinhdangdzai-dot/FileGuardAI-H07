Hoàn thiện Cybersecurity UI: Sáng / Tối / Theo hệ thống trên năm trang và 403/404/503. Menu navbar hỗ trợ keyboard/ARIA, localStorage, đồng bộ tab và OS, áp dụng trước CSS. Chart.js đổi palette tại chỗ, giữ nguyên dữ liệu và instance.

Giữ Login responsive/password toggle/loading và AI Evaluation ba khung metadata/glossary/cảnh báo khoa học/chọn run backend đã validate. Không suy đoán Validation hoặc trộn run. Dataset, artifacts, SQLite nghiệp vụ, Path Traversal, ALLOW/BLOCK/MISS, CSRF/session/role không đổi trong đợt theme.

Kết quả local:
- Pytest: 143 PASS, 0 FAIL, 0 ERROR, 3 SKIP; 15 subtests PASS. SKIP do quyền symlink Windows.
- Acceptance: 6/6 bước exit 0; dashboard TCP 41 PASS; download 33 PASS/3 SKIP; hiệu năng 144 request/144 rows, 0 lỗi. Hash dữ liệu/mô hình/SQLite không đổi.
- Edge/Chromium: 241 PASS, 0 FAIL; không lỗi JS/static; 1440/768/390px, hai palette, System, restart persistence, storage bị chặn, keyboard, auth/CSRF/filter/CSV/download và các run.
- Chrome local FAIL vì browser bị đóng/crash, kể cả trang trắng và portable Chrome for Testing. Chưa xác nhận thành công trên máy này, không biến thành SKIP. Workflow Windows chạy cùng suite Chrome và upload bằng chứng; xem trạng thái CI của commit hiện tại.

Báo cáo/file: [docs/ui/LIGHT_DARK_MODE.md](docs/ui/LIGHT_DARK_MODE.md). Ảnh cuối: docs/ui/browser_20261117T070418Z_61843f/. Pytest: docs/ui/pytest_20261117T070856Z/. Acceptance: docs/bao_cao_h07/evidence/20261117T070909Z_14fe5a/. Giữ evidence thất bại/trung gian và bằng chứng cũ. Không commit browser binary/profile. Không merge main.
