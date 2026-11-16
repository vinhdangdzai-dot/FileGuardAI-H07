Các phần còn thiếu của nghiệm thu H07 được bổ sung trực tiếp trên ứng dụng hiện có: lọc nhật ký theo UTC/action/AI/HTTP với thống kê và CSV cùng phạm vi; trang AI Training chỉ đọc dataset, trọng số thật và lịch sử; mọi dữ liệu quản trị chỉ admin truy cập. Lỗi SQLite trả503 trước khi stream, lỗi audit login không cấp quyền, logout vẫn hủy session.

Windows kiểm tra đường dẫn cuối cùng của handle đã mở trước khi trả nội dung, kèm bài kiểm thử hoán đổi junction thật. AI chỉ cảnh báo, policy độc lập vẫn quyết định quyền tải tệp.

Thí nghiệm offline mới gộp các family chia sẻ canonical key để tránh leakage: train6500/validation1999/test1501, refit development8499 sau lựa chọn C trên validation. LR v1, LR v2 và Regex cùng đạt100% trên strict synthetic holdout và public236; không chứng minh ưu thế v2 hoặc chất lượng trên traffic thực. Dataset, model đang triển khai, frozen v2 và SQLite người dùng giữ nguyên hash; không đổi latest evaluation pointer.

Kiểm thử trên Windows11/Python3.12.10/scikit-learn1.9.1:

- Pytest109 PASS,3 SKIP,15 subtests PASS; cảnh báo InconsistentVersionWarning được coi là lỗi.
- TCP dashboard/auth/CSV41 PASS; download33 PASS,0 FAIL,3 symlink SKIP do quyền Windows.
- Hiệu năng3×48 request/4workers:144/144 log SQLite, integrity ok;90/90 policy violations chặn;36/36 tải hợp lệ đúng body;0 sentinel leak,0 lỗi.
- Hai bài kiểm thử handle/junction Windows PASS; không thay thế bằng chứng3 symlink thật đang SKIP.

12 tài liệu trong docs/bao_cao_h07, bảng HTTP từng TC, JUnit, stdout/stderr, manifest, metrics/PNG/predictions được giữ làm chứng cứ. Ma trận:11 PASS,1 PARTIAL (PI3.1 symlink thật), không khẳng định12/12 hoàn tất. Giới hạn: chưa Windows Python3.11/POSIX/SMB/production load, ACL/secret/TLS theo môi trường, corpus công khai có source bias và không blind real-world. PR phục vụ review; không merge main.
