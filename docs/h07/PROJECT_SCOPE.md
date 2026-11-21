# Phạm vi website và thực nghiệm CANH GÁC SỐ — H07

Tên đề tài giữ nguyên: **Xây dựng hệ thống phát hiện và ngăn chặn tấn công
Path Traversal trên ứng dụng web sử dụng thuật toán Logistic Regression.**

## Ba mục tiêu và các thành phần

| Mục tiêu | Thành phần chính | Minh chứng |
|---|---|---|
| Phát hiện | Logistic Regression v1 đang triển khai, 18 đặc trưng đường dẫn; v2 30 đặc trưng để đối chiếu thực nghiệm | app/ml_features.py, artifacts/model.joblib, trang AI Evaluation/Training và kết quả đã lưu |
| Ngăn chặn | app/security.py kiểm tra ranh giới và mở handle an toàn; app/documents.py kiểm tra quyền tải | HTTP 200/403/404, mock LR sai vẫn không cấp quyền ngoài policy |
| Giám sát | SQLite access_logs + download_context + alerts + alert_events, trang chi tiết Admin | Event ID không bị mất khi gom cảnh báo; Gemini bổ trợ không thay kết quả |

Đăng ký/tài khoản/Argon2id/TOTP chỉ phục vụ quyền tải và bảo vệ quản trị của
ứng dụng nghiên cứu. Không bổ sung phishing detector, malware scanner hoặc
URL fraud analysis. Không dùng Gemini làm mô hình nghiên cứu chính.

## Phân loại tài liệu

- Mọi tệp hiện có ở shared_files ngoài vùng reserved vẫn công khai, không cần
  tài khoản. Đây là chính sách tương thích của kho demo, không phải nơi đặt secret.
- `shared_files/restricted/` và toàn bộ thư mục con yêu cầu phiên đăng nhập
  hợp lệ của User, Auditor hoặc Admin. So sánh tên reserved không phân biệt hoa/thường.
- Guest chỉ thấy tên tệp công khai; không nhận danh sách tên tệp hạn chế.
  Khi đăng nhập, danh mục hiển thị rõ badge Công khai/Cần đăng nhập.
- Admin mới qua password nhưng chưa TOTP vẫn chưa có quyền tải tệp hạn chế.
  Tài khoản khóa, session hết hạn/thu hồi phải đăng nhập lại theo cơ chế hiện có.
- Truy cập vùng hạn chế khi chưa đăng nhập trả BLOCK/403, bao gồm tệp không
  tồn tại trong vùng này, để không phân biệt sự tồn tại trước khi xác thực.
  Đã có quyền nhưng tệp không tồn tại trả MISS/404; tệp hợp lệ trả ALLOW/200.
- Tên Unicode, dấu cách và thư mục con tiếp tục được hỗ trợ. Mọi đường dẫn
  nguy hiểm bị kiểm tra trước bước login, không redirect để bỏ qua traversal.

`/admin/documents` chỉ đọc danh mục/phân loại. Người quản lý kho dùng quyền
hệ điều hành để đặt tài liệu vào đúng vùng; website không thêm upload/xóa/
di chuyển tệp. Không copy hoặc tạo hardlink của tài liệu hạn chế trong vùng
công khai. ACL của repository và tài khoản OS chạy Flask vẫn là trust boundary.
Không cam kết cô lập trước kẻ đã có quyền ghi filesystem của server.

Windows dùng canonical path và kiểm tra lại đường dẫn của handle đã mở để
quyền tải không chỉ dựa vào cách viết URI/case/alias. Symlink/reparse point
tiếp tục do security.py từ chối. Không thêm giải mã URL vào filesystem:
Flask giải mã transport một lần; phần phân tích ML vẫn có view giải mã giới
hạn riêng, không chuyển view đó vào open_authorized.

## Admin và phân quyền

`/admin` là lối vào Dashboard quản trị, `/admin/documents` xem phân loại.
Các URL `/dashboard/...` hiện có được giữ tương thích; cùng yêu cầu Admin
đã hoàn tất TOTP và session server hợp lệ. User/Auditor không đọc nhật ký,
chi tiết Event ID, dữ liệu AI riêng tư, dataset hoặc cấu hình bổ trợ.

