# -*- coding: utf-8 -*-
import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from Scripts.Core import scaffold_core

class TestKeywordInsertBefore(unittest.TestCase):
    def test_insert_before_literal(self):
        """INSERT_BEFORE should insert text exactly before the found block."""
        content = "Line1\n[Target]\nLine3"
        instr = [
            {'keyword': 'FIND', 'content': '[Target]'},
            {'keyword': 'INSERT_BEFORE', 'content': 'New\n'}
        ]
        res, err = scaffold_core.apply_v2_patch(content, instr)
        self.assertIsNone(err)
        # Result should be "Line1\nNew\n[Target]\nLine3"
        self.assertEqual(res, "Line1\nNew\n[Target]\nLine3")

    def test_insert_before_multiline(self):
        """INSERT_BEFORE should handle multiline blocks."""
        content = "Start\nTargetA\nTargetB\nEnd"
        instr = [
            {'keyword': 'FIND', 'content': 'TargetA\nTargetB'},
            {'keyword': 'INSERT_BEFORE', 'content': 'Inserted\n'}
        ]
        res, err = scaffold_core.apply_v2_patch(content, instr)
        self.assertIsNone(err)
        self.assertEqual(res, "Start\nInserted\nTargetA\nTargetB\nEnd")

if __name__ == "__main__":
    unittest.main()
