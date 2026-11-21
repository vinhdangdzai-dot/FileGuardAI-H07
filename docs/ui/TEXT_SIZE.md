# Cỡ chữ trình chiếu và A− / A / A+ — 17/11/2026

Nhánh `h07/cybersecurity-ui`, PR #2. Phạm vi chỉ templates/static và test UI; không sửa backend, dataset, mô hình, artifacts hoặc SQLite nghiệp vụ.

## Cách dùng và thang chữ

Navbar có ba nút A− / A / A+, dùng được bằng Tab, Enter và Space. Nhỏ = root 16px, Vừa = 18px (mặc định), Lớn = 20px. Lựa chọn lưu tại localStorage `fg-text-size`, độc lập `fg-theme`. Áp dụng đồng bộ trước CSS, không tải lại trang; đồng bộ tab qua storage event. Storage bị chặn thì giữ lựa chọn trong trang, trang mới về 18px. Tắt JavaScript vẫn có mặc định 18px và không hiện các nút không hoạt động.

| Thành phần | Mức Vừa, đo theo rem gốc 18px |
|---|---:|
| Nội dung chính | 18px |
| Sidebar / liên kết navbar | 18px |
| Nút, input, select, bảng, đường dẫn | 17px |
| Tiêu đề cột, badge, chú thích, footer, code | 16px |
| H1 | 36px |
| H2 / tiêu đề khối | 24px |
| Số liệu thống kê | 36px |

Mọi cỡ chữ readable được chuyển sang rem/tokens; không còn font-size px cố định ngoài token root. Nhỏ/Lớn thay toàn bộ tỷ lệ, không chỉ body. Vì vậy ở mức Nhỏ, chú thích theo tỷ lệ còn khoảng14,22px; mặc định chú thích16px. H1 khi Lớn tăng lên40px. Màu Sáng/Tối/Theo hệ thống giữ nguyên, không tạo bộ HTML thứ hai. Chart.js cập nhật ticks/legend/tooltip cùng chart khi đổi chữ, giữ nguyên dữ liệu; hình PNG thực nghiệm lưu trữ không bị sửa, bảng số liệu HTML cung cấp nội dung đọc được ở thang chữ mới.

Navbar wrap, sidebar có thể thu gọn và cuộn; card/grid chuyển cột sớm; badge xuống dòng. Bảng cuộn ngang trong vùng bảng, không ép chữ nhỏ để nhét toàn bộ cột vào màn hình. Dataset vẫn phân trang 50/100, chỉ Admin xem/export kèm CSRF như cũ.

## Kiểm thử thực tế

| Kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q -rs` | **165 PASS, 0 FAIL, 0 ERROR, 3 SKIP**;15 subtests PASS;61,99s |
| Acceptance cuối sau sửa tràn | **6/6 bước exit0**, pytest165 PASS/3 SKIP |
| Dashboard TCP | 41 PASS,0 FAIL |
| Download TCP | 33 PASS,0 FAIL,3 symlink SKIP |
| Hiệu năng | 144 request /144 dòng fixture SQLite,0 lỗi |
| Edge/Chromium cuối | **385 PASS,0 FAIL**,0 JavaScript/static errors |

[Pytest stdout](pytest_20261117T084023Z/stdout.txt) · [Acceptance cuối](../bao_cao_h07/evidence/20261117T084505Z_ececf4/summary.json) · [Browser từng check](browser_20261117T084333Z_816797/results.json).

Browser gồm248 checks hiện hữu,90 tổ hợp cỡ chữ (5 trang × 3 mức × 3 độ rộng × 2 màu), kiểm keyboard/persistence/chart và45 phép reflow zoom. Độ rộng1440/768/390px; zoom125/150/200% tại mức Lớn20px. Checks đo root và font riêng của thành phần, document overflow, clipping navbar và quyền thao tác; không chỉ so chuỗi CSS.

**Giới hạn zoom:** công cụ dùng CDP Emulation.setDeviceMetricsOverride để giảm CSS viewport và tăng device scale theo tỷ lệ zoom desktop. Đây là phép kiểm reflow mô phỏng, **chưa xác minh thao tác browser zoom native Ctrl+plus / menu Chrome**. Không gọi kết quả này là PASS cho thao tác native. Khi demo, cần kiểm thêm trên màn hình/máy chiếu thật với zoom browser125/150/200%; không thay mô phỏng bằng chứng thực tế. Chrome local vẫn crash môi trường như báo cáo trước, Edge local chạy thành công; Chrome Windows CI được báo riêng trên PR với artifact theo commit.

Ba SKIP local vẫn do thiếu quyền symlink Windows11, không đổi thành PASS; CI có thể chạy được chúng. Hash dataset/deployed v1/frozen v2/SQLite nghiệp vụ trong acceptance và browser đều không đổi.

## Bằng chứng lỗi được giữ nguyên

- Browser [084026Z](browser_20261117T084026Z_928c62/results.json):334 PASS/3 FAIL. Hai FAIL là trang Kho tệp ở768px/mức Lớn bị tràn badge; sửa badge wrap và stack cột sớm. Một FAIL do selector công cụ trùng root data-text-size với button; đổi selector thành button[data-text-size], không giảm điều kiện kỳ vọng. Lượt cuối385 PASS ở thư mục khác.
- Browser [083032Z](browser_20261117T083032Z_58f480/interrupted.json), pytest [083059Z](pytest_20261117T083059Z/interrupted.json), acceptance [083200Z](../bao_cao_h07/evidence/20261117T083200Z_889d85/interrupted.json): tiến trình bị ngắt, không có exit/final results; ghi ERROR thực thi, không tính PASS hoặc SKIP. Chưa xác định nguyên nhân môi trường.
- Acceptance [084043Z](../bao_cao_h07/evidence/20261117T084043Z_a2b372/summary.json) thành công trước hai sửa UI cuối; giữ riêng, không dùng thay lượt cuối.

## Ảnh thực tế và file thay đổi

Ảnh dùng fixture riêng, không chụp SQLite nghiệp vụ. [Login18px mobile](browser_20261117T084333Z_816797/type_medium_login_390.png) · [Login20px mobile](browser_20261117T084333Z_816797/type_large_login_390.png) · [Dashboard18px](browser_20261117T084333Z_816797/type_medium_dashboard_1440.png) · [Dashboard20px](browser_20261117T084333Z_816797/type_large_dashboard_1440.png) · [Training18px](browser_20261117T084333Z_816797/type_medium_training_1440.png) · [Training20px](browser_20261117T084333Z_816797/type_large_training_1440.png).

Thư mục browser cuối có20 ảnh `type_{medium|large}_{public|login|dashboard|evaluation|training}_{1440|390}.png`, cộng ảnh Light/Dark hiện có và manifest.

File source: `app/static/style.css`, `app/static/text-size.js` (mới), `app/static/dashboard.js`, `app/templates/base.html`, `tests/test_text_size_ui.py` (mới,7 cases), `tools/ui_text_size_checks.py` (mới), `tools/verify_ui_browser.py`. Tài liệu: báo cáo này, README/UI README/PR description và snapshots mới. Không đổi tests bảo mật, nhãn dữ liệu hoặc artifacts. PR #2 giữ draft, không merge main.
