# -*- coding: utf-8 -*-
"""
[KEYWORD TEST: FILE]
Focus: Byte-perfect file creation and literal content preservation.

Why this test is effective:
1. Validates that leading/trailing spaces and tabs are preserved.
2. Specifically checks if the final line without a newline is kept as-is (Literal Mandate).
3. Uses external resource to ensure no Python-level string escaping interferes.
"""
import unittest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core

class TestKeywordFile(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_KW_FILE_"))
        self.resource_dir = Path(__file__).parent / "Resources"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_file_literal_integrity(self):
        input_path = self.resource_dir / "kw_file_input.txt"
        with open(input_path, "r", encoding="utf-8") as f:
            input_text = f.read()

        plan = scaffold_core.generate_plan(self.test_dir, input_text, {})
        target_path = self.test_dir / "raw_binary_sim.txt"
        
        # Expected content (extracted from kw_file_input.txt manually to compare)
        # Note: The newline after BEGIN is framing, the rest is data.
        expected_content = (
            "  Line with leading spaces\n"
            "\t\tLine with tabs\n"
            "Multiple empty lines follow:\n"
            "\n"
            "\n"
            "Final line without newline"
        )
        
        self.assertIn(target_path, plan.file_contents)
        self.assertEqual(plan.file_contents[target_path], expected_content)

if __name__ == "__main__":
    unittest.main()
