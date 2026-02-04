# -*- coding: utf-8 -*-
"""
gui_app.py

A Windows GUI application for scaffolding projects from a tree text description.
Provides a tree editor, safe folder selection, a before/after diff view,
and logging. Built with tkinter and ttk.
"""
import json
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font

import scaffold_core
from file_classifier import FileTypeClassifier

# --- Constants ---
APP_TITLE = "Tree Scaffolder v1.0"
EXAMPLE_TREE_TEXT = r"""
# =========================================================
# - Use @ROOT to define the logical root marker.
# - The first node must be that marker, ending with a '/'.
# - Indent with TABS or 4-SPACES.
# =========================================================

@ROOT {{Root}}

{{Root}}/
	NewModule/
		NewModule.Build.cs
		Public/
			NewModule.h
		Private/
			NewModule.cpp
	AnotherModule/
		AnotherModule.uplugin
		Resources/
			Icon128.png
		Source/
			Private/
				AnotherModule.cpp
			Public/
				AnotherModule.h
""".strip()

class ScaffoldApp:
	"""The main application class for the Tree Scaffolder GUI."""

	def __init__(self, root: tk.Tk):
		self.root = root
		self.root.title(APP_TITLE)
		self.root.geometry("1200x800")
		self.root.minsize(800, 600)
		
		# --- Style Configuration ---
		self.style = ttk.Style()
		self.style.theme_use('vista')
		self.setup_styles()
		
		# --- Member Variables ---
		self.target_root_path = tk.StringVar()
		self.dry_run = tk.BooleanVar(value=True)
		self.enable_similarity_scan = tk.BooleanVar(value=True)
		self.similarity_threshold = tk.DoubleVar(value=0.86)
		
		# To be filled by the analysis
		self.current_plan: scaffold_core.Plan | None = None
		self.classifier = FileTypeClassifier()
		self.tree_text = None # Initialized in setup_left_panel
		self.source_code_text = None # Initialized in setup_left_panel
		self.content_text = None # Initialized in setup_left_panel

		# --- Main Layout ---
		self.main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
		self.main_paned_window.pack(fill=tk.BOTH, expand=True)

		self.left_frame = ttk.Frame(self.main_paned_window, padding=5)
		self.main_paned_window.add(self.left_frame, weight=1)

		self.right_frame = ttk.Frame(self.main_paned_window)
		self.main_paned_window.add(self.right_frame, weight=2)

		self.setup_left_panel()
		self.setup_right_panel()

		# Configure Treeview tags AFTER widgets are created
		self.style.configure('new.Treeview', foreground='green')
		self.style.configure('conflict.Treeview', foreground='red')
		self.style.configure('warning.Treeview', foreground='#E59400')
		self.before_tree.tag_configure('new', foreground='green')
		self.after_tree.tag_configure('new', foreground='green')
		self.after_tree.tag_configure('conflict', foreground='red', font=font.Font(weight='bold'))
		self.after_tree.tag_configure('warning', foreground='#E59400')
		self.after_tree.tag_configure('modified_parent', foreground='#DAA520')

	def setup_styles(self):
		"""Configure styles for Treeview and other widgets."""
		self.style.map("Treeview", background=[('selected', '#0078D7')])


		# Custom font for the text editor
		self.editor_font = font.Font(family="Consolas", size=10)

	def setup_left_panel(self):
		"""Creates all widgets for the left control panel."""
		self.left_frame.rowconfigure(1, weight=1)
		self.left_frame.columnconfigure(0, weight=1)

		# --- Controls Frame ---
		controls_frame = ttk.Frame(self.left_frame)
		controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
		controls_frame.columnconfigure(0, weight=1)

		# Folder Selection
		folder_frame = ttk.LabelFrame(controls_frame, text="1. Select Target Root Folder")
		folder_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
		folder_frame.columnconfigure(0, weight=1)
		
		self.folder_label = ttk.Label(folder_frame, textvariable=self.target_root_path, relief="sunken", padding=3)
		self.target_root_path.set("No folder selected.")
		self.folder_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
		
		browse_button = ttk.Button(folder_frame, text="Browse...", command=self.on_browse_folder)
		browse_button.grid(row=0, column=1, padx=5, pady=5)

		# --- Editor Tabs ---
		editor_tabs_frame = ttk.LabelFrame(self.left_frame, text="2. Define Scaffold Tree")
		editor_tabs_frame.grid(row=1, column=0, sticky="nsew")
		editor_tabs_frame.rowconfigure(0, weight=1)
		editor_tabs_frame.columnconfigure(0, weight=1)

		self.editor_notebook = ttk.Notebook(editor_tabs_frame)
		self.editor_notebook.grid(row=0, column=0, sticky="nsew")

		# --- Scaffold Tree Tab ---
		scaffold_tree_frame = ttk.Frame(self.editor_notebook)
		self.editor_notebook.add(scaffold_tree_frame, text="Scaffold Tree")
		scaffold_tree_frame.rowconfigure(0, weight=1)
		scaffold_tree_frame.columnconfigure(0, weight=1)
		
		self.tree_text = tk.Text(scaffold_tree_frame, wrap=tk.NONE, undo=True, font=self.editor_font, tabs=(self.editor_font.measure('    '),))
		
		tree_yscroller = ttk.Scrollbar(scaffold_tree_frame, orient=tk.VERTICAL, command=self.tree_text.yview)
		tree_xscroller = ttk.Scrollbar(scaffold_tree_frame, orient=tk.HORIZONTAL, command=self.tree_text.xview)
		self.tree_text.config(yscrollcommand=tree_yscroller.set, xscrollcommand=tree_xscroller.set)
		
		self.tree_text.grid(row=0, column=0, sticky="nsew")
		tree_yscroller.grid(row=0, column=1, sticky="ns")
		tree_xscroller.grid(row=1, column=0, sticky="ew")
		
		self.tree_text.insert("1.0", EXAMPLE_TREE_TEXT)
		
		# Load example button
		button_frame = ttk.Frame(scaffold_tree_frame)
		button_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
		load_example_button = ttk.Button(button_frame, text="Load Example", command=self.on_load_example)
		load_example_button.pack(side=tk.RIGHT, padx=2, pady=2)

		# --- Source Code Tab ---
		source_code_frame = ttk.Frame(self.editor_notebook)
		self.editor_notebook.add(source_code_frame, text="Source Code")
		source_code_frame.rowconfigure(0, weight=1)
		source_code_frame.columnconfigure(0, weight=1)

		self.source_code_text = tk.Text(source_code_frame, wrap=tk.NONE, undo=True, font=self.editor_font, tabs=(self.editor_font.measure('    '),))
		
		source_yscroller = ttk.Scrollbar(source_code_frame, orient=tk.VERTICAL, command=self.source_code_text.yview)
		source_xscroller = ttk.Scrollbar(source_code_frame, orient=tk.HORIZONTAL, command=self.source_code_text.xview)
		self.source_code_text.config(yscrollcommand=source_yscroller.set, xscrollcommand=source_xscroller.set)
		
		self.source_code_text.grid(row=0, column=0, sticky="nsew")
		source_yscroller.grid(row=0, column=1, sticky="ns")
		source_xscroller.grid(row=1, column=0, sticky="ew")

		# --- Content Tab ---
		content_frame = ttk.Frame(self.editor_notebook)
		self.editor_notebook.add(content_frame, text="Content")
		content_frame.rowconfigure(0, weight=1)
		content_frame.columnconfigure(0, weight=1)

		self.content_text = tk.Text(content_frame, wrap=tk.NONE, undo=True, font=self.editor_font, tabs=(self.editor_font.measure('    '),))
		
		content_yscroller = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.content_text.yview)
		content_xscroller = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=self.content_text.xview)
		self.content_text.config(yscrollcommand=content_yscroller.set, xscrollcommand=content_xscroller.set)
		
		self.content_text.grid(row=0, column=0, sticky="nsew")
		content_yscroller.grid(row=0, column=1, sticky="ns")
		content_xscroller.grid(row=1, column=0, sticky="ew")


		# --- Settings & Actions Frame ---
		settings_frame = ttk.LabelFrame(self.left_frame, text="3. Settings & Actions")
		settings_frame.grid(row=2, column=0, sticky="ew", pady=5)
		settings_frame.columnconfigure(1, weight=1)

		# Settings
		ttk.Checkbutton(settings_frame, text="Dry Run (don't write files)", variable=self.dry_run).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
		ttk.Checkbutton(settings_frame, text="Scan for similar names", variable=self.enable_similarity_scan).grid(row=1, column=0, columnspan=2, sticky="w", padx=5)

		ttk.Label(settings_frame, text="Similarity Ratio:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
		ttk.Scale(settings_frame, from_=0.5, to=1.0, variable=self.similarity_threshold, orient=tk.HORIZONTAL).grid(row=2, column=1, sticky="ew", padx=5)
		
		# Action Buttons
		actions_subframe = ttk.Frame(settings_frame)
		actions_subframe.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
		actions_subframe.columnconfigure((0, 1), weight=1)

		self.recompute_button = ttk.Button(actions_subframe, text="Compute Diff", command=self.on_recompute, state=tk.DISABLED)
		self.recompute_button.grid(row=0, column=0, padx=2, sticky="ew")

		self.apply_button = ttk.Button(actions_subframe, text="Apply Scaffold", command=self.on_apply, state=tk.DISABLED)
		self.apply_button.grid(row=0, column=1, padx=2, sticky="ew")

	def setup_right_panel(self):
		"""Creates the notebook for showing diffs and logs."""
		self.notebook = ttk.Notebook(self.right_frame)
		self.notebook.pack(fill=tk.BOTH, expand=True)

		# --- Diff View ---
		diff_frame = ttk.Frame(self.notebook, padding=5)
		self.notebook.add(diff_frame, text="Before / After Diff")
		diff_frame.rowconfigure(0, weight=1)
		diff_frame.columnconfigure(0, weight=1)

		diff_paned = ttk.PanedWindow(diff_frame, orient=tk.HORIZONTAL)
		diff_paned.grid(row=0, column=0, sticky="nsew")

		before_frame = ttk.LabelFrame(diff_paned, text="Before (Current State)")
		before_frame.rowconfigure(0, weight=1)
		before_frame.columnconfigure(0, weight=1)
		self.before_tree = self.create_treeview(before_frame)
		diff_paned.add(before_frame, weight=1)
		
		after_frame = ttk.LabelFrame(diff_paned, text="After (Planned State)")
		after_frame.rowconfigure(0, weight=1)
		after_frame.columnconfigure(0, weight=1)
		self.after_tree = self.create_treeview(after_frame)
		diff_paned.add(after_frame, weight=1)

		# --- Log View ---
		log_frame = ttk.Frame(self.notebook, padding=5)
		self.notebook.add(log_frame, text="Log")
		log_frame.rowconfigure(0, weight=1)
		log_frame.columnconfigure(0, weight=1)

		self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9))
		self.log_text.grid(row=0, column=0, sticky="nsew")
		log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
		log_scrollbar.grid(row=0, column=1, sticky="ns")
		self.log_text.config(yscrollcommand=log_scrollbar.set)
	
	def create_treeview(self, parent: ttk.Frame) -> ttk.Treeview:
		"""Helper to create and configure a Treeview widget."""
		tree = ttk.Treeview(parent, show="tree")
		tree.grid(row=0, column=0, sticky="nsew")
		
		scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
		scrollbar.grid(row=0, column=1, sticky="ns")
		tree.config(yscrollcommand=scrollbar.set)
		
		return tree
		
	# --- Event Handlers ---

	def on_load_example(self):
		"""Clears the text area and inserts the example tree text."""
		self.tree_text.delete("1.0", tk.END)
		self.tree_text.insert("1.0", EXAMPLE_TREE_TEXT)

	def on_browse_folder(self):
		"""Handles the 'Browse...' button click to select and validate a folder."""
		path = filedialog.askdirectory(mustexist=True, title="Select a Target Root Folder")
		if not path:
			return

		is_valid, message = self._validate_path(path)

		if not is_valid:
			messagebox.showerror("Invalid Folder", message)
			self.target_root_path.set("No folder selected.")
			self.recompute_button.config(state=tk.DISABLED)
			self._clear_tree(self.before_tree)
			self._clear_tree(self.after_tree)
		else:
			self.target_root_path.set(message) # message is the resolved path on success
			self.recompute_button.config(state=tk.NORMAL)
			self._populate_before_tree(Path(message))
			self._clear_tree(self.after_tree)
			self.apply_button.config(state=tk.DISABLED)


	def on_recompute(self):
		"""Handles the 'Recompute Diff' button click."""
		root_path_str = self.target_root_path.get()
		if not root_path_str or not Path(root_path_str).is_dir():
			messagebox.showerror("Error", "Please select a valid root folder first.")
			return

		root_path = Path(root_path_str)
		tree_text = self.tree_text.get("1.0", tk.END)

		config = {
			"DRY_RUN": self.dry_run.get(),
			"ENABLE_SIMILARITY_SCAN": self.enable_similarity_scan.get(),
			"SIMILARITY_RATIO_THRESHOLD": self.similarity_threshold.get(),
			# Re-use settings from the standalone script's defaults
			"NORMALIZE_LOWER": True,
			"NORMALIZE_REMOVE_NONALNUM": True,
			"SCAN_INCLUDE_EXTENSIONS": {
				".h", ".hpp", ".cpp", ".c", ".cs",
				".Build.cs", ".Target.cs", ".uproject", ".uplugin"
			}
		}

		self.current_plan = scaffold_core.generate_plan(root_path, tree_text, config)
		
		# Refresh "Before" view in case filesystem changed
		self._populate_before_tree(root_path)
		# Populate "After" view with the new plan
		self._populate_after_tree(self.current_plan)

		if self.current_plan.errors:
			error_message = "\n".join(self.current_plan.errors)
			messagebox.showerror("Planning Error", f"Errors found in scaffold tree:\n\n{error_message}")
			self.apply_button.config(state=tk.DISABLED)
		elif self.current_plan.has_conflicts:
			messagebox.showwarning("Conflicts Found", "Path conflicts were detected. 'Apply' is disabled.\nCheck the 'After' view for items marked in red.")
			self.apply_button.config(state=tk.DISABLED)
		else:
			self.apply_button.config(state=tk.NORMAL)
			self.notebook.select(0) # Switch to diff view


	def on_apply(self):
		"""Handles the 'Apply Scaffold' button click."""
		if not self.current_plan or self.current_plan.has_conflicts:
			messagebox.showerror("Cannot Apply", "There is no valid plan to apply, or the plan has conflicts. Please recompute.")
			return

		is_dry_run = self.dry_run.get()
		if is_dry_run:
			msg = "This is a DRY RUN. No files will be written.\n\nProceed with logging the simulation?"
		else:
			num_dirs = len([p for p, s in self.current_plan.path_states.items() if s == 'new' and p in self.current_plan.planned_dirs])
			num_files = len([p for p, s in self.current_plan.path_states.items() if s == 'new' and p in self.current_plan.planned_files])
			msg = f"This will create {num_dirs} directories and {num_files} files.\n\nAre you sure you want to proceed?"

		if messagebox.askyesno("Confirm Apply", msg):
			self.notebook.select(1) # Switch to log tab
			self.recompute_button.config(state=tk.DISABLED)
			self.apply_button.config(state=tk.DISABLED)
			
			self.root.after(100, self._execute_scaffold)

	# --- Helper Methods ---

	def _log(self, message: str, level: str = "info"):
		"""Appends a message to the log widget."""
		self.log_text.config(state=tk.NORMAL)
		
		# Simple colored logging
		tag = f"log_{level}"
		if not hasattr(self, tag):
			color = "black"
			if level == "error": color = "red"
			elif level == "warn": color = "#E59400"
			elif level == "success": color = "green"
			elif level == "skip": color = "gray"
			self.log_text.tag_configure(tag, foreground=color)
			setattr(self, tag, True)

		self.log_text.insert(tk.END, message + '\n', tag)
		self.log_text.see(tk.END)
		self.log_text.config(state=tk.DISABLED)
		self.root.update_idletasks()
		
	def _execute_scaffold(self):
		"""Performs the actual file and directory creation."""
		plan = self.current_plan
		is_dry_run = self.dry_run.get()

		self.log_text.config(state=tk.NORMAL)
		self.log_text.delete('1.0', tk.END)
		self.log_text.config(state=tk.DISABLED)
		
		self._log("="*60)
		if is_dry_run:
			self._log("Starting scaffold simulation (DRY RUN)...", "warn")
		else:
			self._log("Starting scaffold operation...", "info")
		self._log("="*60)

		stats = {"dirs_created": 0, "dirs_skipped": 0, "dirs_error": 0, "files_created": 0, "files_skipped": 0, "files_error": 0}

		# Create directories first
		for path in sorted(plan.planned_dirs, key=lambda p: len(p.parts)):
			if plan.path_states.get(path) == "new":
				ok, created, skipped = self._ensure_dir(path, is_dry_run)
				if ok:
					if created: stats["dirs_created"] += 1
					if skipped: stats["dirs_skipped"] += 1
				else:
					stats["dirs_error"] += 1
			elif plan.path_states.get(path) == "exists":
				self._log(f"[SKIP DIR]  {path}", "skip")
				stats["dirs_skipped"] += 1

		# Create files
		for path in sorted(plan.planned_files, key=lambda p: len(p.parts)):
			if plan.path_states.get(path) == "new":
				ok, created, skipped = self._ensure_file(path, is_dry_run)
				if ok:
					if created: stats["files_created"] += 1
					if skipped: stats["files_skipped"] += 1
				else:
					stats["files_error"] += 1
			elif plan.path_states.get(path) == "exists":
				self._log(f"[SKIP FILE] {path}", "skip")
				stats["files_skipped"] += 1
		
		self._log("\n" + "="*25 + " SUMMARY " + "="*26)
		self._log(f"- Dirs created: {stats['dirs_created']}, skipped: {stats['dirs_skipped']}, errors: {stats['dirs_error']}")
		self._log(f"- Files created: {stats['files_created']}, skipped: {stats['files_skipped']}, errors: {stats['files_error']}")
		
		if plan.duplicate_warnings or plan.similarity_warnings:
			self._log("\n--- Warnings ---", "warn")
			# This could be expanded to log the full warning details
			self._log(f"- Duplicate name warnings: {len(plan.duplicate_warnings)}", "warn")
			self._log(f"- Similar name warnings: {len(plan.similarity_warnings)}", "warn")

		self._log("="*60)
		if stats["dirs_error"] > 0 or stats["files_error"] > 0:
			self._log("Operation finished with errors.", "error")
		else:
			self._log("Operation finished successfully.", "success")
			
		# Finalize
		self.recompute_button.config(state=tk.NORMAL)
		self.on_recompute() # Refresh the view
		self.notebook.select(0) # Switch back to diff view


	def _ensure_dir(self, path: Path, dry_run: bool) -> tuple[bool, bool, bool]:
		"""(ok, created, skipped)"""
		if path.exists(): # Should not happen for 'new' items, but as a safeguard
			self._log(f"[SKIP DIR]  {path}", "skip")
			return True, False, True

		self._log(f"[MKDIR]     {path}", "info")
		if not dry_run:
			try:
				path.mkdir(parents=True, exist_ok=True)
			except Exception as e:
				self._log(f"[ERROR] mkdir failed: {path} | {e}", "error")
				return False, False, False
		return True, True, False

	def _ensure_file(self, path: Path, dry_run: bool) -> tuple[bool, bool, bool]:
		"""(ok, created, skipped)"""
		if path.exists(): # Safeguard
			self._log(f"[SKIP FILE] {path}", "skip")
			return True, False, True

		self._log(f"[CREATE]    {path}", "info")
		if not dry_run:
			try:
				path.parent.mkdir(parents=True, exist_ok=True)
				with path.open("xb"):
					pass
			except FileExistsError:
				self._log(f"[SKIP FILE] {path} (already exists)", "skip")
				return True, False, True
			except Exception as e:
				self._log(f"[ERROR] create file failed: {path} | {e}", "error")
				return False, False, False
		return True, True, False

	def _validate_path(self, path: str) -> tuple[bool, str]:
		"""Calls the external validator script and returns (is_valid, message)."""
		try:
			# Ensure python executable is the same one running this script
			python_exe = sys.executable
			# On Windows, prefer pythonw.exe to avoid console window
			if sys.platform == 'win32' and python_exe.endswith('python.exe'):
				python_exe = python_exe.replace("python.exe", "pythonw.exe")
			
			validator_script = Path(__file__).parent / "folder_selection_validator.py"
			
			if not validator_script.exists():
				return False, "folder_selection_validator.py not found in the script directory."

			# Set up subprocess arguments
			run_kwargs = {
				'capture_output': True,
				'text': True,
				'check': True
			}
			# Add Windows-specific flag to hide console window
			if sys.platform == 'win32':
				run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

			process = subprocess.run(
				[python_exe, str(validator_script), path],
				**run_kwargs
			)
			result = json.loads(process.stdout)
			
			if result["ok"]:
				return True, result["resolved_path"]
			else:
				error_message = "\n".join(result["errors"])
				return False, error_message

		except subprocess.CalledProcessError as e:
			return False, f"Validator script failed: {e.stderr}"
		except FileNotFoundError:
			return False, "Python executable or validator script not found."
		except json.JSONDecodeError:
			return False, f"Could not parse response from validator script: {process.stdout}"
		except Exception as e:
			return False, f"An unexpected error occurred during validation: {e}"

	def _clear_tree(self, tree: ttk.Treeview):
		"""Removes all items from a treeview."""
		for item in tree.get_children():
			tree.delete(item)

	def _populate_before_tree(self, root_path: Path):
		"""Fills the 'Before' treeview with the contents of the root_path."""
		self._clear_tree(self.before_tree)
		
		# Insert the root directory
		icon = self.classifier.classify_path(root_path)
		root_node = self.before_tree.insert("", "end", text=f"{icon} {root_path.name}", open=True, values=[str(root_path)])
		
		# Dictionary to keep track of parent nodes in the treeview
		dir_nodes = {str(root_path): root_node}
		
		all_paths = []
		try:
			# Security: prevent walking up from the root path
			for p in root_path.rglob('*'):
				all_paths.append(p)
		except Exception as e:
			messagebox.showerror("Error Reading Directory", f"Could not read the directory contents: {e}")
			return

		# Sort paths to ensure parents are created before children and consistent ordering
		all_paths.sort(key=lambda p: (len(p.parts), p.name.lower()))

		for path in all_paths:
			parent_path_str = str(path.parent)
			parent_node_id = dir_nodes.get(parent_path_str)
			
			if parent_node_id is None:
				continue

			icon = self.classifier.classify_path(path)
			if path.is_dir():
				node = self.before_tree.insert(parent_node_id, "end", text=f"{icon} {path.name}", open=False, values=[str(path)])
				dir_nodes[str(path)] = node
			else:
				self.before_tree.insert(parent_node_id, "end", text=f"{icon} {path.name}", values=[str(path)])

	def _populate_after_tree(self, plan: scaffold_core.Plan):
		"""Renders the generated plan in the 'After' treeview."""
		self._clear_tree(self.after_tree)
		root_path = plan.root_path

		# This dictionary will map a Path object to its corresponding treeview item ID.
		# It will contain all existing AND newly planned directories.
		dir_nodes = {}

		# Identify parent directories of 'new' items that are themselves existing.
		modified_parent_dirs = set()
		for p, state in plan.path_states.items():
			if state == 'new':
				current_parent = p.parent
				while current_parent != root_path and current_parent.is_relative_to(root_path):
					# Only mark as 'modified_parent' if it's an *existing* directory
					# and not itself marked as 'new' or 'conflict'
					if plan.path_states.get(current_parent) not in ('new', 'conflict_file', 'conflict_dir'):
						modified_parent_dirs.add(current_parent)
					current_parent = current_parent.parent

		# 1. Insert the root node
		icon = self.classifier.classify_path(root_path)
		root_node_id = self.after_tree.insert("", "end", text=f"{icon} {root_path.name}", open=True, values=[str(root_path)])
		dir_nodes[root_path] = root_node_id

		# 2. Get all directory paths: existing and planned
		all_dirs = set()
		# Add existing dirs
		try:
			for p in root_path.rglob('*'):
				if p.is_dir():
					all_dirs.add(p)
		except Exception:
			# Failsafe, though root should be readable
			pass
		# Add planned dirs
		for p in plan.planned_dirs:
			all_dirs.add(p)
			# Also add all parents of the planned dir so the tree can be built
			for parent in p.parents:
				if parent != root_path and parent.is_relative_to(root_path):
					all_dirs.add(parent)
				if parent == root_path:
					break

		# 3. Create all directory nodes in the treeview first
		sorted_dirs = sorted(list(all_dirs), key=lambda p: (len(p.parts), p.name.lower()))
		for dir_path in sorted_dirs:
			if dir_path == root_path:
				continue
			
			parent_id = dir_nodes.get(dir_path.parent)
			if not parent_id:
				continue

			tags = []
			state = plan.path_states.get(dir_path)
			if state == 'new':
				tags.append('new')
			elif state == 'conflict_file':
				tags.append('conflict')
			elif dir_path in modified_parent_dirs:
				tags.append('modified_parent')
			
			# 예정된 디렉토리이면 무조건 폴더 아이콘 사용
			if dir_path in plan.planned_dirs:
				icon = self.classifier.FOLDER_ICON
			else: # 실제 이미 존재하는 디렉토리라면 classify_path가 Path.is_dir()을 통해 폴더 아이콘 반환할 것임
				icon = self.classifier.classify_path(dir_path)
			
			node_id = self.after_tree.insert(parent_id, "end", text=f"{icon} {dir_path.name}", open=False, tags=tags, values=[str(dir_path)])
			dir_nodes[dir_path] = node_id

		# 4. Get all file paths: existing and planned
		all_files = set()
		# Add existing files
		try:
			for p in root_path.rglob('*'):
				if p.is_file():
					all_files.add(p)
		except Exception:
			pass
		# Add planned files
		for p in plan.planned_files:
			all_files.add(p)
		
		# 5. Insert all file nodes into the treeview
		sorted_files = sorted(list(all_files), key=lambda p: (len(p.parts), p.name.lower()))
		for file_path in sorted_files:
			parent_id = dir_nodes.get(file_path.parent)
			if not parent_id:
				continue
			
			tags = []
			state = plan.path_states.get(file_path)
			if state == 'new':
				tags.append('new')
			elif state == 'conflict_dir':
				tags.append('conflict')
			
			icon = self.classifier.classify_path(file_path)
			self.after_tree.insert(parent_id, "end", text=f"{icon} {file_path.name}", tags=tags, values=[str(file_path)])




def main():
	"""Main entry point for the GUI application."""
	try:
		root = tk.Tk()
		app = ScaffoldApp(root)
		root.mainloop()
	except Exception as e:
		messagebox.showerror("Fatal Error", f"An unhandled exception occurred: {e}")

if __name__ == "__main__":
	main()