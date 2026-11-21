"""Document visibility inside the existing path boundary; no ML permissions."""
import os
from pathlib import Path

from .security import RejectedPath, list_allowed_files, safe_path, _windows_opened_path


class LoginRequired(PermissionError):
    pass


def visibility(root, raw, opened=None):
    """Classify canonical paths, including Windows case/short-name aliases.

    Existing root files are public. The reserved top-level restricted directory
    requires any fully authenticated role. Repository OS writers are trusted;
    they must not copy/hardlink restricted content into the public namespace.
    """
    root = Path(root).resolve(strict=True)
    target = _windows_opened_path(opened) if opened is not None and os.name == 'nt' else safe_path(root, raw)
    if not target.is_relative_to(root):
        raise RejectedPath('Truy cập ngoài thư mục cho phép')
    parts = target.relative_to(root).parts
    return 'authenticated' if parts and parts[0].upper() == 'RESTRICTED' else 'public'


def catalog(root, authenticated=False):
    rows = []
    for path in list_allowed_files(root):
        try:
            access = visibility(root, path)
        except (OSError, RejectedPath):
            continue
        if access == 'public' or authenticated:
            rows.append({'path': path, 'visibility': access})
    return rows


def enforce(access, authenticated):
    if access == 'authenticated' and not authenticated:
        raise LoginRequired('Tài liệu hạn chế yêu cầu đăng nhập bằng tài khoản hợp lệ.')
