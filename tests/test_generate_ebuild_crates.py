import os
import json
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil
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

if __name__ == "__main__":
    unittest.main()
