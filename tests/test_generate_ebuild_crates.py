import os
import json
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
import subprocess
import generate_ebuild_crates


class TestGenerateEbuildCrates(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    # --- Extraction Tests ---

    def test_get_crates_lockfile(self):
        lock_content = b"""
[[package]]
name = "libc"
version = "0.2.147"
source = "registry+https://github.com/rust-lang/crates.io-index"

[[package]]
name = "other"
version = "1.0.0"
# No source, should be ignored (likely local or git)

[[package]]
name = "serde"
version = "1.0.171"
source = "registry+https://github.com/rust-lang/crates.io-index"
"""
        lock_path = os.path.join(self.test_dir, "Cargo.lock")
        with open(lock_path, "wb") as f:
            f.write(lock_content)
        
        crates = generate_ebuild_crates.get_crates_lockfile(self.test_dir)
        self.assertEqual(crates, ["libc@0.2.147", "serde@1.0.171"])

    @patch("subprocess.run")
    def test_get_crates_metadata(self, mock_run):
        # Mock Cargo.toml existence
        with open(os.path.join(self.test_dir, "Cargo.toml"), "w") as f:
            f.write("[package]")
        
        mock_stdout = {
            "packages": [
                {
                    "name": "libc",
                    "version": "0.2.147",
                    "source": "registry+https://github.com/rust-lang/crates.io-index"
                },
                {
                    "name": "serde",
                    "version": "1.0.171",
                    "source": "registry+https://github.com/rust-lang/crates.io-index"
                },
                {
                    "name": "local-pkg",
                    "version": "0.1.0",
                    "source": None
                }
            ]
        }
        
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_stdout),
            check_returncode=lambda: None
        )
        
        crates = generate_ebuild_crates.get_crates_metadata(self.test_dir)
        self.assertEqual(crates, ["libc@0.2.147", "serde@1.0.171"])

    # --- Formatting Tests ---

    def test_format_crates_block(self):
        crates = ["libc@0.2.147", "serde@1.0.171"]
        expected = 'CRATES="\n    libc@0.2.147\n    serde@1.0.171\n"'
        self.assertEqual(generate_ebuild_crates.format_crates_block(crates), expected)

    def test_format_crates_block_empty(self):
        self.assertEqual(generate_ebuild_crates.format_crates_block([]), 'CRATES=""')

    # --- Ebuild Update Tests ---

    def test_update_ebuild_replace(self):
        ebuild_path = os.path.join(self.test_dir, "test.ebuild")
        with open(ebuild_path, "w") as f:
            f.write('EAPI=8\nCRATES="old@1.0"\ninherit cargo')
        
        new_block = 'CRATES="\n    new@2.0\n"'
        generate_ebuild_crates.update_ebuild(ebuild_path, new_block)
        
        with open(ebuild_path, "r") as f:
            content = f.read()
        self.assertIn('CRATES="\n    new@2.0\n"', content)
        self.assertNotIn('old@1.0', content)

    def test_update_ebuild_insert(self):
        ebuild_path = os.path.join(self.test_dir, "test.ebuild")
        with open(ebuild_path, "w") as f:
            f.write('EAPI=8\ninherit cargo')
        
        new_block = 'CRATES="\n    new@2.0\n"'
        generate_ebuild_crates.update_ebuild(ebuild_path, new_block)
        
        with open(ebuild_path, "r") as f:
            content = f.read()
        self.assertEqual(content, f'EAPI=8\n{new_block}\n\ninherit cargo')

    def test_update_ebuild_append(self):
        ebuild_path = os.path.join(self.test_dir, "test.ebuild")
        with open(ebuild_path, "w") as f:
            f.write('EAPI=8')
        
        new_block = 'CRATES="\n    new@2.0\n"'
        generate_ebuild_crates.update_ebuild(ebuild_path, new_block)
        
        with open(ebuild_path, "r") as f:
            content = f.read()
        self.assertEqual(content, f'EAPI=8\n\n{new_block}\n')

    # --- Additional coverage tests to achieve 100% ---

    def test_get_crates_metadata_missing_cargo_toml(self):
        with self.assertRaises(SystemExit) as e:
            generate_ebuild_crates.get_crates_metadata(self.test_dir)
        self.assertEqual(e.exception.code, 1)

    @patch("subprocess.run")
    def test_get_crates_metadata_cargo_missing(self, mock_run):
        with open(os.path.join(self.test_dir, "Cargo.toml"), "w") as f:
            f.write("[package]")
        mock_run.side_effect = FileNotFoundError()
        with self.assertRaises(SystemExit) as e:
            generate_ebuild_crates.get_crates_metadata(self.test_dir)
        self.assertEqual(e.exception.code, 1)

    @patch("subprocess.run")
    def test_get_crates_metadata_cargo_failed(self, mock_run):
        with open(os.path.join(self.test_dir, "Cargo.toml"), "w") as f:
            f.write("[package]")
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["cargo", "metadata"], stderr="Metadata failed"
        )
        with self.assertRaises(SystemExit) as e:
            generate_ebuild_crates.get_crates_metadata(self.test_dir)
        self.assertEqual(e.exception.code, 1)

    def test_get_crates_lockfile_tomllib_none(self):
        # Temporarily mock tomllib to None
        with patch("generate_ebuild_crates.tomllib", None):
            with self.assertRaises(SystemExit) as e:
                generate_ebuild_crates.get_crates_lockfile(self.test_dir)
            self.assertEqual(e.exception.code, 1)

    def test_get_crates_lockfile_missing(self):
        with self.assertRaises(SystemExit) as e:
            generate_ebuild_crates.get_crates_lockfile(self.test_dir)
        self.assertEqual(e.exception.code, 1)

    def test_update_ebuild_missing_ebuild(self):
        with self.assertRaises(SystemExit) as e:
            generate_ebuild_crates.update_ebuild(os.path.join(self.test_dir, "nonexistent.ebuild"), "block")
        self.assertEqual(e.exception.code, 1)

    @patch("generate_ebuild_crates.get_crates_metadata")
    @patch("sys.argv", ["generate_ebuild_crates.py", "/fake/path"])
    def test_main_stdout_metadata(self, mock_get_crates):
        mock_get_crates.return_value = ["a@1.0"]
        with patch('builtins.print') as mock_print:
            generate_ebuild_crates.main()
            mock_print.assert_any_call('CRATES="\n    a@1.0\n"')

    @patch("generate_ebuild_crates.get_crates_lockfile")
    @patch("sys.argv", ["generate_ebuild_crates.py", "/fake/path", "--method", "lockfile"])
    def test_main_stdout_lockfile(self, mock_get_crates):
        mock_get_crates.return_value = ["b@2.0"]
        with patch('builtins.print') as mock_print:
            generate_ebuild_crates.main()
            mock_print.assert_any_call('CRATES="\n    b@2.0\n"')


    @patch("generate_ebuild_crates.get_crates_metadata")
    @patch("generate_ebuild_crates.update_ebuild")
    @patch("sys.argv", ["generate_ebuild_crates.py", "/fake/path", "--ebuild", "test.ebuild"])
    def test_main_update_ebuild(self, mock_update_ebuild, mock_get_crates):
        mock_get_crates.return_value = ["a@1.0"]
        generate_ebuild_crates.main()
        mock_update_ebuild.assert_called_once_with("test.ebuild", 'CRATES="\n    a@1.0\n"')

    def test_main_invocation(self):
        import runpy
        import sys
        with patch("sys.argv", ["generate_ebuild_crates.py", "--help"]):
            try:
                runpy.run_path(
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "../generate_ebuild_crates.py")),
                    run_name="__main__"
                )
            except SystemExit as e:
                self.assertEqual(e.code, 0)

    def test_import_without_tomllib(self):
        import sys
        import importlib
        # Mock sys.modules to simulate python without tomllib
        with patch.dict(sys.modules, {'tomllib': None}):
            importlib.reload(generate_ebuild_crates)
            self.assertIsNone(generate_ebuild_crates.tomllib)
        # Restore
        importlib.reload(generate_ebuild_crates)



if __name__ == "__main__":
    unittest.main()
