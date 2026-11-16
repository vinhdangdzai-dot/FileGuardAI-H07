# 07 — Cơ chế ngăn chặn độc lập với AI

Bản nghiệm thu ngày 17/11/2026 (giờ Việt Nam). Phạm vi: MVP localhost Windows 11; không phải chứng nhận triển khai Internet.

Đây là IPS tầng ứng dụng tại chức năng tải tệp, không phải firewall mạng. Quyết định policy không phụ thuộc probability hay nhãn LR. Thư mục `shared_files` là root cho phép, không phải mọi đường dẫn có cùng tiền tố chuỗi.

1. Flask giải mã query transport đúng một lần. `+` của query là dấu cách; muốn tên có dấu cộng phải gửi `%2B`. Mã tải tệp không gọi unquote lặp.
2. Từ chối đường dẫn rỗng/quá giới hạn/NUL, thành phần `..`, rooted/drive/UNC/colon và escape cấu trúc còn sót (kể cả chuỗi lồng `%25`). Chính sách nghiêm chấp nhận mất một số tên literal chứa escape nguy hiểm; không coi mọi `%` là độc hại.
3. Resolve đường dẫn trong root; kiểm tra containment bằng quan hệ đường dẫn, không startswith; symlink/junction resolve ra ngoài bị từ chối.
4. Chỉ mở tệp thường. POSIX dùng cơ chế không theo link khi có hỗ trợ; Windows lấy đường dẫn chuẩn của **handle đã mở** qua GetFinalPathNameByHandleW rồi kiểm tra với root đã ghim. Không dựa vào việc resolve lại chuỗi request sau open. Lỗi truy vấn handle đóng file và từ chối.
5. Trong phạm vi nhưng thiếu tệp→404; vi phạm policy→403; hợp lệ→200. Lỗi ghi log→503 trước stream.

Nguyên tắc giải mã để truy cập khác góc nhìn ML: ML v2 có raw+hai view hữu hạn để phát hiện, nhưng không được biến view thành đường dẫn tải. Ví dụ `%252e%252e%252f...` qua transport còn `%2e%2e%2f...` bị policy từ chối, không giải mã rồi mở lần nữa.

Test Windows hoán đổi junction sau check trước open chứng minh handle cuối cùng ra ngoài bị chặn; test lỗi API chứng minh đóng handle. Ba symlink thật vẫn SKIP trên Windows11 cục bộ vì quyền OS. CI Windows Server2025 đã chạy cả112 tests,0 SKIP, bao gồm3 symlink thật: [bằng chứng CI](evidence/ci_3839f3d.json). Không thay kết quả cục bộ bằng kết quả OS khác, không lấy junction thay thế symlink. PI3.1 vẫn PARTIAL cho yêu cầu trình diễn symlink trên Windows11 đích; bằng chứng nhánh Windows có tiến bộ rõ ràng.

Giới hạn: không bảo vệ trước đối thủ có quyền thay public root/ACL, hardlink tới dữ liệu nhạy cảm, kernel/provider không tin cậy hoặc cấu hình filesystem mạng chưa kiểm thử. Cần root chỉ đọc với tài khoản phục vụ, cấm upload ghi tùy ý, tách private storage. Không tuyên bố hết mọi TOCTOU trên mọi nền tảng.

Mã: [security.py](../../app/security.py), [Windows tests](../../tests/test_windows_handle.py). API tham chiếu: [Microsoft GetFinalPathNameByHandleW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew).

**Trạng thái: PARTIAL — chặn đã kiểm chứng; symlink thật còn SKIP.** Đối chiếu [ma trận tổng hợp](12_MA_TRAN_NGHIEM_THU.md). Bằng chứng chạy thực tế: [summary](evidence/20261116T182248Z_5acba3/summary.json), [pytest](evidence/20261116T182248Z_5acba3/pytest.stdout.txt), [bảng HTTP](evidence/20261116T182248Z_5acba3/http_test_cases.csv).
