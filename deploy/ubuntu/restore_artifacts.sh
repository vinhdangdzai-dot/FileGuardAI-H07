#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

APP_DIR=${APP_DIR:-/home/deploy/apps/canhgacso}
MODEL_SHA=4d7324aa302ecb3d1b731561210a0041e4aef3f740cc68d9187097a80e5a6322
DATA_SHA=2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0

usage() { echo "Usage: sudo $0 /trusted/model.joblib /trusted/paths_synthetic.csv" >&2; exit 2; }
[[ $# -eq 2 ]] || usage
[[ $EUID -eq 0 ]] || { echo "Run with sudo." >&2; exit 1; }
MODEL_SOURCE=$1
DATA_SOURCE=$2
[[ -f "$MODEL_SOURCE" && ! -L "$MODEL_SOURCE" ]] || { echo "Trusted model source is missing or a symlink." >&2; exit 1; }
[[ -f "$DATA_SOURCE" && ! -L "$DATA_SOURCE" ]] || { echo "Trusted dataset source is missing or a symlink." >&2; exit 1; }

check_hash() {
    local path=$1 expected=$2 actual
    actual=$(sha256sum -- "$path" | awk '{print $1}')
    [[ "$actual" == "$expected" ]] || { echo "SHA-256 mismatch: $path" >&2; exit 1; }
}
check_hash "$MODEL_SOURCE" "$MODEL_SHA"
check_hash "$DATA_SOURCE" "$DATA_SHA"
install -d -o deploy -g deploy -m 0750 "$APP_DIR/artifacts" "$APP_DIR/data"

for target in "$APP_DIR/artifacts/model.joblib" "$APP_DIR/data/paths_synthetic.csv"; do
    if [[ -e "$target" ]]; then
        echo "Refusing to overwrite existing artifact: $target" >&2
        exit 1
    fi
done
install -o deploy -g deploy -m 0640 "$MODEL_SOURCE" "$APP_DIR/artifacts/model.joblib"
install -o deploy -g deploy -m 0640 "$DATA_SOURCE" "$APP_DIR/data/paths_synthetic.csv"
check_hash "$APP_DIR/artifacts/model.joblib" "$MODEL_SHA"
check_hash "$APP_DIR/data/paths_synthetic.csv" "$DATA_SHA"
echo "Trusted model and dataset restored with verified SHA-256."
