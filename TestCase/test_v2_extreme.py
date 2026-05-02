# -*- coding: utf-8 -*-
"""
[EXTREME TEST: FINAL STRESS TEST]
Focus: Empty blocks, boundary conditions, symbol collisions, and multi-op chains.

Why this test is effective:
1. It tests matching strings at index 0 and at the very last byte of a file.
2. It uses content that LITERALLY contains "@@@" and "{{}}" to ensure no tag collisions.
3. It validates that multiple FIND/REPLACE pairs in one block maintain state correctly.
"""
import unittest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core

class TestV2Extreme(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_EXTREME_"))
        self.base_file = self.test_dir / "extreme.txt"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_boundary_matching(self):
        """Matches at the absolute START and END of the file."""
        self.base_file.write_text("START_DATA\nMiddle\nEND_DATA", encoding='utf-8')
        patch = (
            "@@@PATCH_BEGIN {{Root}}/extreme.txt\n"
            "@@@FIND_BEGIN {{None}}\nSTART_DATA\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\nTOP\n@@@REPLACE_END\n"
            "@@@FIND_BEGIN {{None}}\nEND_DATA\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\nBOTTOM\n@@@REPLACE_END\n"
            "@@@PATCH_END"
        )
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        # Should be TOP\nMiddle\nBOTTOM
        self.assertEqual(plan.file_contents[self.base_file], "TOP\nMiddle\nBOTTOM")

    def test_symbol_collision(self):
        """Content contains actual markers like @@@ and {{Parameter}}."""
        collision_text = "Literal @@@ and {{Tag}} here."
        self.base_file.write_text(collision_text, encoding='utf-8')
        patch = (
            "@@@PATCH_BEGIN {{Root}}/extreme.txt\n"
            "@@@FIND_BEGIN {{None}}\n@@@ and {{Tag}}\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\nSUCCESS\n@@@REPLACE_END\n"
            "@@@PATCH_END"
        )
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        self.assertEqual(plan.file_contents[self.base_file], "Literal SUCCESS here.")

    def test_empty_blocks(self):
        """Tests how the engine handles empty FIND or REPLACE contents."""
        self.base_file.write_text("Line1\n[DeleteMe]\nLine3", encoding='utf-8')
        # REPLACE with empty is valid (acts like REMOVE)
        patch = (
            "@@@PATCH_BEGIN {{Root}}/extreme.txt\n"
            "@@@FIND_BEGIN {{None}}\n[DeleteMe]\n\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\n@@@REPLACE_END\n"
            "@@@PATCH_END"
        )
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        # Note: [DeleteMe]\n (with its newline) is replaced by ""
        self.assertEqual(plan.file_contents[self.base_file], "Line1\nLine3")

    def test_multi_step_patch_state(self):
        """Verifies that multiple FINDs in one PATCH work sequentially on the MOVING result."""
        self.base_file.write_text("A B C", encoding='utf-8')
        patch = (
            "@@@PATCH_BEGIN {{Root}}/extreme.txt\n"
            "@@@FIND_BEGIN {{None}}\nA\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\n1\n@@@REPLACE_END\n"
            "@@@FIND_BEGIN {{None}}\nB\n@@@FIND_END\n"
            "@@@REPLACE_BEGIN {{None}}\n2\n@@@REPLACE_END\n"
            "@@@PATCH_END"
        )
        plan = scaffold_core.generate_plan(self.test_dir, patch, {})
        # A B C -> 1 B C -> 1 2 C
        self.assertEqual(plan.file_contents[self.base_file], "1 2 C")

if __name__ == "__main__":
    unittest.main()
