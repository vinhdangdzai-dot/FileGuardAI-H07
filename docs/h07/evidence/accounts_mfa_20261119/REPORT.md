# Báo cáo thực nghiệm tài khoản và MFA — 19/11/2026

## Kết quả chức năng

Đã bổ sung Argon2id, TOTP bắt buộc cho Admin (hash file và SQLite), backup
codes dùng một lần, AES-256-GCM cho seed với keyring riêng, RBAC và session
reference có thể thu hồi ở server. Luồng đăng ký, username/email login, profile,
đổi/reset password, khóa/mở/cấp quyền và audit SQLite của phần tài khoản tiếp
tục được dùng. Không có chế độ bỏ TOTP khi TESTING.

Admin password đúng chỉ chuyển sang `/login/mfa`, chưa có role quản trị.
Admin cũ dùng password cũ, thiết lập TOTP lần đầu và lưu tám mã dự phòng.
Đổi password/khôi phục email không tắt TOTP. Khóa hoặc đổi quyền thu hồi
phiên/challenge. Logout thu hồi SID trên SQLite, từ chối cookie đã sao chép.

Schema version 2 chỉ cộng thêm bảng; dữ liệu và hash cũ được giữ khi migration.
Login hợp lệ nâng hash cũ bằng compare-and-swap/ghi file nguyên tử có backup,
không tự đổi password. Có CLI recovery trực tiếp trên máy chủ, yêu cầu quyền
console, password Admin, xác nhận rõ ràng và audit; login sau recovery vẫn
bắt buộc thiết lập TOTP mới. Không có endpoint web tắt MFA.

## Kết quả đã chạy

**Lượt chốt đã hoàn tất.** Số liệu lấy từ verification-summary.json và các
artifact được chỉ rõ, không gộp PASS giữa các suite:

| Bộ kiểm chứng cuối | Kết quả | Bằng chứng |
|---|---|---|
| Pytest trực tiếp | **372 PASS, 0 FAIL, 0 ERROR, 3 SKIP**; 15 subtest PASS | pytest-verified.xml, pytest-verified.stdout.txt |
| Pytest bên trong acceptance | **372 PASS, 0 FAIL, 0 ERROR, 3 SKIP** | docs/bao_cao_h07/evidence/20261118T174808Z_56b9fa/summary.json |
| Acceptance | **6/6 tiến trình exit 0** | acceptance-verified.stdout.txt, execution-verified.json |
| Dashboard TCP | **43 PASS, 0 FAIL** | summary của acceptance cuối |
| Download TCP | **33 PASS, 0 FAIL, 3 SKIP** | summary của acceptance cuối |
| Hiệu năng tải tệp | **144 request, 144 dòng SQLite, 0 failure** | performance trong summary cuối |
| Probe symlink riêng | **3 SKIP, WinError 1314** | symlinks.stdout.txt của acceptance cuối |
| Chrome tài khoản/TOTP | **74 PASS, 0 FAIL, native exit 0** | docs/ui/accounts_20261118T174446Z_d1d768/results.json |
| Chrome regression | **475 PASS, 0 FAIL, native exit 0** | docs/ui/browser_20261118T174520Z_fbef9d/results.json |
| TCP hai lần khởi động OS process | **32 PASS, 0 FAIL, native exit 0** | docs/auth/evidence/restart_20261118T174841Z_3dd918/results.json |

23 testcase MFA raw requests nằm trong lượt Pytest chốt. Ba SKIP symlink ở
mỗi suite phải đọc riêng, không cộng hoặc gọi là PASS. SMTP/Gemini thật,
thiết bị Authenticator vật lý và VPS không được kiểm chứng trong đợt này.

Sau các lượt trên có chỉnh nhãn breadcrumb tài khoản/2FA; smoke render tám
trang liên quan đạt 8 PASS, 0 FAIL (breadcrumb-smoke-verified.json). Probe
đầu ghi 4 PASS/4 FAIL ở phép so sánh nhãn tiếng Việt do PowerShell pipe đổi
literal của script sang ASCII; cả tám HTTP đều 200. Giữ log gốc, sửa literal
của probe bằng Unicode escape, không sửa dữ liệu/HTML để khớp kết quả.

