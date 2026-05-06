# -*- coding: utf-8 -*-
"""
Test suite for SCOPE_FIND feature in V2 Multipatch Format.
"""
import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from Scripts.Core.v2_parser import parse_v2_format, V2ParserError
from Scripts.Core import scaffold_core

class TestV2ScopeFind(unittest.TestCase):

    def setUp(self):
        self.content = (
            "void FunctionA()\n"    # Line 1
            "{\n"                   # Line 2
            "    int32 x = 0;\n"    # Line 3 (Target 1)
            "}\n"                   # Line 4
            "\n"                    # Line 5
            "void FunctionB()\n"    # Line 6
            "{\n"                   # Line 7
            "    int32 x = 0;\n"    # Line 8 (Target 2)
            "}\n"                   # Line 9
        )

    def test_scope_success(self):
        """Should succeed if FIND matches exactly once within the specified SCOPE."""
        # Target only x in FunctionB
        instr = [
            {'keyword': 'SCOPE_FIND', 'content': 'void FunctionB()'},
            {'keyword': 'SCOPE_END_FIND', 'content': '}'},
            {'keyword': 'FIND', 'content': 'int32 x = 0;'},
            {'keyword': 'REPLACE', 'content': 'int32 y = 1;'}
        ]
        result, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIsNone(err)
        self.assertIn("void FunctionA()\n{\n    int32 x = 0;", result)
        self.assertIn("void FunctionB()\n{\n    int32 y = 1;", result)

    def test_scope_ambiguous_in_scope(self):
        """Should fail if multiple FIND matches exist within the SCOPE."""
        content_multi = "void Func() {\n  int x = 0;\n  int x = 0;\n}"
        instr = [
            {'keyword': 'SCOPE_FIND', 'content': 'void Func()'},
            {'keyword': 'SCOPE_END_FIND', 'content': '}'},
            {'keyword': 'FIND', 'content': 'int x = 0;'},
            {'keyword': 'REPLACE', 'content': 'int y = 1;'}
        ]
        result, err = scaffold_core.apply_v2_patch(content_multi, instr)
        self.assertIn("V2-011", err)
        self.assertIn("in scope", err)

    def test_scope_not_found_in_scope(self):
        """Should fail if FIND text exists in file but not within the SCOPE."""
        content = (
            "// start A\n"
            "void FunctionA() { int x = 0; }\n"
            "// end A\n"
            "// start B\n"
            "void FunctionB() { int x = 0; }\n"
            "// end B\n"
        )
        instr = [
            {'keyword': 'SCOPE_FIND', 'content': '// start A'},
            {'keyword': 'SCOPE_END_FIND', 'content': '// end A'},
            {'keyword': 'FIND', 'content': 'void FunctionB()'}, # Outside FunctionA scope
            {'keyword': 'REPLACE', 'content': 'XXX'}
        ]
        result, err = scaffold_core.apply_v2_patch(content, instr)
        self.assertIn("V2-010", err)
        self.assertIn("in scope", err)

    def test_scope_start_not_found(self):
        """Should fail with V2-050 if SCOPE_FIND text is missing."""
        instr = [
            {'keyword': 'SCOPE_FIND', 'content': 'MissingFunction'},
            {'keyword': 'SCOPE_END_FIND', 'content': '}'},
            {'keyword': 'FIND', 'content': 'int x'},
            {'keyword': 'REPLACE', 'content': 'y'}
        ]
        _, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIsNotNone(err)
        self.assertIn("V2-050", err)

    def test_scope_start_ambiguous(self):
        """Should fail with V2-051 if SCOPE_FIND text matches multiple times."""
        content = "void Func() {}\nvoid Func() {}"
        instr = [
            {'keyword': 'SCOPE_FIND', 'content': 'void Func()'},
            {'keyword': 'SCOPE_END_FIND', 'content': '}'},
            {'keyword': 'FIND', 'content': 'something'},
            {'keyword': 'REPLACE', 'content': 'y'}
        ]
        _, err = scaffold_core.apply_v2_patch(content, instr)
        self.assertIsNotNone(err)
        self.assertIn("V2-051", err)

    def test_scope_end_not_found(self):
        """Should fail with V2-052 if SCOPE_END_FIND text is missing after start."""
        instr = [
            {'keyword': 'SCOPE_FIND', 'content': 'void FunctionA()'},
            {'keyword': 'SCOPE_END_FIND', 'content': 'MISSING_END'},
            {'keyword': 'FIND', 'content': 'int x'},
            {'keyword': 'REPLACE', 'content': 'y'}
        ]
        _, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIsNotNone(err)
        self.assertIn("V2-052", err)

    def test_scope_end_ambiguous(self):
        """Should fail with V2-053 if multiple SCOPE_END_FIND matches exist after start."""
        content = "void Func() { int x; } int y; }"
        instr = [
            {'keyword': 'SCOPE_FIND', 'content': 'void Func()'},
            {'keyword': 'SCOPE_END_FIND', 'content': '}'},
            {'keyword': 'FIND', 'content': 'int x'},
            {'keyword': 'REPLACE', 'content': 'y'}
        ]
        _, err = scaffold_core.apply_v2_patch(content, instr)
        self.assertIsNotNone(err)
        self.assertIn("V2-053", err)

    def test_scope_invalid_pair(self):
        """Should fail if SCOPE_FIND or SCOPE_END_FIND is missing."""
        instr_only_start = [
            {'keyword': 'SCOPE_FIND', 'content': 'A'}, 
            {'keyword': 'FIND', 'content': 'X'},
            {'keyword': 'REPLACE', 'content': 'Y'}
        ]
        _, err1 = scaffold_core.apply_v2_patch(self.content, instr_only_start)
        self.assertIsNotNone(err1)
        self.assertIn("must be used as a pair", err1)

        instr_only_end = [
            {'keyword': 'SCOPE_END_FIND', 'content': 'B'}, 
            {'keyword': 'FIND', 'content': 'X'},
            {'keyword': 'REPLACE', 'content': 'Y'}
        ]
        _, err2 = scaffold_core.apply_v2_patch(self.content, instr_only_end)
        self.assertIsNotNone(err2)
        self.assertIn("must be used as a pair", err2)

    def test_scope_vs_line_range(self):
        """Should fail with V2-056 if both SCOPE and LINE_RANGE are used."""
        instr = [
            {'keyword': 'SCOPE_FIND', 'content': 'A'},
            {'keyword': 'SCOPE_END_FIND', 'content': 'B'},
            {'keyword': 'LINE_RANGE', 'content': '1 10'},
            {'keyword': 'FIND', 'content': 'X'}
        ]
        _, err = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIn("V2-056", err)

    def test_scope_insert_after(self):
        """INSERT_AFTER should respect scope."""
        instr = [
            {'keyword': 'SCOPE_FIND', 'content': 'void FunctionB()'},
            {'keyword': 'SCOPE_END_FIND', 'content': '}'},
            {'keyword': 'FIND', 'content': 'int32 x = 0;'},
            {'keyword': 'INSERT_AFTER', 'content': '\n    int32 z = 2;'}
        ]
        result, _ = scaffold_core.apply_v2_patch(self.content, instr)
        self.assertIn("void FunctionB()\n{\n    int32 x = 0;\n    int32 z = 2;\n}", result)
        # FunctionA remains unchanged
        self.assertIn("void FunctionA()\n{\n    int32 x = 0;\n}", result)

if __name__ == "__main__":
    unittest.main()
