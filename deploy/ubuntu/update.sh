#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

APP_DIR=${APP_DIR:-/home/deploy/apps/canhgacso}
BRANCH=h07/cybersecurity-ui
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR=$APP_DIR/backups/$STAMP

[[ $EUID -eq 0 ]] || { echo "Run with sudo." >&2; exit 1; }
[[ -d "$APP_DIR/.git" ]] || { echo "Repository not found." >&2; exit 1; }
[[ -f /etc/canhgacso/canhgacso.env ]] || { echo "Production environment file is missing." >&2; exit 1; }

install -d -o deploy -g deploy -m 0750 "$BACKUP_DIR"
if [[ -f "$APP_DIR/instance/events.sqlite3" ]]; then
    sqlite3 "$APP_DIR/instance/events.sqlite3" ".timeout 10000" ".backup '$BACKUP_DIR/events.sqlite3'"
    chown deploy:deploy "$BACKUP_DIR/events.sqlite3"; chmod 0600 "$BACKUP_DIR/events.sqlite3"
fi
for file in admin_password.hash auditor_password.hash mfa_keys.json ai_explanations.sqlite3; do
    [[ ! -f "$APP_DIR/instance/$file" ]] || install -o deploy -g deploy -m 0600 "$APP_DIR/instance/$file" "$BACKUP_DIR/$file"
done
sudo -u deploy git -C "$APP_DIR" diff --quiet && sudo -u deploy git -C "$APP_DIR" diff --cached --quiet || {
    echo "Refusing update: VPS worktree has local tracked changes." >&2; exit 1;
}
OLD_COMMIT=$(sudo -u deploy git -C "$APP_DIR" rev-parse HEAD)
echo "$OLD_COMMIT" > "$BACKUP_DIR/previous_commit.txt"
chown deploy:deploy "$BACKUP_DIR/previous_commit.txt"

sudo -u deploy git -C "$APP_DIR" fetch origin "$BRANCH"
sudo -u deploy git -C "$APP_DIR" checkout "$BRANCH"
sudo -u deploy git -C "$APP_DIR" merge --ff-only "origin/$BRANCH"
sudo -u deploy "$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"
[[ ! -f /etc/systemd/system/canhgacso.service ]] || cp -a /etc/systemd/system/canhgacso.service "$BACKUP_DIR/canhgacso.service"
install -o root -g root -m 0644 "$APP_DIR/deploy/ubuntu/canhgacso.service" /etc/systemd/system/canhgacso.service

for path in artifacts/model.joblib data/paths_synthetic.csv instance/admin_password.hash; do
    [[ -f "$APP_DIR/$path" ]] || { echo "Missing required runtime file after update: $path" >&2; exit 1; }
done
systemctl daemon-reload
nginx -t
systemctl restart canhgacso
systemctl reload nginx
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/health
echo
echo "Updated successfully. Backup: $BACKUP_DIR; previous commit: $OLD_COMMIT"
