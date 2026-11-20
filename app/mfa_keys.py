"""Separate versioned AES-256-GCM keyring. Never derive MFA keys from SECRET_KEY."""
import base64
import json
import os
from pathlib import Path
import re
import uuid

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .credential_store import credential_lock


class MFACryptoError(RuntimeError):
    pass


class KeyRing:
    def __init__(self, path, raw=None, encrypted_present=False):
        path = Path(path)
        if raw is None or raw == '':
            with credential_lock(path):
                if path.is_symlink():
                    raise MFACryptoError('MFA key file must not be a symbolic link')
                if not path.exists():
                    if encrypted_present:
                        raise MFACryptoError('MFA key missing: restore the separate key backup; no automatic replacement')
                    content = {'version': 1, 'active': 'k-' + uuid.uuid4().hex[:12], 'keys': {}}
                    content['keys'][content['active']] = base64.urlsafe_b64encode(os.urandom(32)).decode('ascii')
                    temporary=path.with_name('.mfa-key-'+uuid.uuid4().hex+'.tmp')
                    try:
                        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
                            json.dump(content, stream);stream.flush();os.fsync(stream.fileno())
                        os.replace(temporary,path)
                    finally:
                        if temporary.exists():temporary.unlink()
                if path.stat().st_size > 8192 or (os.name != 'nt' and path.stat().st_mode & 0o077):
                    raise MFACryptoError('MFA key file must be private and valid')
                raw = path.read_text(encoding='utf-8')
        try:
            data = json.loads(raw)
            if data['version'] != 1 or not 1 <= len(data['keys']) <= 8:
                raise ValueError()
            self.keys = {}
            for kid, encoded in data['keys'].items():
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', kid):
                    raise ValueError()
                value = base64.b64decode(encoded, altchars=b'-_', validate=True)
                if len(value) != 32:
                    raise ValueError()
                self.keys[kid] = value
            self.active = data['active']
            if self.active not in self.keys:
                raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError):
            raise MFACryptoError('Invalid MFA keyring configuration') from None

    def encrypt(self, subject, plaintext):
        nonce = os.urandom(12)
        aad = ('canhgacso-mfa-v1:' + subject).encode('ascii')
        encrypted = AESGCM(self.keys[self.active]).encrypt(nonce, plaintext.encode('ascii'), aad)
        return self.active + '.' + base64.urlsafe_b64encode(nonce + encrypted).decode('ascii')

    def decrypt(self, subject, encrypted):
        try:
            kid, encoded = encrypted.split('.', 1)
            data = base64.b64decode(encoded, altchars=b'-_', validate=True)
            if len(data) < 29:
                raise ValueError()
            aad = ('canhgacso-mfa-v1:' + subject).encode('ascii')
            return AESGCM(self.keys[kid]).decrypt(data[:12], data[12:], aad).decode('ascii')
        except (ValueError, KeyError, InvalidTag, UnicodeError, AttributeError):
            raise MFACryptoError('MFA encrypted state unavailable; restore the matching keyring') from None
