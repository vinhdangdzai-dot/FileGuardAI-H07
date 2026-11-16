# Chương 1 — Cơ sở lý thuyết và phạm vi

## 1. Bài toán

FileGuardAI H07 nghiên cứu phát hiện cú pháp Path Traversal bằng Logistic
Regression và ngăn truy cập file ngoài kho bằng policy độc lập. Nhãn
malicious/suspicious trong dữ liệu là dấu hiệu cú pháp, không khẳng định
khai thác thành công. Đầu vào nghiên cứu là chuỗi path; ứng dụng nhận path
sau một lần giải mã query của Flask. Hai cách biểu diễn không được đánh
đồng khi diễn giải thực nghiệm.

Path traversal (CWE-22) có relative `../`, biến thể separator Windows,
absolute path, percent/double encoding và link filesystem. Nguồn gốc và
bảng rủi ro có tại [RUI_RO_CWE22.md](RUI_RO_CWE22.md). Tài sản được bảo vệ
là file ngoài shared_files và dữ liệu private, không phải chỉ file
`secret.txt` của fixture. Quyền OS, junction và thời điểm mở file đều
ảnh hưởng tính an toàn; score ML không giải quyết các vấn đề đó.

## 2. Logistic Regression

Với vector đặc trưng x, mô hình tính z = w^T x + b,
p(y=1|x) = 1/(1+exp(-z)). Nhãn dự đoán là 1 nếu p>=0,5. Hàm loss là
binary cross-entropy có regularization L2; C kiểm soát nghịch mức phạt.
StandardScaler dùng mean/std của **train**, tuyệt đối không fit toàn bộ
dataset trước khi chia. Pipeline lưu cả scaler và LR để dự đoán nhất quán.

V1 dùng 18 đặc trưng: chiều dài, slash/backslash, dotdot, phần trăm,
encoded dot/slash/backslash, absolute/drive/colon, space/non-ASCII/digit,
multiple dots, NUL, question và entropy ký tự. Entropy
H=-sum(p(c) log2 p(c)) mô tả phân bố ký tự, không phải bằng chứng tấn công.

V2 giữ 18 đặc trưng cũ và thêm 12 thống kê cấu trúc trên raw, decode một
lần và decode hai lần: parent components/tỷ lệ, rooted/drive/UNC,
separator/mixed separator, lexical escape depth, dot components, NUL,
structural escape và số lượt decode thay đổi input. View decode chỉ để
ML; không dùng kết quả đó trong open_authorized. Trích xuất được cố định
trước lựa chọn C trên validation; test cũ đã từng xem nên kết luận về
độc lập phải giới hạn rõ.

## 3. Phương pháp đối chứng và đại lượng

Regex hiện có là baseline phát hiện đơn giản, không phải policy truy cập.
So sánh LR v1/v2/regex trên **cùng các dòng** của mỗi tập; không so số từ
các tập hoặc lần đo khác nhau để quảng bá ưu thế.

- Accuracy=(TP+TN)/N.
- Precision=TP/(TP+FP); Recall=TP/(TP+FN).
- F1=2TP/(2TP+FP+FN), zero_division=0 khi không có mẫu dự đoán dương.
- Confusion matrix: hàng nhãn thật, cột dự đoán, thứ tự benign=0/suspicious=1.
- Tỷ lệ ngăn chặn HTTP = số policy-violation trả 403 / tổng policy-violation
  đã thực hiện; không tính 404 vào denominator tấn công và không gọi đây là Recall ML.
- Latency HTTP gồm đọc hết body; thời gian predict batch không bao gồm
  Flask/SQLite/network. µs/path từ batch chỉ là amortized time.

## 4. Mục tiêu và giới hạn khoa học

Mục tiêu tối thiểu là mô hình chạy được, đánh giá có thể tính lại, policy
file có test, log/dashboard có quyền truy cập và báo cáo trung thực.
100% trên corpus minh họa không đủ chứng minh vượt trội thực tế. Chưa
có nhãn traffic thực do bên thứ ba kiểm tra, hoặc bài thử blind không ai
trong nhóm đã xem. Không công bố đạt mục tiêu recall traffic 95% nếu chỉ
có số liệu synthetic/public lexical.

Tài liệu gốc: [MITRE CWE-22](https://cwe.mitre.org/data/definitions/22.html),
[OWASP Path Traversal](https://community.owasp.org/attacks/Path_Traversal),
[OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
Chi tiết nguồn dữ liệu, commit và giới hạn xem Chương 4.
