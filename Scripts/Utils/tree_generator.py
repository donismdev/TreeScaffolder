# -*- coding: utf-8 -*-
"""
tree_generator.py

Provides functionality to generate a scaffold tree text structure from a list of file paths.
"""
from pathlib import PurePath
from collections.abc import Iterable

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
        
        p = PurePath(path_str)
        parts = p.parts
        
        current_level = tree
        for part in parts[:-1]: # Iterate through directories
            current_level = current_level.setdefault(part, {})
        
        # Handle the last part (file or directory)
        last_part = parts[-1]
        # Treat paths ending in a separator as directories
        is_dir = path_str.endswith(('/', '\\')) or (not last_part and path_str)

        if is_dir:
            if last_part: # Avoid adding an empty key if path ends with /
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
