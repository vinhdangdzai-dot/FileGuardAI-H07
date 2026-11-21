"""Prompt locally for a password and persist ONLY its salted Argon2id hash."""
import argparse
from datetime import datetime, timezone
from getpass import getpass
import os
from pathlib import Path
import shutil
import uuid
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.credential_store import credential_lock, atomic_hash_write
from app.passwords import password_hash


def store_password(password, path):
    if len(password) < 6 or len(password) > 128:
        raise ValueError('Use a password from 6 to 128 characters')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with credential_lock(path):
        if path.exists():
            history = path.parent / 'credential_history'
            history.mkdir(exist_ok=True)
            shutil.copy2(path, history / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex + '.hash'))
        atomic_hash_write(path, password_hash(password))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', choices=('admin', 'auditor'), default='admin')
    args = parser.parse_args()
    password = getpass('New password (6-128 characters): ')
    if password != getpass('Confirm password: '):
        raise SystemExit('Confirmation does not match')
    store_password(password, ROOT / 'instance' / (args.role + '_password.hash'))
    print('Hash saved. Active servers reload it on request; prior role sessions are revoked.')
