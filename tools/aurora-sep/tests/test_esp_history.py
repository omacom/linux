"""EFI history custody, boot-reference protection and archive failure controls."""
from pathlib import Path
import importlib.util
import json
import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'esp-history.py'
SPEC = importlib.util.spec_from_file_location('esp_history', SCRIPT)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.esp = self.root / 'esp'; self.esp.mkdir()
        self.state = self.root / 'state'; self.state.mkdir()
        self.destination = self.state / 'esp-history'
        self.conf = self.esp / 'limine.conf'
        self.conf.write_text('/Active\n path: boot():/EFI/Linux/main.efi\n')
        (self.esp / 'EFI/Linux').mkdir(parents=True)
        (self.esp / 'EFI/Linux/main.efi').write_bytes(b'active')
        self.history = self.esp / 'limine_history'; self.history.mkdir()
        self.boot = self.esp / 'm1n1'; self.boot.mkdir()
        (self.boot / 'boot.bin').write_bytes(b'current')
        for index in range(4):
            for p in (self.history / f'old{index}.efi', self.boot / f'boot.bin.before-v{index}'):
                p.write_bytes(bytes([index]) * 100)
                os.utime(p, ns=(index+1, index+1))
        self.locks = [self.root / 'boot.lock', self.root / 'limine.lock']

    def archive(self):
        actual = os.stat
        # The fixture's archive and FAT stand-in share a test filesystem.
        def different(path, *args, **kwargs):
            value = actual(path, *args, **kwargs)
            if Path(path) == self.destination:
                values = list(value); values[2] += 1
                return os.stat_result(values)
            return value
        with patch.object(M.os, 'stat', side_effect=different):
            return M.archive(self.esp, self.state, self.destination, self.locks)

    def test_report_retains_newest_and_never_changes_files(self):
        before = {p:p.read_bytes() for p in self.esp.rglob('*') if p.is_file()}
        rows = M.inventory(self.esp, self.state)
        self.assertEqual(sum(not row['protected'] for row in rows), 4)
        self.assertEqual(sum(row['protected']=='recent' for row in rows), 4)
        self.assertEqual(before, {p:p.read_bytes() for p in self.esp.rglob('*') if p.is_file()})

    def test_archive_verified_copies_and_restore_receipts(self):
        rows = self.archive()
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertFalse((self.esp / row['original']).exists())
            self.assertEqual(M.digest(self.destination / row['archive']), row['sha256'])
            path_key = hashlib.sha256(row['original'].encode()).hexdigest()[:16]
            self.assertEqual(json.loads((self.destination / (row['sha256']+'-'+path_key+'.receipt')).read_text()), row)
        self.assertTrue((self.esp / 'EFI/Linux/main.efi').is_file())
        self.assertTrue((self.boot / 'boot.bin').is_file())
        self.assertEqual(self.archive(), [])

    def test_config_state_and_utf16_references_protect_history(self):
        self.conf.write_text('path: boot():/limine_history/OLD0.EFI...#1234\n')
        (self.state / 'recovery.json').write_text('{"file":"m1n1/boot.bin.before-v0"}')
        (self.esp / 'ubootefi.var').write_bytes('old1.efi'.encode('utf-16-le'))
        archived = {row['original'] for row in self.archive()}
        self.assertEqual(archived, {'m1n1/boot.bin.before-v1'})

    def test_missing_config_keeps_all_files(self):
        self.conf.unlink()
        with self.assertRaisesRegex(ValueError, 'configuration missing'):
            self.archive()
        self.assertTrue((self.history / 'old0.efi').exists())

    def test_same_filesystem_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'different filesystem'):
            M.archive(self.esp, self.state, self.destination, self.locks)
        self.assertTrue((self.history / 'old0.efi').exists())

    def test_symlink_tree_is_refused(self):
        (self.esp / 'linked.conf').symlink_to(self.conf)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.archive()
        self.assertTrue((self.history / 'old0.efi').exists())

    def test_damaged_archive_never_removes_original(self):
        self.destination.mkdir()
        old = self.history / 'old0.efi'
        (self.destination / (M.digest(old)+'.bin')).write_bytes(b'damaged')
        with self.assertRaisesRegex(ValueError, 'damaged archive'):
            self.archive()
        self.assertTrue(old.exists())

    def test_changed_boot_reference_retains_original(self):
        original = M.inventory; calls = 0
        def change(esp, state):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.conf.write_text('path: boot():/m1n1/boot.bin.before-v0\n')
            return original(esp, state)
        with patch.object(M, 'inventory', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'boot state changed'):
                self.archive()
        self.assertTrue((self.boot / 'boot.bin.before-v0').exists())

    def test_copy_write_failure_retains_original(self):
        with patch.object(M.os, 'fsync', side_effect=OSError('write failure')):
            with self.assertRaisesRegex(OSError, 'write failure'):
                self.archive()
        self.assertTrue((self.boot / 'boot.bin.before-v0').exists())

    def test_existing_correct_archive_sync_failure_retains_original(self):
        self.destination.mkdir()
        original = self.boot / 'boot.bin.before-v0'
        saved = self.destination / (M.digest(original) + '.bin')
        saved.write_bytes(original.read_bytes())
        with patch.object(M.os, 'fsync', side_effect=OSError('archive sync failed')):
            with self.assertRaisesRegex(OSError, 'archive sync failed'):
                self.archive()
        self.assertTrue(original.exists())
        self.assertFalse(list(self.destination.glob('*.receipt')))


if __name__ == '__main__':
    unittest.main()
