B? sung AI Training duy?t ?? 10.000 m?u b?ng ph?n trang server-side 50/100, t?m ???ng d?n Unicode/literal, l?c label/family, STT CSV g?c v? Trang tr??c/sau. HTML ch? nh?n t?i ?a 100 m?u. POST export lu?n ?? 10.000 m?u v? gi? CSRF/admin-only; XSS ???c escape. Kh?ng thay dataset/model tri?n khai/SQLite/policy Path Traversal.

CSV x?c nh?n: 10.000 d?ng, 5.000/5.000 nh?n, 35 family, 0 tr?ng exact, 32 nh?m/32 d?ng d? canonical, 0 xung ??t nh?n. SHA-256: `2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0`. T?i t?o trong RAM b?ng generator seed 2026 kh?p hash. CSV v?n ignore, c? h??ng d?n kh?i ph?c kh?ng ghi ??.

Training m?c ??nh strict run h?p l? m?i nh?t, c? l?a ch?n l?ch s?; metadata/metrics c?ng run, ph?n bi?t r? tr?ng s? deployed v1/frozen v2. ?? ch?y evaluate_strict_groups.py v?o run m?i `20261117T081416Z_5cb7da`: Train 6500, Validation 1999, Test 1501, overlap family/exact/canonical b?ng 0; C v2=0.1 ch?n b?ng validation. LR v1/v2/Regex ??u Accuracy/Precision/Recall/F1=1.0, CM [[1001,0],[0,500]]; t?p ngo?i 236 m?u hi?n c? ??u 1.0, CM [[118,0],[0,118]]. Kh?ng ph?i blind real-world test; kh?ng c? b?ng ch?ng v2 t?t h?n. Kh?ng ghi ?? artifacts/model.joblib ho?c latest.json.

Ki?m th? local: **158 PASS, 0 FAIL/ERROR, 3 symlink SKIP**, 15 subtests PASS. Acceptance **6/6 exit 0**; dashboard41 PASS; download33 PASS/3 SKIP;144 requests/144 fixture rows/0 l?i. Edge TCP **248 PASS,0 FAIL**,0 JS/static errors; g?m ph?n trang/l?c/export ??y ?? v? Light/Dark t?i1440/768/390px. Hash dataset/model/SQLite kh?ng ??i. Chrome local v?n c? gi?i h?n crash ?? ghi; Chrome CI ???c b?o ri?ng theo commit, kh?ng d?ng Edge thay Chrome.

B?o c?o/file/TC: [docs/datasets/INTEGRATION_10000.md](docs/datasets/INTEGRATION_10000.md). Audit `docs/datasets/audit_20261117T081413Z_b9cdfa/`; pytest `docs/ui/pytest_20261117T081620Z/`; browser/?nh `docs/ui/browser_20261117T081653Z_148fdc/`; acceptance `docs/bao_cao_h07/evidence/20261117T081743Z_92c28e/`. Gi? b?ng ch?ng c?. PR draft, kh?ng merge main.

---
??t Light/Dark tr??c (s? li?u l?ch s?, kh?ng ph?i l?n ch?y dataset m?i):

Hoàn thiện Cybersecurity UI: Sáng / Tối / Theo hệ thống trên năm trang và 403/404/503. Menu navbar hỗ trợ keyboard/ARIA, localStorage, đồng bộ tab và OS, áp dụng trước CSS. Chart.js đổi palette tại chỗ, giữ nguyên dữ liệu và instance.

Giữ Login responsive/password toggle/loading và AI Evaluation ba khung metadata/glossary/cảnh báo khoa học/chọn run backend đã validate. Không suy đoán Validation hoặc trộn run. Dataset, artifacts, SQLite nghiệp vụ, Path Traversal, ALLOW/BLOCK/MISS, CSRF/session/role không đổi trong đợt theme.

Kết quả local:
- Pytest: 143 PASS, 0 FAIL, 0 ERROR, 3 SKIP; 15 subtests PASS. SKIP do quyền symlink Windows.
- Acceptance: 6/6 bước exit 0; dashboard TCP 41 PASS; download 33 PASS/3 SKIP; hiệu năng 144 request/144 rows, 0 lỗi. Hash dữ liệu/mô hình/SQLite không đổi.
- Edge/Chromium: 241 PASS, 0 FAIL; không lỗi JS/static; 1440/768/390px, hai palette, System, restart persistence, storage bị chặn, keyboard, auth/CSRF/filter/CSV/download và các run.
- Chrome local FAIL vì browser bị đóng/crash, kể cả trang trắng và portable Chrome for Testing. Chưa xác nhận thành công trên máy này, không biến thành SKIP. Workflow Windows chạy cùng suite Chrome và upload bằng chứng; xem trạng thái CI của commit hiện tại.

Báo cáo/file: [docs/ui/LIGHT_DARK_MODE.md](docs/ui/LIGHT_DARK_MODE.md). Ảnh cuối: docs/ui/browser_20261117T070418Z_61843f/. Pytest: docs/ui/pytest_20261117T070856Z/. Acceptance: docs/bao_cao_h07/evidence/20261117T070909Z_14fe5a/. Giữ evidence thất bại/trung gian và bằng chứng cũ. Không commit browser binary/profile. Không merge main.
