# 10 — Báo cáo thực nghiệm Logistic Regression

Bản nghiệm thu ngày 17/11/2026 (giờ Việt Nam). Phạm vi: MVP localhost Windows 11; không phải chứng nhận triển khai Internet.

Hai câu hỏi tách biệt: chất lượng phân loại chuỗi (LR/Regex) và hiệu quả policy ngăn đọc tệp (HTTP/body). Không dùng tỷ lệ chặn thay Recall của AI. Metrics: Accuracy=(TP+TN)/N; Precision=TP/(TP+FP); Recall=TP/(TP+FN); F1=2PR/(P+R). Confusion matrix theo thứ tự nhãn [benign,suspicious], dạng [[TN,FP],[FN,TP]].

| Tập / phương pháp | Accuracy | Precision | Recall | F1 | Confusion matrix |
|---|---:|---:|---:|---:|---|
| Holdout cũ2001 — LR v1 | 87.5062% | 100% | 75% | 85.7143% | [[1001,0],[250,750]] |
| Holdout cũ2001 — Regex | 87.5062% | 100% | 75% | 85.7143% | [[1001,0],[250,750]] |
| Holdout cũ2001 — v2 frozen | 100% | 100% | 100% | 100% | [[1001,0],[0,1000]] |
| Strict canonical holdout1501 — LR v1 mới fit development | 100% | 100% | 100% | 100% | [[1001,0],[0,500]] |
| Cùng strict1501 — LR v2 mới fit development | 100% | 100% | 100% | 100% | [[1001,0],[0,500]] |
| Cùng strict1501 — Regex | 100% | 100% | 100% | 100% | [[1001,0],[0,500]] |
| Public236 — cả ba strict model/Regex | 100% | 100% | 100% | 100% | [[118,0],[0,118]] |
| OWASP challenge20 — frozen v1/v2 | 100% | 100% | 100% | 100% | [[10,0],[0,10]] |
| Cùng challenge20 — Regex | 80% | 100% | 60% | 75% | [[10,0],[4,6]] |

250 FN cũ là family double encoding: tín hiệu v1/Regex không đủ trong cách chia family cũ; v2 bổ sung view hữu hạn và cấu trúc thành phần. Tuy nhiên holdout cũ đã công bố kết quả, có15 canonical equivalents vượt train/test; không thể gọi là blind independent. Tập dữ liệu toàn bộ có32 bản trùng canonical dù0 chuỗi trùng chính xác.

Thí nghiệm mới [20261116T181019Z_dea9ec](../evaluations/20261116T181019Z_dea9ec/results.json) gộp family chung canonical key thành26 connected components. Train6500, validation1999, test1501; chọn C trong[0.1,1,10] trên validation, chọn0.1 khi hòa; refit development8499, đóng băng rồi mới predict test. V1 giữ C1 làm đối chứng; scaler cũng chỉ fit development. Không thay deployed v1 hoặc frozen v2. Tập strict khác tập holdout cũ nên không so trực tiếp87.51→100 như mức cải thiện v2. Cả ba đều100 trên strict: **không chứng minh v2 ưu thế trên tập này**.

Artifacts: [plan trước fit](../evaluations/20261116T181019Z_dea9ec/plan_before_fit.json), [kết quả và timing chính xác](../evaluations/20261116T181019Z_dea9ec/results.json), [thư mục biểu đồ PNG và predictions](../evaluations/20261116T181019Z_dea9ec), [mã đánh giá](../../tools/evaluate_strict_groups.py). Thời gian dự đoán là số đo perf_counter trong run, đọc trực tiếp JSON; không lấy latency HTTP làm inference time. Mỗi bảng so sánh chỉ dùng cùng tập trong cùng hàng nhóm. Dashboard lịch sử mở `?run=20261116T181019Z_dea9ec`; con trỏ latest cũ giữ nguyên để bảo toàn run tham chiếu.

Public236 chọn118 attack từ SecLists LFISuite và118 benign từ Starlette; canonical-disjoint với10k và tập public400 cũ. Challenge20 gồm10 ví dụ OWASP và10 controls; không khẳng định độc lập với236, vì có controls chia sẻ. Nguồn/commit/raw/license/nhãn ở [data/external](../../data/external). Nhãn theo intent/cấu trúc nguồn, chưa gán nhãn thủ công mù bởi nhiều chuyên gia; legacy overlong có thể chỉ là tên literal404 trên Flask hiện đại.

Thời gian thực tế từ run strict (inference_only không gồm features; end_to_end có features; µs/path là batch amortized, không phải latency request đơn):

| Phép đo strict1501,7 lượt | Median batch ms | Bình quân µs/path |
|---|---:|---:|
| lr_inference_only | 0.2965 | 0.1975 |
| lr_end_to_end | 18.2894 | 12.1848 |
| improved_inference_only | 0.3353 | 0.2234 |
| improved_end_to_end | 38.9098 | 25.9226 |
| regex_end_to_end | 1.4434 | 0.9616 |


Hiệu năng IPS:3×48 request,4workers,TCP localhost,144 dòng SQLite,0 lỗi/0 sentinel leak,90/90 vi phạm policy bị chặn. Tải hợp lệ đúng body: **36/36 = 100.00%**. Đây là tỷ lệ trên bộ test đã đo, không phải100% mọi cuộc tấn công. Chi tiết [performance](../h07/evidence/20261116T182323Z_0090f9/performance.json); không có cam kết throughput production.

| Trial,48 requests /4workers | p50 ms | p95 ms | p99 ms | Request/s |
|---|---:|---:|---:|---:|
| 1 | 60.970 | 160.089 | 185.215 | 59.962 |
| 2 | 57.459 | 121.538 | 137.191 | 71.632 |
| 3 | 52.378 | 104.540 | 118.129 | 68.187 |


Giới hạn: dữ liệu tổng hợp cân bằng, nhóm lexical dễ phân biệt, biết trước test lịch sử, source bias trên corpus ngoài, không real traffic/blind site split; accuracy100 có thể phản ánh bài toán dễ. Cần corpus thực được phép, nhãn độc lập, temporal/source holdout, calibration, CI bootstrap theo nhóm và stress test nhiều môi trường trước kết luận tổng quát hóa.

**Trạng thái: PASS.** Đối chiếu [ma trận tổng hợp](12_MA_TRAN_NGHIEM_THU.md). Bằng chứng chạy thực tế: [summary](evidence/20261116T182248Z_5acba3/summary.json), [pytest](evidence/20261116T182248Z_5acba3/pytest.stdout.txt), [bảng HTTP](evidence/20261116T182248Z_5acba3/http_test_cases.csv).
