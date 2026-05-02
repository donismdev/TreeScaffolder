# -*- coding: utf-8 -*-
"""
[KEYWORD TEST: INSERT_TOP / INSERT_BOTTOM / INSERT_AFTER]
Focus: Positional accuracy and newline preservation.

Why this test is effective:
1. Verifies that INSERT_TOP does not force a newline if not provided.
2. Verifies that INSERT_BOTTOM adheres to the "End with Newline" normalization rule (Section 11).
3. Verifies that INSERT_AFTER works mid-string without corrupting surrounding bytes.
"""
import unittest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core

class TestKeywordInsert(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_KW_INSERT_"))
        self.base_file = self.test_dir / "base.txt"
        self.base_file.write_text("Middle", encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_insert_top_literal(self):
        """INSERT_TOP should prepended text exactly."""
        patch = "@@@PATCH_BEGIN {{Root}}/base.txt\n@@@INSERT_TOP_BEGIN {{None}}\nTOP\n@@@INSERT_TOP_END\n@@@PATCH_END"
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        self.assertEqual(plan.file_contents[self.base_file], "TOPMiddle")

    def test_insert_bottom_normalization(self):
        """INSERT_BOTTOM must ensure the file ends with exactly one newline if specified in logic."""
        patch = "@@@PATCH_BEGIN {{Root}}/base.txt\n@@@INSERT_BOTTOM_BEGIN {{None}}\nBOT\n@@@INSERT_BOTTOM_END\n@@@PATCH_END"
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        # Middle -> Middle\nBOT\n (normalized)
        self.assertEqual(plan.file_contents[self.base_file], "Middle\nBOT\n")

    def test_insert_after_no_newline(self):
        """INSERT_AFTER should not inject newlines unless explicitly provided."""
        self.base_file.write_text("AAA[Match]BBB", encoding='utf-8')
        patch = (
            "@@@PATCH_BEGIN {{Root}}/base.txt\n"
            "@@@FIND_BEGIN {{None}}\n[Match]\n@@@FIND_END\n"
            "@@@INSERT_AFTER_BEGIN {{None}}\n-INSERTED-\n@@@INSERT_AFTER_END\n"
            "@@@PATCH_END"
        )
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        self.assertEqual(plan.file_contents[self.base_file], "AAA[Match]-INSERTED-BBB")

if __name__ == "__main__":
    unittest.main()
