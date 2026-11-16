# 11 — Dataset, nhãn và phòng chống leakage

Bản nghiệm thu ngày 17/11/2026 (giờ Việt Nam). Phạm vi: MVP localhost Windows 11; không phải chứng nhận triển khai Internet.

CSV gốc [paths_synthetic.csv](../../data/paths_synthetic.csv) có10.000 dòng,5.000 benign/5.000 suspicious,35 family (15 benign/20 suspicious),0 dòng trùng chuỗi,0 conflicting raw labels. Các số được audit lại; không tạo lại dataset hay dùng AI đoán nhãn rồi coi là ground truth.

Canonical key phục vụ audit: Unicode NFC→unquote đúng hai lượt→backslash thành slash→casefold. Không resolve filesystem, không khẳng định đây là mọi quan hệ tương đương. Có9.968 key,32 duplicate excess rows. Không được báo “không trùng” nếu chỉ kiểm raw. Holdout lịch sử có15 giao canonical, đã ghi hạn chế.

Mới: union-find gộp toàn family nếu chia sẻ key;26 components; tách có phân tầng nhãn và seed2026 thành train6500 (3000/3500), validation1999 (999/1000), test1501 (1001/500). Không chia một component sang hai tập; ba cặp tập không giao family hoặc key. Nếu conflicting canonical labels hoặc không đủ component thì fail, không relabel hay random-row fallback. Sau chọn C ở validation, refit8499 development; test chỉ predict và tính metrics. Dữ liệu đã được xem trước trong lịch sử nên đây là cải thiện protocol trên nguồn đã biết, chưa blind evaluation.

Nguồn public236:118 LFISuite payload và118 Starlette path controls, snapshot/commit và license nằm [h07 corpus](../../data/external/h07_20261116T171550Z_5b8ba9). Nguồn challenge20: [OWASP corpus](../../data/external/owasp_20261116T172733Z_800c38). Attack label là ý định traversal của ví dụ, không chứng minh request khai thác được trên Flask hiện tại. Benign là control trong scope, không có nghĩa tệp tồn tại. Dedupe canonical đối với tập gốc và public400 được lưu manifest; không gộp challenge với236 để quảng cáo independence.

SHA256 dataset: `2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0`.
Model đang triển khai: `4d7324aa302ecb3d1b731561210a0041e4aef3f740cc68d9187097a80e5a6322`.
Frozen v2: `07e73c85cdbbd4a8acbc785565514a8330e3252483602c191c34208e04f8e368`.
Cả ba và DB người dùng giữ nguyên trước/sau acceptance. Models strict nằm trong run mới, không chép vào artifacts/model.joblib.

Kiểm chứng: [strict_groups.py](../../ml/strict_groups.py), [tests](../../tests/test_strict_groups.py), [split và manifest](../evaluations/20261116T181019Z_dea9ec). Hạn chế lớn nhất là đại diện tổng hợp, không phải chỉ số lượng10.000; cần thêm lỗi thực tế/benign phức tạp và nhãn được review độc lập.

**Trạng thái: PASS.** Đối chiếu [ma trận tổng hợp](12_MA_TRAN_NGHIEM_THU.md). Bằng chứng chạy thực tế: [summary](evidence/20261116T182248Z_5acba3/summary.json), [pytest](evidence/20261116T182248Z_5acba3/pytest.stdout.txt), [bảng HTTP](evidence/20261116T182248Z_5acba3/http_test_cases.csv).
