# -*- coding: utf-8 -*-
"""
scaffold_core.py

Core logic for parsing tree text and planning the scaffold.
This module is shared between the standalone script and the GUI app,
and it performs NO filesystem writes.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional

from v2_parser import parse_v2_format, V2ParserError

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
	similarity_warnings: Dict[Path, List[Tuple[str, float, List[Path]]]] = field(default_factory=dict)
	
	# Errors
	errors: List[str] = field(default_factory=list)
	
	@property
	def has_conflicts(self) -> bool:
		return any(v.startswith("conflict") for v in self.path_states.values())

# ---------- Parsing Logic ----------

def _count_raw_indent(line: str) -> int:
    """Counts raw indentation level from a line."""
    leading_match = re.match(r"^[	 ]*", line)
    prefix = leading_match.group(0) if leading_match else ""
    tab_count = prefix.count("	")
    space_count = prefix.count(" ")
    space_level = space_count // 4
    return tab_count + space_level

def _get_content(line: str) -> str:
    """Gets the stripped content of a line."""
    return line.strip()

def parse_tree_text(text: str) -> Tuple[List[NodeItem], Optional[str], Optional[str]]:
    """
    Parses the multiline tree text into a list of NodeItems,
    skipping content within V2 patch blocks and normalizing indentation.
    """
    items: List[NodeItem] = []
    root_marker_name: Optional[str] = None
    parsing_v2_content: bool = False
    tree_lines_info: List[Tuple[int, str]] = [] # (line_index, raw_line)
    
    lines = text.splitlines()

    # --- First pass: Identify tree lines and the root marker ---
    for i, line in enumerate(lines):
        raw = line.rstrip("\n")
        trimmed = _get_content(raw)

        if trimmed.startswith("@@@FILE_BEGIN"):
            parsing_v2_content = True
            continue
        elif trimmed.startswith("@@@FILE_END"):
            parsing_v2_content = False
            continue
        
        if parsing_v2_content or not trimmed or trimmed.startswith("#"):
            continue

        if trimmed.startswith("@ROOT"):
            match = re.search(r'@ROOT\s+([^{\s}]+|{{[^}]+}})', trimmed)
            if match:
                root_marker_name = match.group(1)
            continue
        
        tree_lines_info.append((i, raw))

    # --- Determine base indentation from the collected tree lines ---
    if tree_lines_info:
        # Find the indentation of the first actual tree node to handle global offsets
        first_node_line = tree_lines_info[0][1]
        min_indent_level = _count_raw_indent(first_node_line)
    else:
        min_indent_level = 0
    
    # --- Second pass: Build NodeItems with normalized indentation ---
    for line_index, raw_line in tree_lines_info:
        raw_indent = _count_raw_indent(raw_line)
        content = _get_content(raw_line)
        
        effective_indent = raw_indent - min_indent_level
        if effective_indent < 0: # Should not happen, but as a safeguard
            effective_indent = 0

        is_dir = content.endswith("/")
        name = content[:-1] if is_dir else content
        
        # Check for invalid path characters - reject absolute paths and path traversal
        if name.startswith(('/', '\\')) or '..' in name or ':' in name:
            return [], None, f"Error at line {line_index + 1}: Invalid characters in path name ('..', '/', '\\', ':'). Found: '{name}'"
        
        items.append(NodeItem(indent=effective_indent, name=name, is_dir=is_dir, line_number=line_index + 1))
    
    # --- Post-parsing validation ---
    if not root_marker_name and items:
        return [], None, "Error: Missing '@ROOT {marker}' declaration for the provided tree structure."
    
    if root_marker_name and items and (items[0].name != root_marker_name or not items[0].is_dir):
        return [], root_marker_name, f"Error: The first node must be '{root_marker_name}/' and have the lowest indentation."

    return items, root_marker_name, None

# ---------- Planning and Analysis Logic (unchanged) ----------
def _normalize_filename(name: str, config: dict) -> str:
    n = name
    if config.get("NORMALIZE_LOWER", True): n = n.lower()
    if config.get("NORMALIZE_REMOVE_NONALNUM", True): n = re.sub(r"[^a-z0-9]", "", n)
    return n

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

def find_similar_candidates(existing_map: Dict[str, List[Path]], target_name: str, config: dict) -> List[Tuple[str, float, List[Path]]]:
    if not config.get("ENABLE_SIMILARITY_SCAN", True): return []
    threshold = config.get("SIMILARITY_RATIO_THRESHOLD", 0.86)
    target_norm = _normalize_filename(target_name, config)
    if not target_norm: return []
    out = []
    for exist_name, paths in existing_map.items():
        exist_norm = _normalize_filename(exist_name, config)
        if not exist_norm: continue
        ratio = difflib.SequenceMatcher(a=target_norm, b=exist_norm).ratio()
        if ratio >= threshold:
            out.append((exist_name, ratio, paths))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
# -------------------------------------------------------------

def generate_plan(root_path: Path, text_input: str, config: dict) -> Plan:
	"""
	Generates a unified plan from a text input that may contain both a
	scaffold tree and V2 patch blocks.
	"""
	plan = Plan(root_path=root_path, tree_text=text_input, config=config)

	# 1. Parse scaffold tree structure
	tree_nodes, initial_root_marker, tree_error = parse_tree_text(text_input)
	if tree_error:
		plan.errors.append(tree_error)

	# Determine the effective root_marker for replacement in V2 paths
	effective_root_marker = initial_root_marker
	if not effective_root_marker and "{{Root}}" in text_input:
		effective_root_marker = "{{Root}}"

	if tree_nodes:
		plan.nodes = tree_nodes[1:] # Remove {{Root}} node
		stack: List[Tuple[int, Path]] = [(0, root_path)]
		for item in plan.nodes:
			while stack and stack[-1][0] >= item.indent:
				stack.pop()
			if not stack or item.indent > stack[-1][0] + 1:
				plan.errors.append(f"Structure error at line {item.line_number}: Invalid indentation. Node '{item.name}' is indented too deeply. It must be at most one level deeper than its parent.")
				continue
			base_path = stack[-1][1]
			current_path = base_path / item.name
			if item.is_dir:
				plan.planned_dirs.add(current_path)
				stack.append((item.indent, current_path))
			else:
				plan.planned_files.add(current_path)
	
	# 2. Parse V2 patch blocks
	try:
		patch_data = parse_v2_format(text_input, root_marker=effective_root_marker)
		for item in patch_data:
			path_str = item['path']
			content = item['content']
			if '..' in path_str or Path(path_str).is_absolute():
				plan.errors.append(f"Invalid path in patch: '{path_str}'.")
				continue
			target_path = root_path / path_str
			plan.planned_files.add(target_path)
			plan.file_contents[target_path.resolve()] = content
			for parent in target_path.parents:
				if parent != root_path and parent.is_relative_to(root_path):
					plan.planned_dirs.add(parent)
	except V2ParserError as e:
		plan.errors.append(f"V2 Patch Error: {e}")

	if not plan.planned_dirs and not plan.planned_files:
		if not plan.errors:
			plan.errors.append("No valid scaffold tree or V2 patch blocks found in the input.")
		return plan

	# 3. Analyze filesystem state
	all_planned_paths = plan.planned_dirs.union(plan.planned_files)
	for path in sorted(list(all_planned_paths), key=lambda p: len(p.parts)):
		state = ""
		if path.exists():
			is_planned_dir = path in plan.planned_dirs
			is_planned_file = path in plan.planned_files
			is_fs_dir = path.is_dir()

			if is_planned_dir and not is_fs_dir: state = "conflict_file"
			elif is_planned_file and is_fs_dir: state = "conflict_dir"
			elif is_planned_file and path.resolve() in plan.file_contents: state = "overwrite"
			else: state = "exists"
		else:
			state = "new"
		
		if state: plan.path_states[path] = state
		if state.startswith("conflict"):
			plan.errors.append(f"Conflict at '{path}': trying to create { 'dir' if is_planned_dir else 'file' } but a { 'file' if not is_fs_dir else 'dir' } exists.")

	# 4. Analyze warnings
	plan.existing_files = scan_existing_files(root_path, config)

	return plan