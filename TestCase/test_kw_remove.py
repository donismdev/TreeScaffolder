# -*- coding: utf-8 -*-
"""
[KEYWORD TEST: REMOVE]
Focus: Selective deletion of content.

Why this test is effective:
1. Verifies that REMOVE only deletes the matched string and nothing else.
2. Ensures that no unintended whitespace/newlines are left behind or added.
"""
import unittest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core

class TestKeywordRemove(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_KW_REMOVE_"))
        self.base_file = self.test_dir / "remove.txt"
        self.base_file.write_text("AAA -REMOVE- BBB", encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_remove_literal(self):
        """REMOVE should delete exactly what was found."""
        # We want to remove " [DELETE] " (including spaces) from "AAA [DELETE] BBB"
        self.base_file.write_text("AAA [DELETE] BBB", encoding='utf-8')
        patch = (
            "@@@PATCH_BEGIN {{Root}}/remove.txt\n"
            "@@@FIND_BEGIN {{None}}\n"
            " [DELETE] \n"
            "@@@FIND_END\n"
            "@@@REMOVE_BEGIN {{None}}\n"
            "@@@REMOVE_END\n"
            "@@@PATCH_END"
        )
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        # AAA + BBB = AAABBB
        self.assertEqual(plan.file_contents[self.base_file], "AAABBB")

if __name__ == "__main__":
    unittest.main()
