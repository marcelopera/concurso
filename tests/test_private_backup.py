import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.private_backup import copy_tree, create_backup, tree_manifest, verify_tree


class PrivateBackupTests(unittest.TestCase):
    def test_manifest_includes_empty_directories_and_verifies_exact_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            (root / "empty").mkdir(parents=True)
            (root / "nested").mkdir()
            (root / "nested" / "data.bin").write_bytes(b"private")
            expected = tree_manifest(root)

            verify_tree(root, expected)
            (root / "extra.txt").write_text("unexpected", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "extras"):
                verify_tree(root, expected)

    def test_copy_excludes_only_explicit_components(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            (root / "skip-me" / "nested").mkdir(parents=True)
            (root / "skip-me" / "nested" / "skip.txt").write_text("skip", encoding="utf-8")
            (root / "kept.txt").write_text("keep", encoding="utf-8")
            destination = Path(temporary) / "copy"

            copy_tree(root, destination, frozenset({"skip-me"}))

            expected = tree_manifest(root, frozenset({"skip-me"}))
            verify_tree(destination, expected)
            self.assertFalse((destination / "skip-me").exists())
            self.assertEqual((destination / "kept.txt").read_text(encoding="utf-8"), "keep")

    def test_copy_preserves_symlinks_when_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            (root / "kept.txt").write_text("keep", encoding="utf-8")
            try:
                (root / "link").symlink_to("kept.txt")
            except OSError as error:
                self.skipTest(f"Symlink creation unavailable on this system: {error}")
            destination = Path(temporary) / "copy"

            copy_tree(root, destination, frozenset())

            verify_tree(destination, tree_manifest(root))
            self.assertTrue((destination / "link").is_symlink())

    def test_verification_fails_when_content_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "dataset.jsonl").write_text("original", encoding="utf-8")
            expected = tree_manifest(root)
            (root / "dataset.jsonl").write_text("changed", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "divergentes"):
                verify_tree(root, expected)

    def test_backup_destination_cannot_recurse_into_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "checkout"
            source.mkdir()
            subprocess.run(["git", "init", str(source)], check=True, capture_output=True)

            with self.assertRaisesRegex(ValueError, "fora do checkout"):
                create_backup(source, source / "backups", "unused-remote", "test-run")

            self.assertFalse((source / "backups").exists())


if __name__ == "__main__":
    unittest.main()
