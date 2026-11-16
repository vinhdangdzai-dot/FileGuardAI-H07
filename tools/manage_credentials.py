"""Prompt locally for a password and persist ONLY its Werkzeug hash."""
import argparse
from datetime import datetime, timezone
from getpass import getpass
import os
from pathlib import Path
import shutil
import uuid
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]


def store_password(password, path):
    if len(password) < 12 or len(password) > 128:
        raise ValueError('Use a password from 12 to 128 characters')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        history = path.parent / 'credential_history'
        history.mkdir(exist_ok=True)
        shutil.copy2(path, history / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex + '.hash'))
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8') as f:
        f.write(generate_password_hash(password) + '\n')
    os.chmod(temporary, 0o600)
    temporary.replace(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', choices=('admin', 'auditor'), default='admin')
    args = parser.parse_args()
    password = getpass('New password (12-128 characters): ')
    if password != getpass('Confirm password: '):
        raise SystemExit('Confirmation does not match')
    store_password(password, ROOT / 'instance' / (args.role + '_password.hash'))
    print('Hash saved. Restart Flask to activate; existing sessions will expire.')
