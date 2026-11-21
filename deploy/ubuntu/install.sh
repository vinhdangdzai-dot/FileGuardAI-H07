#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

APP_DIR=${APP_DIR:-/home/deploy/apps/canhgacso}
ENV_DIR=/etc/canhgacso
ENV_FILE=$ENV_DIR/canhgacso.env
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)

[[ $EUID -eq 0 ]] || { echo "Run with sudo." >&2; exit 1; }
id deploy >/dev/null 2>&1 || { echo "Linux account deploy does not exist." >&2; exit 1; }
[[ -d "$APP_DIR/.git" && -f "$APP_DIR/app/web.py" ]] || { echo "Repository not found at $APP_DIR" >&2; exit 1; }

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip nginx certbot python3-certbot-nginx sqlite3

install -d -o deploy -g deploy -m 0750 "$APP_DIR/instance" "$APP_DIR/artifacts" "$APP_DIR/data"
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    sudo -u deploy python3 -m venv "$APP_DIR/.venv"
fi
sudo -u deploy "$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
sudo -u deploy "$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

install -d -o root -g deploy -m 0750 "$ENV_DIR"
if [[ ! -e "$ENV_FILE" ]]; then
    install -o root -g deploy -m 0640 "$SCRIPT_DIR/env.example" "$ENV_FILE"
    secret=$("$APP_DIR/.venv/bin/python" -c 'import secrets; print(secrets.token_hex(32))')
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$secret/" "$ENV_FILE"
    unset secret
    echo "Created $ENV_FILE. Review optional SMTP/Gemini settings before production."
else
    echo "Preserving existing $ENV_FILE."
fi

install -o root -g root -m 0644 "$SCRIPT_DIR/canhgacso.service" /etc/systemd/system/canhgacso.service
if [[ ! -e /etc/nginx/sites-available/canhgacso ]]; then
    install -o root -g root -m 0644 "$SCRIPT_DIR/nginx.conf" /etc/nginx/sites-available/canhgacso
fi
if [[ ! -e /etc/nginx/sites-enabled/canhgacso && ! -L /etc/nginx/sites-enabled/canhgacso ]]; then
    ln -s /etc/nginx/sites-available/canhgacso /etc/nginx/sites-enabled/canhgacso
fi
nginx -t
systemctl daemon-reload
systemctl enable canhgacso nginx

missing=0
for path in "$APP_DIR/artifacts/model.joblib" "$APP_DIR/data/paths_synthetic.csv" "$APP_DIR/instance/admin_password.hash"; do
    if [[ ! -f "$path" ]]; then echo "Required before start: $path" >&2; missing=1; fi
done
if [[ $missing -ne 0 ]]; then
    echo "Installation prepared but service NOT started. Restore artifacts and configure Admin first." >&2
    exit 3
fi

chown -R deploy:deploy "$APP_DIR/instance"
systemctl restart canhgacso
systemctl reload nginx
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/health
echo
echo "Application service is healthy on loopback. Run Certbot only after DNS is verified."
