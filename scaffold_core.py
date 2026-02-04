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

	# Raw parsed nodes
	nodes: List[NodeItem] = field(default_factory=list)

	# Planned creations
	planned_dirs: List[Path] = field(default_factory=list)
	planned_files: List[Path] = field(default_factory=list)

	# Analysis results
	existing_files: Dict[str, List[Path]] = field(default_factory=dict)
	
	# Status of each planned path
	path_states: Dict[Path, str] = field(default_factory=dict) # "new", "exists", "conflict_file", "conflict_dir"
	
	# Warnings
	duplicate_warnings: Dict[Path, List[Path]] = field(default_factory=dict)
	similarity_warnings: Dict[Path, List[Tuple[str, float, List[Path]]]] = field(default_factory=dict)
	
	# Errors
	errors: List[str] = field(default_factory=list)
	
	@property
	def has_conflicts(self) -> bool:
		return any(v.startswith("conflict") for v in self.path_states.values())

# ---------- Parsing Logic ----------

def _count_indent(line: str) -> Tuple[int, str]:
	"""Counts indentation (tabs or 4-spaces) and returns the level and content."""
	raw = line.rstrip("\n")
	if not raw.strip():
		return 0, ""

	leading_match = re.match(r"^[	 ]*", raw)
	prefix = leading_match.group(0) if leading_match else ""
	content = raw[len(prefix):].strip()

	tab_count = prefix.count("	")
	# Treat 4 spaces as one indent level
	space_count = prefix.count(" ")
	space_level = space_count // 4

	indent = tab_count + space_level
	return indent, content

def parse_tree_text(text: str) -> Tuple[List[NodeItem], Optional[str]]:
	"""
	Parses the multiline tree text into a list of NodeItems.
	Returns a tuple of (items, error_message).
	"""
	items: List[NodeItem] = []
	root_marker_name: Optional[str] = None
	
	lines = text.splitlines()
	for i, line in enumerate(lines):
		raw = line.strip("\n")
		trimmed = raw.strip()

		if not trimmed or trimmed.startswith("#"):
			continue

		# Extract the root marker, e.g., @ROOT {{Root}}
		if trimmed.startswith("@ROOT"):
			match = re.search(r'@ROOT\s+([^{\s}]+|{{\w+}})', trimmed)
			if match:
				root_marker_name = match.group(1)
			continue

		indent, content = _count_indent(raw)
		if not content:
			continue

		is_dir = content.endswith("/")
		name = content[:-1] if is_dir else content
		
		# Security: Validate the name to prevent path traversal attacks
		if name.startswith('/') or name.startswith('\\'):
			return [], f"Error at line {i + 1}: Path names cannot start with '/' or '\\' (absolute paths not allowed)."
		if name == '..' or '/..' in name or '\\..' in name or name.startswith('..'):
			return [], f"Error at line {i + 1}: Path traversal with '..' is not allowed."
		if ':' in name and len(name) > 1 and name[1] == ':':
			return [], f"Error at line {i + 1}: Windows drive letters in paths are not allowed."
		
		items.append(NodeItem(indent=indent, name=name, is_dir=is_dir, line_number=i + 1))
	
	# Validation
	if not root_marker_name:
		return [], "Error: Tree text must contain an '@ROOT {{marker}}' line."
	
	if not items or items[0].name != root_marker_name:
		return [], f"Error: The first node in the tree must be the root marker '{root_marker_name}/'."

	if items[0].is_dir is False:
		return [], f"Error: The root marker node '{root_marker_name}/' must be a directory (end with '/')."
		
	# Pass the validation, do not remove the logical root node from the list yet
	return items, None

# ---------- Planning and Analysis Logic ----------

def _normalize_filename(name: str, config: dict) -> str:
	"""Normalizes a filename for comparison based on config."""
	n = name
	if config.get("NORMALIZE_LOWER", True):
		n = n.lower()
	if config.get("NORMALIZE_REMOVE_NONALNUM", True):
		n = re.sub(r"[^a-z0-9]", "", n)
	return n

def _is_interesting_file(path: Path, config: dict) -> bool:
	"""Checks if a file is relevant for similarity scanning."""
	extensions = config.get("SCAN_INCLUDE_EXTENSIONS", {".h", ".cpp", ".cs"})
	name = path.name
	if any(name.endswith(ext) for ext in extensions if ext.startswith(".")):
		return True
	return path.suffix in extensions
	
def scan_existing_files(root: Path, config: dict) -> Dict[str, List[Path]]:
	"""Scans the root directory for existing files to use in analysis."""
	result: Dict[str, List[Path]] = {}
	try:
		for p in root.rglob("*"):
			if p.is_file() and _is_interesting_file(p, config):
				if p.name not in result:
					result[p.name] = []
				result[p.name].append(p)
	except OSError as e:
		# Handle potential permission errors gracefully
		print(f"Warning: Could not scan directory fully: {e}")
	return result

