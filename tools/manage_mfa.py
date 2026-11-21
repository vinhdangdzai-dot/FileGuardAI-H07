"""Local recovery of an Admin factor; never disables the requirement to enroll MFA."""
import argparse
from contextlib import closing, nullcontext
from getpass import getpass
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.account_store import audit, find, take_rate
from app.credential_store import credential_lock, read_hash
from app.database import connect, init_db
from app.passwords import check_password_hash


def recover(database, subject, password, admin_file):
    if not Path(database).is_file():
        raise ValueError('Existing account database is required')
    init_db(database)  # Additive migration only; no application/keyring startup.
    if not take_rate(database, 'mfa_console_recovery', subject, 5, 300):
        raise ValueError('Recovery rate limited')
    legacy = subject == 'legacy:admin'
    with credential_lock(admin_file) if legacy else nullcontext():
        row = None if legacy else find(database, identifier=subject)
        stored = read_hash(admin_file) if legacy else row['password_hash'] if row else ''
        valid = check_password_hash(stored, password) and (legacy or row['role'] == 'admin' and row['active'])
        target = 'legacy:admin' if legacy else 'user:' + str(row['id']) if row else None
        with closing(connect(database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if not legacy and row:
                active = db.execute('SELECT password_hash,role,active FROM auth_users WHERE id=?', (row['id'],)).fetchone()
                valid = valid and active and active['active'] and active['role'] == 'admin' and active['password_hash'] == stored
            if valid:
                db.execute('UPDATE auth_mfa SET enabled=0,version=? WHERE subject=?', (secrets.token_urlsafe(32), target))
                db.execute('UPDATE auth_backup_codes SET used=1 WHERE subject=?', (target,))
                db.execute('UPDATE auth_sessions SET revoked=1 WHERE subject=?', (target,))
                db.execute('UPDATE auth_mfa_challenges SET used=1 WHERE subject=?', (target,))
                audit(db, 'local', 'admin', 'mfa_console_recovery:' + target)
            else:
                audit(db, 'local', 'anonymous', 'mfa_console_recovery_failed')
        if not valid:
            raise ValueError('Cannot verify an active Admin account')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--account', default='legacy:admin', help='legacy:admin or an Admin username/email')
    parser.add_argument('--database', type=Path, default=ROOT / 'instance/events.sqlite3')
    parser.add_argument('--admin-hash', type=Path, default=ROOT / 'instance/admin_password.hash')
    args = parser.parse_args()
    print('Local operator identity must be verified. Back up SQLite and the separate MFA keyring first.')
    if input('Type RESET MFA to revoke this Admin factor and require enrollment again: ') != 'RESET MFA':
        return 1
    try:
        recover(args.database, args.account, getpass('Current Admin password: '), args.admin_hash)
    except (ValueError, OSError):
        print('Recovery rejected. Restore the appropriate backup or check account/permissions.')
        return 1
    print('Factor revoked; accounts, password hashes and logs preserved. Next login requires new TOTP enrollment.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
