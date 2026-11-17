# File của bản sửa Pytest Windows

So với dc83cae; không xóa file, không sửa code ứng dụng hoặc mô hình.

| Trạng thái | File / thư mục | Nội dung |
|---|---|---|
| Sửa | .gitignore | Ignore runtime riêng |
| Tạo | conftest.py | Runtime cho pytest thông thường, khôi phục env sau session |
| Tạo | pytest.ini | Tắt cacheprovider, capture=sys |
| Tạo | tools/pytest_runtime.py | Tạo parent UUID riêng mỗi invocation; không dùng TEMP mặc định |
| Sửa | tools/run_h07_acceptance.py | Env/args riêng và thống kê JUnit |
| Tạo | tests/test_pytest_runtime.py |7 regression cases, gồm subprocess/fault injection |
| Sửa | README.md | Link bản sửa và kết quả hiện hành |
| Sửa | docs/MA_TRAN_H07.md | Bằng chứng mới, giữ PI3.1 PARTIAL |
| Sửa | docs/bao_cao_h07/06_MA_TRAN_KIEM_THU.md | Ghi đợt116 PASS mới, giữ lịch sử |
| Sửa | docs/bao_cao_h07/12_MA_TRAN_NGHIEM_THU.md | Cập nhật PI2.3 và cách phân loại ERROR |
| Tạo | docs/bao_cao_h07/13_SUA_LOI_PYTEST_WINDOWS11.md | Nguyên nhân, giới hạn, hướng dẫn xác minh |
| Tạo | docs/bao_cao_h07/DANH_SACH_FILE_SUA_PYTEST.md | Bản kê này |
| Giữ và đưa vào bằng chứng | docs/bao_cao_h07/evidence/20261116T184504Z_6d5e3a/ | Log lỗi người dùng có sẵn trước bản sửa, không sửa nội dung |
| Tạo | docs/bao_cao_h07/evidence/pytest_temp_fix_20261116T185415Z/ | Lần trung gian115 PASS |
| Tạo | docs/bao_cao_h07/evidence/pytest_temp_fix_20261116T185537Z/ | Lệnh pytest cuối116 PASS và ACL chỉ đọc |
| Tạo | docs/bao_cao_h07/evidence/20261116T185722Z_cc572a/ | Acceptance mới: stdout/stderr/JUnit/summary/manifest/audit |
| Giữ và bổ sung | docs/evaluations/dashboard_http_*_http_2ac702e9ae40.json; *_97ccc5c7cf0d.json | TCP dashboard của run lỗi cũ và run mới |
| Giữ và bổ sung | docs/evidence/tcp_20261116T184531Z_86e3d0/; tcp_20261116T185844Z_088f17/ | TC download của hai lần chạy |
| Giữ và bổ sung | docs/h07/evidence/20261116T184534Z_00a490/; 20261116T185850Z_f242be/ | Hiệu năng/fixture sentinel của hai lần chạy |

SQLite và runtime fixture vẫn bị Git ignore; không đưa DB nghiệp vụ/credential vào PR. Danh sách file chính xác có trong diff commit/PR; các hàng thư mục trên đại diện toàn bộ log/CSV/JSON bên trong, không phải file mô phỏng.
