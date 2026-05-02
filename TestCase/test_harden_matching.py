# -*- coding: utf-8 -*-
"""
[HARDEN TEST: MATCHING ENGINE]
Focus: Regex escape side-effects, large block fidelity, and BOM.

Why this test is effective:
1. It uses a mock large C++ function that contains multiline brackets and parenthesis.
2. It tests if the matching engine can find content that starts with a UTF-8 BOM.
3. It validates that pure string matching is used, not regex, by testing symbols like .* which regex would interpret.
"""
import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core

class TestHardenMatching(unittest.TestCase):
    def test_regex_symbol_matching(self):
        """Ensures that symbols like .* are treated LITERALLY, not as regex patterns."""
        content = "Match this literal .* string"
        instr = [
            {'keyword': 'FIND', 'content': '.*'},
            {'keyword': 'REPLACE', 'content': 'SUCCESS'}
        ]
        res, err = scaffold_core.apply_v2_patch(content, instr)
        self.assertEqual(res, "Match this literal SUCCESS string")

    def test_multiline_symbol_hell(self):
        """Tests a complex multiline block with brackets, newlines and tabs."""
        content = (
            "void Function()\n"
            "{\n"
            "\t// [Bracket Test]\n"
            "\tif (Value > 0.0f)\n"
            "\t{\n"
            "\t\tReturn();\n"
            "\t}\n"
            "}\n"
        )
        # We want to replace the WHOLE thing
        instr = [
            {'keyword': 'FIND', 'content': content.strip('\n')},
            {'keyword': 'REPLACE', 'content': 'REPLACED'}
        ]
        res, err = scaffold_core.apply_v2_patch(content, instr)
        self.assertIsNone(err)
        # Note: since we found everything except maybe the final newline of the file
        self.assertIn("REPLACED", res)

    def test_utf8_bom_matching(self):
        """Tests if content starting with a BOM is correctly matched."""
        # \ufeff is the UTF-8 BOM representation in Python strings
        content = "\ufeffLine 1\nLine 2"
        instr = [
            {'keyword': 'FIND', 'content': 'Line 1'},
            {'keyword': 'REPLACE', 'content': 'BOM_STILL_HERE'}
        ]
        # Matching should succeed because we use string search
        res, _ = scaffold_core.apply_v2_patch(content, instr)
        self.assertIn("BOM_STILL_HERE", res)
        self.assertTrue(res.startswith("\ufeff"))

if __name__ == "__main__":
    unittest.main()
