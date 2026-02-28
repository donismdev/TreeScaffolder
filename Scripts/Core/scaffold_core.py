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

# ---------- Planning and Analysis Logic ----------
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
    """Strictly compares two contents including the exact number of newlines. 
    Only normalizes line endings to a common '\n' format for comparison.
    """
    def to_lf(text):
        if text is None: return ""
        # Convert all to LF so we can compare the raw content and newline counts fairly
        return text.replace('\r\n', '\n').replace('\r', '\n')

    return to_lf(actual) == to_lf(planned)

def generate_plan(root_path: Path, text_input: str, config: dict) -> Plan:
	"""
	Generates a unified plan from a text input that may contain both a
	scaffold tree and V2 patch blocks.
	"""
	plan = Plan(root_path=root_path, tree_text=text_input, config=config)

	# 1. Surgical Split: Only pass text BEFORE the first V2 block to the tree parser.
	# This ensures source code never interferes with tree parsing.
	tree_part = text_input
	v2_start_idx = text_input.find("@@@")
	if v2_start_idx != -1:
		tree_part = text_input[:v2_start_idx]

	# 2. Parse the Scaffold Tree structure from the isolated tree part.
	tree_nodes, root_marker, tree_err = parse_tree_text(tree_part)
	if tree_err:
		plan.errors.append(tree_err)
		return plan
	
	plan.nodes = tree_nodes

	# 3. Map Tree Nodes to Paths
	node_paths: Dict[int, Path] = {} # line_number -> absolute path
	if tree_nodes:
		# stack stores (indent_level, path_object)
		# We start with -1 level for the logical root so that level 0 items (under root) 
		# correctly append to the root_path.
		stack: List[tuple[int, Path]] = [(-1, root_path)] 
		
		for node in tree_nodes:
			# If this is the very first node and it's the root marker, 
			# just assign root_path and set its indent as the base.
			if node.name == root_marker and node.indent == 0:
				node_paths[node.line_number] = root_path
				# Adjust stack base to this node
				stack = [(0, root_path)]
				continue

			# Pop from stack until we find the parent (indent must be less than current)
			while stack and stack[-1][0] >= node.indent:
				stack.pop()
			
			if not stack:
				# Should not happen with base -1, but for safety:
				current_path = root_path / node.name
			else:
				current_path = stack[-1][1] / node.name
			
			node_paths[node.line_number] = current_path
			
			if node.is_dir:
				plan.planned_dirs.add(current_path)
				stack.append((node.indent, current_path))
			else:
				plan.planned_files.add(current_path)
				# Default content for files in tree is empty string
				plan.file_contents[current_path] = ""

	# 4. Parse V2 blocks to identify file contents.
	try:
		patch_data = parse_v2_format(text_input)
	except V2ParserError as e:
		plan.errors.append(f"{e}") 
		return plan

	# 5. Process V2 patch data (Overrides/Updates tree definitions)
	# Determine a best-guess root marker for substitution.
	effective_root_marker = root_marker if root_marker else "{{Root}}"
	
	for item in patch_data:
		raw_path_str = item['path'].strip()
		content = item['content']
		
		# CRITICAL SECURITY: Strictly forbid '..' to ensure paths ONLY move downwards
		if '..' in raw_path_str:
			plan.errors.append(f"Security Violation: Path traversal '..' is strictly forbidden in '{raw_path_str}'. All paths must move downwards from the root.")
			continue

		norm_path = raw_path_str.replace('\\', '/').strip()
		markers = ["{{Root}}"]
		if effective_root_marker and effective_root_marker.lower() != "{{root}}":
			markers.insert(0, effective_root_marker)
		
		target_path = None
		temp_path = norm_path.lstrip('/')
		for m in markers:
			if temp_path.lower().startswith(m.lower()):
				rel_part = temp_path[len(m):].lstrip('/')
				target_path = (root_path / rel_part).resolve()
				break
		
		# CRITICAL: Strict Enforcement of Root Marker
		if not target_path:
			plan.errors.append(f"Invalid path format: '{raw_path_str}'. Every file path in Source Code MUST start with the '{{{{Root}}}}' marker.")
			continue
		
		try:
			if not target_path.is_relative_to(root_path):
				plan.errors.append(f"Path resolves outside of target root: '{raw_path_str}'")
				continue
		except Exception:
			plan.errors.append(f"Invalid path resolution: '{raw_path_str}'")
			continue

		# V2 block content takes precedence over the tree
		plan.planned_files.add(target_path)
		plan.file_contents[target_path] = content
		# Ensure parents are planned as directories
		for parent in target_path.parents:
			if parent != root_path and parent.is_relative_to(root_path):
				plan.planned_dirs.add(parent)

	if not plan.planned_dirs and not plan.planned_files:
		if not plan.errors:
			plan.errors.append("No valid scaffold tree or V2 patch blocks found in the input.")
		return plan

	# --- 0. Internal Plan Consistency Check ---
	# Check if the same path is defined as both a file and a directory in the SAME plan.
	internal_conflicts = plan.planned_dirs.intersection(plan.planned_files)
	for conflict_path in internal_conflicts:
		plan.errors.append(f"Internal Plan Error: '{conflict_path.name}' is defined as both a FILE and a DIRECTORY at the same location.")

	# --- 1. Final Analysis and Filesystem Conflict Detection ---
	# We process all planned paths to determine their state relative to the physical disk.
	all_planned_paths = plan.planned_dirs.union(plan.planned_files)
	
	# Sort by depth so we process parents before children (though states are independent)
	sorted_planned = sorted(list(all_planned_paths), key=lambda p: len(p.parts))
	
	for path in sorted_planned:
		state = "new"
		is_planned_dir = path in plan.planned_dirs
		is_planned_file = path in plan.planned_files
		
		if path.exists():
			is_fs_dir = path.is_dir()
			is_fs_file = path.is_file()
			
			if is_planned_dir:
				if is_fs_dir:
					state = "exists"
				else:
					# Planned as DIR, but a FILE exists on disk
					state = "conflict_file"
					plan.errors.append(t("message.conflicts_msg_detail", path=path.name, type="directory", existing="file"))
			
			elif is_planned_file:
				if is_fs_file:
					# Check content if we have planned content
					try:
						planned_content = plan.file_contents.get(path.resolve())
						if planned_content is not None:
							existing_content = path.read_text(encoding='utf-8', errors='replace')
							if is_content_identical(existing_content, planned_content):
								state = "identical"
							else:
								state = "overwrite"
						else:
							# File in tree but no source code provided
							state = "exists"
					except Exception:
						state = "overwrite"
				else:
					# Planned as FILE, but a DIR exists on disk
					state = "conflict_dir"
					plan.errors.append(t("message.conflicts_msg_detail", path=path.name, type="file", existing="directory"))
		
		plan.path_states[path] = state

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

