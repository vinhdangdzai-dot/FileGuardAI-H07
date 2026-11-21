# Triển khai Ubuntu 24.04 — CANH GÁC SỐ

Kiến trúc: Internet → Nginx HTTPS → Gunicorn `127.0.0.1:8000` → Flask → SQLite/model cục bộ. Gunicorn chạy bằng `deploy`, không chạy root và không mở port 8000 ra Internet.

## 1. Artifact chính thức

`model.joblib` và CSV cố ý không nằm trong Git. Chuyển bản local đã kiểm chứng vào thư mục tạm trên VPS, sau đó:

```bash
sudo bash deploy/ubuntu/restore_artifacts.sh /tmp/model.joblib /tmp/paths_synthetic.csv
```

Script chỉ chấp nhận SHA-256 chính thức và từ chối ghi đè. Không dùng model trong `docs/evaluations` làm model triển khai.

## 2. Cài đặt lần đầu

```bash
cd /home/deploy/apps/canhgacso
sudo bash deploy/ubuntu/install.sh
sudo -u deploy .venv/bin/python tools/manage_credentials.py --role admin
sudo systemctl restart canhgacso
curl -fsS http://127.0.0.1:8000/health
```

Nếu script dừng mã 3, đó là fail-closed vì còn thiếu artifact hoặc hash Admin. Hoàn tất các mục được báo rồi chạy lại; secret hiện có không bị ghi đè.

## 3. HTTPS và firewall

Chỉ sau khi cả `canhgacso.fun` và tên `www` dự định dùng đã trỏ về VPS:

```bash
sudo nginx -t
sudo certbot --nginx -d canhgacso.fun -d www.canhgacso.fun
sudo certbot renew --dry-run
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw status verbose
```

Không bật UFW trước khi cho phép OpenSSH. Nếu `www` chưa có DNS, chỉ xin chứng chỉ cho domain gốc.

## 4. Cập nhật an toàn

```bash
cd /home/deploy/apps/canhgacso
sudo bash deploy/ubuntu/update.sh
sudo systemctl --no-pager --full status canhgacso
sudo journalctl -u canhgacso -n 100 --no-pager
```

Script backup SQLite/credential/MFA sidecar, từ chối worktree bẩn, chỉ fast-forward đúng nhánh, không huấn luyện model và không chạm file môi trường.

## 5. Rollback

Đọc `backups/<UTC>/previous_commit.txt`, sau đó kiểm tra commit trước khi thực hiện:

```bash
sudo systemctl stop canhgacso
sudo -u deploy git checkout h07/cybersecurity-ui
sudo -u deploy git reset --hard <PREVIOUS_COMMIT>
sudo -u deploy .venv/bin/python -m pip install -r requirements.txt
sudo cp backups/<UTC>/events.sqlite3 instance/events.sqlite3
sudo chown deploy:deploy instance/events.sqlite3
sudo chmod 600 instance/events.sqlite3
sudo systemctl start canhgacso
```

Rollback là thao tác có chủ đích; không chạy tự động. Sao lưu bản DB hiện tại trước khi phục hồi bản cũ.

## 6. Kiểm tra vận hành

```bash
systemctl is-active canhgacso nginx
ss -ltnp | grep -E ':(80|443|8000)\b'
curl -fsS https://canhgacso.fun/health
curl -o /dev/null -sS -w '%{http_code}\n' 'https://canhgacso.fun/download?path=..%2Fetc%2Fpasswd'
```

Traversal phải trả 403. `/health` cho biết model có được nạp nhưng không tiết lộ secret. Nginx phải ghi đè `X-Forwarded-For` bằng `$remote_addr`; `TRUST_PROXY=1` chỉ an toàn khi Gunicorn bind loopback như unit này.
