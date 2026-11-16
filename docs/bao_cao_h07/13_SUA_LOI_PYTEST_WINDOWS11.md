# Sửa lỗi quyền thư mục tạm Pytest Windows 11

## Nguyên nhân và bằng chứng ban đầu

Lần chạy được người dùng cung cấp đã được giữ nguyên tại [evidence/20261116T184504Z_6d5e3a](evidence/20261116T184504Z_6d5e3a/summary.json). Console ghi **25 PASS, 0 FAIL, 85 ERROR, 2 SKIP, 2 warnings;15 subtests PASS**, pytest exit1. ERROR xuất hiện trong setup fixture `tmp_path` khi truy cập `AppData/Local/Temp/pytest-of-HUU VINH`, không phải85 bài assertion bảo mật bị FAIL. `.pytest_cache` cũng không ghi được.

Kiểm tra [ACL chỉ đọc](evidence/pytest_temp_fix_20261116T185537Z/acl_observed.json) cho thấy cả hai thư mục thuộc `CodexSandboxOffline`, DACL protected, chỉ có quyền cho OWNER RIGHTS, SYSTEM và Administrators. Điều này phù hợp với lỗi từ terminal của tài khoản khác không có quyền tương ứng. Không suy đoán tiến trình cụ thể nào đã tạo ACL; không chạy Set-Acl, xóa thư mục hoặc yêu cầu Administrator.

## Bản sửa

| File | Thay đổi / mục đích |
|---|---|
| [tools/pytest_runtime.py](../../tools/pytest_runtime.py) | Mỗi lần chạy tạo **thư mục UUID trực tiếp dưới workspace**, không tái dùng một thư mục cha chung có thể thuộc tài khoản khác. Probe quyền ghi; lỗi thật vẫn raise PermissionError. |
| [tools/run_h07_acceptance.py](../../tools/run_h07_acceptance.py) | Dùng helper; truyền `--basetemp=<UUID mới>/pytest` còn chưa tồn tại, tắt cache plugin; TEMP/TMP/TMPDIR riêng cho các tiến trình con; lưu path và phân loại JUnit PASS/FAIL/ERROR/SKIP. |
| [conftest.py](../../conftest.py) | Lệnh pytest thông thường cũng dùng runtime riêng. Thay cả env và cache `tempfile.tempdir` vốn có thể đã khởi tạo; phục hồi sau session. Không can thiệp runtime Flask. |
| [pytest.ini](../../pytest.ini) | Tắt cacheprovider để không đụng `.pytest_cache` cũ. Dùng capture=sys vì FD capture có thể mở tệp TEMP trước khi conftest chạy. Vẫn giữ capture stdout/stderr Python và báo lỗi thật. |
| [.gitignore](../../.gitignore) | Bỏ qua runtime; không đưa fixture/credential tạm vào Git. Không tự xóa runtime cũ. |
| [tests/test_pytest_runtime.py](../../tests/test_pytest_runtime.py) |7 regression cases: khoảng trắng; temp mặc định bị từ chối; workspace không ghi được phải ERROR; cha chung khác owner; subprocess pytest với default và explicit basetemp; phân biệt JUnit bốn trạng thái. |

UUID parent được tạo độc quyền `exist_ok=False`; chỉ child `pytest` chưa tồn tại được truyền tới pytest. Không đưa public root, workspace root, thư mục bằng chứng hay dữ liệu người dùng vào `--basetemp`. Nếu người vận hành tự truyền `--basetemp`, họ phải chọn thư mục dùng riêng có thể bỏ được; không dùng thư mục có dữ liệu quan trọng. Không cần chỉnh ACL hay xóa cache bị khóa.

## Kết quả và phạm vi xác minh

Lệnh chính xác `python -m pytest -q -rs`: **116 PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS;63.53s**. [stdout](evidence/pytest_temp_fix_20261116T185537Z/pytest.stdout.txt), [stderr](evidence/pytest_temp_fix_20261116T185537Z/pytest.stderr.txt), [command/exitcode](evidence/pytest_temp_fix_20261116T185537Z/command.json). Không còn PytestCacheWarning. Lần trung gian115 PASS ở thư mục185415Z cũng được giữ, không thay làm bằng chứng bản cuối.

Acceptance runner: tất cả6 bước exit0. Pytest116 PASS,0 FAIL,0 ERROR,3 SKIP;15 subtests PASS. Dashboard TCP41 PASS;download TCP33 PASS/3 SKIP;hiệu năng144 request/144 dòng SQLite,0 lỗi;symlink probe vẫn có SKIP, không suy PASS từ exit0. Xem [summary mới](evidence/20261116T185722Z_cc572a/summary.json), [pytest stdout](evidence/20261116T185722Z_cc572a/pytest.stdout.txt), [JUnit](evidence/20261116T185722Z_cc572a/pytest.xml). Hash dataset, deployed v1, frozen v2 và SQLite người dùng đều không đổi trước/sau. `junit_counts` đếm node testcase thực sự được serialize (116/0/0/3 trong run này);15 subtests ghi riêng theo console, không tự cộng vào số node. Counting note cũ trong snapshot nói chung về subtests; mã hiện hành đã làm rõ cách đếm, không sửa lại snapshot bằng chứng.

Không sửa dữ liệu huấn luyện, artifacts AI, SQLite nghiệp vụ, Flask routes hoặc policy Path Traversal. Ba SKIP vẫn liên quan đặc quyền symlink Windows, không phải lỗi temp được đổi thành SKIP. PI3.1 vẫn PARTIAL trên Windows11 đích; trạng thái minimum11 PASS/1 PARTIAL giữ nguyên. Nguồn/bằng chứng cũ giữ nguyên.

## Xác minh bằng terminal người dùng bình thường

Từ `FileGuardAI_H07`, không chạy VS Code/terminal bằng Administrator:

```powershell
..\.venv\Scripts\python.exe -m pytest -q -rs
..\.venv\Scripts\python.exe tools/run_h07_acceptance.py
```

Đối chiếu exitcode, console và summary ở thư mục evidence mới. Không còn85 ERROR do default temp hoặc cảnh báo `.pytest_cache`; kiểm tra3 SKIP có đúng lý do symlink. Nếu vẫn lỗi, gửi stdout/stderr/summary mới; không xóa temp hoặc sửa ACL để che lỗi.

Giới hạn: kết quả ở đây chạy trong môi trường Codex trên máy này, **chưa phải lần chạy lại bằng tài khoản terminal thông thường của người dùng**. Regression test có fault injection PermissionError và tiến trình pytest thật, không đổi ACL OS thật; không tuyên bố đã kiểm chứng thành công dưới tài khoản người dùng. Workspace cần cho tài khoản hiện tại tạo thư mục con; nếu workspace cũng bị khóa, lỗi vẫn được báo. Runtime được giữ để điều tra, có thể tăng dung lượng; không tự dọn. Các plugin bên thứ ba tự truy cập TEMP trước hook, hoặc người dùng ép `--capture=fd`/bật lại cache, nằm ngoài cấu hình đã kiểm thử này.
