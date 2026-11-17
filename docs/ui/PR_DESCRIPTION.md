Mới nhất: mặc định root18px, A− / A / A+ chọn16/18/20px, lưu fg-text-size trước CSS và đồng bộ tab. Chuyển toàn bộ thang chữ sang rem/CSS tokens; mặc định body18, navbar/sidebar18, controls/bảng17, chú thích/badge/cột16, H1/stat36, H2 24. Chart.js đổi font mà giữ dữ liệu. Giữ Light/Dark/System, auth/CSRF/roles, dataset/model/SQLite/Path Traversal.

Local cuối: pytest165 PASS,0 FAIL/ERROR,3 symlink SKIP;15 subtests PASS. Acceptance6/6 exit0, dashboard41 PASS,download33 PASS/3 SKIP,144 request/144 rows/0 lỗi. Edge385 PASS,0 FAIL,0 JS/static errors. Có90 tổ hợp cỡ chữ ở1440/768/390 và45 phép reflow zoom125/150/200% mô phỏng CDP (chưa xác minh zoom native Ctrl+plus).20 ảnh thật mức18/20px cho5 trang desktop/mobile.

Báo cáo/file/bằng chứng: [docs/ui/TEXT_SIZE.md](docs/ui/TEXT_SIZE.md). Browser cuối docs/ui/browser_20261117T084333Z_816797/. Giữ lượt334 PASS/3 FAIL trước sửa tràn tablet/selector và các lượt ngắt ghi ERROR, không đổi FAIL thành SKIP. Hash các dữ liệu/model/SQLite được bảo vệ không đổi. Chrome local vẫn có giới hạn; Chrome CI được báo riêng theo commit. Không merge main.

---
Lịch sử đợt dataset trước:

Bổ sung AI Training duyệt đủ 10.000 mẫu bằng phân trang server-side 50/100, tìm đường dẫn Unicode/literal, lọc label/family, STT CSV gốc và Trang trước/sau. HTML chỉ nhận tối đa 100 mẫu. POST export luôn đủ 10.000 mẫu và giữ CSRF/admin-only; XSS được escape. Không thay dataset/model triển khai/SQLite/policy Path Traversal. Giữ giao diện Sáng/Tối/Theo hệ thống và cải tiến Login/Evaluation.

CSV xác nhận: 10.000 dòng, 5.000/5.000 nhãn, 35 family, 0 trùng exact, 32 nhóm/32 dòng dư canonical, 0 xung đột nhãn. SHA-256: `2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0`. Tái tạo trong RAM bằng generator seed 2026 khớp hash. CSV vẫn ignore, có hướng dẫn khôi phục không ghi đè.

Training mặc định strict run hợp lệ mới nhất, có lựa chọn lịch sử; metadata/metrics cùng run, phân biệt rõ trọng số deployed v1/frozen v2. Đã chạy evaluate_strict_groups.py vào run mới `20261117T081416Z_5cb7da`: Train 6500, Validation 1999, Test 1501, overlap family/exact/canonical bằng 0; C v2=0.1 chọn bằng validation. LR v1/v2/Regex đều Accuracy/Precision/Recall/F1=1.0, CM [[1001,0],[0,500]]; tập ngoài 236 mẫu hiện có đều 1.0, CM [[118,0],[0,118]]. Không phải blind real-world test; không có bằng chứng v2 tốt hơn. Không ghi đè artifacts/model.joblib hoặc latest.json.

Kiểm thử local: **158 PASS, 0 FAIL/ERROR, 3 symlink SKIP**, 15 subtests PASS. Acceptance **6/6 exit 0**; dashboard41 PASS; download33 PASS/3 SKIP;144 requests/144 fixture rows/0 lỗi. Edge TCP **248 PASS,0 FAIL**,0 JS/static errors; gồm phân trang/lọc/export đầy đủ và Light/Dark tại1440/768/390px. Hash dataset/model/SQLite không đổi. Chrome local vẫn có giới hạn crash đã ghi; Chrome CI được báo riêng theo commit, không dùng Edge thay Chrome.

Báo cáo/file/TC: [docs/datasets/INTEGRATION_10000.md](docs/datasets/INTEGRATION_10000.md). Audit `docs/datasets/audit_20261117T081413Z_b9cdfa/`; pytest `docs/ui/pytest_20261117T081620Z/`; browser/ảnh `docs/ui/browser_20261117T081653Z_148fdc/`; acceptance `docs/bao_cao_h07/evidence/20261117T081743Z_92c28e/`. Giữ bằng chứng cũ và toàn bộ lịch sử run. PR draft, không merge main.
