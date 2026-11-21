"""Argon2id for new credentials; verify existing Werkzeug hashes during migration."""
from contextlib import contextmanager
import threading

from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import HashingError, InvalidHashError, VerificationError, VerifyMismatchError
from werkzeug.security import check_password_hash as verify_werkzeug

HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1,
                        hash_len=32, salt_len=16, type=Type.ID)
_SLOTS = threading.BoundedSemaphore(2)  # Bound simultaneous Argon2 operations/process.


class PasswordBusy(RuntimeError):
    pass


@contextmanager
def hashing_slot():
    if not _SLOTS.acquire(timeout=5):
        raise PasswordBusy('Password verification temporarily busy')
    try:
        yield
    finally:
        _SLOTS.release()


def validate_argon_hash(value):
    if not isinstance(value, str) or not value.startswith('$argon2id$') or len(value) > 1024:
        raise ValueError('Invalid Argon2id credential')
    try:
        parameters = extract_parameters(value)
    except (InvalidHashError, ValueError):
        raise ValueError('Invalid Argon2id credential') from None
    if not (parameters.type == Type.ID and parameters.version == 19
            and 19456 <= parameters.memory_cost <= 131072
            and 2 <= parameters.time_cost <= 10 and 1 <= parameters.parallelism <= 8
            and parameters.salt_len >= 16 and parameters.hash_len >= 32):
        raise ValueError('Unsupported Argon2id parameters')
    return value


def password_hash(password):
    # Six is the explicitly retained localhost demo policy; see security limitations.
    if not isinstance(password, str) or not 6 <= len(password) <= 128:
        raise ValueError('password_length')
    with hashing_slot():
        try:
            return HASHER.hash(password)  # The library generates a fresh random salt.
        except HashingError:
            raise PasswordBusy('Password hashing temporarily unavailable') from None


def check_password_hash(stored, password):
    if not isinstance(stored, str) or not isinstance(password, str) or len(password) > 128:
        return False
    if stored.startswith('$argon2'):
        try:
            validate_argon_hash(stored)
            with hashing_slot():
                return HASHER.verify(stored, password)
        except (InvalidHashError, VerifyMismatchError, ValueError):
            return False
        except VerificationError:
            raise PasswordBusy('Password verification temporarily unavailable') from None
    try:
        return verify_werkzeug(stored, password)
    except (ValueError, TypeError):
        return False


def needs_upgrade(stored):
    if not stored.startswith('$argon2id$'):
        return True
    parameters=extract_parameters(validate_argon_hash(stored))
    return (parameters.memory_cost < HASHER.memory_cost or parameters.time_cost < HASHER.time_cost
            or parameters.hash_len < HASHER.hash_len or parameters.salt_len < HASHER.salt_len)