### Lịch sử các lượt được giữ lại

| Lượt | PASS | FAIL | ERROR | SKIP | Bằng chứng |
|---|---:|---:|---:|---:|---|
| Mốc trước yêu cầu Argon2/TOTP | 349 | 0 | 0 | 3 | ../accounts_20261118/pytest-full.xml |
| MFA focused đầu tiên | 14 | 0 | 0 | 0 | ../accounts_mfa_20261119-focused.xml |
| MFA focused mở rộng | 19 | 0 | 0 | 0 | mfa-focused.xml |
| Pytest tích hợp đầu | 361 | 2 | 0 | 3 | pytest-first.xml |
| Rerun pipeline Gemini với bước TOTP | 4 | 0 | 0 | 0 | pipeline-rerun.xml |
| Pytest sau sửa pipeline | 371 | 0 | 0 | 3 | pytest-final.xml |
| Pytest lặp có lỗi fixture theo giờ thật | 371 | 0 | 1 | 3 | pytest-complete.xml |
| Regression fixture clock + MFA + dataset | 38 | 0 | 0 | 0 | clock-regression.xml |

Các lượt Pytest toàn bộ còn có **15 subtest PASS**, được giữ riêng với số
testcase JUnit; không cộng để tăng số PASS. Ba SKIP do quyền symlink Windows
ở tests/test_app.py:49 và tests/test_security.py:54/:66.

Hai FAIL đầu: hai công cụ kiểm tra pipeline Gemini vẫn dừng sau password
và truy cập Dashboard khi chưa hoàn thành TOTP. Đã sửa harness để thực hiện
TOTP qua TCP, giữ nguyên probe API, assertion BLOCK, lưu Event/Alerts và số
lượt provider. Kết quả Gemini trong đợt này hoàn toàn là mock, không kết luận
đã kết nối API thật từ các test đó.

ERROR fixture xuất hiện ở test_invalid_dataset_parameters_rejected[query1]
trong lúc khởi tạo session Admin. Fixture dùng giờ thật giữa sinh và gửi OTP,
có thể đổi cửa sổ 30 giây. Đã giữ đồng hồ ổn định cho fixture unit và vẫn gửi
password/OTP qua endpoints thật. Test MFA dùng raw requests kiểm tra riêng
replay, hết hạn/cửa sổ, race và rate-limit; Chrome/TCP dùng giờ thật. Không
nới cửa sổ TOTP của runtime, bỏ assertion hoặc đổi ERROR thành SKIP.

Lượt kiểm chứng cuối đã có ở pytest-verified.*, acceptance-verified.*,
execution-verified.json và verification-summary.json; các lượt trước không
bị ghi đè. Mã trả về native của cả hai tiến trình cuối đều bằng 0.

## HTTP, Chrome và bảo toàn dữ liệu

- TCP qua hai tiến trình Flask TESTING=False độc lập: 32 PASS, 0 FAIL ở
  docs/auth/evidence/restart_20261118T172405Z_c7bf09/results.json. Có password
  persistence, MFA qua restart, thay hash, download 200 và traversal 403.
- Chrome account/TOTP: 74 PASS, 0 FAIL ở
  docs/ui/accounts_20261118T172900Z_a25eda/results.json. Có 54 ảnh,
  Light/Dark tại 1440/768/390px. Seed/QR đã che trên ảnh setup; mã dự phòng
  không được ghi vào báo cáo. Kiểm tra Admin chưa có MFA bị redirect, QR nội
  bộ, CSRF, khóa/mở, reset và cookie sao chép bị thu hồi sau logout.
- Chrome regression: 475 PASS, 0 FAIL ở
  docs/ui/browser_20261118T173044Z_1d28c4/results.json. Không ghi nhận lỗi
  JavaScript hoặc tải static; giữ chart/CSV, bộ lọc, AI, Light/Dark/font controls.
  Zoom của suite là CDP emulation, không chứng nhận phím zoom native.
