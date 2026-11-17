> **Bản hiện hành:** [12_MA_TRAN_NGHIEM_THU](bao_cao_h07/12_MA_TRAN_NGHIEM_THU.md),17/11/2026. 11 PASS,1 PARTIAL. [Sửa lỗi quyền temp](bao_cao_h07/13_SUA_LOI_PYTEST_WINDOWS11.md):116 pytest PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS trong môi trường Codex, chưa chạy lại bằng tài khoản người dùng. Chỉ admin đọc dữ liệu quản trị. Nội dung dưới đây giữ làm lịch sử, không thay bằng chứng mới.

# Đối chiếu mã nguồn với yêu cầu H07

## Tự đánh giá kỹ thuật cập nhật — 17/11/2026

Giữ nguyên 12 mã PI và 4 CLO từ bản kế hoạch. “Đạt” là đủ minimum trong
phạm vi MVP localhost, không phải production certification hoặc xác nhận
điểm của trường. Bản trước được lưu nguyên tại
[h07/MA_TRAN_BAN_DAU.md](h07/MA_TRAN_BAN_DAU.md).

| PI | Tiêu chí minimum tự đối chiếu | Trạng thái | File minh chứng | Kết quả thực tế |
|---|---|---|---|---|
| 1.1 | Nhận diện CWE-22, tài sản, threat boundary và bảng rủi ro | Đạt | [Rủi ro](h07/RUI_RO_CWE22.md), security.py | 11 rủi ro, score nhận định được phân biệt với số đo |
| 1.2 | Giải thích LR/đặc trưng/quy trình phát hiện và đối chứng | Đạt | [Chương 1](h07/CHUONG_1.md), ml_features.py, improve.py | 18/30 đặc trưng; validation từ train, model không cấp quyền |
| 1.3 | Activity và xử lý 200/403/404/lỗi AI | Đạt | [Thiết kế](h07/THIET_KE.md), [UML](h07/diagrams/download_activity.puml) | Test valid/missing/policy/AI error đã PASS |
| 2.1 | Kiến trúc/module và ranh giới triển khai | Đạt | [Thiết kế](h07/THIET_KE.md), [Chương 3](h07/CHUONG_3.md) | Factory/routes/security/auth/database/ML tách vai trò |
| 2.2 | ERD và lưu/đọc event đúng schema | Đạt | THIET_KE.md, app/database.py | 2 bảng thực; index/trigger; test SQLite và backup PASS |
| 2.3 | Kịch bản và bằng chứng HTTP có thể kiểm tra | Đạt | [Chương 4](h07/CHUONG_4.md), tests/, JSON TCP | Pytest 76 PASS/3 SKIP, clone sạch cùng kết quả; TCP download 33 PASS/3 SKIP; dashboard/RBAC 27 PASS |
| 3.1 | Ngăn traversal, gồm chứng minh symlink thực trên Windows | Chưa đạt | security.py, check_symlinks.py, [summary](h07/evidence/final_20261117/symlink_summary.json) | Traversal/junction PASS; 3 symlink SKIP/1314; TOCTOU/ACL chưa có chứng minh đầy đủ |
| 3.2 | Query/filter, backup và bảo vệ nhật ký | Đạt | database.py, backup_logs.py, [runbook](h07/AN_NINH_VAN_HANH.md) | Bound filter, append-only triggers, backup không ghi đè/integrity, admin export PASS; không tamper-proof trước OS writer |
| 3.3 | Ít nhất 5 Use Case có actor/luồng/ngoại lệ | Đạt | [Use Cases](h07/USE_CASES.md) | 10 UC; routes/CLI tương ứng có test |
| 3.4 | Quyền web và bảo vệ quản trị ở phạm vi demo | Đạt | auth.py, tests/test_auth.py, runbook | Guest/Admin/Auditor, CSRF, hash, login throttle, session, private-storage guard PASS; chưa triển khai Internet |
| 4.1 | Metrics/latency/block rate thực tế và phân tích FP/FN | Đạt | [Chương 4](h07/CHUONG_4.md), performance.json, predictions CSV | 3×48 TCP, 90/90 policy violations bị chặn; public challenge regex FN4, LR FN0; không đồng nhất block rate với ML Recall |
| 4.2 | Dữ liệu 10.000 mẫu + nguồn ngoài có nhãn/provenance, không fit test | Đạt | [Chương 4](h07/CHUONG_4.md), data/external/, tests/test_h07_evaluation.py | 236 mẫu nguồn mới + challenge20; freeze model; ngưỡng không đổi; nhãn lexical/source bias/không blind/15 canonical overlap cũ được công khai |

