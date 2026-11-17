# Hoàn thiện Login và AI Evaluation — PR #2

Đợt tiếp theo trên `h07/cybersecurity-ui`, baseline `5866eb8`. Giữ dark navy/cyan/tím; không sửa policy Path Traversal, ALLOW/BLOCK/MISS, auth/session/CSRF, dataset, model, SQLite nghiệp vụ hoặc artifacts thực nghiệm cũ.

## Thay đổi thực hiện

Login: navbar cho phép wrap theo chiều rộng, không che overflow để giấu lỗi; nút và nhãn không bị cắt. Giảm margin phía trên, cân hai cột desktop; tablet/mobile xếp một cột. Chữ mô tả16px, nhãn15.2px, nội dung phụ14.08px được đo từ computed styles. Nút hiện/ẩn là `type=button`, có aria-controls/aria-pressed và thao tác được bằng Space/Enter; không submit hoặc đổi giá trị mật khẩu. Khi trở lại trang, mật khẩu được che lại. Submit thật có aria-busy và chữ “Đang xác thực…”, không đặt loading nhầm lên nút hiện mật khẩu. Không preventDefault, giả phản hồi hoặc sửa payload đăng nhập. Thông báo thất bại có tiêu đề rõ, vẫn dùng thông báo chung do Flask cấp và không phản chiếu mật khẩu.

Evaluation có ba khu vực A/B/C: dữ liệu; cấu hình; độ tin cậy/giới hạn. Có cảnh báo tĩnh, dễ đọc:

> Kết quả 100% trên tập dữ liệu kiểm thử không chứng minh hệ thống phát hiện hoặc ngăn chặn 100% các cuộc tấn công Path Traversal trong thực tế.

Thuật ngữ Train/Validation/Test/Seed/C/Threshold/Group Overlap/Canonical Path Overlap nằm trong phần details có thể thu gọn, không cần thư viện tooltip hoặc thêm chữ vào mọi ô.

Run selector sử dụng **GET `/dashboard/ai-evaluation?run=...` đã có**. Backend chỉ thêm danh sách từ `evaluation_history()` vốn đã kiểm ID, containment, giới hạn2MiB và schema; bổ sung `experiment_type` từ chính JSON để phân loại strict/lịch sử. Không thêm endpoint, không mở quyền, không đọc pickle, fit hoặc deploy model. Không đổi `latest.json`. Run không hợp lệ vẫn trả trang rỗng theo hợp đồng cũ, không âm thầm thay bằng latest.

## Dữ liệu không bị trộn

| Run đã kiểm | Train / fit chọn C v2 | Validation | Test | Development/refit | Canonical overlap |
|---|---:|---|---:|---:|---|
|153450Z_e5b13b, v1 gốc |7999 |Không được cung cấp |2001 |7999 |Không được cung cấp |
|172733Z_800c38, comparison lịch sử |6583 |1416 |2001 |7999 |Không được cung cấp |
|181019Z_dea9ec, strict |6500 |1999 |1501 |8499 |0 theo metadata split |

Các ID trên đều có tiền tố20261116T. Số nguyên bản được lấy từ `audit`, `selection`, `split` của **chính run đang xem**. Không cộng refit như một tập thứ tư. Không suy Validation bằng phép trừ; không lấy canonical overlap từ run strict để điền cho run cũ. Không đồng nhất exact duplicates, exact overlap và canonical overlap. C v2 có trong selection; C v1 không có trong results.json hiện tại nên hiển thị “Không được cung cấp”, không lấy C của deployed model bù vào.

Thẻ chỉ số/chart so sánh dùng metrics top-level test của run; tập ngoài được ghi riêng cùng đường dẫn nguồn `datasets.<name>`. Ảnh confusion/metrics/latency có caption và URL ghim `run` hiện tại. Thời điểm xuất artifact không được gọi là thời điểm mọi phần được huấn luyện/đo lại; thông tin run tham chiếu được giữ khi có. Số liệu, ảnh và artifacts gốc không sửa.

## Kết quả kiểm thử

| Bộ kiểm thử | Trước | Sau |
|---|---|---|
| Pytest |127 PASS,3 SKIP |135 PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS |
| Acceptance |6 bước exit0 |6 bước exit0 |
| Dashboard/auth/filter/CSV TCP |41 PASS |41 PASS |
| Download/security TCP |33 PASS,3 SKIP |33 PASS,3 SKIP |
| Hiệu năng |144 requests/144 log rows,0 lỗi |144 requests/144 log rows,0 lỗi |
| Browser |42 PASS,0 FAIL |85 PASS,0 FAIL;0 JS error;0 lỗi tải static |

