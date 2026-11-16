"""Path access boundary. AI scores never grant filesystem access.

On POSIX, openat-style per-component O_NOFOLLOW prevents symlink replacement
between authorization and open. On Windows, this local educational demo rejects
links and checks resolved containment, but requires a trusted, non-writable
file repository to avoid reparse-point / TOCTOU races.
"""
from __future__ import annotations

import os
import re
import stat
from pathlib import Path


class RejectedPath(ValueError):
    """The requested path violates the file repository policy."""


_WINDOWS_RESERVED = re.compile(
    r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.IGNORECASE
)
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
# Reserved URL escapes after Flask's single transport decode. %25 is reserved
# too, so nested encodings are rejected in constant passes, never unwrapped.
_RESIDUAL_STRUCTURE = re.compile(r"%(?:25|2e|2f|5c|00|3a)", re.IGNORECASE)


def validate_relative_path(raw: str) -> tuple[str, ...]:
    """Validate a framework-decoded path exactly once; do not URL-decode again."""
    if not isinstance(raw, str) or not raw or len(raw) > 4096:
        raise RejectedPath("Đường dẫn trống hoặc quá dài")
    if _RESIDUAL_STRUCTURE.search(raw):
        raise RejectedPath("Đường dẫn chứa mã hóa cấu trúc URL còn sót lại")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in raw):
        raise RejectedPath("Đường dẫn chứa ký tự điều khiển")
    if "\x00" in raw or "\\" in raw or _WINDOWS_DRIVE.match(raw) or raw.startswith("/"):
        raise RejectedPath("Đường dẫn tuyệt đối hoặc ký tự phân cách không hợp lệ")
    if any(ch in raw for ch in ':*?"<>|'):
        raise RejectedPath("Tên tệp chứa ký tự không hợp lệ")
    parts = tuple(raw.split("/"))
    if any(
        p in {"", ".", ".."}
        or p.endswith(".") or p.endswith(" ")
        or _WINDOWS_RESERVED.fullmatch(p)
        for p in parts
    ):
        raise RejectedPath("Đường dẫn chứa thành phần không hợp lệ")
    return parts


def safe_path(base: Path, raw: str) -> Path:
    """Resolve links, compare path components, reject any symlink in path."""
    parts = validate_relative_path(raw)
    base = Path(base).resolve(strict=True)
    if not base.is_dir():
        raise RejectedPath("Thư mục lưu trữ không hợp lệ")
    candidate = base.joinpath(*parts)
    current = base
    for name in parts:
        current = current / name
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(metadata.st_mode)
                or getattr(metadata, 'st_file_attributes', 0)
                & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)):
            raise RejectedPath("Không cho phép symlink hoặc reparse point")
    target = candidate.resolve(strict=False)
    if not target.is_relative_to(base):
        raise RejectedPath("Truy cập ngoài thư mục cho phép")
    return target


def open_authorized(base: Path, raw: str):
    """Return an open *regular file*; caller must close after streaming.

    POSIX implementation uses directory fds and O_NOFOLLOW for each path
    component; on Windows use only with a repository that untrusted users
    cannot mutate (see README limitation).
    """
    path = safe_path(base, raw)
    parts = validate_relative_path(raw)
    if os.name == 'posix' and hasattr(os, 'O_NOFOLLOW'):
        dflags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        base_fd = os.open(str(Path(base).resolve(strict=True)), dflags)
        current_fd = base_fd
        try:
            for name in parts[:-1]:
                next_fd = os.open(name, dflags, dir_fd=current_fd)
                if current_fd != base_fd:
                    os.close(current_fd)
                current_fd = next_fd
            flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0)
            file_fd = os.open(parts[-1], flags, dir_fd=current_fd)
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                os.close(file_fd)
                raise RejectedPath("Chỉ được phép tải tệp thông thường")
            return os.fdopen(file_fd, 'rb')
        except OSError as exc:
            if exc.errno in {getattr(__import__('errno'), 'ELOOP'), getattr(__import__('errno'), 'ENOTDIR')}:
                raise RejectedPath("Liên kết hoặc thư mục không hợp lệ") from exc
            raise
        finally:
            if current_fd != base_fd:
                os.close(current_fd)
            os.close(base_fd)
    if path.is_dir():
        raise RejectedPath("Chỉ được phép tải tệp thông thường")
    try:
        f = open(path, 'rb')
    except IsADirectoryError as exc:
        raise RejectedPath("Chỉ được phép tải tệp thông thường") from exc
    if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
        f.close()
        raise RejectedPath("Chỉ được phép tải tệp thông thường")
    return f


def list_allowed_files(base: Path) -> list[str]:
    """List only regular files that pass the same authorization policy."""
    root = Path(base).resolve(strict=True)
    result = []
    for p in root.rglob('*'):
        if len(result) >= 200:
            break
        if p.is_symlink() or not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        try:
            safe_path(root, rel)
        except (RejectedPath, OSError):
            continue
        result.append(rel)
    return sorted(result, key=str.casefold)
