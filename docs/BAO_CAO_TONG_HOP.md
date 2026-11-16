# Báo cáo tổng hợp rà soát FileGuardAI H07

Ngày **16/11/2026**, lượt rà soát bắt đầu khoảng **23:32, Asia/Saigon**;
timestamp từng phép kiểm tra được lưu trong bằng chứng.
Kết quả dưới đây được lấy từ chương trình đã chạy trong workspace.
Không huấn luyện lại/tuning thêm model ở lần rà soát này. Không push GitHub.

## 1. Phạm vi và môi trường

Đã rà soát app Flask, lớp security, đặc trưng ML v1/v2, SQLite, sáu template,
JS/CSS, các chương trình sinh/huấn luyện/đánh giá dữ liệu, collector nguồn
công khai, các công cụ TCP, bộ tests, script Windows và tài liệu/artifact
thực nghiệm liên quan. Kiểm tra cú pháp thành công **23 file Python**.

Môi trường thực tế: Windows 11 build 26200; Python 3.12.10; Flask 3.1.3;
scikit-learn 1.9.1; NumPy 2.5.5; joblib 1.6.0; pytest 9.2.0;
matplotlib 3.11.2. `pip check`: **No broken requirements found**.

Các bằng chứng của lượt rà soát nằm tại
`docs/reviews/review_20261116T163259Z_049c87/`.

## 2. Những lỗi và điểm thiếu đã sửa

| Thành phần | Phát hiện | Thay đổi và xác minh |
|---|---|---|
| SQLite | Context manager của connection chỉ kết thúc transaction, chưa đóng connection rõ ràng | Dùng `closing` kết hợp transaction trong cả bốn thao tác DB. Test xác nhận connection đã đóng, SQL injection được lưu như text, file DB đổi tên ngay trên Windows |
| Liệt kê kho | `rglob` có thể duyệt vào junction trước khi kiểm tra từng tệp | Duyệt `scandir`, đọc metadata không follow link, loại symlink/reparse trước khi đi xuống. Test junction có guard xác nhận không gọi scandir vào target |
| Windows filename | Thiếu console device và COM/LPT dùng chữ số superscript; basename thiết bị có khoảng trắng trước extension | Bổ sung từ chối `CONIN$`, `CONOUT$`, COM/LPT¹²³ và basename thiết bị sau bỏ khoảng trắng cuối; kiểm tra trước khi mở |
| AI advisory | Load lỗi, inference exception hoặc NaN/xác suất ngoài [0,1] có thể làm hỏng luồng hoặc log | Cô lập lỗi AI, log nhãn `error`/score NULL; security vẫn quyết định 200/403/404 |
| Path quá dài | Chấm AI trước khi kiểm tra độ dài, có thể tốn CPU cho input vốn sẽ bị từ chối | Không chạy feature/model với path >4096 ký tự; nhãn `skipped`, security trả 403, log cắt path ở 4096 như chính sách cũ |
| Query mơ hồ | Nhiều tham số `path` bị lấy giá trị đầu mà không có chính sách rõ ràng | Yêu cầu đúng một `path`; thiếu hoặc trùng đều 403 |
| JSON dashboard | Chỉ kiểm tra key tầng ngoài; thiếu cấu trúc lồng có thể gây 500, NaN có thể hiển thị như số liệu | Thêm validator cho schema lịch sử/v2, count, confusion matrix, metrics khớp matrix, timing và metadata. Không tự sửa số liệu lỗi; hiển thị trạng thái chưa có kết quả hợp lệ |
| Ảnh dashboard | `latest` đổi giữa lúc tải HTML và ảnh làm ảnh của run cũ bị 404 | Đọc run lưu trữ đã nêu trong URL sau kiểm tra tên/containment/schema; vẫn chỉ cho ba tên PNG, cần đăng nhập |
| Bảo toàn huấn luyện | CLI cũ tái sinh CSV và ghi đè model/results | Dùng CSV hiện có; generator từ chối ghi đè; training sao lưu output cũ vào history trước ghi output mới. Test bằng artifact tạm, không thay model triển khai |
| Chia nhóm | Invariant dùng assert và thiếu kiểm tra nhóm quá ít/mixed label | Dùng ValueError, kiểm tra mỗi lớp có ít nhất hai family và các family đồng nhất nhãn; giữ nguyên cách chia dữ liệu hiện tại |
| Generator | Số mẫu lẻ bị làm tròn xuống mà không thông báo | Yêu cầu số chẵn >=60 để số dòng và cân bằng nhãn đúng yêu cầu |
| Tests/evidence | Test v2 phụ thuộc pointer latest; công cụ TCP có thể ghi đè bằng chứng của cùng run | Test hồi quy dùng archive cố định và pointer riêng trong tmp; mỗi lượt dashboard TCP có tên bằng chứng mới |