Admin login vẫn đến Dashboard cũ sau TOTP để giữ hợp đồng hiện hành; có thể
vào trực tiếp `/admin`. Accounts/2FA là các mục hỗ trợ nằm sau các mục giám
sát, Security Alerts và đánh giá AI trong sidebar.

Argon2id, migration hash cũ, TOTP, backup codes, CSRF, brute-force và session
không được thiết kế lại trong đợt này. Xem MFA_SECURITY.md và USER_ACCOUNTS.md.
Giữ chính sách demo 6–128 ký tự đã chốt; không tự tuyên bố đáp ứng đầy đủ ASVS.

## Nhật ký, phân biệt chặn quyền với chặn đường dẫn

Thêm bảng download_context gắn duy nhất với access_logs.id, chỉ append,
cùng transaction với nhật ký và cảnh báo. Không ALTER/xóa log hoặc backfill
giả kết luận cho sự kiện cũ. Fields: path_outcome (permitted/rejected/missing),
visibility (public/authenticated/unknown), access_outcome
(allowed/login_required/not_applicable).

BLOCK/403 vì chưa login không tự tạo cảnh báo policy_block của Path Traversal.
Nếu LR vẫn gán suspicious, có thể tạo cảnh báo ml_suspicious mức trung bình;
đó là tín hiệu ML, không phải xác nhận vi phạm đường dẫn. Nhánh quyền tải
không gửi Gemini. BLOCK do đường dẫn tạo cảnh báo cục bộ ngay; gom nhóm vẫn
giữ mọi Event ID trong alert_events. Các log cũ không có context vẫn đọc được.

Dashboard giữ tổng ALLOW/BLOCK/MISS, đồng thời tách số BLOCK theo đường dẫn
và theo login. Không dùng tổng BLOCK của mọi loại từ chối làm tỷ lệ ngăn chặn
Path Traversal. Trang chi tiết chỉ Admin thấy raw path/IP, điểm LR, các chỉ
dấu, HTTP, nguyên nhân, cảnh báo, thời gian và khuyến nghị.

Khuyến nghị cục bộ theo quy tắc được gắn nhãn riêng; không giả làm câu trả lời
Gemini. API thiếu key/mất mạng/quota/lỗi response không đổi ALLOW/BLOCK/MISS
và không làm mất cảnh báo đã lưu. Không đưa IP, tên tệp, raw path, password
hoặc token vào dịch vụ ngoài.

## Thực nghiệm và tái lập

- `python -m pytest -q -rs` và `python tools/run_h07_acceptance.py` kiểm tra
  toàn bộ auth, RBAC, Path Traversal, SQLite, cảnh báo và chế độ offline.
- `python tools/verify_project_scope.py --browser` chạy TCP thật với LR đang
  triển khai (chỉ đọc artifact), SQLite/tài khoản/tệp giả lập riêng và 30 ảnh
  Light/Dark tại 1440/768/390px. Cần môi trường Playwright/Chrome test hiện có.
- Kịch bản: public, Unicode, thư mục con, restricted có/không login, Windows,
  traversal trực tiếp, URL encoding, double encoding, missing, Admin TOTP,
  đăng ký User, gom cảnh báo và bảo toàn Event ID.
- Test fault injection mô phỏng LR false positive/false negative để chứng
  minh policy độc lập. Không coi điểm mô phỏng là dự đoán thật của mô hình.
  Tool TCP lưu điểm thật; nếu không quan sát FP/FN phải ghi rõ, không tạo số liệu.
- Symlink thật trên Windows thiếu quyền vẫn SKIP/1314. Phải kiểm tra riêng
  ở môi trường đủ quyền; không đổi SKIP thành PASS.

Không huấn luyện lại hoặc điều chỉnh threshold, không sửa dataset/model,
latest pointer hay kết quả đã lưu. Các chỉ số ở trang đánh giá vẫn theo từng
run. Kết quả 100% trên tập tổng hợp/nguồn công khai nhỏ không chứng minh phát
hiện hoặc ngăn chặn 100% tấn công thực tế. Giữ rõ phạm vi v1 deployed và mô
hình v1/v2 huấn luyện cho từng thực nghiệm; không gán metric của run cho một
artifact triển khai khác.

Kết quả đợt này và bảng 18 yêu cầu: evidence/project_scope_20261119/REPORT.md.
Không commit, push GitHub hoặc triển khai VPS tự động.
