# -*- coding: utf-8 -*-
"""
grep_engine.py

Core logic for file searching, text grepping, and file merging.
Adapted from GrepFiles for integration with TreeScaffolder.
"""
import os
import re
import datetime
from pathlib import Path
from Scripts.Utils import logger

def parse_keywords(raw_text):
    """Parses raw text into a list of clean keywords or paths."""
    result = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line in ("[", "]", "],", ");") or line.startswith("//"):
            continue
        
        if line.startswith("검색어:"):
            line = line.replace("검색어:", "", 1).strip()
            
        # Extract quoted items
        quoted_items = re.findall(r'["\'](.*?)["\']', line)
        if quoted_items:
            for item in quoted_items:
                cleaned = item.strip().strip("[]").strip().strip('"').strip("'").rstrip(",").strip()
                if cleaned: result.append(cleaned)
        else:
            cleaned = line.strip().strip("[]").strip().strip('"').strip("'").rstrip(",").strip()
            if cleaned: result.append(cleaned)
    return result

def iter_project_files(root_path: Path, extensions=None):
    """Iterates through files in the project root with optional extension filter."""
    if not root_path or not root_path.exists():
        return
    
    for root, _, files in os.walk(root_path):
        for filename in files:
            if extensions and not filename.lower().endswith(extensions):
                continue
            yield Path(os.path.join(root, filename))

def find_files(root_path: Path, raw_text):
    """Searches for files matching keywords in names or paths."""
    keywords = parse_keywords(raw_text)
    if not keywords: return "No keywords found."
    
    results = []
    for kw in keywords:
        results.append(f"Search: {kw}")
        match_count = 0
        kw_lower = kw.lower()
        
        for file_path in iter_project_files(root_path):
            try:
                rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")
                display_path = f"{{{{Root}}}}/{rel_path}"
            except:
                display_path = str(file_path)
                
            if kw_lower in display_path.lower():
                results.append(display_path)
                match_count += 1
        
        if match_count == 0:
            results.append("  (No results)")
        results.append("-" * 40)
    return "\n".join(results)

def grep_text(root_path: Path, raw_text):
    """Searches for text keywords within project files."""
    keywords = parse_keywords(raw_text)
    if not keywords: return "No keywords found."
    
    results = []
    for kw in keywords:
        results.append(f"Grep: {kw}")
        match_count = 0
        
        for file_path in iter_project_files(root_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, content in enumerate(f, 1):
                        if kw in content:
                            try:
                                rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")
                                display_path = f"{{{{Root}}}}/{rel_path}"
                            except:
                                display_path = str(file_path)
                            results.append(f"{display_path}:{line_num}: {content.rstrip()}")
                            match_count += 1
            except Exception:
                continue
        
        if match_count == 0:
            results.append("  (No results)")
        results.append("-" * 40)
    return "\n".join(results)

def merge_files(root_path: Path, raw_text, tree_text):
    """Merges files into a single V2-formatted block."""
    seen = set()
    targets = []
    
    def add_target(t):
        t = t.split("#")[0].split("//")[0].strip()
        if t and t not in seen:
            seen.add(t)
            targets.append(t)

    # 1. Keywords
    for kw in parse_keywords(raw_text):
        add_target(kw)
    
    # 2. Tree structures (common pattern [├└]── Path)
    for tree_match in re.findall(r"[├└]──\s+([\w\.\-/]+)", tree_text):
        if "." in tree_match:
            add_target(tree_match)

    # Pre-index files by name for faster lookup
    file_map = {}
    for file_path in iter_project_files(root_path):
        name = file_path.name
        if name not in file_map: file_map[name] = []
        file_map[name].append(file_path)

    failed = []
    contents = []
    
    for target in targets:
        name = os.path.basename(target)
        matches = file_map.get(name, [])
        final_path = None
        
        if len(matches) == 1:
            final_path = matches[0]
        elif len(matches) > 1:
            # Try to match sub-path
            sub_target = target.replace("{{Root}}/", "").lstrip("/")
            filtered = [m for m in matches if sub_target in str(m).replace("\\", "/")]
            if len(filtered) == 1:
                final_path = filtered[0]
            else:
                failed.append(f"Ambiguous: {target}")
        else:
            failed.append(f"Not Found: {target}")
            
        if final_path:
            try:
                try:
                    rel_path = str(final_path.relative_to(root_path)).replace("\\", "/")
                    display_path = f"{{{{Root}}}}/{rel_path}"
                except:
                    display_path = str(final_path)
                
                with open(final_path, "r", encoding="utf-8", errors="ignore") as f:
                    contents.append((display_path, f.read()))
            except Exception as e:
                failed.append(f"Read Error: {display_path} | {e}")

    if failed:
        return False, "\n".join([f"✖ {f}" for f in failed])
    
    if not contents:
        return False, "No files identified for merging."

    # Generate V2 format
    output = ["@@@COMMENT_BEGIN {{None}}", "Merged Files:"]
    for path, _ in contents:
        output.append(f"- {path}")
    output.append("@@@COMMENT_END\n")
    
    for path, content in contents:
        output.append(f"@@@FILE_BEGIN {path}")
        output.append(content)
        if not content.endswith("\n"):
            output.append("")
        output.append("@@@FILE_END\n")
        
    return True, "\n".join(output)
