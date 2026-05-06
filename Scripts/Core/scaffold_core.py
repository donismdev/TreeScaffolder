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
from Scripts.Utils.line_endings import ensure_lf
from Scripts.Utils import logger as sys_logger
import difflib

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

    last_effective_indent = -1
    for line_index, raw_line, level in temp_info:
        content = raw_line.strip()
        effective_indent = level - min_level
        if effective_indent < 0:
            effective_indent = 0

        # CRITICAL FIX: Check for indentation jumps (CASE-TREE-01)
        # A node cannot be more than 1 level deeper than the previous node.
        if effective_indent > last_effective_indent + 1:
            return [], None, t("message.err_deep_indent", line=line_index + 1, name=content)

        is_dir = content.endswith("/") or content.endswith("\\")
        name = content[:-1] if is_dir else content
        name = name.replace("\\", "/")

        if name.startswith('/') or '..' in name or ':' in name:
            return [], None, t("message.err_invalid_char", line=line_index + 1, name=name)

        items.append(NodeItem(indent=effective_indent, name=name, is_dir=is_dir, line_number=line_index + 1))
        last_effective_indent = effective_indent

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
    return ensure_lf(actual) == ensure_lf(planned)

def _get_byte_range_from_lines(content: str, start_line: int, end_line: int) -> tuple[int, int]:
    """Converts 1-indexed line numbers to 0-indexed character offsets in LF content."""
    if start_line < 1: start_line = 1
    
    pos = 0
    current_line = 1
    start_offset = 0
    
    # Find start of start_line
    while current_line < start_line and pos < len(content):
        next_nl = content.find('\n', pos)
        if next_nl == -1:
            pos = len(content)
            break
        pos = next_nl + 1
        current_line += 1
    start_offset = pos
    
    # Find end of end_line (include the entire end_line)
    while current_line <= end_line and pos < len(content):
        next_nl = content.find('\n', pos)
        if next_nl == -1:
            pos = len(content)
            break
        pos = next_nl + 1
        current_line += 1
    end_offset = pos
    
    return start_offset, end_offset

import difflib

