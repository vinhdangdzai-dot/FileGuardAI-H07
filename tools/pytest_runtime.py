"""Allocate fresh, disposable pytest paths without consulting system TEMP.

Never pass an existing directory to --basetemp: pytest recursively clears it.
Only our new UUID parent is created; its pytest child must not exist yet.
No cleanup of previous runs, cache directories or user TEMP is performed.
"""
import os
from pathlib import Path
import uuid


def create_runtime(workspace, purpose='pytest'):
    workspace = Path(workspace).resolve(strict=True)
    if purpose not in ('pytest', 'acceptance'):
        raise ValueError('Unknown test runtime purpose')
    # No shared parent: it too could have been created under another account
    # with an owner-only ACL. Each invocation creates a direct fresh sibling.
    run = workspace / ('.test_runtime_' + purpose + '_' + uuid.uuid4().hex)
    if not run.resolve().is_relative_to(workspace):
        raise PermissionError('Test runtime must remain inside workspace')
    run.mkdir(exist_ok=False)
    temporary = run / 'os_tmp'
    temporary.mkdir()
    # Verify write access now; an actual failure must remain an ERROR.
    with (temporary / 'write_probe').open('x', encoding='utf-8') as stream:
        stream.write('owned test runtime\n')
    return {'root': run, 'basetemp': run / 'pytest', 'temporary': temporary}


def runtime_environment(runtime, original=None):
    env = dict(os.environ if original is None else original)
    for key in ('TEMP', 'TMP', 'TMPDIR'):
        env[key] = str(runtime['temporary'])
    env['PYTHONIOENCODING'] = 'utf-8'
    return env
