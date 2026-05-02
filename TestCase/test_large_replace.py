# -*- coding: utf-8 -*-
import unittest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core

class TestLargeReplace(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_LARGE_"))
        self.resource_dir = Path(__file__).parent / "Resources"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_reproduce_large_replace(self):
        """Reproduces the reported FIND failed error for large C++ blocks."""
        base_content = (Path(__file__).parent / "Resources/large_base.txt").read_text(encoding='utf-8')
        input_text = (Path(__file__).parent / "Resources/large_input.txt").read_text(encoding='utf-8')
        
        target_file = self.test_dir / "large.txt"
        target_file.write_text(base_content, encoding='utf-8')
        
        plan = scaffold_core.generate_plan(self.test_dir, input_text, {})
        
        # Check for error
        if plan.errors:
            print(f"\n[REPRODUCED] Error: {plan.errors[0]}")
        
        self.assertEqual(len(plan.errors), 0, f"Failure reproduced: {plan.errors}")
        self.assertEqual(plan.file_contents[target_file], "// REPLACED")

if __name__ == "__main__":
    unittest.main()