Quy tắc tên thiết bị Windows đối chiếu với
[Microsoft: Naming Files, Paths, and Namespaces](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file).

Thay đổi không tác động hàm `extract_features`/v2, hệ số model hoặc ngưỡng.
Giao diện và chức năng cũ giữ nguyên; chỉ tăng khả năng xử lý lỗi và kiểm tra.

## 3. Kiểm tra bảo mật đường dẫn

Luồng quyền truy cập vẫn độc lập AI:

1. Flask giải mã transport query một lần.
2. Security từ chối `..`, `.`, absolute/drive/UNC, backslash, ADS, tên thiết
   bị, ký tự điều khiển, thành phần rỗng hoặc hậu tố không hợp lệ.
3. Escape cấu trúc còn sót `%2e/%2f/%5c/%00/%3a/%25` bị từ chối theo chính
   sách, không decode lặp để mở file. Không đồng nhất score cao với HTTP 403.
4. Kiểm tra từng thành phần bằng lstat và reparse flag, resolve containment,
   chỉ mở regular file. POSIX có nhánh O_NOFOLLOW; không chạy nhánh đó trên máy này.
5. Tệp hợp lệ tồn tại -> 200; path hợp lệ nhưng thiếu tệp -> 404;
   vi phạm chính sách -> 403. AI lỗi/không có vẫn giữ phân biệt này.

Kết quả thực nghiệm TCP mới tại `127.0.0.1:5000`:

| Bộ | PASS | FAIL | SKIP |
|---|---:|---:|---:|
| Smoke HTTP cơ bản | 10 | 0 | 0 |
| TCP chi tiết, 36 test case | 33 | 0 | 3 |
| Dashboard và biểu đồ qua TCP | 14 | 0 | 0 |

