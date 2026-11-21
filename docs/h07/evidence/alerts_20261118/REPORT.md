# Kết quả nâng cấp cảnh báo tự động — 18/11/2026

## Chức năng đã thực hiện

Tái sử dụng pipeline trong app/web.py, dịch vụ Gemini app/ai_explanations.py,
SQLite nghiệp vụ và pipeline strict canonical split. Không xây lại ứng dụng.

- Mỗi request tiếp tục được LR đánh giá và chính sách đường dẫn xử lý độc lập.
- BLOCK tạo cảnh báo ưu tiên cao; LR suspicious với ALLOW/MISS tạo cảnh báo
  ưu tiên trung bình. Không gọi mọi BLOCK là khai thác thành công.
- Nhật ký, nhóm cảnh báo và liên kết Event ID được commit cùng giao dịch,
  trước khi đưa đặc trưng vào hàng đợi Gemini. Không đợi API để cảnh báo.
- Gom trùng theo IP/rule/nhóm đặc trưng, cửa sổ cố định 60 giây, giữ từng log
  và liên kết sự kiện. Nhóm đã xử lý có sự kiện mới sẽ tạo nhóm mới.
- Trang Admin /dashboard/alerts có trạng thái mới/đã xem/đã xử lý, lọc trạng
  thái/ưu tiên, phân trang 50 nhóm, link Event Detail. State/settings có CSRF
  và audit. Guest/Auditor không được truy cập.
- Dashboard và trang cảnh báo polling 5 giây, timeout 4 giây, backoff lỗi
  tối đa 60 giây. Tối đa 3 thông báo/phút/trang, không bỏ nhật ký vì rate limit.
- Admin bật/tắt thông báo độc lập với bật/tắt giải thích Gemini. Tắt thông
  báo vẫn tiếp tục lưu cảnh báo. Không gửi Telegram/email trong đợt này.
- Gemini tiếp tục xử lý nền, chỉ nhận đặc trưng sạch, không IP/đường dẫn/tên
  tệp/nội dung tệp/mật khẩu/token người dùng; API không sửa ALLOW/BLOCK/MISS.

Thiết kế, sơ đồ, quy tắc và hướng dẫn vận hành: docs/h07/AUTOMATIC_ALERTS.md.

## Kết quả kiểm thử thực tế

| Bộ kiểm thử | PASS | FAIL | ERROR | SKIP | Bằng chứng |
|---|---:|---:|---:|---:|---|
| Pytest toàn bộ trong acceptance | 278 | 0 | 0 | 3 | docs/bao_cao_h07/evidence/20261118T094612Z_944e9d/pytest.stdout.txt và pytest.xml |
| Subtest, không cộng vào testcase | 15 | 0 | 0 | 0 | cùng stdout |
| Regression cảnh báo mới | 11 | 0 | 0 | 0 | focused-final.stdout.txt |
| Dashboard TCP | 41 | 0 | 0 | 0 | acceptance/dashboard_tcp.stdout.txt |
| Download TCP | 33 | 0 | 0 | 3 | acceptance/download_tcp.stdout.txt |
| Chrome đầy đủ sau sửa | 475 | 0 | 0 | 0 | docs/ui/browser_20261118T095624Z_8fda86/results.json |
| Chrome cảnh báo/rate limit/mất mạng | 16 | 0 | 0 | 0 | docs/ui/alerts_20261118T095815Z_9b7273/results.json |

Pytest chạy 216,32 giây. Lệnh tools/run_h07_acceptance.py có cả sáu bước
pytest, dashboard_tcp, download_tcp, performance, symlinks, audit exit 0.
Không cộng gộp các bộ có testcase trùng lặp thành một tổng giả.

Ba SKIP pytest là symlink trên Windows thiếu quyền: tests/test_app.py:49,
tests/test_security.py:54 và :66. Symlink probe exit 0 không biến SKIP/WinError
1314 thành PASS. Giữ nguyên kết quả thực tế.

Regression xác minh benign, tệp không tồn tại, traversal, LR false positive
vẫn tải 200/cảnh báo trung bình và LR false negative vẫn BLOCK 403/cảnh báo
cao; Gemini network/timeout/quota/authentication/invalid_response; gom trùng,
cửa sổ thời gian, nguồn khác nhau, trạng thái, lọc, phân trang, feed cursor,
phân quyền/CSRF và init DB không mất log. Bộ Gemini hiện có tiếp tục kiểm tra
privacy, cache, rate limit, phản hồi lỗi và lỗi SQLite sidecar.