def reconstruct_source_only_tree(plan: Plan) -> str:
	"""Generates a tree structure using only files defined in the Source Code blocks."""
	# Filter to only include files from Source Code and their parents
	source_files = set(plan.file_contents.keys())
	source_dirs = set()
	for f in source_files:
		for parent in f.parents:
			if parent != plan.root_path and parent.is_relative_to(plan.root_path):
				source_dirs.add(parent)
	
	all_source_paths = source_files.union(source_dirs)
	return reconstruct_tree_string(plan, filter_paths=all_source_paths, show_annotations=False)

def reconstruct_tree_string(plan: Plan, filter_paths: Optional[Set[Path]] = None, show_annotations: bool = True) -> str:
	"""Generates a text-based tree structure from the planned paths, optionally filtered and annotated."""
	all_planned = plan.planned_dirs.union(plan.planned_files)
	if filter_paths is not None:
		all_paths_list = sorted(list(all_planned.intersection(filter_paths)), key=lambda p: (len(p.parts), str(p).lower()))
	else:
		all_paths_list = sorted(list(all_planned), key=lambda p: (len(p.parts), str(p).lower()))
		
	if not all_paths_list:
		return ""

	root_path = plan.root_path
	# Find the root marker name from the plan nodes if possible
	root_marker = "{{Root}}"
	for node in plan.nodes:
		if node.indent == 0:
			root_marker = node.name
			break

	lines = [f"@ROOT {root_marker}", "", f"{root_marker}/"]
	
	def get_rel_depth(p):
		try:
			return len(p.relative_to(root_path).parts)
		except:
			return 0

	for p in all_paths_list:
		if p == root_path: continue
		depth = get_rel_depth(p)
		indent = "\t" * depth
		
		is_dir = p in plan.planned_dirs
		name = p.name + ("/" if is_dir else "")
		
		# Add annotation if the file already matches the plan
		annotation = ""
		if show_annotations and not is_dir:
			state = plan.path_states.get(p)
			if state == "identical":
				annotation = " // (Already matches)"
			elif state == "exists":
				annotation = " // (File exists)"
		
		lines.append(f"{indent}{name}{annotation}")
		
	return "\n".join(lines)
	