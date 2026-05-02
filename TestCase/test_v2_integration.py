# -*- coding: utf-8 -*-
"""
Integration test for V2 Multipatch Format v1.1.
This test performs ACTUAL file operations in a temporary directory
to verify 100% literal data integrity (no unwanted newlines or modifications).
"""
import unittest
import sys
import os
import shutil
import tempfile
from pathlib import Path

# Add project root to path so we can import Scripts
sys.path.append(str(Path(__file__).parent.parent))

from Scripts.Core import scaffold_core

class TestV2Integration(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for file operations
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_Test_"))
        self.config = {"ENABLE_SIMILARITY_SCAN": False}

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_literal_file_creation(self):
        """
        [TEST: FILE_BEGIN/END Literal Integrity]
        Verifies that content with specific trailing newlines is written exactly as provided.
        We test three cases: no trailing newline, exactly one, and multiple.
        """
        content_no_nl = "Line 1\nLine 2"
        content_one_nl = "Line 1\nLine 2\n"
        content_multi_nl = "Line 1\nLine 2\n\n\n"

        input_text = (
            f"@@@FILE_BEGIN {{{{Root}}}}/no_nl.txt\n{content_no_nl}\n@@@FILE_END\n"
            f"@@@FILE_BEGIN {{{{Root}}}}/one_nl.txt\n{content_one_nl}\n@@@FILE_END\n"
            f"@@@FILE_BEGIN {{{{Root}}}}/multi_nl.txt\n{content_multi_nl}\n@@@FILE_END\n"
        )

        plan = scaffold_core.generate_plan(self.test_dir, input_text, self.config)
        
        # Verify in memory first
        self.assertEqual(plan.file_contents[self.test_dir / "no_nl.txt"], content_no_nl)
        self.assertEqual(plan.file_contents[self.test_dir / "one_nl.txt"], content_one_nl)
        self.assertEqual(plan.file_contents[self.test_dir / "multi_nl.txt"], content_multi_nl)

    def test_patch_literal_integrity(self):
        """
        [TEST: PATCH/REPLACE Literal Integrity]
        Verifies that REPLACE does not inject any extra newlines around the replaced text.
        """
        initial_content = "Prefix[Target]Suffix"
        # We want to replace '[Target]' with something that has NO newlines.
        replace_text = "SUCCESS"
        
        input_text = (
            "@@@PATCH_BEGIN {{Root}}/patch_test.txt\n"
            "@@@FIND_BEGIN {{None}}\n[Target]\n@@@FIND_END\n"
            f"@@@REPLACE_BEGIN {{None}}\n{replace_text}\n@@@REPLACE_END\n"
            "@@@PATCH_END\n"
        )

        # Mock initial file on disk
        target_file = self.test_dir / "patch_test.txt"
        target_file.write_text(initial_content, encoding='utf-8')

        plan = scaffold_core.generate_plan(self.test_dir, input_text, self.config)
        
        # Result should be exactly "PrefixSUCCESSSuffix" with NO newlines added
        expected = "PrefixSUCCESSSuffix"
        self.assertEqual(plan.file_contents[target_file], expected)

    def test_insert_after_literal(self):
        """
        [TEST: INSERT_AFTER Framing]
        Verifies that INSERT_AFTER places text exactly after the match without forcing a newline
        unless the user provided one in the block.
        """
        initial = "Part1MatchPart2"
        # Insert "INS" right after "Match"
        input_text = (
            "@@@PATCH_BEGIN {{Root}}/insert.txt\n"
            "@@@FIND_BEGIN {{None}}\nMatch\n@@@FIND_END\n"
            "@@@INSERT_AFTER_BEGIN {{None}}\nINS\n@@@INSERT_AFTER_END\n"
            "@@@PATCH_END\n"
        )
        
        target_file = self.test_dir / "insert.txt"
        target_file.write_text(initial, encoding='utf-8')
        
        plan = scaffold_core.generate_plan(self.test_dir, input_text, self.config)
        self.assertEqual(plan.file_contents[target_file], "Part1MatchINSPart2")

    def test_clear_after_logic(self):
        """
        [TEST: CLEAR_AFTER Boundary]
        Verifies that CLEAR_AFTER keeps the line of the match and removes everything else.
        """
        initial = "Line1\nMatchLine\nLine3\nLine4"
        input_text = (
            "@@@PATCH_BEGIN {{Root}}/clear.txt\n"
            "@@@FIND_BEGIN {{None}}\nMatchLine\n@@@FIND_END\n"
            "@@@CLEAR_AFTER_BEGIN {{None}}\n\n@@@CLEAR_AFTER_END\n"
            "@@@PATCH_END\n"
        )
        
        target_file = self.test_dir / "clear.txt"
        target_file.write_text(initial, encoding='utf-8')
        
        plan = scaffold_core.generate_plan(self.test_dir, input_text, self.config)
        # Should keep "Line1\nMatchLine\n"
        self.assertEqual(plan.file_contents[target_file], "Line1\nMatchLine\n")

if __name__ == "__main__":
    unittest.main()