- Acceptance đợt 20261118T173035Z_0df9b5: sáu tiến trình exit 0; Pytest
  371 PASS/3 SKIP, dashboard TCP 43 PASS, download TCP 33 PASS/3 SKIP,
  hiệu năng 144 request/144 dòng SQLite/0 failure. Probe symlink riêng có
  ba SKIP WinError 1314; exit 0 của probe không được tính là symlink PASS.

JSON Chrome của hai lượt đầu đều ghi assertion PASS nhưng shell trả exit 1:
redirect stderr trong Windows PowerShell sinh NativeCommandError cả khi
Python exit 0. Có probe tối giản native-probe.* để tái hiện riêng tình huống
này; các lượt browser kiểm chứng sẽ lưu trực tiếp $LASTEXITCODE trong
browser-execution.json. Cả hai lượt Chrome kiểm chứng và TCP restart đã
ghi nhận native exit 0. Các traceback sqlite3.OperationalError trong log
browser cũ đến từ phép tiêm lỗi audit có chủ đích để kiểm tra trang 503.
Không suy đoán process PASS chỉ từ việc có ảnh.

Các bullet nêu artifact 17:29–17:34Z bên trên là các lượt trước lượt chốt;
bảng đầu phần này và verification-summary.json gắn chính xác artifact cuối.
Ảnh setup có mask màu magenta để che QR/seed, không phải màu QR của website.

Dataset giữ SHA-256 2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0.
Các report bảo toàn đều xác nhận model đang triển khai, model thực nghiệm,
SQLite nghiệp vụ không đổi; suite account/TCP còn kiểm tra hash Admin thực.
Toàn bộ DB, keyring và tài khoản dùng cho test nằm trong fixture riêng.

## Giới hạn và thao tác cần làm

Người dùng đã chọn tiếp tục password 6–128 ký tự cho demo. Mức tối thiểu 6
chưa đạt ASVS 5.0 6.2.1; chưa có breached-password corpus và MFA toàn vai trò.
Không tuyên bố tuân thủ/chứng nhận ASVS đầy đủ hoặc chống được mọi cuộc tấn công.
TOTP chưa có tính chống phishing như WebAuthn; chưa thử trên thiết bị Authenticator
vật lý. Thiếu quyền symlink Windows là giới hạn test thật, không phải PASS.

SMTP và Gemini thật chưa được gọi trong đợt tài khoản/MFA; cấu hình SMTP qua
môi trường theo USER_ACCOUNTS.md rồi xác minh delivery riêng. Chưa triển khai
VPS hoặc kiểm chứng nhiều worker Gunicorn thật. Windows cần kiểm tra NTFS ACL
keyring; POSIX yêu cầu 0600. Keyring phải sao lưu tách DB; mất/sai khóa đang
dùng sẽ từ chối startup, không tự thay khóa hoặc bỏ MFA. Mailqueue chưa bền qua
restart. Hướng dẫn recovery và quản lý key ở ../../MFA_SECURITY.md.

Người vận hành áp dụng bằng cách backup trước, cài requirements và restart
Flask. Không đổi SECRET_KEY đang cấu hình; production nhiều worker phải dùng
chung secret ổn định và keyring riêng. Lần đăng nhập Admin tiếp theo sẽ yêu
cầu thiết lập TOTP và lưu mã dự phòng. Không commit/push/merge/deploy trong đợt này.

Danh sách **63 file source/test/tool/tài liệu** đã chạm trong phần tài khoản
và MFA nằm ở changed-files.json, kèm SHA-256; từng testcase thực tế ở
test-cases.csv, tổng hợp ở verification-summary.json và checksum evidence ở
manifest.json. Inventory có cả file tạo mới và file có chỉnh sửa từ trước
rồi được bổ sung phần tài khoản; không tự nhận toàn bộ working tree là mới.
Các thay đổi Gemini/Alerts có từ trước trong working tree được giữ nguyên;
không coi toàn bộ git diff hiện có là phần thay đổi tài khoản.
