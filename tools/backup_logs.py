"""Local operator-only SQLite online backup, no overwrite or source mutation."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]


def backup_logs(source, destination):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve()
    if source == destination:
        raise ValueError('Backup must differ from source')
    if destination.is_relative_to((ROOT / 'shared_files').resolve()):
        raise ValueError('Never place log backups in the public file repository')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Reserve an exclusive destination rather than overwriting prior evidence.
    with destination.open('xb'):
        pass
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Backup integrity check failed')
    return destination


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destination', type=Path)
    p.add_argument('--source', type=Path, default=ROOT / 'instance/events.sqlite3')
    args = p.parse_args()
    print('Backup created:', backup_logs(args.source, args.destination))
