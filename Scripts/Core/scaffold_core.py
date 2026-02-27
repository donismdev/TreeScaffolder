# -*- coding: utf-8 -*-
"""
scaffold_core.py

Core logic for parsing tree text and planning the scaffold.
This module is shared between the standalone script and the GUI app,
and it performs NO filesystem writes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set, Optional

from .v2_parser import parse_v2_format, V2ParserError
from Scripts.Utils.i18n import t
from Scripts.Utils.similarity_checker import find_similar_candidates

# ---------- Data Structures ----------

@dataclass
class NodeItem:
	"""Represents a single node in the parsed tree text."""
	indent: int
	name: str
	is_dir: bool
	line_number: int

@dataclass
class Plan:
	"""Holds the entire plan for a scaffolding operation."""
	root_path: Path
	tree_text: str
	
	# Configuration used for this plan
	config: dict = field(default_factory=dict)

	# Raw parsed nodes from tree text
	nodes: List[NodeItem] = field(default_factory=list)

	# Planned creations
	planned_dirs: Set[Path] = field(default_factory=set)
	planned_files: Set[Path] = field(default_factory=set)

	# For V2 patch format, stores the content for each file.
	file_contents: Dict[Path, str] = field(default_factory=dict)

	# Analysis results
	existing_files: Dict[str, List[Path]] = field(default_factory=dict)
	
	# Status of each planned path: "new", "exists", "conflict_file", "conflict_dir", "overwrite"
	path_states: Dict[Path, str] = field(default_factory=dict)
	
	# Warnings
	duplicate_warnings: Dict[Path, List[Path]] = field(default_factory=dict)
	similarity_warnings: Dict[Path, List[tuple[str, float, List[Path]]]] = field(default_factory=dict)
	migration_warnings: List[str] = field(default_factory=list) # New field for migration messages
	
	# Errors
	errors: List[str] = field(default_factory=list)
	
	@property
	def has_conflicts(self) -> bool:
		return any(v.startswith("conflict") for v in self.path_states.values())

# ---------- Parsing Logic ----------

def _count_raw_indent(line: str) -> int:
    """Counts raw indentation level from a line, handling tabs and spaces more flexibly."""
    leading_match = re.match(r"^[	 ]*", line)
    prefix = leading_match.group(0) if leading_match else ""
    
    # Each TAB is one level. 
    # For spaces, we look for the most common indentation (2, 4, or 8)
    # but as a fallback, we use 4.
    tab_count = prefix.count("	")
    space_count = prefix.count(" ")
    
    # If there are only spaces and no tabs, we try to be smart, 
    # but stick to 4 for consistency unless it's clearly 2.
    if space_count > 0 and tab_count == 0:
        if space_count % 4 == 0:
            return space_count // 4
        if space_count % 2 == 0:
            return space_count // 2
        return space_count // 4
    
    return tab_count + (space_count // 4)

def parse_tree_text(text: str) -> tuple[List[NodeItem], Optional[str], Optional[str]]:
    """
    Parses the multiline tree text with strict Python-style indentation validation.
    Forbids mixing tabs and spaces and enforces a consistent indentation unit.
    """
    items: List[NodeItem] = []
    root_marker_name: Optional[str] = None
    tree_lines_info: List[tuple[int, str]] = []

    lines = text.splitlines()

    # --- First pass: Identify tree lines and the root marker ---
    for i, line in enumerate(lines):
        raw = line.rstrip("\n")
        trimmed = line.strip()

        if not trimmed or trimmed.startswith("#"):
            continue

        if trimmed.startswith("@ROOT"):
            match = re.search(r'@ROOT\s+([^{\s}]+|{{[\w-]+}})', trimmed)
            if match:
                root_marker_name = match.group(1)
            continue

        tree_lines_info.append((i, raw))

    # --- Strict Indentation Validation ---
    indent_unit_type = None  # 'tab' or 'space'
    indent_unit_size = None  # Number of spaces if type is 'space'
    
    for line_index, raw_line in tree_lines_info:
        leading_match = re.match(r"^[ \t]*", raw_line)
        whitespace = leading_match.group(0) if leading_match else ""
        
        if not whitespace:
            continue
            
        # 1. Check for mixed tabs and spaces
        has_tabs = "\t" in whitespace
        has_spaces = " " in whitespace
        
        if has_tabs and has_spaces:
            return [], None, t("message.err_tab_mix", line=line_index + 1)
            
        current_type = 'tab' if has_tabs else 'space'
        current_size = len(whitespace) if current_type == 'space' else whitespace.count("\t")
        
        # 2. Establish the indentation unit from the very first indented line
        if indent_unit_type is None:
            indent_unit_type = current_type
            indent_unit_size = current_size
        
        # 3. Validate against established unit
        if current_type != indent_unit_type:
            return [], None, t("message.err_indent_type", line=line_index + 1)
            
        if indent_unit_type == 'space':
            if current_size % indent_unit_size != 0:
                return [], None, t("message.err_indent_unit", line=line_index + 1, unit=indent_unit_size)
            effective_indent = current_size // indent_unit_size
        else:
            effective_indent = current_size # Tab count is the level

    # --- Second pass: Build NodeItems with calculated effective_indent ---
    # To handle global offsets (if the whole tree is indented), we find the min level
    temp_info = []
    for line_index, raw_line in tree_lines_info:
        leading_match = re.match(r"^[ \t]*", raw_line)
        whitespace = leading_match.group(0) if leading_match else ""
        
        if not whitespace:
            level = 0
        elif indent_unit_type == 'space':
            level = len(whitespace) // indent_unit_size
        else:
            level = whitespace.count("\t")
        temp_info.append((line_index, raw_line, level))
        
    min_level = temp_info[0][2] if temp_info else 0

    for line_index, raw_line, level in temp_info:
        content = raw_line.strip()
        effective_indent = level - min_level
        if effective_indent < 0:
            effective_indent = 0

        is_dir = content.endswith("/") or content.endswith("\\")
        name = content[:-1] if is_dir else content
        name = name.replace("\\", "/")

        if name.startswith('/') or '..' in name or ':' in name:
            return [], None, t("message.err_invalid_char", line=line_index + 1, name=name)

        items.append(NodeItem(indent=effective_indent, name=name, is_dir=is_dir, line_number=line_index + 1))

    if not root_marker_name and items:
        return [], None, t("message.err_no_root")

    if root_marker_name and items and (items[0].name != root_marker_name or not items[0].is_dir):
        return [], root_marker_name, t("message.err_root_first", name=root_marker_name)

    return items, root_marker_name, None

# ---------- Planning and Analysis Logic (unchanged) ----------
def _is_interesting_file(path: Path, config: dict) -> bool:
    extensions = config.get("SCAN_INCLUDE_EXTENSIONS", {".h", ".cpp", ".cs"})
    name = path.name
    return any(name.endswith(ext) for ext in extensions if ext.startswith(".")) or path.suffix in extensions

def scan_existing_files(root: Path, config: dict) -> Dict[str, List[Path]]:
    result: Dict[str, List[Path]] = {}
    try:
        for p in root.rglob("*"):
            if p.is_file() and _is_interesting_file(p, config):
                result.setdefault(p.name, []).append(p)
    except OSError as e:
        print(f"Warning: Could not scan directory fully: {e}")
    return result

def is_content_identical(actual: str, planned: str) -> bool:
    """Compares actual and planned content with normalization."""
    def normalize(text):
        if text is None: return ""
        # Normalize line endings
        text = text.replace('\r\n', '\n')
        # Strip trailing whitespace from each line
        lines = [line.rstrip() for line in text.splitlines()]
        # Remove trailing empty lines from the end of the file
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)
    
    return normalize(actual) == normalize(planned)

def generate_plan(root_path: Path, text_input: str, config: dict) -> Plan:
	"""
	Generates a unified plan from a text input that may contain both a
	scaffold tree and V2 patch blocks.
	"""
	# 1. Pre-process the input to remove any text between an END and a BEGIN marker for any keyword.
	end_begin_junk_pattern = re.compile(r"(@@@[A-Z_]+_END)[\s\S]*?(@@@[A-Z_]+_BEGIN)")
	text_input = end_begin_junk_pattern.sub(r"\1\n\2", text_input)

	plan = Plan(root_path=root_path, tree_text=text_input, config=config)

	# 2. High-Priority: Validate and parse V2 blocks from the pre-processed text.
	# This ensures block integrity before we try to separate tree vs. V2 content.
	try:
		# Determine a best-guess root marker for the V2 parser.
		root_match_in_full_text = re.search(r'@ROOT\s+([^{\s}]+|{{[\w-]+}})', text_input)
		effective_root_marker = None
		if root_match_in_full_text:
			effective_root_marker = root_match_in_full_text.group(1)
		elif "{{Root}}" in text_input:
			effective_root_marker = "{{Root}}"
		
		patch_data = parse_v2_format(text_input, root_marker=effective_root_marker)
	except V2ParserError as e:
		plan.errors.append(f"{e}") # Removed "V2 Patch Error: " prefix to show user the direct error
		return plan

	# 3. Isolate Tree Text: If V2 parsing was successful, remove all blocks to get clean tree text.
	all_blocks_pattern = re.compile(r"@@@[A-Z_]+_BEGIN[\s\S]*?@@@[A-Z_]+_END\n?")
	tree_text_only = all_blocks_pattern.sub("", text_input)

	# 4. Parse the isolated scaffold tree structure.
	tree_nodes, initial_root_marker, tree_error = parse_tree_text(tree_text_only)
	if tree_error:
		plan.errors.append(tree_error)

	# 5. Process the parsed tree nodes to build the directory/file plan.
	if tree_nodes:
		plan.nodes = tree_nodes[1:] # Remove {{Root}} node
		stack: List[Tuple[int, Path]] = [(0, root_path)]
		for item in plan.nodes:
			while stack and stack[-1][0] >= item.indent:
				stack.pop()
			if not stack or item.indent > stack[-1][0] + 1:
				plan.errors.append(t("message.err_deep_indent", line=item.line_number, name=item.name))
				continue
			base_path = stack[-1][1]
			current_path = base_path / item.name
			if item.is_dir:
				plan.planned_dirs.add(current_path)
				stack.append((item.indent, current_path))
			else:
				plan.planned_files.add(current_path)
	
	# 6. Process the already-parsed V2 patch data to populate file contents.
	seen_paths_in_v2: Dict[Path, str] = {}
	for item in patch_data:
		path_str = item['path']
		content = item['content']
		if '..' in path_str or Path(path_str).is_absolute():
			plan.errors.append(f"Invalid path in patch: '{path_str}'.")
			continue
		target_path = (root_path / path_str).resolve()

		# Check for duplicates within the source code itself
		if target_path in seen_paths_in_v2:
			prev_path_str = seen_paths_in_v2[target_path]
			plan.errors.append(t("message.err_duplicate_v2", path=path_str))
		
		seen_paths_in_v2[target_path] = path_str
		plan.planned_files.add(target_path)
		plan.file_contents[target_path] = content
		for parent in target_path.parents:
			if parent != root_path and parent.is_relative_to(root_path):
				plan.planned_dirs.add(parent)

	if not plan.planned_dirs and not plan.planned_files:
		if not plan.errors:
			plan.errors.append("No valid scaffold tree or V2 patch blocks found in the input.")
		return plan

	# --- Final Analysis ---
	all_planned_paths = plan.planned_dirs.union(plan.planned_files)
	for path in sorted(list(all_planned_paths), key=lambda p: len(p.parts)):
		state = ""
		if path.exists():
			is_planned_dir = path in plan.planned_dirs
			is_planned_file = path in plan.planned_files
			is_fs_dir = path.is_dir()
			if is_planned_dir and not is_fs_dir: state = "conflict_file"
			elif is_planned_file and is_fs_dir: state = "conflict_dir"
			elif is_planned_file and path.resolve() in plan.file_contents:
				# Compare content if it's a file and we have planned content
				try:
					existing_content = path.read_text(encoding='utf-8', errors='replace')
					planned_content = plan.file_contents[path.resolve()]
					if is_content_identical(existing_content, planned_content):
						state = "identical"
					else:
						state = "overwrite"
				except Exception:
					state = "overwrite" # Fallback to overwrite if we can't read it
			else:
				state = "exists"
		else:
			state = "new"
		if state: plan.path_states[path] = state
		if state.startswith("conflict"):
			plan.errors.append(f"Conflict at '{path}': trying to create { 'dir' if is_planned_dir else 'file' } but a { 'file' if not is_fs_dir else 'dir' } exists.")

	plan.existing_files = scan_existing_files(root_path, config)

	# --- Similarity Scan ---
	if config.get("ENABLE_SIMILARITY_SCAN", True):
		for planned_file in plan.planned_files:
			target_name = planned_file.name
			similar = find_similar_candidates(plan.existing_files, target_name, config)
			# Filter out exact matches (those are handled by overwrite/identical logic)
			similar = [s for s in similar if s[0] != target_name]
			if similar:
				plan.similarity_warnings[planned_file] = similar

	return plan