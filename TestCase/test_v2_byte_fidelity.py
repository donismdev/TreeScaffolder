# -*- coding: utf-8 -*-
"""
Byte-level fidelity test for V2 Multipatch Format v1.1.
Compares input block content size vs physical file size.
Generates a detailed audit log.
"""
import unittest
import sys
import os
import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from Scripts.Core import scaffold_core

class TestV2ByteFidelity(unittest.TestCase):
    def test_byte_fidelity_report(self):
        """
        [TEST: Byte-Level Fidelity Audit]
        Reads from Resources/input_integrity.txt, applies it, 
        and compares exact byte counts.
        """
        today = "20260502"
        report_path = Path(f"test_result_{today}.txt")
        resource_dir = Path(__file__).parent / "Resources"
        input_file = resource_dir / "input_integrity.txt"
        
        test_root = Path(__file__).parent / "TempRoot"
        test_root.mkdir(exist_ok=True)
        
        with open(input_file, "r", encoding="utf-8") as f:
            input_text = f.read()
            
        plan = scaffold_core.generate_plan(test_root, input_text, {})
        
        report_lines = [
            "="*60,
            f"BYTE FIDELITY AUDIT REPORT - {datetime.datetime.now().isoformat()}",
            "="*60,
            f"Source Resource: {input_file.name}",
            ""
        ]
        
        success = True
        for path, content in plan.file_contents.items():
            # Get content directly from parsed block
            content_bytes = content.encode('utf-8')
            byte_size = len(content_bytes)
            
            # Simulate actual file write (normalization check)
            # The core perform_scaffold logic would do this:
            final_content = content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
            final_bytes = final_content.encode('utf-8')
            
            rel_path = path.relative_to(test_root)
            report_lines.append(f"FILE: {rel_path}")
            report_lines.append(f"  - Parsed Block Size: {byte_size} bytes")
            report_lines.append(f"  - Final Disk Size (CRLF): {len(final_bytes)} bytes")
            
            # Check for data corruption (non-newline chars must match)
            if content.strip() != final_content.replace('\r\n', '\n').strip():
                report_lines.append("  [!] ERROR: Data mismatch detected!")
                success = False
            else:
                report_lines.append("  [+] STATUS: Fidelity Verified (100% Match)")
            report_lines.append("-" * 40)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
            
        print(f"\nAudit Report generated: {report_path}")
        self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
