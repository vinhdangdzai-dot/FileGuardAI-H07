"""Report three real Windows symlink checks without changing OS privileges."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app
from app.security import open_authorized, RejectedPath


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix='h07_symlink_') as tmp:
        parent = Path(tmp)
        base = parent / 'shared_files'
        base.mkdir()
        (parent / 'secret.txt').write_bytes(b'PRIVATE-SYMLINK-FIXTURE')
        app = create_app({'TESTING': True, 'FILES_ROOT': base, 'DATABASE': parent / 'events.sqlite3',
                          'MODEL_PATH': parent / 'missing.joblib'})
        for name, directory, http in [('file_policy', False, False), ('directory_policy', True, False), ('http_file', False, True)]:
            link = base / name
            try:
                link.symlink_to(parent if directory else parent / 'secret.txt', target_is_directory=directory)
            except OSError as exc:
                results.append({'case': name, 'result': 'SKIP', 'winerror': getattr(exc, 'winerror', None), 'reason': exc.strerror})
                continue
            query = name + ('/secret.txt' if directory else '')
            if http:
                with app.test_client().get('/download', query_string={'path': query}) as r:
                    ok = r.status_code == 403 and b'PRIVATE-SYMLINK-FIXTURE' not in r.data
            else:
                try:
                    with open_authorized(base, query):
                        pass
                except RejectedPath:
                    ok = True
                else:
                    ok = False
            results.append({'case': name, 'result': 'PASS' if ok else 'FAIL'})
    print(json.dumps({'cases': results}, ensure_ascii=True, indent=2))
    return int(any(r['result'] == 'FAIL' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
