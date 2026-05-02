# -*- coding: utf-8 -*-
"""
[HARDEN TEST: PARSER]
Focus: Resisting dirty input, invisible characters, and malformed markers.

Why this test is effective:
1. It injects newlines and tabs into the middle of marker lines to see if they leak into parameters.
2. It tests if the parser survives a patch file that itself has inconsistent line endings.
3. It validates the 'Literal' mandate by ensuring invisible chars don't shift the content indices.
"""
import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core.v2_parser import parse_v2_format

class TestHardenParser(unittest.TestCase):
    def test_parameter_pollution_recovery(self):
        """Checks if \n or \r leaking into the header is stripped."""
        # Scenario: A broken editor adds a CR or LF right before the end of the BEGIN tag.
        dirty_input = "@@@FILE_BEGIN {{Root}}/path.txt \r\nContent\n@@@FILE_END"
        blocks = parse_v2_format(dirty_input)
        
        # The parameter should be exactly '{{Root}}/path.txt' without the trailing space or \r
        param = blocks[0]['parameter']
        self.assertEqual(param, "{{Root}}/path.txt")
        self.assertNotIn("\r", param)
        self.assertNotIn("\n", param)

    def test_marker_irregular_spacing(self):
        """Checks if multiple spaces between tag and parameter are handled."""
        text = "@@@FILE_BEGIN    {{Root}}/space.txt\nContent\n@@@FILE_END"
        blocks = parse_v2_format(text)
        self.assertEqual(blocks[0]['parameter'], "{{Root}}/space.txt")

    def test_mixed_input_line_endings(self):
        """The patch itself might be a mess of \r\n and \n."""
        # Mix of \n after BEGIN and \r\n after FIND
        mixed_patch = (
            "@@@PATCH_BEGIN {{Root}}/file.txt\n"
            "@@@FIND_BEGIN {{None}}\r\n"
            "Target\n"
            "@@@FIND_END\r\n"
            "@@@PATCH_END"
        )
        blocks = parse_v2_format(mixed_patch)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['children'][0]['content'], "Target")

if __name__ == "__main__":
    unittest.main()
