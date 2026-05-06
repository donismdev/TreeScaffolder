# -*- coding: utf-8 -*-
"""
Test suite for LINE_RANGE feature in V2 Multipatch Format.
"""
import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from Scripts.Core.v2_parser import parse_v2_format, V2ParserError
from Scripts.Core import scaffold_core

class TestV2LineRange(unittest.TestCase):

    def setUp(self):
        self.content = (
            "Line 1: Target\n"  # 1
            "Line 2: Other\n"   # 2
            "Line 3: Target\n"  # 3
            "Line 4: Other\n"   # 4
            "Line 5: Target\n"  # 5
            "Line 6: EOF"       # 6
        )

    def test_line_range_success(self):
        """Should succeed if FIND matches exactly once within the specified LINE_RANGE."""
        # Search for "Target" between lines 2 and 4 (should only find Line 3)
        instr = [
            {'keyword': 'LINE_RANGE', 'content': '2 4'},
            {'keyword': 'FIND', 'content': 'Target'},
            {'keyword': 'REPLACE', 'content': 'Matched'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIsNone(err)
        self.assertIn("Line 3: Matched", result)
        self.assertIn("Line 1: Target", result)
        self.assertIn("Line 5: Target", result)

    def test_line_range_ambiguous(self):
        """Should fail with V2-011 if multiple matches are found within the range."""
        # Search for "Target" between lines 1 and 5 (should find 3 matches)
        instr = [
            {'keyword': 'LINE_RANGE', 'content': '1 5'},
            {'keyword': 'FIND', 'content': 'Target'},
            {'keyword': 'REPLACE', 'content': 'Matched'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIn("V2-011", err)
        self.assertIn("line range 1-5", err)

    def test_line_range_not_found(self):
        """Should fail with V2-010 if FIND exists in file but not within the range."""
        # Search for "Line 1" between lines 2 and 6
        instr = [
            {'keyword': 'LINE_RANGE', 'content': '2 6'},
            {'keyword': 'FIND', 'content': 'Line 1'},
            {'keyword': 'REPLACE', 'content': 'Matched'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIn("V2-010", err)
        self.assertIn("line range 2-6", err)

    def test_no_line_range_ambiguous(self):
        """Standard behavior (without LINE_RANGE) should fail if multiple matches exist in whole file."""
        instr = [
            {'keyword': 'FIND', 'content': 'Target'},
            {'keyword': 'REPLACE', 'content': 'Matched'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIn("V2-011", err)

    def test_line_range_clamping(self):
        """Should clamp StartLine and EndLine to valid file boundaries."""
        # StartLine 0 -> 1, EndLine 99 -> 6
        instr = [
            {'keyword': 'LINE_RANGE', 'content': '0 99'},
            {'keyword': 'FIND', 'content': 'Line 1: Target'},
            {'keyword': 'REPLACE', 'content': 'Line 1: Matched'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIsNone(err)
        self.assertIn("Line 1: Matched", result)

    def test_line_range_invalid_range(self):
        """Should fail with V2-041 if StartLine > EndLine."""
        instr = [
            {'keyword': 'LINE_RANGE', 'content': '5 2'},
            {'keyword': 'FIND', 'content': 'Target'},
            {'keyword': 'REPLACE', 'content': 'Matched'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIn("V2-041", err)

    def test_line_range_duplicate(self):
        """Should fail with V2-042 if multiple LINE_RANGE blocks are provided in one PATCH."""
        instr = [
            {'keyword': 'LINE_RANGE', 'content': '1 2'},
            {'keyword': 'LINE_RANGE', 'content': '3 4'},
            {'keyword': 'FIND', 'content': 'Target'},
            {'keyword': 'REPLACE', 'content': 'Matched'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIn("V2-042", err)

    def test_line_range_invalid_value(self):
        """Should fail with V2-044 if values are not integers."""
        instr = [
            {'keyword': 'LINE_RANGE', 'content': 'abc 200'},
            {'keyword': 'FIND', 'content': 'Target'},
            {'keyword': 'REPLACE', 'content': 'Matched'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIn("V2-044", err)
        
        instr2 = [
            {'keyword': 'LINE_RANGE', 'content': '100'}, # Only one value
            {'keyword': 'FIND', 'content': 'Target'},
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr2)
        self.assertIn("V2-044", err)

    def test_parser_recognizes_line_range(self):
        """The parser should correctly identify LINE_RANGE as a block."""
        text = (
            "@@@PATCH_BEGIN {{Root}}/file.txt\n"
            "@@@LINE_RANGE_BEGIN {{None}}\n10 20\n@@@LINE_RANGE_END\n"
            "@@@FIND_BEGIN {{None}}\ntarget\n@@@FIND_END\n"
            "@@@PATCH_END\n"
        )
        blocks = parse_v2_format(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['children'][0]['keyword'], "LINE_RANGE")
        self.assertEqual(blocks[0]['children'][0]['content'], "10 20")

    def test_line_range_exact_match_rule(self):
        """Even within the range, if 2 matches exist, it must fail with V2-011."""
        # Line 1 and 3 both have "Target". Range 1-4 covers both.
        instr = [
            {'keyword': 'LINE_RANGE', 'content': '1 4'},
            {'keyword': 'FIND', 'content': 'Target'},
            {'keyword': 'REPLACE', 'content': 'Matched'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIn("V2-011", err)
        self.assertIn("Found 2 occurrences", err)

if __name__ == "__main__":
    unittest.main()