- Lệnh `python -m pytest -q -rs`: [stdout](pytest_20261117T061509Z/stdout.txt), [stderr](pytest_20261117T061509Z/stderr.txt), [command/exit](pytest_20261117T061509Z/command.json),81.95s. Thêm8 regression cases, không sửa các test cũ để che lỗi.
- Lệnh `python tools/run_h07_acceptance.py`: [summary](../bao_cao_h07/evidence/20261117T061555Z_a3849d/summary.json), [JUnit](../bao_cao_h07/evidence/20261117T061555Z_a3849d/pytest.xml), [bảng HTTP](../bao_cao_h07/evidence/20261117T061555Z_a3849d/http_test_cases.csv). Bốn hash được bảo vệ (dataset,deployed v1,frozen v2,DB nghiệp vụ) không đổi trong đợt chạy.
- [Chrome trước sửa](browser_20261117T054723Z_271f19/results.json) và [Chrome sau sửa85 checks](browser_20261117T061827Z_9c7831/results.json), dùng1440/768/390px, cả5 trang; kiểm thêm navbar/login guest ở cả3 kích thước. Mọi check có actual values; không ghi PASS chỉ từ ảnh đẹp.
- Browser xác minh Space/Enter hiện/ẩn mật khẩu, submit loading thật, login sai/đúng, CSRF, filter/export, native Unicode download, single/double traversal403 và missing404, run selector, dữ liệu/chart/ảnh đúng run, glossary, sidebar/focus/Escape, no-JS links và không tràn trang/navbar.
- Đo tương phản trên các phần chữ quan trọng bằng computed foreground/background: login tối thiểu8.15:1, đoạn cảnh báo khoa học12.69:1; các cặp đã chọn đều≥4.5:1. Đây không phải audit WCAG đầy đủ hoặc kiểm mọi trạng thái trình duyệt.

Lần [16 PASS/1 FAIL](browser_20261117T061155Z_baf123/results.json) được giữ nguyên: công cụ cố đọc DOM ngay trong callback chặn navigation, dẫn tới timeout trước khi gửi login. Đã đổi sang quan sát thụ động sự kiện submit, không chặn request hoặc sửa phản hồi, vẫn kiểm aria-busy/label đúng. Lần [82 PASS](browser_20261117T061501Z_97df52/results.json) và lần85 PASS (thêm phép đo tương phản/cỡ chữ) cũng giữ riêng. Không đổi FAIL thành SKIP.

Ba SKIP vẫn là symlink Windows thiếu quyền; không nâng trạng thái PI3.1 vì thay UI. Browser chạy Chrome headless ngoài sandbox để đọc thư viện kiểm thử cài riêng, sau phê duyệt; không sửa ACL, không yêu cầu VS Code Administrator. Không tuyên bố đã kiểm Firefox/Safari, thiết bị vật lý hoặc mọi công nghệ hỗ trợ.

## Ảnh trước / sau thực tế

Ảnh do Chrome render Flask localhost, dùng tệp và SQLite fixture riêng. Không giả làm nhật ký sản xuất hoặc ảnh AI-generated. Bản trước/sau đều giữ nguyên cùng nguồn model/data; login error dùng mật khẩu sai fixture, không ghi credential thật.

| Trang | Trước | Sau |
|---|---|---|
| Login desktop |[Ảnh](browser_20261117T054723Z_271f19/03_login_desktop.png) |[Ảnh](browser_20261117T061827Z_9c7831/03_login_desktop.png) |
| Login mobile |[Ảnh](browser_20261117T054723Z_271f19/login_mobile.png) |[Guest390px](browser_20261117T061827Z_9c7831/login_guest_390.png) |
| Evaluation, cùng run latest |[Ảnh](browser_20261117T054723Z_271f19/05_evaluation_desktop.png) |[Ảnh](browser_20261117T061827Z_9c7831/05_evaluation_desktop.png) |
| Evaluation mobile |[Ảnh](browser_20261117T054723Z_271f19/evaluation_mobile.png) |[Ảnh](browser_20261117T061827Z_9c7831/evaluation_mobile.png) |

[Run strict](browser_20261117T061827Z_9c7831/evaluation_strict_desktop.png) · [Run cũ không ghi Validation](browser_20261117T061827Z_9c7831/evaluation_legacy_desktop.png) · [Login thất bại thật](browser_20261117T061827Z_9c7831/login_error_desktop.png) · [Guest tablet768px](browser_20261117T061827Z_9c7831/login_guest_768.png).

## File tạo / sửa của đợt này

| File | Nội dung |
|---|---|
|app/templates/base.html |Navbar/login body class và thông báo thất bại |
|app/templates/login.html |Password toggle, trợ giúp, loading label |
|app/static/style.css |Navbar wrap, font/layout login, ba khung metadata/cảnh báo/glossary |
|app/static/ui.js |Reveal keyboard/ARIA, loading đúng submit, phục hồi pageshow |
|app/templates/ai_evaluation.html |Chọn run, nguồn metric/chart, include ba khu vực |
|app/templates/_evaluation_context.html (mới) |Facts từ từng run, thiếu dữ liệu=N/A, glossary/cảnh báo |
|app/web.py |Chỉ truyền history đã kiểm sang template Evaluation; routes/auth không đổi |
|app/training_view.py |Thêm experiment_type từ JSON vào item history để phân loại selector |
|tests/test_ui_refinement.py (mới) |8 test metadata/absence/pinning/authorization/CSRF/failure |
|tools/verify_ui_browser.py |Kiểm Chrome mở rộng, actual contrast/font/bounds/source comparisons |
|README.md;docs/ui/README.md;docs/ui/PR_DESCRIPTION.md |Liên kết bản bàn giao hiện hành và mô tả PR |
|docs/ui/REFINEMENT_LOGIN_AI.md (mới) |Báo cáo này |
|Evidence mới |4 thư mục browser054723/061155/061501/061827;pytest061509;acceptance061555 và TCP/performance do summary tham chiếu |

Bằng chứng025117Z có sẵn từ trước vẫn để nguyên ngoài commit này. Không xóa bất kỳ bằng chứng hoặc dữ liệu cũ. Mở bằng `python run.py`, vào Login, đăng nhập admin rồi AI Evaluation; chọn lịch sử hoặc strict từ selector. Không cần huấn luyện hoặc đổi model để demo. PR#2 phục vụ review, không merge main.
