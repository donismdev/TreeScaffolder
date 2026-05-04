# -*- coding: utf-8 -*-
import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from Scripts.Core.v2_parser import parse_v2_format, V2ParserError

class TestV2ParserStrict(unittest.TestCase):
    def test_unrecognized_keyword(self):
        """Parser should raise V2-040 for unrecognized @@@ keywords."""
        bad_text = "@@@UNKNOWN_BEGIN {{None}}\ncontent\n@@@UNKNOWN_END"
        with self.assertRaises(V2ParserError) as cm:
            parse_v2_format(bad_text)
        self.assertIn("V2-040", str(cm.exception))
        self.assertIn("UNKNOWN", str(cm.exception))

    def test_typo_keyword(self):
        """Parser should catch typos in keywords."""
        typo_text = "@@@PATH_BEGIN {{Root}}/file.txt\n@@@PATCH_END" # PATCH -> PATH typo
        with self.assertRaises(V2ParserError) as cm:
            parse_v2_format(typo_text)
        self.assertIn("V2-040", str(cm.exception))
        self.assertIn("PATH", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
