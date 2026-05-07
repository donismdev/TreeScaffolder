# -*- coding: utf-8 -*-
"""
Test suite for grep_engine.py logic.
Verifies keyword parsing, file discovery, text searching, and V2 merging.
"""
import unittest
import sys
import os
import shutil
import tempfile
from pathlib import Path

# Add project root to path so we can import Scripts
sys.path.append(str(Path(__file__).parent.parent))

from Scripts.Core import grep_engine

class TestGrepEngine(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for file operations
        self.test_dir = Path(tempfile.mkdtemp(prefix="TS_GrepTest_"))
        
        # Create some sample files for testing
        (self.test_dir / "src").mkdir()
        (self.test_dir / "src" / "main.py").write_text("print('hello world')\n# TODO: fix this", encoding='utf-8')
        (self.test_dir / "src" / "utils.py").write_text("def helper():\n    return True", encoding='utf-8')
        (self.test_dir / "README.md").write_text("# Project README\nContains documentation.", encoding='utf-8')

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_parse_keywords(self):
        """Tests the keyword parsing logic with various input formats."""
        raw_text = """
        main.py
        'utils.py'
        "README.md"
        검색어: helper
        // This is a comment
        [
            "special_file.txt",
        ]
        """
        keywords = grep_engine.parse_keywords(raw_text)
        self.assertIn("main.py", keywords)
        self.assertIn("utils.py", keywords)
        self.assertIn("README.md", keywords)
        self.assertIn("helper", keywords)
        self.assertIn("special_file.txt", keywords)
        self.assertNotIn("// This is a comment", keywords)

    def test_find_files(self):
        """Tests searching for files by keyword in name or path."""
        # Search for 'main'
        result = grep_engine.find_files(self.test_dir, "main")
        self.assertIn("{{Root}}/src/main.py", result)
        
        # Search for 'src'
        result = grep_engine.find_files(self.test_dir, "src")
        self.assertIn("{{Root}}/src/main.py", result)
        self.assertIn("{{Root}}/src/utils.py", result)

    def test_grep_text(self):
        """Tests searching for text content within files."""
        # Search for 'hello'
        result = grep_engine.grep_text(self.test_dir, "hello")
        self.assertIn("{{Root}}/src/main.py:1: print('hello world')", result)
        
        # Search for 'helper'
        result = grep_engine.grep_text(self.test_dir, "helper")
        self.assertIn("{{Root}}/src/utils.py:1: def helper():", result)

    def test_merge_files_success(self):
        """Tests merging multiple files into a V2 block."""
        raw_input = "main.py\nutils.py"
        tree_input = "" # Not using tree input for this test
        
        success, result = grep_engine.merge_files(self.test_dir, raw_input, tree_input)
        
        self.assertTrue(success)
        self.assertIn("@@@FILE_BEGIN {{Root}}/src/main.py", result)
        self.assertIn("print('hello world')", result)
        self.assertIn("@@@FILE_BEGIN {{Root}}/src/utils.py", result)
        self.assertIn("def helper():", result)
        self.assertIn("@@@FILE_END", result)

    def test_merge_files_from_tree(self):
        """Tests identifying files to merge from a tree-style input."""
        raw_input = ""
        tree_input = """
        C:/Project/
        ├── README.md
        └── src/
            └── main.py
        """
        
        success, result = grep_engine.merge_files(self.test_dir, raw_input, tree_input)
        
        self.assertTrue(success)
        self.assertIn("@@@FILE_BEGIN {{Root}}/README.md", result)
        self.assertIn("@@@FILE_BEGIN {{Root}}/src/main.py", result)

    def test_merge_files_ambiguous(self):
        """Tests handling of ambiguous file matches."""
        # Create another main.py in a different folder
        (self.test_dir / "backup").mkdir()
        (self.test_dir / "backup" / "main.py").write_text("print('backup')", encoding='utf-8')
        
        raw_input = "main.py"
        success, result = grep_engine.merge_files(self.test_dir, raw_input, "")
        
        # Should be ambiguous because there are two main.py files
        self.assertFalse(success)
        self.assertIn("Ambiguous: main.py", result)

    def test_merge_files_not_found(self):
        """Tests handling of files that don't exist."""
        raw_input = "non_existent.py"
        success, result = grep_engine.merge_files(self.test_dir, raw_input, "")
        
        self.assertFalse(success)
        self.assertIn("Not Found: non_existent.py", result)

if __name__ == "__main__":
    unittest.main()