**Tổng: 11/12 Đạt minimum, 1/12 Chưa đạt.** Không đổi trạng thái 3.1
thành Đạt khi chưa chạy được symlink thật. Các thiếu sót về traffic thực,
OS ACL/TOCTOU, production IAM và ảnh chụp demo thủ công vẫn phải trình
bày trong giới hạn; không suy rộng “Đạt MVP” thành “đã hoàn thiện mọi
yêu cầu của khóa luận”. Chưa có bản Word H07 chính thức trong workspace
để xác nhận rubric chi tiết ngoài 12 PI trong bản kế hoạch hiện có.

Tài liệu kỹ thuật bốn chương: [Chương 1](h07/CHUONG_1.md),
[Chương 2](h07/CHUONG_2.md), [Chương 3](h07/CHUONG_3.md),
[Chương 4](h07/CHUONG_4.md).

## Nội dung lập kế hoạch ban đầu (giữ để đối chiếu)

Mẫu H07: 4 CLO, 12 PI; báo cáo gồm Giới thiệu, 4 chương, Kết luận, TLTK và phụ lục. Các phần cần hoàn thiện thêm được đánh dấu **CẦN LÀM**.

| PI | Minh chứng trong MVP | Còn phải hoàn thiện khi làm đồ án |
|---|---|---|
| 1.1 | `app/security.py`, README §6 | Bảng đánh giá rủi ro và ví dụ CWE-22 |
| 1.2 | `app/ml_features.py`, `ml/train_model.py` | Sơ đồ quy trình phát hiện và cơ sở lý luận |
| 1.3 | `app/__init__.py`, `app/security.py` | UML Activity Diagram và luồng xử lý lỗi |
| 2.1 | Flask app + cấu trúc thư mục | Sơ đồ kiến trúc chi tiết, mô tả các module |
| 2.2 | `app/database.py`, `/dashboard` | ERD, bảng mô tả trường dữ liệu, chính sách log |
| 2.3 | `tests/test_security.py`, `tests/test_app.py` | Bảng kịch bản thực nghiệm và ảnh chụp |
| 3.1 | `open_authorized` tách rời AI | Phân tích giới hạn, đo tỷ lệ chặn, minh chứng cấu hình |
| 3.2 | SQLite tạo tự động, log từng yêu cầu | Chứng minh truy vấn/lọc, sao lưu và bảo vệ nhật ký |
| 3.3 | Xem/tải tệp, phân tích, ngăn chặn, nhật ký | Use Case Diagram và đặc tả 5 Use Case |
| 3.4 | HTML/Bootstrap, login, Chart.js | Bổ sung phân quyền người dùng và hardening nếu công khai |
| 4.1 | Pytest, thống kê, thời gian xử lý | Benchmark nhiều lần; phân tích false positive/negative |
| 4.2 | Dữ liệu synthetic 10.000 đường dẫn mặc định | Thu thập nguồn độc lập, kiểm tra nhãn và bias |

## Dàn ý báo cáo bắt buộc theo H07

- Giới thiệu đề tài
- Chương 1. Cơ sở lý thuyết
- Chương 2. Phân tích yêu cầu hệ thống
- Chương 3. Thiết kế và triển khai hệ thống
- Chương 4. Kết quả kiểm thử hoạt động (Hoạt động thử nghiệm, phân tích kết quả đạt được, logs, tài liệu hướng dẫn)
- Kết luận
- Tài liệu tham khảo
- Phụ lục (nếu có)

## Lưu ý triển khai và đánh giá

- Các **Lưu ý** trong mẫu H07 Word là chỉ dẫn của giảng viên và nhà trường, cần giữ nguyên trên đề cương, không xóa.
- Không thay đổi CLO–PI cố định nếu chưa có chấp thuận.
- Không tự ghi số liệu thực nghiệm chưa đo được.
- Không đăng nguồn dữ liệu cá nhân hoặc mật khẩu quản trị lên GitHub.