def find_similar_candidates(
	existing_map: Dict[str, List[Path]], 
	target_name: str, 
	config: dict
) -> List[Tuple[str, float, List[Path]]]:
	"""Finds files with names similar to the target name."""
	if not config.get("ENABLE_SIMILARITY_SCAN", True):
		return []

	threshold = config.get("SIMILARITY_RATIO_THRESHOLD", 0.86)
	target_norm = _normalize_filename(target_name, config)
	if not target_norm:
		return []

	out: List[Tuple[str, float, List[Path]]] = []
	for exist_name, paths in existing_map.items():
		exist_norm = _normalize_filename(exist_name, config)
		if not exist_norm:
			continue

		ratio = difflib.SequenceMatcher(a=target_norm, b=exist_norm).ratio()
		if ratio >= threshold:
			out.append((exist_name, ratio, paths))

	out.sort(key=lambda x: x[1], reverse=True)
	return out

def generate_plan(root_path: Path, tree_text: str, config: dict) -> Plan:
	"""
	Generates a complete scaffolding plan including analysis of the current state.
	This is a read-only operation.
	"""
	plan = Plan(root_path=root_path, tree_text=tree_text, config=config)

	# Get all nodes, including the conceptual root marker, and the marker name itself
	full_nodes, error = parse_tree_text(tree_text)
	if error:
		plan.errors.append(error)
		return plan
	
	if not full_nodes: # Should not happen if parse_tree_text passed validation
		plan.errors.append("Internal error: No nodes parsed after successful tree text validation.")
		return plan

	# The first node is guaranteed to be the root marker by parse_tree_text
	root_marker_node = full_nodes[0]
	
	# The actual nodes to process (excluding the root marker node)
	plan.nodes = full_nodes[1:]

	# 1. Build the list of planned paths
	# Initialize stack with the actual filesystem root path.
	# The conceptual root marker node effectively maps to this real root_path.
	stack: List[Tuple[int, Path]] = [(0, root_path)] # (indent_level, actual_path)
	
	for item in plan.nodes:
		# Adjust stack based on indentation
		# Pop items from stack if current item is at a shallower or same level
		while stack and stack[-1][0] >= item.indent:
			stack.pop()
		
		# If the current item's indent is deeper than its supposed parent on stack,
		# or if stack is empty but item has indent > 0 (meaning no parent was found), this is an error.
		if not stack or item.indent > stack[-1][0] + 1:
			plan.errors.append(f"Structure error at line {item.line_number}: Invalid indentation level or missing parent directory.")
			return plan
		
		base_path = stack[-1][1] # Get the actual path of the parent

		current_path = base_path / item.name

		if item.is_dir:
			plan.planned_dirs.append(current_path)
			stack.append((item.indent, current_path)) # Push new directory to stack
		else:
			plan.planned_files.append(current_path)
		
	# 2. Analyze the current filesystem state against the plan
	plan.existing_files = scan_existing_files(root_path, config)
	
	all_planned_paths = plan.planned_dirs + plan.planned_files
	for path in all_planned_paths:
		if path.exists():
			is_planned_dir = path in plan.planned_dirs
			is_fs_dir = path.is_dir()
			
			if is_planned_dir and not is_fs_dir:
				plan.path_states[path] = "conflict_file" # Trying to create dir, but file exists
				plan.errors.append(f"Conflict: A file exists at '{path}' where a directory is planned.")
			elif not is_planned_dir and is_fs_dir:
				plan.path_states[path] = "conflict_dir" # Trying to create file, but dir exists
				plan.errors.append(f"Conflict: A directory exists at '{path}' where a file is planned.")
			else:
				plan.path_states[path] = "exists"
		else:
			plan.path_states[path] = "new"

	# 3. Analyze warnings (Duplicates and Similarity)
	for target_path in plan.planned_files:
		# Duplicate name check
		existing_with_same_name = plan.existing_files.get(target_path.name, [])
		# Filter out the identical path if it already exists
		other_paths = [p for p in existing_with_same_name if p.resolve() != target_path.resolve()]
		if other_paths:
			plan.duplicate_warnings[target_path] = other_paths
			
		# Similarity check
		if config.get("ENABLE_SIMILARITY_SCAN"):
			candidates = find_similar_candidates(plan.existing_files, target_path.name, config)
			# Filter out trivial self-similarity
			filtered_candidates = []
			for exist_name, ratio, paths in candidates:
				if exist_name == target_path.name:
					# If same name, only warn if it exists elsewhere
					other_locs = [p for p in paths if p.resolve() != target_path.resolve()]
					if other_locs:
						filtered_candidates.append((exist_name, ratio, other_locs))
				else:
					filtered_candidates.append((exist_name, ratio, paths))
			
			if filtered_candidates:
				plan.similarity_warnings[target_path] = filtered_candidates

	return plan