def apply_v2_patch(content: str, instructions: List[Dict[str, Any]]) -> tuple[str, Optional[str]]:
    """
    Applies V2 patch instructions to the given content.
    Returns (updated_content, error_message).
    """
    current_content = content
    last_find = None
    line_range = None
    
    for instr in instructions:
        keyword = instr['keyword']
        block_content = instr['content']
        
        if keyword == "FIND":
            last_find = block_content
            continue
            
        if keyword == "LINE_RANGE":
            if line_range is not None:
                return current_content, f"[V2-042] Duplicate Line Range: Multiple 'LINE_RANGE' blocks found in a single 'PATCH'."
            
            parts = block_content.strip().split()
            if len(parts) != 2:
                return current_content, f"[V2-044] Invalid Line Range Value: 'LINE_RANGE' requires exactly two integers. Found: {repr(block_content)}"
            
            try:
                start_l = int(parts[0])
                end_l = int(parts[1])
            except ValueError:
                return current_content, f"[V2-044] Invalid Line Range Value: 'LINE_RANGE' contains non-integer values. Found: {repr(block_content)}"
            
            if start_l > end_l:
                 return current_content, f"[V2-041] Invalid Line Range: StartLine ({start_l}) is greater than EndLine ({end_l})."
            
            line_range = (start_l, end_l)
            continue
        
        if keyword == "INSERT_TOP":
            current_content = block_content + current_content
        elif keyword == "INSERT_BOTTOM":
            # Section 11 Spec: "The tool should normalize the final newline safely... 
            # the resulting file should end with a newline."
            if current_content and not current_content.endswith("\n"):
                current_content += "\n"
            current_content += block_content
            if not current_content.endswith("\n"):
                current_content += "\n"
        elif keyword in ("REPLACE", "INSERT_AFTER", "INSERT_BEFORE", "REMOVE", "CLEAR_AFTER"):
            if last_find is None:
                return current_content, f"[V2-012] Missing Context: Operation '{keyword}' requires a preceding 'FIND' block."
            
            # --- LINE RANGE HINT ---
            search_area = current_content
            area_offset = 0
            if line_range:
                start_off, end_off = _get_byte_range_from_lines(current_content, line_range[0], line_range[1])
                search_area = current_content[start_off:end_off]
                area_offset = start_off

            # --- LITERAL MATCH CHECK (Mandatory: Exactly one match) ---
            # We use direct string operations to avoid regex-escape issues with newlines/tabs.
            match_count = search_area.count(last_find)
            
            # Prepare a short snippet for the UI error message
            find_snippet = (last_find[:40] + "...") if len(last_find) > 40 else last_find
            find_snippet_repr = repr(find_snippet)
            range_info = f" in line range {line_range[0]}-{line_range[1]}" if line_range else ""

            if match_count == 0:
                # --- DIAGNOSTIC LOGGING ---
                sys_logger.error(f"[DIAGNOSTIC] FIND failed for {keyword}{range_info}")
                sys_logger.error(f"[DIAGNOSTIC] last_find (len={len(last_find)}): {repr(last_find)}")
                sys_logger.error(f"[DIAGNOSTIC] last_find hex: {last_find.encode('utf-8').hex()}")
                sys_logger.error(f"[DIAGNOSTIC] search_area total len: {len(search_area)}")
                
                # Check for Tab vs Space mismatch
                lf_no_tabs = last_find.replace('\t', '    ')
                cc_no_tabs = search_area.replace('\t', '    ')
                if lf_no_tabs in cc_no_tabs:
                    sys_logger.error("[DIAGNOSTIC] Match found after normalizing TABS to SPACES. Please check indentation consistency.")
                
                # Check for common issues: whitespace mismatches
                if last_find.strip() in search_area:
                    sys_logger.error("[DIAGNOSTIC] Found stripped version of last_find. Likely whitespace mismatch at start/end.")
                
                # --- FUZZY DIFF LOGGING ---
                # Try to find the best match to show what is different
                sys_logger.error("[DIAGNOSTIC] Attempting fuzzy match to identify differences...")
                lines_cc = search_area.splitlines()
                lines_lf = last_find.splitlines()
                
                if lines_lf:
                    first_line = lines_lf[0].strip()
                    # Find all lines in search_area that contain the first line of our search block
                    potential_starts = [i for i, line in enumerate(lines_cc) if first_line in line]
                    
                    if potential_starts:
                        # Take the first potential start for comparison
                        best_idx = potential_starts[0]
                        window = lines_cc[best_idx : best_idx + len(lines_lf)]
                        
                        sys_logger.error(f"[DIAGNOSTIC] Potential match found starting at search_area line {best_idx + 1}")
                        diff = difflib.ndiff(lines_lf, window)
                        sys_logger.error("[DIAGNOSTIC] Line-by-line Diff (-: Expected, +: Actual):")
                        for line in diff:
                            if line.startswith(('-', '+', '?')):
                                sys_logger.error(f"[DIAGNOSTIC] {repr(line)}")
                    else:
                        sys_logger.error("[DIAGNOSTIC] Could not even find the first line of the search block in the search_area.")
                
                return current_content, f"[V2-010] Text Not Found: Match failed for '{keyword}'{range_info}. Searched for: {find_snippet_repr}"
            
            if match_count > 1:
                return current_content, f"[V2-011] Ambiguous Match: Found {match_count} occurrences for '{keyword}'{range_info}. Searched for: {find_snippet_repr}"
            
            # Find the start and end of the literal match within the search_area
            match_start_in_area = search_area.find(last_find)
            start = area_offset + match_start_in_area
            end = start + len(last_find)
            
            if keyword == "REPLACE":
                current_content = current_content[:start] + block_content + current_content[end:]
            elif keyword == "INSERT_AFTER":
                current_content = current_content[:end] + block_content + current_content[end:]
            elif keyword == "INSERT_BEFORE":
                current_content = current_content[:start] + block_content + current_content[start:]
            elif keyword == "REMOVE":
                current_content = current_content[:start] + current_content[end:]
            elif keyword == "CLEAR_AFTER":
                # CLEAR_AFTER: The line containing the first found FIND text remains. All content below that line is deleted.
                # Find the end of the line containing the match
                next_newline = current_content.find('\n', end)
                if next_newline == -1:
                    current_content = current_content[:end]
                else:
                    current_content = current_content[:next_newline + 1]
            
            last_find = None # Reset last_find after use? The spec implies one FIND per operation.
        elif keyword == "COMMENT":
            pass
        elif keyword == "LINE_RANGE":
            pass # Already handled above
        else:
            return current_content, f"Unsupported keyword '{keyword}' inside PATCH."
            
    return current_content, None

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
	
	for block in patch_data:
		keyword = block['keyword']
		raw_path_str = block['parameter'].strip()
		
		# Skip COMMENT blocks at top level
		if keyword == "COMMENT":
			continue

		norm_path = raw_path_str.replace('\\', '/').strip()
		# CRITICAL SECURITY: Strictly forbid '..' to ensure paths ONLY move downwards
		if '..' in raw_path_str or '..' in norm_path:
			plan.errors.append(f"Security Violation: Path traversal '..' is strictly forbidden in '{raw_path_str}'. All paths must move downwards from the root.")
			continue

		norm_path = norm_path.lstrip('/')
		markers = ["{{Root}}"]
		if effective_root_marker and effective_root_marker.lower() != "{{root}}":
			markers.insert(0, effective_root_marker)
		
		target_path = None
		for m in markers:
			if norm_path.lower().startswith(m.lower()):
				rel_part = norm_path[len(m):].lstrip('/')
				# Use joinpath and normpath
				target_path = root_path.joinpath(rel_part)
				break
		
		# CRITICAL: Strict Enforcement of Root Marker
		if not target_path:
			plan.errors.append(f"Invalid path format: '{raw_path_str}'. Every file path in Source Code MUST start with the '{{{{Root}}}}' marker.")
			continue
		
		# Ensure the path is actually under the root (extra safety)
		try:
			# On Windows, this also handles drive mismatches if both are absolute
			if not str(target_path.resolve()).lower().startswith(str(root_path.resolve()).lower()):
				raise ValueError()
		except Exception:
			plan.errors.append(f"Path resolves outside of target root: '{raw_path_str}'")
			continue

		# Process block content based on keyword
		if keyword == "FILE":
			plan.planned_files.add(target_path)
			plan.file_contents[target_path] = block['content']
		elif keyword == "CLEAR_FILE":
			plan.planned_files.add(target_path)
			plan.file_contents[target_path] = ""
		elif keyword == "PATCH":
			# PATCH applies to either existing planned content or physical disk content
			initial_content = ""
			if target_path in plan.file_contents:
				initial_content = plan.file_contents[target_path]
			elif target_path.is_file():
				try:
					raw_disk_content = target_path.read_text(encoding='utf-8')
					# CRITICAL: Normalize disk content to \n for matching with V2 blocks
					initial_content = ensure_lf(raw_disk_content)
				except Exception as e:
					plan.errors.append(f"Could not read existing file for PATCH (UTF-8 required): {target_path}. Error: {e}")
					continue
			
			updated_content, patch_err = apply_v2_patch(initial_content, block['children'])
			if patch_err:
				plan.errors.append(f"Patch error in '{raw_path_str}': {patch_err}")
				continue
			
			plan.planned_files.add(target_path)
			plan.file_contents[target_path] = updated_content
		
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

