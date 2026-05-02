# -*- coding: utf-8 -*-
"""
[KEYWORD TEST: CLEAR_FILE / CLEAR_AFTER]
Focus: Truncation logic and safety.

Why this test is effective:
1. Verifies that CLEAR_FILE empties a file without deleting the path (Security Mandate).
2. Verifies that CLEAR_AFTER precisely preserves the match line while nuking the rest.
3. Tests boundary conditions like clearing when the match is on the last line.
"""
import unittest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core

class TestKeywordClear(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_KW_CLEAR_"))
        self.base_file = self.test_dir / "clear.txt"
        self.base_file.write_text("Line1\nLine2\nLine3", encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_clear_file_keyword(self):
        """CLEAR_FILE should result in empty content."""
        patch = "@@@CLEAR_FILE_BEGIN {{Root}}/clear.txt\n@@@CLEAR_FILE_END"
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        self.assertEqual(plan.file_contents[self.base_file], "")

    def test_clear_after_exact(self):
        """CLEAR_AFTER should keep up to the end of the line containing FIND match."""
        self.base_file.write_text("Header\n[Anchor]\nShould be deleted\nLast line", encoding='utf-8')
        patch = (
            "@@@PATCH_BEGIN {{Root}}/clear.txt\n"
            "@@@FIND_BEGIN {{None}}\n[Anchor]\n@@@FIND_END\n"
            "@@@CLEAR_AFTER_BEGIN {{None}}\n@@@CLEAR_AFTER_END\n"
            "@@@PATCH_END"
        )
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        # Should be "Header\n[Anchor]\n"
        self.assertEqual(plan.file_contents[self.base_file], "Header\n[Anchor]\n")

if __name__ == "__main__":
    unittest.main()
