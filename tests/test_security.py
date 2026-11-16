from pathlib import Path
import os
import tempfile
import unittest

from app.security import RejectedPath, list_allowed_files, open_authorized, safe_path


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.base = root / 'allowed'
        self.base.mkdir()
        (self.base / 'tailieu').mkdir()
        (self.base / 'baocao.pdf').write_bytes(b'%PDF-1.4\nmock test file\n')
        (self.base / 'báo cáo tốt nghiệp.pdf').write_bytes(b'PDF-DEMO')
        (self.base / 'tailieu' / 'chuong1.pdf').write_bytes(b'CH1')
        (root / 'secret.txt').write_text('NOT PUBLIC', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_files_and_unicode(self):
        for name in ('baocao.pdf', 'báo cáo tốt nghiệp.pdf', 'tailieu/chuong1.pdf'):
            self.assertTrue(safe_path(self.base, name).is_file())
            with open_authorized(self.base, name) as f:
                self.assertTrue(f.read())

    def test_traversal_and_windows_paths_rejected(self):
        bad = [
            '../secret.txt', '../../config.txt', 'tailieu/../../secret.txt',
            '..\\secret.txt', '..\\..\\secret.txt',
            '/etc/passwd', 'C:\\Windows\\win.ini',
            '\\\\server\\share\\file', 'tailieu//chuong1.pdf',
            'CON', 'aux.txt', 'file.txt:stream', './baocao.pdf',
            'tailieu/../baocao.pdf', 'x\x00.txt',
        ]
        for name in bad:
            with self.subTest(name=name):
                with self.assertRaises(RejectedPath):
                    safe_path(self.base, name)

    def test_missing_file_stays_missing(self):
        with self.assertRaises(FileNotFoundError):
            with open_authorized(self.base, 'missing.txt'):
                pass

    def test_external_file_not_listed(self):
        files = list_allowed_files(self.base)
        self.assertIn('baocao.pdf', files)
        self.assertNotIn('secret.txt', files)

    def test_external_symlink_rejected(self):
        symlink = self.base / 'link.txt'
        try:
            symlink.symlink_to(Path(self.tmp.name) / 'secret.txt')
        except (NotImplementedError, OSError):
            self.skipTest('Symlink unavailable without permissions on this system')
        with self.assertRaises(RejectedPath):
            safe_path(self.base, 'link.txt')
        with self.assertRaises(RejectedPath):
            with open_authorized(self.base, 'link.txt'):
                pass

    def test_symlink_directory_rejected(self):
        symlink = self.base / 'shared_out'
        try:
            symlink.symlink_to(Path(self.tmp.name), target_is_directory=True)
        except (NotImplementedError, OSError):
            self.skipTest('Symlink unavailable')
        with self.assertRaises(RejectedPath):
            safe_path(self.base, 'shared_out/secret.txt')


if __name__ == '__main__':
    unittest.main()
