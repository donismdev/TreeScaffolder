# -*- coding: utf-8 -*-
"""
Exhaustive test suite for V2 Multipatch Format v1.1.
Verifies all keywords and data integrity mandates.
"""
import unittest
import sys
import os
from pathlib import Path

# Add project root to path so we can import Scripts
sys.path.append(str(Path(__file__).parent.parent))

from Scripts.Core.v2_parser import parse_v2_format, V2ParserError
from Scripts.Core import scaffold_core

class TestV2V11(unittest.TestCase):

    # --- 1. Parser Tests (Literal extraction) ---

    def test_parser_literal_content(self):
        """Test that parser preserves exact characters including leading/trailing newlines."""
        text = "@@@FILE_BEGIN {{Root}}/test.txt\n\n  Indented text  \n\n\n@@@FILE_END\n"
        blocks = parse_v2_format(text)
        self.assertEqual(len(blocks), 1)
        # The marker pattern consumes the \n after BEGIN, 
        # but EVERYTHING after that until the final \n@@@FILE_END must be kept.
        # My current parser consumes \n after BEGIN.
        self.assertEqual(blocks[0]['content'], "\n  Indented text  \n\n")

    def test_parser_nested_patch(self):
        """Test that PATCH can contain child blocks correctly."""
        text = (
            "@@@PATCH_BEGIN {{Root}}/file.txt\n"
            "@@@FIND_BEGIN {{None}}\ntarget\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\nnew\n@@@REPLACE_END\n"
            "@@@PATCH_END\n"
        )
        blocks = parse_v2_format(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['keyword'], "PATCH")
        self.assertEqual(len(blocks[0]['children']), 2)
        self.assertEqual(blocks[0]['children'][0]['keyword'], "FIND")
        self.assertEqual(blocks[0]['children'][0]['content'], "target")

    # --- 2. Patching Logic Tests (Execution) ---

    def test_op_replace_exact_one(self):
        """REPLACE must fail if not exactly one match is found."""
        # 1 match: Success
        content = "aaa\nbbb\nccc"
        instr = [
            {'keyword': 'FIND', 'content': 'bbb'},
            {'keyword': 'REPLACE', 'content': 'XXX'}
        ]
        result, err = scaffold_core.apply_v2_patch(content, instr)
        self.assertIsNone(err)
        self.assertEqual(result, "aaa\nXXX\nccc")

        # 0 matches: Fail
        instr_zero = [{'keyword': 'FIND', 'content': 'ddd'}, {'keyword': 'REPLACE', 'content': 'X'}]
        _, err = scaffold_core.apply_v2_patch(content, instr_zero)
        self.assertIn("V2-010", err)

        # 2 matches: Fail
        content_multi = "aaa\nbbb\nbbb\nccc"
        instr_multi = [{'keyword': 'FIND', 'content': 'bbb'}, {'keyword': 'REPLACE', 'content': 'X'}]
        _, err = scaffold_core.apply_v2_patch(content_multi, instr_multi)
        self.assertIn("V2-011", err)

    def test_op_insert_top_bottom(self):
        """Test TOP/BOTTOM insertions with literal integrity."""
        content = "Middle"
        
        # TOP
        instr_top = [{'keyword': 'INSERT_TOP', 'content': "Header\n"}]
        res, _ = scaffold_core.apply_v2_patch(content, instr_top)
        self.assertEqual(res, "Header\nMiddle")

        # BOTTOM (Spec: ensure file ends with newline)
        instr_bot = [{'keyword': 'INSERT_BOTTOM', 'content': "Footer"}]
        res, _ = scaffold_core.apply_v2_patch(content, instr_bot)
        # "Middle" -> "Middle\nFooter\n" (normalized)
        self.assertEqual(res, "Middle\nFooter\n")

    def test_op_clear_after(self):
        """CLEAR_AFTER keeps the line containing FIND text and deletes everything below."""
        content = "Keep1\nTargetLine\nDelete1\nDelete2"
        instr = [
            {'keyword': 'FIND', 'content': 'TargetLine'},
            {'keyword': 'CLEAR_AFTER', 'content': ''}
        ]
        res, _ = scaffold_core.apply_v2_patch(content, instr)
        # Line containing TargetLine + its newline remains.
        self.assertEqual(res, "Keep1\nTargetLine\n")

    def test_op_remove(self):
        """REMOVE deletes the exact matched text."""
        content = "Part1 Target Part2"
        instr = [{'keyword': 'FIND', 'content': ' Target '}, {'keyword': 'REMOVE', 'content': ''}]
        res, _ = scaffold_core.apply_v2_patch(content, instr)
        self.assertEqual(res, "Part1Part2")

    # --- 3. Planning & Security Tests ---

    def test_security_traversal(self):
        """Verify that '..' in paths is rejected."""
        plan = scaffold_core.generate_plan(Path("C:/Dummy"), "@@@FILE_BEGIN {{Root}}/../outside.txt\ncontent\n@@@FILE_END", {})
        has_security_error = any("Security Violation" in e or "outside of target root" in e for e in plan.errors)
        self.assertTrue(has_security_error, f"Expected security error but got: {plan.errors}")

    def test_clear_file(self):
        """CLEAR_FILE keyword should result in empty content but planned file."""
        root = Path("C:/Dummy")
        plan = scaffold_core.generate_plan(root, "@@@CLEAR_FILE_BEGIN {{Root}}/empty.txt\n@@@CLEAR_FILE_END", {})
        
        # Robust comparison: Compare lower-case posix strings
        planned_str_set = {p.as_posix().lower() for p in plan.planned_files}
        target_str = root.joinpath("empty.txt").as_posix().lower()
        
        self.assertIn(target_str, planned_str_set, f"Target {target_str} not in {planned_str_set}")
        
        # Check content
        content_map = {p.as_posix().lower(): c for p, c in plan.file_contents.items()}
        self.assertEqual(content_map[target_str], "")

if __name__ == "__main__":
    unittest.main()
