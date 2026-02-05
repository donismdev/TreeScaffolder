# -*- coding: utf-8 -*-
"""
scaffold_from_tree.py v1.6 (standalone)

This script scaffolds a directory structure from a tree-like text description.
It is designed to be run directly and has no external dependencies.

- IT WILL NOT OVERWRITE existing files or directories. It skips them.
- It only reports an error if a path conflict occurs (e.g., trying to
  create a directory where a file of the same name already exists).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import the shared logic
import scaffold_core

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# --- Main Tree Text ---
# Paste your desired folder/file structure here.
# - Use @ROOT to define your logical root marker.
# - The first node must be that marker, ending with a forward slash (/).
# - Indent with TABS or 4-SPACES.
TREE_TEXT = r"""
# =========================================================
# Scaffold Tree
# - '@ROOT {{Root}}' marks the logical root of this tree
# - '{{Root}}' is NOT a real folder name. It's a marker.
# - The actual filesystem root is ROOT_DIR (config below).
# =========================================================

@ROOT {{Root}}

{{Root}}/
	NewModule/
		NewModule.Build.cs
		Public/
			NewModule.h
		Private/
			NewModule.cpp
""".strip()

# --- Script Settings ---

# The directory where the scaffold will be created.
# Leave as "" to use the current working directory where the script is run.
ROOT_DIR = ""  # e.g., r"C:\projects\my_game\Source"

# If True, the script will only print what it would do, without creating anything.
DRY_RUN = False

# This marker must match the @ROOT marker used in TREE_TEXT.
# For simplicity, this is not currently used as core logic autodetects it,
# but it's kept for conceptual clarity.
ROOT_DIR_MARKER = "{{Root}}"

# --- Scanning and Analysis ---

# Toggle similarity analysis for generated file names.
ENABLE_SIMILARITY_SCAN = True
SIMILARITY_RATIO_THRESHOLD = 0.86  # Recommended: 0.80 - 0.92

# Filename normalization rules for similarity checking.
NORMALIZE_LOWER = True
NORMALIZE_REMOVE_NONALNUM = True  # e.g., "My-File_1.txt" -> "myfile1txt"

# When scanning for existing files, only consider these extensions.
SCAN_INCLUDE_EXTENSIONS = {
	".h", ".hpp", ".cpp", ".c", ".cs",
	".Build.cs", ".Target.cs", ".uproject", ".uplugin"
}

# --- Output verbosity ---
MAX_LIST_ITEMS = 100

# ==============================================================================
# EXECUTION LOGIC
# ==============================================================================

# --- ANSI Colors for Terminal Output ---
def _supports_ansi() -> bool:
	try:
		return sys.stdout.isatty()
	except Exception:
		return False

ANSI_OK = _supports_ansi()

def _c(text: str, code: str) -> str:
	return f"\x1b[{code}m{text}\x1b[0m" if ANSI_OK else text

def _green(text: str) -> str: return _c(text, "32")
def _yellow(text: str) -> str: return _c(text, "33")
def _red(text: str) -> str: return _c(text, "31")
def _dim(text: str) -> str: return _c(text, "90")
def _status_light(ok: bool) -> str: return _green("[GREEN]") if ok else _red("[RED]")

# --- Filesystem Operations (with safety checks) ---

def _ensure_dir(path: Path) -> Tuple[bool, bool, bool]:
	"""Returns: (ok, created, skipped)"""
	if path.exists():
		if path.is_dir():
			print(_dim(f"[SKIP DIR]  {path}"))
			return True, False, True
		print(_red(f"[ERROR] Path exists but is a file: {path}"))
		return False, False, False

	print(f"[MKDIR]     {path}")
	if not DRY_RUN:
		try:
			path.mkdir(parents=True, exist_ok=True)
		except Exception as e:
			print(_red(f"[ERROR] mkdir failed: {path} | {e}"))
			return False, False, False
	return True, True, False

def _ensure_file(path: Path, content: str = "") -> Tuple[bool, bool, bool]:
	"""Returns: (ok, created, skipped)"""
	if path.exists():
		if path.is_file():
			print(f"[OVERWRITE] {path}") # Changed from SKIP FILE
			if not DRY_RUN:
				try:
					path.unlink() # Delete existing file
				except Exception as e:
					print(_red(f"[ERROR] delete file failed: {path} | {e}"))
					return False, False, False
		else: # Path exists but is a directory
			print(_red(f"[ERROR] Path exists but is a directory: {path}"))
			return False, False, False

	print(f"[CREATE]    {path}")
	if not DRY_RUN:
		try:
			# Ensure parent directory exists
			path.parent.mkdir(parents=True, exist_ok=True)
			with path.open("w", encoding="utf-8") as f: # Changed to "w" for writing content
				f.write(content)
		except Exception as e:
			print(_red(f"[ERROR] create file failed: {path} | {e}"))
			return False, False, False
	return True, True, False

# --- Main Application Flow ---

def main():
	"""Main execution function."""
	print("--- Scaffold from Tree v1.6 (Standalone) ---")
	print(f"- DRY_RUN: {DRY_RUN}")

	root = Path(ROOT_DIR) if ROOT_DIR else Path.cwd()
	print(f"- Root Dir: '{root.resolve()}'")
	
	if not root.exists() or not root.is_dir():
		print(_red(f"\n[FATAL] Root directory does not exist: {root}"))
		sys.exit(1)

	config = {
		"ENABLE_SIMILARITY_SCAN": ENABLE_SIMILARITY_SCAN,
		"SIMILARITY_RATIO_THRESHOLD": SIMILARITY_RATIO_THRESHOLD,
		"NORMALIZE_LOWER": NORMALIZE_LOWER,
		"NORMALIZE_REMOVE_NONALNUM": NORMALIZE_REMOVE_NONALNUM,
		"SCAN_INCLUDE_EXTENSIONS": SCAN_INCLUDE_EXTENSIONS,
	}

	# 1. Generate a plan (read-only)
	print("\n[1/3] Parsing tree and analyzing structure...")
	plan = scaffold_core.generate_plan(root, TREE_TEXT, config)

	if plan.errors or plan.has_conflicts:
		print(_red("\n[FATAL] Errors found in plan. Cannot proceed."))
		for error in plan.errors:
			print(_red(f"- {error}"))
		sys.exit(1)

	print(f"Plan: {len(plan.planned_dirs)} directories, {len(plan.planned_files)} files to create.")
	
	# 2. Execute the plan (write to filesystem)
	print("\n[2/3] Executing scaffold operation...")
	
	created_files, skipped_files, error_files = 0, 0, 0
	created_dirs, skipped_dirs, error_dirs = 0, 0, 0
	final_ok = True
	
	# Create directories first
	for path in plan.planned_dirs:
		if plan.path_states.get(path) == "new":
			ok, created, skipped = _ensure_dir(path)
			if ok:
				if created: created_dirs += 1
				if skipped: skipped_dirs += 1
			else:
				error_dirs += 1
				final_ok = False
		elif plan.path_states.get(path) == "exists":
			skipped_dirs += 1

	# Create files
	for path in plan.planned_files:
		file_content = plan.file_contents.get(path.resolve(), "") # Get content, default to empty string
		# If the file exists and is in file_contents, we're overwriting (or creating if deleted)
		if plan.path_states.get(path) == "new" or plan.path_states.get(path) == "overwrite":
			ok, created, skipped = _ensure_file(path, file_content)
			if ok:
				if created: created_files += 1
				if skipped: skipped_files += 1
			else:
				error_files += 1
				final_ok = False
		elif plan.path_states.get(path) == "exists":
			# This case means the file existed but was NOT part of V2 content, so we skip it.
			skipped_files += 1

	# 3. Print final summary and warnings
	print("\n[3/3] Reporting results...")
	print("\n" + "="*20 + " SUMMARY " + "="*20)
	print(f"Directories : {created_dirs} created, {skipped_dirs} skipped, {error_dirs} errors")
	print(f"Files       : {created_files} created, {skipped_files} skipped, {error_files} errors")

	# Print warnings if any were found during planning
	if plan.duplicate_warnings or plan.similarity_warnings:
		print("\n" + "="*18 + " WARNINGS " + "="*19)
		if plan.duplicate_warnings:
			print(_yellow(f"\n--- Found {len(plan.duplicate_warnings)} file(s) with duplicate names ---"))
			for i, (target, others) in enumerate(plan.duplicate_warnings.items()):
				if i >= MAX_LIST_ITEMS:
					print(_dim(f"...and {len(plan.duplicate_warnings) - MAX_LIST_ITEMS} more."))
					break
				print(_yellow(f"Target: '{target.name}'"))
				print(_dim(f"  - Planned at: {target}"))
				for other_path in others:
					print(_dim(f"  - Exists at:  {other_path}"))
		
		if plan.similarity_warnings:
			print(_yellow(f"\n--- Found {len(plan.similarity_warnings)} file(s) with similar names ---"))
			for i, (target, cands) in enumerate(plan.similarity_warnings.items()):
				if i >= MAX_LIST_ITEMS:
					print(_dim(f"...and {len(plan.similarity_warnings) - MAX_LIST_ITEMS} more."))
					break
				print(_yellow(f"Target: '{target.name}'"))
				for name, ratio, paths in cands:
					print(_dim(f"  - Similar to '{name}' (ratio: {ratio:.2f}) at: {paths[0]}"))

	print("\n" + "="*50)

	print(f"\nFinal Status: {_status_light(final_ok)}")
	if not final_ok:
		print(_red("Errors occurred during the operation."))
	else:
		print(_green("Operation completed successfully."))

if __name__ == "__main__":
	try:
		main()
	except Exception as e:
		print(_red(f"\n[UNHANDLED EXCEPTION] {e}"))
		sys.exit(1)
	finally:
		if sys.stdout.isatty(): # Pause only if in interactive terminal
			input("\nPress Enter to exit.")