Chrome sử dụng fixture có ghi rõ, dữ liệu SQLite/credential riêng và TCP
localhost. Kiểm tra 1440/768/390px, Light/Dark, trạng thái thật qua form,
cảnh báo có ngay khi provider còn chờ, polling tự hiển thị cảnh báo,
giới hạn 3 thông báo trong khi vẫn lưu đủ 4 nhóm mới, lỗi mạng và phục hồi.
Không có lỗi JavaScript hoặc tải tài nguyên ở lượt đầy đủ cuối.

### Các lỗi phát hiện và sửa, không che giấu

- Unit lượt đầu: 9 PASS, 2 FAIL. Một fixture dùng model thật nhưng giả định
  missing.txt luôn benign; đổi fixture sang dự đoán benign có kiểm soát, giữ
  kiểm thử false positive riêng. Một test vá đồng hồ time toàn cục làm phiên
  Flask hết hiệu lực; dùng clock riêng của module để kiểm tra cửa sổ 60 giây.
  Không sửa dataset, nhãn hoặc model thật để làm test PASS.
- Chrome đầy đủ lượt đầu: 472 PASS, 3 FAIL, lưu nguyên ở
  docs/ui/browser_20261118T094628Z_72cd16/results.json. Hai FAIL do tràn ngang
  tại 390px. Nhãn screen-reader position:absolute có containing block nằm
  ngoài vùng bảng; thêm position:relative cho form cảnh báo để nhãn nằm
  trong vùng cuộn. Không che lỗi bằng overflow:hidden toàn trang.
- FAIL trạng thái đọc hàng đầu tiên sau khi cảnh báo mới làm đổi thứ tự.
  Test nay đối chiếu chính xác action/Alert ID đã cập nhật; backend không
  thay đổi nghiệp vụ để làm vừa assertion.
- Log chẩn đoán và ảnh trước sửa được giữ. Các lượt focused cuối 12/12 và
  16/16 PASS; lượt đầy đủ cuối 475/475 PASS. Lần đầu tool focused dùng tên
  runtime không hợp lệ bị ERROR trước khi chạy browser, đã sửa dùng allocator
  hợp lệ; log browser-focused.stderr.txt giữ nguyên.

## Huấn luyện và đánh giá chạy thực tế

Lệnh python tools/evaluate_strict_groups.py tạo run mới:
docs/evaluations/20261118T094256Z_8c5825/.

- Dữ liệu có nhãn: 10.000 mẫu, seed 2026, scikit-learn 1.9.1.
- Train 6500; validation 1999; test 1501. Sau khi chọn C trên validation,
  refit train+validation 8499, không dùng test để fit/chọn C.
- 26 thành phần nhóm sau gộp family/canonical; family, chuỗi gốc và canonical
  không giao nhau giữa train/validation/test. C v2 chọn 0.1, threshold 0.5.
- LR v1, LR v2 và Regex đều Accuracy=Precision=Recall=F1=1.0 trên test;
  từng confusion matrix [[1001,0],[0,500]]. Corpus ngoài 236 mẫu: từng phương
  pháp đều 1.0, matrix [[118,0],[0,118]]. Không khẳng định v2 tốt hơn v1/Regex.
- Thời gian end-to-end amortized trên test trong run: LR v1 43,059 µs/path,
  LR v2 101,519 µs/path, Regex 4,001 µs/path. Đây là batch benchmark máy này,
  không phải độ trễ HTTP hoặc số đo suy luận Gemini.
- Lưu plan trước fit, models_frozen_before_test.json, split.csv, dự đoán,
  results.json, biểu đồ và model mới ở thư mục riêng. Model v1/v2 của run là
  model thử nghiệm tái huấn luyện theo phiên bản đặc trưng, không tự thay
  model đang triển khai. Giữ pointer benchmark/dashboard hiện có.

Số liệu lấy trực tiếp từ results.json; **100% trên dữ liệu tổng hợp/corpus
lexical không chứng minh phát hiện/ngăn chặn 100% ngoài thực tế**. Dữ liệu
đã được nghiên cứu trước đó, không phải blind test độc lập thế giới thực.
Không chỉnh đặc trưng theo kết quả test đợt này.

## Hiệu năng và bảo toàn dữ liệu