Đã xác minh Unicode, dấu cách, thư mục con, `../`, `..`, `..\`, absolute,
encoding một/hai/nhiều lớp, junction thoát kho, Windows devices, ADS,
control character, duplicate `path`, input dài, tệp thiếu trong thư mục
con và trường hợp tệp thường được dùng như thư mục cha. Hai trường hợp
cuối trả **404**, không bị ép thành 403 bởi AI.

Không ca TCP đã thực hiện nào trả marker của tệp kiểm chứng ngoài kho.
Ba ca symlink vẫn **SKIP do WinError 1314**, không đánh dấu PASS.
Junction tạo được và đã kiểm tra thành công. Các helper chỉ gỡ link/junction
chính chúng tạo, không xóa target. Server kiểm thử đã tắt sau khi chạy.

[Tổng hợp TCP](evidence/tcp_20261116T163844Z_cc01e8/summary.json),
[bảng đầy đủ đầu vào/mong đợi/thực tế/bằng chứng](evidence/tcp_20261116T163844Z_cc01e8/test_cases.md),
[CSV Excel](evidence/tcp_20261116T163844Z_cc01e8/test_cases.csv),
[TCP dashboard](evaluations/dashboard_http_20261116T154448Z_7a27a7_http_9ccf89f23170.json).

## 4. SQLite và bảo toàn dữ liệu

Database sử dụng thật được mở **read-only** để kiểm tra:

- `PRAGMA integrity_check` -> `ok`.
- 7 bản ghi hiện có: ALLOW/200 = 1, BLOCK/403 = 4, MISS/404 = 2.
- Có đủ các cột IP, path, score/label AI, quyết định, HTTP, lý do,
  timestamp UTC và duration_ms. Không thay schema hoặc sửa các bản ghi cũ.

Database TCP riêng có **43 bản ghi**: 6 HTTP 200, 32 HTTP 403, 5 HTTP 404;
integrity_check = `ok`. Mỗi ca chi tiết đối chiếu một log mới với IP
127.0.0.1, path sau Flask decode, điểm/nhãn tính lại, action, HTTP, lý do,
timestamp và duration hữu hạn không âm. Ca quá dài ghi score NULL và
`skipped` đúng chính sách, không tạo điểm AI giả.

Đối chiếu trước/sau xác nhận **50 file được bảo vệ không đổi**, gồm CSV
gốc, model triển khai, SQLite thật và các file thực nghiệm có sẵn đã đưa
vào snapshot. Artifact mới lưu riêng. Model triển khai SHA-256:
`4d7324aa302ecb3d1b731561210a0041e4aef3f740cc68d9187097a80e5a6322`.

[Snapshot trước sửa](reviews/review_20261116T163259Z_049c87/before.json),
[xác minh bảo toàn và SQLite TCP](reviews/review_20261116T163259Z_049c87/verification.json).

## 5. Audit dữ liệu và chỉ số AI được tính lại

CSV vẫn có **10.000 dòng/10.000 path duy nhất**, benign=5.000,
suspicious=5.000, **35 family**, không trùng exact hoặc xung đột nhãn.
Train/test seed 2026 vẫn đúng **7.999/2.001** mẫu, không giao nhau exact
path hoặc family. V1 và model triển khai có 18 đặc trưng; v2 có 30,
C=0,1 đã chọn bằng validation 1.416 mẫu từ train ở lần thực nghiệm trước.

Lần rà soát này chỉ load pipeline và predict lại; không fit, tuning,
thay nhãn hoặc chọn model. Manifest, nguồn công khai và metrics đều
đối chiếu thành công: **14 kiểm tra toàn vẹn/cấu trúc PASS, 0 FAIL**.
Các kiểm tra đó không đồng nghĩa test hoàn toàn độc lập về ngữ nghĩa.

### Test cố định, 2.001 mẫu

| Method | Accuracy | Precision | Recall | F1 | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LR v1/triển khai | 0,875062 | 1,000000 | 0,750000 | 0,857143 | 1001 | 0 | 250 | 750 |
| LR v2 thực nghiệm | 1,000000 | 1,000000 | 1,000000 | 1,000000 | 1001 | 0 | 0 | 1000 |
| Regex | 0,875062 | 1,000000 | 0,750000 | 0,857143 | 1001 | 0 | 250 | 750 |

### Corpus ngoài đã lưu, 400 mẫu

Cả ba đạt Accuracy/Precision/Recall/F1 = **1,0**,
confusion matrix **`[[200,0],[0,200]]`**. Không có bằng chứng v2 vượt
baseline trên corpus này. Nguồn SecLists và tên file repo Flask được giữ
nguyên; annotation lexical, nguồn tương quan nhãn và phần được chọn
không có mẫu cần hai lớp decode. Không coi là traffic thực tế.

### Thời gian dự đoán mới đo trong lượt audit

7 lượt warm batch, gồm trích đặc trưng và suy luận. Giá trị µs/path là
median batch chia số mẫu; không phải latency từng HTTP request.

| Dataset | LR v1 µs/path | LR v2 µs/path | Regex µs/path |
|---|---:|---:|---:|
| Holdout 2.001 | 11,781259 | 25,160820 | 0,835982 |
| External 400 | 11,306250 | 25,461750 | 0,736250 |

V2 chậm hơn trong lượt này. Thời gian khác các lượt trước do điều kiện
đo/tải hệ thống; không ghép số đo khác lượt để quảng bá tốc độ. Raw batch,
median, P95 và inference-only đều có trong JSON. Các biểu đồ lịch sử vẫn
mang số liệu của lần chạy được nêu trên trang, không bị ghi đè bằng số mới.

[Audit JSON: dữ liệu, model, timings, manifest và SQLite](reviews/review_20261116T163259Z_049c87/audit.json).

## 6. Phát hiện mới về tính độc lập của benchmark

Chuẩn hóa **Unicode NFC -> đúng hai lớp URL decode -> backslash thành
slash -> casefold**, không resolve filesystem: tìm thấy **15 canonical
key giao nhau train/test**, tương ứng **15 dòng test**. Do đó các phát
biểu trước đây “không rò rỉ” chỉ đúng ở mức exact string/family, chưa đủ
để kết luận độc lập về biểu diễn. Đây là nguy cơ tương quan/rò rỉ ngữ
nghĩa, không phải bằng chứng mô hình đã ghi nhớ từng mẫu.

Giữ nguyên test khóa, model và chỉ số trên dashboard. Tạo **phân tích độ
nhạy bổ sung**, loại đúng 15 dòng test có canonical key xuất hiện trong
train, chỉ dựa vào path, không dựa nhãn hoặc dự đoán. Không fit lại model.
Còn **1.986 mẫu**: 1.001 benign + 985 suspicious, không giao canonical
với train theo định nghĩa trên.

| Method | Accuracy | Precision | Recall | F1 | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LR v1 | 0,879154 | 1,000000 | 0,756345 | 0,861272 | 1001 | 0 | 240 | 745 |
| LR v2 | 1,000000 | 1,000000 | 1,000000 | 1,000000 | 1001 | 0 | 0 | 985 |
| Regex | 0,879154 | 1,000000 | 0,756345 | 0,861272 | 1001 | 0 | 240 | 745 |

Đây là phân tích **post-hoc trên benchmark đã biết**, không phải một
test blind mới và không thay thế số liệu test khóa. Family vẫn có chung
bộ sinh và từ vựng; chưa chứng minh generalization ngoài thực tế. Lần
nghiên cứu mới cần nhóm các biến thể canonical cùng một partition và
khóa test độc lập trước thiết kế/tuning, thay vì tiếp tục chọn theo test cũ.

[Cặp path tương đương](reviews/review_20261116T163259Z_049c87/canonical_overlap.csv),
[methodology JSON](reviews/review_20261116T163259Z_049c87/methodology.json),
[dự đoán từng dòng tập con](reviews/review_20261116T163259Z_049c87/sensitivity_predictions.csv).

## 7. Kết quả pytest và kiểm tra hồi quy

Lệnh chạy:

```powershell
..\.venv\Scripts\python.exe -m pytest -q -rs -W error::sklearn.exceptions.InconsistentVersionWarning
```

Thực tế cuối cùng **67 passed, 3 skipped, 15 subtests passed**, không FAIL.
20 test mới đều PASS; bao phủ các bản sửa mục 2, gồm sự cố AI, dữ liệu
JSON sai cấu trúc, đóng DB, junction không được duyệt, bảo toàn khi huấn
luyện và tính hợp lệ của split/generator. Các test trước vẫn xác minh
Unicode/dấu cách, encoding, AI false positive/negative, model artifact,
validation không dùng test, recompute metrics, dashboard, login/logout.

[Đầu ra pytest cuối](reviews/review_20261116T163259Z_049c87/pytest_final.txt),
[JUnit XML cuối](reviews/review_20261116T163259Z_049c87/pytest_final.xml).
Đầu ra lượt 66 PASS trước khi thêm test số nguyên quá lớn vẫn được giữ lại.

## 8. Hạn chế và phần cần hoàn thiện trong khóa luận

- Windows chưa có handle-based authorization chống mọi TOCTOU. Kho phải
  được bảo vệ khỏi ghi đồng thời bởi người không tin cậy. Không suy ra
  an toàn production từ các ca tĩnh đã PASS.
- Ba test symlink cần quyền phù hợp/Developer Mode để chạy thật; chưa
  kiểm thử nhánh POSIX, tải lớn/concurrency hoặc deployment Internet.
- 100% của v2 chỉ mô tả các tập đã đo, đặc biệt test cũ đã công bố và có
  15 tương đương canonical trước phân tích bổ sung. Corpus ngoài còn dễ,
  có source-label confounding và chưa kiểm chứng double encoding độc lập.
- Các escape cấu trúc được dành riêng: tên literal chứa chúng có thể bị
  từ chối dù nằm trong kho; không gọi đây là chứng minh filesystem escape.
- Danh sách kho giới hạn 200 tệp và tối đa 10.000 entry được quét; không
  đi vào link/reparse tĩnh. Kho lớn có thể không hiển thị toàn bộ; tải
  path hợp lệ cụ thể vẫn dùng cùng lớp authorization.
- AI advisory được cô lập lỗi; vẫn tuyệt đối không load joblib/pickle
  không tin cậy. Bắt exception không làm pickle an toàn.
- Demo chưa có CSRF token, rate limiting/throttling đăng nhập, quản lý
  user/role, HTTPS hoặc secret production bền vững. SameSite và bind
  localhost không thay thế các yêu cầu production đó.
- Nên bổ sung tập test độc lập được gán nhãn kiểm tra, đối chứng benign
  khó, encoding đa lớp/malformed/Unicode và đo tải có phương pháp trước
  khi kết luận tổng quát hóa. Không thay số liệu thật bằng mục tiêu mong muốn.

## 9. Tái lập và danh sách file

Từ thư mục `FileGuardAI_H07`, dùng `.venv` ở thư mục cha hiện tại:

```powershell
..\.venv\Scripts\python.exe -m pytest -q -rs
..\.venv\Scripts\python.exe tools/audit_project.py --repeats 7
..\.venv\Scripts\python.exe tools/verify_tcp.py
..\.venv\Scripts\python.exe tools/verify_evaluation_http.py
```

Cổng 5000 cần trống cho verify_tcp; công cụ tự khởi động/tắt server local.
Audit và TCP tạo bằng chứng mới, không ghi đè lượt cũ; audit không fit.
`python -m ml.train_model` chỉ nên dùng khi chủ động muốn huấn luyện/lưu
model triển khai: lệnh đó nay giữ CSV và sao lưu output cũ. Để nghiên cứu
so sánh mà không thay model triển khai, dùng các lệnh evaluate/improve
đã mô tả trong tài liệu trước.

[Danh mục file của lần rà soát](REVIEW_FILES.md).
Các báo cáo trước được giữ nguyên làm lịch sử; báo cáo này bổ sung phát
hiện canonical overlap và kết quả mới, không sửa ngược số liệu cũ.
