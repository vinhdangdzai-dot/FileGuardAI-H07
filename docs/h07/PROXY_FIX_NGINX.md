# IP người truy cập sau một Nginx reverse proxy

## Nguyên nhân và thay đổi

Gunicorn nhận kết nối TCP từ Nginx trên localhost, nên địa chỉ peer ban đầu là
127.0.0.1. Flask không tự tin tưởng địa chỉ do client gửi trong HTTP header.

Factory thực tế ở `app/web.py` (được `app/__init__.py` chuyển tiếp) chỉ bọc
Werkzeug ProxyFix khi biến môi trường **TRUST_PROXY=1**. Các giá trị khác,
kể cả không cấu hình, không bật middleware. Cấu hình:
`x_for=1, x_proto=1, x_host=0, x_port=0, x_prefix=0`.

Các chức năng tiếp tục dùng `request.remote_addr`: nhật ký tải tệp, đăng nhập,
giới hạn thử đăng nhập, đổi mật khẩu và sự kiện xuất dữ liệu. Không sửa
`run.py`, mật khẩu, SECRET_KEY, SQLite nghiệp vụ, AI hoặc chính sách đường dẫn.

## Điều kiện an toàn bắt buộc trên VPS

ProxyFix chỉ đếm hop, **không xác thực peer**. Cấu hình này dành cho đúng một
Nginx trước Gunicorn. Gunicorn phải chỉ bind **127.0.0.1:8000**, không mở trực
tiếp cổng 8000 ra Internet. Nginx phải ghi đè X-Forwarded-For bằng
**$remote_addr**, không dùng **$proxy_add_x_forwarded_for** từ nguồn không tin cậy.
Tiến trình cục bộ có quyền truy cập socket vẫn nằm trong ranh giới tin cậy.

Trong `location /` thuộc server Nginx hiện có (giữ cấu hình TLS/domain hiện tại):

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host "";
    proxy_set_header X-Forwarded-Port "";
    proxy_set_header X-Forwarded-Prefix "";
    proxy_set_header X-Forwarded-SSL "";
    proxy_set_header X-Forwarded-Protocol "";
    proxy_set_header Forwarded "";
}
```

Nếu có CDN/load balancer trước Nginx, $remote_addr có thể là IP của lớp đó.
Không áp dụng nguyên trạng cho chuỗi nhiều proxy; cần thiết kế trusted real-IP
riêng theo dải IP chính thức, không tin tưởng header client hoặc toàn Internet.

## Các bước vận hành cần thực hiện thủ công

1. Cập nhật mã đã review; giữ nguyên cấu hình secret và thông tin xác thực.
2. Đặt `TRUST_PROXY=1` trong môi trường service Gunicorn, ví dụ
   `Environment=TRUST_PROXY=1` trong systemd. Đặt bind loopback như trên.
   Ví dụ lệnh chạy từ thư mục dự án với virtualenv đã có Gunicorn:

   ```bash
   TRUST_PROXY=1 /path/to/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 1 --forwarded-allow-ips='' 'app:create_app()'
   ```

   Gunicorn cũng có cơ chế xử lý secure-scheme header riêng. Chuỗi rỗng cho
   `--forwarded-allow-ips` vô hiệu hóa cơ chế đó trên kết nối TCP, để ProxyFix
   là nơi xử lý forwarded headers theo opt-in. Không dùng wildcard `*`.
   Không dùng `--preload` cho ví dụ này vì ứng dụng có worker nền khởi tạo
   trong factory. Giữ cấu hình SECRET_KEY hiện có; không phát sinh secret mới.
3. Áp dụng header Nginx như trên; chạy `sudo nginx -t` trước khi reload Nginx.
   Restart đúng service Gunicorn sau khi cập nhật biến môi trường; nếu đổi
   unit systemd thì daemon-reload trước. Các thao tác này chưa được thực hiện
   bởi đợt sửa mã này.
4. Kiểm tra `ss -ltnp` xác nhận cổng 8000 chỉ lắng nghe 127.0.0.1, không phải
   0.0.0.0 hoặc [::]. Kiểm tra firewall và khả năng truy cập trực tiếp từ ngoài.
5. Từ máy bên ngoài VPS, tải tệp hợp lệ và thử một tên tệp không tồn tại qua
   domain HTTPS. Gửi thêm header giả `X-Forwarded-For: 203.0.113.9`; IP nhật ký
   phải là IP kết nối thực tới Nginx, không phải giá trị giả. Xác minh tải hợp
   lệ 200, traversal 403, không tồn tại 404. Đây là các request kiểm thử có
   ghi nhật ký, không cần xóa bằng chứng.
6. Muốn tắt: bỏ TRUST_PROXY hoặc đặt 0, rồi restart service. Nếu middleware
   tắt sau reverse proxy, nhật ký quay lại IP peer loopback là hành vi dự kiến.

## Kiểm chứng thực tế trong workspace Windows

Lệnh: `..\.venv\Scripts\python.exe -m pytest -q`.

Kết quả: **252 passed, 3 skipped, 15 subtests passed**, 0 failed, 0 errors;
exit code 0; thời gian 69,19 giây. Log gốc:
`docs/h07/evidence/proxy_fix_20261117/pytest.stdout.txt` và `pytest.stderr.txt`.

11 trường hợp mới chứng minh opt-in chính xác, mặc định chống XFF giả, lấy IP
hop cuối khi bật, bỏ qua forwarded host/port/prefix, giữ IP peer nếu thiếu
header, ghi SQLite đúng IP/ALLOW/BLOCK/MISS, tải tệp 200, traversal mã hóa 403,
không tồn tại 404, CSRF và giới hạn đăng nhập theo IP hiệu lực.

Ba SKIP thuộc các bài symlink hiện có trên Windows, không được chuyển thành
PASS. Không sửa bài kiểm thử cũ để che lỗi. Đây là kiểm thử WSGI/Flask và toàn
bộ bộ test hiện có, **chưa chạy Nginx/Gunicorn thực tế trên Ubuntu**; cần xác
minh VPS theo các bước trên. Không commit, push, merge hay triển khai VPS.

## Tài liệu chính thức

- [Werkzeug ProxyFix và ranh giới tin cậy](https://werkzeug.palletsprojects.com/en/stable/middleware/proxy_fix/)
- [Nginx proxy_set_header](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header)
- [Gunicorn forwarded_allow_ips và secure_scheme_headers](https://gunicorn.org/reference/settings/)
- [Gunicorn xử lý danh sách IP rỗng trong cấu hình](https://github.com/benoitc/gunicorn/blob/master/gunicorn/config.py)
