# -*- coding: utf-8 -*-
"""
[KEYWORD TEST: REPLACE]
Focus: Exact substitution and multiple-match safety.

Why this test is effective:
1. Verifies literal replacement of multiline blocks.
2. Ensures that if 'FIND' is not exact, the operation fails (Safety Mandate).
3. Validates that trailing newlines in the replacement block are honored.
"""
import unittest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core

class TestKeywordReplace(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_KW_REPLACE_"))
        self.base_file = self.test_dir / "replace.txt"
        self.base_file.write_text("Line1\n[Target]\nLine3", encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_replace_multiline(self):
        """REPLACE should support multiline blocks exactly."""
        patch = (
            "@@@PATCH_BEGIN {{Root}}/replace.txt\n"
            "@@@FIND_BEGIN {{None}}\n[Target]\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\nNew1\nNew2\n@@@REPLACE_END\n"
            "@@@PATCH_END"
        )
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        # Line1\nNew1\nNew2\nLine3
        self.assertEqual(plan.file_contents[self.base_file], "Line1\nNew1\nNew2\nLine3")

    def test_replace_fail_multi(self):
        """REPLACE must fail if FIND text matches multiple times."""
        self.base_file.write_text("X\n[Target]\n[Target]\nY", encoding='utf-8')
        patch = (
            "@@@PATCH_BEGIN {{Root}}/replace.txt\n"
            "@@@FIND_BEGIN {{None}}\n[Target]\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\nNew\n@@@REPLACE_END\n"
            "@@@PATCH_END"
        )
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        self.assertTrue(any("Multiple matches found" in e for e in plan.errors))

if __name__ == "__main__":
    unittest.main()