Acceptance TCP: 3 lượt × 48 request, 4 worker, tổng 144 log/144 request,
SQLite integrity=ok, failures=0. Mỗi lượt chặn 30/30 trường hợp nguy hiểm
trong fixture. Throughput lần lượt 33,17 / 37,33 / 39,06 RPS; không khẳng định
hiệu năng production hoặc so sánh nhân quả với baseline khác điều kiện.

SHA-256 protected_unchanged đều true trong acceptance summary.json và
browser results.json: data/paths_synthetic.csv, artifacts/model.joblib,
model thử nghiệm cũ và instance/events.sqlite3. Dataset giữ SHA
2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0.
Không chạy Flask production hoặc thay DB đang dùng bằng DB kiểm thử.

## File thay đổi trong đợt cảnh báo

| File | Nội dung |
|---|---|
| app/alerts.py | DDL, quy tắc, dedup, filter/phân trang, cấu hình thông báo |
| app/database.py | Init bảng mới; ghi log/cảnh báo trong cùng transaction |
| app/web.py | Trang quản lý, state/settings/feed chỉ Admin; gắn cảnh báo vào Event Detail |
| app/static/alerts.js | Polling, timeout/backoff, rate limit và DOM an toàn |
| app/static/style.css | Fix containing block nhãn hỗ trợ truy cập trong bảng |
| app/templates/alerts.html | Trang quản lý cảnh báo |
| app/templates/_alert_live.html | Vùng thông báo trực tiếp |
| app/templates/base.html | Navigation Security Alerts và layout quản trị |
| app/templates/dashboard.html | Hiển thị thông báo trực tiếp |
| app/templates/event_detail.html | Hiển thị cảnh báo liên kết Event ID |
| tests/test_alerts.py | 11 regression testcase mới |
| tools/ui_ai_analysis_checks.py | Kiểm tra cảnh báo không chờ API, polling, responsive và đúng Alert ID |
| tools/verify_alerts_browser.py | Browser/TCP tập trung, network/rate limit và chẩn đoán overflow |
| docs/h07/AUTOMATIC_ALERTS.md | Thiết kế, sơ đồ, hướng dẫn và giới hạn |
| docs/h07/evidence/alerts_20261118/ | Báo cáo, log, manifest |

Tái sử dụng app/ai_explanations.py, tools/evaluate_strict_groups.py và
ml/strict_groups.py; không sửa thêm chúng trong đợt này. Các thay đổi Gemini
chưa commit từ đợt trước vẫn giữ nguyên, không ghi đè.

Thư mục kết quả mới: run huấn luyện trên; acceptance
20261118T094612Z_944e9d; TCP tcp_20261118T095001Z_dc3691; H07 probe
20261118T095005Z_d1421f; dashboard_http_20261116T172733Z_800c38_http_c72d6539ce28.json;
các thư mục browser_/alerts_ ngày 18/11 từ 09:46 UTC trở đi có tên trong log.
Các ảnh alerts_fixture_* ở lượt đầy đủ cuối và light/dark_*.png ở focused
là ảnh chạy thật trên fixture, không phải mockup hay phản hồi Gemini thật.

## Giới hạn và vận hành

- Môi trường chưa có AI_EXPLANATION_API_KEY; không thử Gemini thật trong
  đợt này. Dịch vụ và contract được mock kiểm thử, không khẳng định model
  Google cụ thể đã hoạt động. Cấu hình theo GEMINI_INTEGRATION.md và dùng
  tools/check_gemini_connection.py khi key/model có sẵn, không gửi key vào chat.
- Hàng đợi Gemini nằm trong bộ nhớ; đầy/restart có thể mất giải thích chưa
  xử lý. Cảnh báo và nhật ký SQLite đã commit vẫn tồn tại. Không tự retry
  vô hạn hoặc đảm bảo mọi cảnh báo có giải thích.
- Rate limit thông báo áp dụng từng trang/tab. Không có Telegram/email hoặc
  thông báo ngoài browser khi đóng trang. Muốn triển khai ngoài cần thiết
  kế outbox, người nhận và chính sách chia sẻ dữ liệu riêng.
- Bảng quản lý là snapshot lúc tải; vùng polling cho biết nhóm mới và link
  sự kiện. Tải lại trang để cập nhật bộ đếm/hàng. Không tự đổi trạng thái khi
  mở chi tiết; Admin đánh dấu rõ ràng bằng form.
- Chưa triển khai Ubuntu/VPS. Không commit/push/merge hoặc deploy production.
