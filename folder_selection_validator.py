# -*- coding: utf-8 -*-
"""
folder_selection_validator.py

Accepts a folder path, performs strict safety validation, and returns a
structured JSON result. This script is read-only and does not perform
any filesystem modifications.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Set

def get_forbidden_system_paths() -> Set[Path]:
    """
    Returns a set of resolved, absolute, case-normalized paths that should
    be blocked for safety.
    """
    forbidden: Set[Path] = set()
    env_vars = [
        "SystemRoot", "windir",
        "ProgramFiles", "ProgramFiles(x86)",
        "ProgramData",
        "Public",
        "APPDATA",
        "LOCALAPPDATA",
    ]

    for env_var in env_vars:
        path_str = os.environ.get(env_var)
        if path_str:
            try:
                # Resolve to a canonical path and normalize case for comparison
                forbidden.add(Path(path_str).resolve())
            except (OSError, FileNotFoundError):
                # Path might not exist or be accessible, which is fine
                continue
    
    # Add the "Default" user profile directory, which isn't in an env var
    system_drive = os.environ.get("SystemDrive", "C:")
    users_path = Path(system_drive) / "Users"
    if users_path.exists():
        forbidden.add((users_path / "Default").resolve())

    return forbidden

def validate_folder(path_to_check: str | Path) -> dict:
    """
    Performs strict validation on a folder path.

    Args:
        path_to_check: The folder path to validate.

    Returns:
        A dictionary with the structured validation result.
    """
    result = {
        "ok": False,
        "errors": [],
        "warnings": [],
        "resolved_path": None,
        "blocked_reason": None,
    }

    if not path_to_check:
        result["errors"].append("Input path is empty.")
        result["blocked_reason"] = "EMPTY_PATH"
        return result

    # --- 1. Initial Resolution ---
    try:
        # Use resolve() to handle symlinks and normalize the path (e.g., "..")
        resolved_path = Path(path_to_check).resolve()
        result["resolved_path"] = str(resolved_path)
    except (OSError, FileNotFoundError) as e:
        result["errors"].append(f"Path cannot be resolved or does not exist: {e}")
        result["blocked_reason"] = "UNRESOLVABLE_OR_MISSING"
        return result
    except Exception as e:
        result["errors"].append(f"An unexpected error occurred during path resolution: {e}")
        result["blocked_reason"] = "RESOLUTION_ERROR"
        return result
        
    # --- 2. Basic Checks ---
    if not resolved_path.exists():
        result["errors"].append("Path does not exist.")
        result["blocked_reason"] = "DOES_NOT_EXIST"
        return result

    if not resolved_path.is_dir():
        result["errors"].append("Path is not a directory.")
        result["blocked_reason"] = "NOT_A_DIRECTORY"
        return result

    # --- 3. Critical Safety Checks ---
    # Check if it's a drive root (e.g., C:\, D:\)
    if resolved_path.parent == resolved_path:
        result["errors"].append("Path is a drive root, which is not allowed.")
        result["blocked_reason"] = "IS_DRIVE_ROOT"
        return result

    # Check against forbidden system paths
    forbidden_paths = get_forbidden_system_paths()
    for forbidden in forbidden_paths:
        # Check if the path is exactly a forbidden path
        if resolved_path == forbidden:
            result["errors"].append(f"Path is a protected system directory: {forbidden}")
            result["blocked_reason"] = "IS_SYSTEM_DIR"
            return result
        # Check if the path is a subdirectory of a forbidden path
        try:
            if resolved_path.relative_to(forbidden):
                result["errors"].append(f"Path is inside a protected system directory: {forbidden}")
                result["blocked_reason"] = "INSIDE_SYSTEM_DIR"
                return result
        except ValueError:
            # This occurs if the path is not relative to the forbidden one (e.g., different drive), which is safe.
            continue
            
    # --- 4. If all checks pass ---
    result["ok"] = True
    return result

def main():
    """
    CLI entry point. Takes a path as an argument and prints validation
    result as a JSON string to stdout.
    """
    if len(sys.argv) < 2:
        result = {
            "ok": False,
            "errors": ["No path provided. Usage: python folder_selection_validator.py <path>"],
            "warnings": [],
            "resolved_path": None,
            "blocked_reason": "NO_PATH_PROVIDED",
        }
    else:
        input_path = sys.argv[1]
        result = validate_folder(input_path)

    try:
        # Use separators for compact JSON output
        json_output = json.dumps(result, separators=(',', ':'))
        print(json_output)
    except TypeError as e:
        # Failsafe in case of non-serializable data
        fallback_result = {
            "ok": False,
            "errors": [f"Failed to serialize result to JSON: {e}"],
            "warnings": [],
            "resolved_path": result.get("resolved_path"),
            "blocked_reason": "JSON_SERIALIZATION_ERROR",
        }
        print(json.dumps(fallback_result))

if __name__ == "__main__":
    main()