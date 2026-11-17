"""Private local credential storage; locks span threads/processes, writes are atomic."""
from contextlib import contextmanager
import hashlib
import hmac
import os
from pathlib import Path
import re
import threading
import uuid

_LOCK = threading.RLock()


def validate_hash(value):
    if not isinstance(value,str) or not re.fullmatch(r'(scrypt:\d+:\d+:\d+|pbkdf2:[A-Za-z0-9_]+:\d+)\$[A-Za-z0-9]+\$[0-9a-f]+',value):
        raise ValueError('Invalid Werkzeug credential hash; restore with credential CLI')
    if value.startswith('pbkdf2:') and value.split(':')[1] not in hashlib.algorithms_available:
        raise ValueError('Unsupported credential digest')
    return value


def read_hash(path):
    path = Path(path)
    if path.stat().st_size > 4096:
        raise ValueError('Invalid credential file')
    value = path.read_text(encoding='utf-8').strip()
    return validate_hash(value)


@contextmanager
def credential_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with _LOCK:
        with (path.parent/'.credential-update.lock').open('a+b') as lock:
            lock.seek(0,2)
            if lock.tell()==0:
                lock.write(b'0');lock.flush()
            lock.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(lock.fileno(),msvcrt.LK_LOCK,1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            try:
                yield
            finally:
                lock.seek(0)
                if os.name=='nt':msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def atomic_hash_write(path,value):
    """Caller holds credential_lock. Never truncate the active file."""
    value=validate_hash(value)
    path=Path(path)
    temporary=path.with_name('.credential-'+uuid.uuid4().hex+'.tmp')
    try:
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:
            stream.write(value+'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


class Credentials:
    def __init__(self,app):self.app=app

    def current(self,role):
        if role=='admin':return read_hash(self.app.config['ADMIN_HASH_FILE'])
        path=self.app.config.get('AUDITOR_HASH_FILE')
        if path and Path(path).is_file():return read_hash(path)
        return self.app.config.get('AUDITOR_HASH')

    def version(self,role,value=None):
        # Cookie stores a keyed opaque version, never the password hash itself.
        key=self.app.secret_key
        if isinstance(key,str):key=key.encode('utf-8')
        return hmac.new(key,(role+':'+str(self.current(role) if value is None else value)).encode('utf-8'),hashlib.sha256).hexdigest()
