# -*- coding: utf-8 -*-
"""
Deep-dive test suite for Line Endings (LF vs CRLF).
This test explicitly targets cross-platform compatibility and byte-level correctness.

Why this test is effective:
1. It uses BYTES (wb/rb) to create and read files, bypassing Python's automatic newline conversion.
2. It tests applying a Unix-style (LF) patch to a Windows-style (CRLF) file and vice-versa.
3. It validates the centralized line_endings.py utility in extreme edge cases (Mixed endings, CR-only).
"""
import unittest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core
from Scripts.Utils import line_endings

class TestLineEndingsDeep(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_LE_DEEP_"))
        self.resource_dir = Path(__file__).parent / "Resources" / "LineEndings"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_apply_lf_patch_to_crlf_file(self):
        """
        [TEST: Cross-Platform Matching]
        Scenario: File on disk is Windows (CRLF), but the V2 Patch is Unix (LF).
        Requirement: Centralized ensure_lf must allow FIND to match correctly.
        """
        # 1. Create a CRLF file manually
        target_file = self.test_dir / "windows.txt"
        with open(target_file, "wb") as f:
            f.write(b"Line 1\r\nLine 2\r\nLine 3")

        # 2. V2 Patch with LF (typical for AI/Web editors)
        patch_text = (
            "@@@PATCH_BEGIN {{Root}}/windows.txt\n"
            "@@@FIND_BEGIN {{None}}\nLine 2\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\nREPLACED\n@@@REPLACE_END\n"
            "@@@PATCH_END"
        )

        plan = scaffold_core.generate_plan(self.test_dir, patch_text, {})
        
        # Check if matched and replaced without error
        self.assertEqual(len(plan.errors), 0, f"Match failed: {plan.errors}")
        
        # Result in memory should be LF normalized
        self.assertEqual(plan.file_contents[target_file], "Line 1\nREPLACED\nLine 3")

    def test_mixed_endings_normalization(self):
        """
        [TEST: Resilience]
        Scenario: A file has mixed LF, CRLF, and CR endings (corruption simulation).
        Requirement: ensure_lf must unify all to LF perfectly.
        """
        mixed_input = b"L1\nL2\r\nL3\rL4"
        expected_output = "L1\nL2\nL3\nL4"
        
        # Manual byte read simulation
        text = mixed_input.decode('utf-8')
        normalized = line_endings.ensure_lf(text)
        self.assertEqual(normalized, expected_output)

    def test_ensure_native_windows(self):
        """
        [TEST: Output Fidelity]
        Scenario: Internal text is LF, but we are saving on Windows.
        Requirement: ensure_native must convert all to CRLF exactly.
        """
        internal_text = "L1\nL2\nL3"
        import platform
        if platform.system() == "Windows":
            native = line_endings.ensure_native(internal_text)
            # Encode to bytes to verify literal \r\n (0D 0A)
            native_bytes = native.encode('utf-8')
            # Expected: L1\r\nL2\r\nL3
            # Byte sequence: 4C 31 0D 0A 4C 32 0D 0A 4C 33
            self.assertEqual(native_bytes.count(b'\r\n'), 2)
            self.assertNotIn(b'\n', native_bytes.replace(b'\r\n', b''))

    def test_cross_platform_resource_integrity(self):
        """
        [TEST: Resource Deep Scan]
        Compare unix.txt and windows.txt resources byte-by-byte after internal normalization.
        """
        unix_path = self.resource_dir / "unix.txt"
        win_path = self.resource_dir / "windows.txt"
        
        # Read raw bytes
        unix_bytes = unix_path.read_bytes()
        win_bytes = win_path.read_bytes()
        
        # Verify they are physically different
        self.assertNotEqual(unix_bytes, win_bytes)
        
        # Normalize and verify they are logically identical
        u_norm = line_endings.ensure_lf(unix_bytes.decode('utf-8'))
        w_norm = line_endings.ensure_lf(win_bytes.decode('utf-8'))
        
        self.assertEqual(u_norm, w_norm)
        self.assertEqual(u_norm, "Line 1\nLine 2\nLine 3\n")

    def test_patch_with_crlf_input(self):
        """
        [TEST: Robust Input]
        Scenario: The user provides the V2 patch string itself with CRLF line endings.
        Requirement: Parser must normalize the INPUT itself before tokenizing.
        """
        raw_patch = b"@@@FILE_BEGIN {{Root}}/test.txt\r\nContent\r\n@@@FILE_END\r\n"
        input_text = raw_patch.decode('utf-8')
        
        plan = scaffold_core.generate_plan(self.test_dir, input_text, {})
        self.assertEqual(len(plan.errors), 0)
        self.assertEqual(plan.file_contents[self.test_dir / "test.txt"], "Content")

    def test_byte_fidelity_check_resource(self):
        """
        [TEST: Resource Fidelity]
        Verifies that our actual resource files are read correctly as LF internally.
        """
        unix_res = self.resource_dir / "unix.txt"
        win_res = self.resource_dir / "windows.txt"
        
        # Reading both and ensuring they are identical after LF normalization
        u_text = line_endings.ensure_lf(unix_res.read_text(encoding='utf-8'))
        w_text = line_endings.ensure_lf(win_res.read_text(encoding='utf-8'))
        
        self.assertEqual(u_text, w_text)
        self.assertEqual(u_text, "Line 1\nLine 2\nLine 3\n")

if __name__ == "__main__":
    unittest.main()
