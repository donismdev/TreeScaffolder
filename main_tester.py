# -*- coding: utf-8 -*-
"""
Main Test Runner for TreeScaffolder.
Executes all test suites in the TestCase folder.
"""
import unittest
import sys
from pathlib import Path

def run_all_tests():
    # Set the start directory for test discovery
    start_dir = str(Path(__file__).parent / "TestCase")
    
    print("=" * 60)
    print("TreeScaffolder Multi-Suite Test Runner")
    print(f"Discovering tests in: {start_dir}")
    print("=" * 60)
    
    # Discover and run all tests starting with 'test_*.py'
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("ALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print(f"TESTS FAILED! (Failures: {len(result.failures)}, Errors: {len(result.errors)})")
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
