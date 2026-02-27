# -*- coding: utf-8 -*-
"""
tree_generator.py

Provides functionality to generate a scaffold tree text structure from a list of file paths.
"""
from pathlib import PurePath
from collections.abc import Iterable
from Scripts.Core.v2_parser import parse_v2_format

def generate_tree_from_v2(v2_text: str) -> str:
    """
    Parses V2 format text and generates a scaffold tree structure.
    
    Args:
        v2_text: The source code text in V2 multipatch format.
        
    Returns:
        A string representing the scaffold tree.
    """
    try:
        patch_data = parse_v2_format(v2_text)
        paths = [item['path'] for item in patch_data]
        return generate_tree_from_paths(paths)
    except Exception:
        return ""

def generate_tree_from_paths(paths: Iterable[str], root_marker_name: str = "{{Root}}") -> str:
    """
    Generates an indented tree structure string from a list of file paths.

    Args:
        paths: A list of string paths (e.g., ['path/to/file.txt', 'path/dir/']).
        root_marker_name: The name of the root marker to use in the tree.

    Returns:
        A string representing the scaffold tree.
    """
    if not isinstance(paths, Iterable):
        return ""

    tree = {}
    for path_str in paths:
        if not path_str:
            continue
        
        # Standardize separators and trim
        norm_path = path_str.replace('\\', '/').strip().lstrip('/')
        
        # Strip root marker if present at start
        if norm_path.startswith(root_marker_name):
            norm_path = norm_path[len(root_marker_name):].lstrip('/')
        elif norm_path.lower().startswith("{{root}}"): # Case-insensitive check for default
            norm_path = norm_path[len("{{root}}"):].lstrip('/')

        p = PurePath(norm_path)
        parts = p.parts
        
        current_level = tree
        for part in parts[:-1]: # Iterate through directories
            current_level = current_level.setdefault(part, {})
        
        # Handle the last part (file or directory)
        if parts:
            last_part = parts[-1]
            is_dir = path_str.endswith(('/', '\\'))
            if is_dir:
                current_level.setdefault(last_part, {})
            else:
                current_level.setdefault(last_part, None) # Use None to signify a file

    def build_string_recursive(subtree: dict, indent_level: int) -> str:
        """Recursively builds the string representation of the tree."""
        tree_str = ""
        indent = "    " * indent_level

        sorted_keys = sorted(subtree.keys())
        dirs = [k for k in sorted_keys if isinstance(subtree[k], dict)]
        files = [k for k in sorted_keys if subtree[k] is None]

        for key in dirs:
            tree_str += f"{indent}{key}/\n"
            tree_str += build_string_recursive(subtree[key], indent_level + 1)
        
        for key in files:
            tree_str += f"{indent}{key}\n"
            
        return tree_str

    header = f"@ROOT {root_marker_name}\n\n{root_marker_name}/\n"
    tree_body = build_string_recursive(tree, 1)

    return header + tree_body.rstrip()
