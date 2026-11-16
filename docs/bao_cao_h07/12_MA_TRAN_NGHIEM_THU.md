# 12 — Ma trận12 tiêu chí và hồ sơ bốn chương

Bản nghiệm thu ngày 17/11/2026 (giờ Việt Nam). Phạm vi: MVP localhost Windows 11; không phải chứng nhận triển khai Internet.

| PI | Yêu cầu | Tài liệu | Mã / test / bằng chứng | Trạng thái | Kết quả thực tế |
|---|---|---|---|---|---|
| 1.1 | Rủi ro CWE-22 | [01_PHAN_TICH_RUI_RO.md](01_PHAN_TICH_RUI_RO.md) | [Mã](../../app/security.py) / [test](../../tests/test_security.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PASS | 11 kịch bản, kiểm soát và giới hạn |
| 1.2 | Quy trình AI | [02_QUY_TRINH_AI.md](02_QUY_TRINH_AI.md) | [Mã](../../app/ml_features.py) / [test](../../tests/test_ml.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PASS | 18/30 features, LR, scaler và không cấp quyền |
| 1.3 | UML Activity | [03_UML_ACTIVITY.md](03_UML_ACTIVITY.md) | [Mã](../../app/web.py) / [test](../../tests/test_app.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PASS | 200/403/404/503 và AI lỗi |
| 2.1 | Kiến trúc | [04_KIEN_TRUC_HE_THONG.md](04_KIEN_TRUC_HE_THONG.md) | [Mã](../../app/web.py) / [test](../../tests/test_review.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PASS | Module/I/O và boundary |
| 2.2 | SQLite / ERD | [05_CO_SO_DU_LIEU.md](05_CO_SO_DU_LIEU.md) | [Mã](../../app/database.py) / [test](../../tests/test_acceptance_extensions.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PASS | 144/144 dòng; integrity ok; filter/error tests |
| 2.3 | Kiểm thử | [06_MA_TRAN_KIEM_THU.md](06_MA_TRAN_KIEM_THU.md) | [Mã](../../tools/run_h07_acceptance.py) / [test](../../tests/test_app.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PASS | 109 PASS +3 SKIP minh bạch; TCP74 PASS |
| 3.1 | IPS / symlink | [07_CO_CHE_IPS.md](07_CO_CHE_IPS.md) | [Mã](../../app/security.py) / [test](../../tests/test_windows_handle.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PARTIAL | Traversal/junction/handle PASS; symlink thật3 SKIP |
| 3.2 | Bảo vệ / truy vấn log | [05_CO_SO_DU_LIEU.md](05_CO_SO_DU_LIEU.md) | [Mã](../../app/log_filters.py) / [test](../../tests/test_acceptance_extensions.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PASS | Admin, filters, triggers, backup; không OS tamper-proof |
| 3.3 | Ít nhất5 Use Case | [08_USE_CASE.md](08_USE_CASE.md) | [Mã](../../app/web.py) / [test](../../tests/test_app.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PASS | UC01–UC05 đúng yêu cầu, đủ luồng/ngoại lệ/tests |
| 3.4 | UI / phân quyền | [09_GIAO_DIEN_PHAN_QUYEN.md](09_GIAO_DIEN_PHAN_QUYEN.md) | [Mã](../../app/auth.py) / [test](../../tests/test_auth.py) / [kết quả](evidence/20261116T182248Z_5acba3/pytest.xml) | PASS | Admin-only; AI Training chỉ đọc; CSV/CSRF/RBAC |
| 4.1 | Metrics / performance | [10_DANH_GIA_MO_HINH.md](10_DANH_GIA_MO_HINH.md) | [Mã](../../tools/evaluate_strict_groups.py) / [test](../../tests/test_strict_groups.py) / [kết quả](../evaluations/20261116T181019Z_dea9ec/results.json) | PASS | LR/Regex, confusion matrices; TCP144; không suy rộng |
| 4.2 | Dữ liệu / independent protocol | [11_DU_LIEU_HUAN_LUYEN.md](11_DU_LIEU_HUAN_LUYEN.md) | [Mã](../../ml/strict_groups.py) / [test](../../tests/test_strict_groups.py) / [kết quả](../evaluations/20261116T181019Z_dea9ec/results.json) | PASS | Canonical-group split, provenance public; không blind real-world |


**Tổng:11 PASS,1 PARTIAL,0 FAIL ở mức minimum MVP. Không xác nhận12/12 đã hoàn tất.** PI3.1 chỉ đổi PASS sau khi có bằng chứng chạy symlink thật; không tính SKIP thành PASS. PASS nghĩa có triển khai/bằng chứng trong phạm vi ghi rõ, không phải hội đồng đã chấm Đạt hoặc chất lượng production. Những tài liệu06/07 có PARTIAL chi tiết không phải hai PI khác nhau.

Bổ sung sau CI: [run3839f3d](evidence/ci_3839f3d.json) thành công trên Windows Server2025 với112 PASS,0 SKIP,15 subtests PASS;3 symlink thật đã chạy. Windows11 cục bộ/TCP vẫn3 SKIP. Giữ PI3.1 PARTIAL theo môi trường trình diễn Windows11 đích, không phủ nhận bằng chứng symlink trên CI và không tự đổi3 SKIP cũ thành PASS.

Hồ sơ khóa luận: Chương1 dùng01+02 (bài toán/rủi ro/cơ sở LR); Chương2 dùng03+04+05+08 (phân tích/thiết kế); Chương3 dùng07+09 và mã nguồn (cài đặt/bảo vệ); Chương4 dùng06+10+11+12 (thực nghiệm, tái lập, giới hạn). Bộ bốn chương trước tại [docs/h07](../h07) được giữ làm nền, các số/quyền hiện hành theo hồ sơ này.

Chạy lại từ root project với venv: `python -m pytest -q -rs`, `python tools/run_h07_acceptance.py`. Thí nghiệm mới chỉ đọc dữ liệu, lưu artifact thư mục duy nhất: `python tools/evaluate_strict_groups.py`. Không dùng train_model để khởi động demo hoặc tự thay deployed model.

Đợt chứng cứ [evidence/20261116T182248Z_5acba3](evidence/20261116T182248Z_5acba3/summary.json) giữ lệnh,exitcode,stdout,stderr,JUnit,bảng HTTP,hash bảo vệ. [Run strict](../evaluations/20261116T181019Z_dea9ec) giữ split/plan/metrics/plots/predictions/model đóng băng. Thời gian UTC trong tên run là16/11, tương ứng rạng sáng17/11 Việt Nam; không sửa timestamp thành giờ giả.

Việc còn lại: chạy3symlink trên máy có đặc quyền, thử POSIX/SMB, review ACL/secret/TLS theo môi trường triển khai, corpus traffic thực và blind labels, kiểm UI thủ công, định dạng bản Word theo mẫu trường. Không xóa dữ liệu, model hoặc bằng chứng cũ; không merge main. PR chỉ phục vụ review.

**Trạng thái: PARTIAL — 11/12 PASS, 1/12 PARTIAL.** Đối chiếu [ma trận tổng hợp](12_MA_TRAN_NGHIEM_THU.md). Bằng chứng chạy thực tế: [summary](evidence/20261116T182248Z_5acba3/summary.json), [pytest](evidence/20261116T182248Z_5acba3/pytest.stdout.txt), [bảng HTTP](evidence/20261116T182248Z_5acba3/http_test_cases.csv).