def reconstruct_tree_string(plan: Plan, filter_paths: Optional[Set[Path]] = None, show_annotations: bool = True, unchecked_paths: Optional[Set[Path]] = None) -> str:
	"""Generates a text-based tree structure with correct hierarchical nesting."""
	all_planned = plan.planned_dirs.union(plan.planned_files)
	
	# Determine base set of paths
	if filter_paths is not None:
		# Use provided filter (for Actually Applied tree)
		target_paths = all_planned.intersection(filter_paths)
	else:
		# Use all planned paths
		target_paths = all_planned

	if not target_paths:
		return ""

	root_path = plan.root_path
	# Find the root marker name
	root_marker = "{{Root}}"
	for node in plan.nodes:
		if node.indent == 0:
			root_marker = node.name
			break

	# CRITICAL FIX: Sort by path parts (case-insensitive) to ensure correct hierarchical nesting.
	# String sorting of absolute paths fails on Windows because '\' (92) sorts after 'S' (83) etc.
	path_list = sorted(list(target_paths), key=lambda p: [part.lower() for part in p.parts])
	
	lines = [f"@ROOT {root_marker}", "", f"{root_marker}/"]
	
	def get_rel_depth(p):
		try:
			return len(p.relative_to(root_path).parts)
		except:
			return 0

	for p in path_list:
		if p == root_path: continue
		depth = get_rel_depth(p)
		indent = "\t" * depth
		
		is_dir = p in plan.planned_dirs
		name = p.name + ("/" if is_dir else "")
		
		# Annotation logic
		annotation = ""
		if show_annotations:
			if unchecked_paths and p in unchecked_paths:
				annotation = " // (Unchecked - Not applied)"
			elif not is_dir:
				state = plan.path_states.get(p)
				if state == "identical":
					annotation = " // (Already matches)"
				elif state == "exists":
					annotation = " // (File exists)"
		
		lines.append(f"{indent}{name}{annotation}")
		
	return "\n".join(lines)
