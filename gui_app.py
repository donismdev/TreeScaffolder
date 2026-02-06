# -*- coding: utf-8 -*-
"""
gui_app.py

A Windows GUI application for scaffolding projects from a tree text description.
Provides a tree editor, safe folder selection, a before/after diff view,
and logging. Built with tkinter and ttk.
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font

from Scripts.Core import scaffold_core
import re
from Scripts.Utils import file_classifier
from Scripts.Core.v2_parser import V2ParserError

# --- Constants ---
APP_TITLE = "Tree Scaffolder v1.1"
LOG_DIR = "Log"
CONFIG_FILE = "config.json"
DEFAULT_GEOMETRY = "1200x700"
DEFAULT_TREE_TEMPLATE = """# =========================================================
# - Use @ROOT to define the logical root marker.
# - The first node must be that marker, ending with a '/'.
# - Indent with TABS or 4-SPACES.
# =========================================================

 @ROOT {{Root}}

{{Root}}/
"""

class ScaffoldApp:
	"""The main application class for the Tree Scaffolder GUI."""

	def __init__(self, root: tk.Tk):
		self.root = root
		self.root.title(APP_TITLE)
		self.root.geometry("1200x700") # Default size
		self.root.minsize(800, 600)
		self._load_window_geometry() # Load saved geometry, if any
		
		# --- Style Configuration ---
		self.style = ttk.Style()
		self.style.theme_use('vista')
		self.setup_styles()
		
		# --- Member Variables ---
		self.target_root_path = tk.StringVar()
		self.dry_run = tk.BooleanVar(value=True)
		self.enable_similarity_scan = tk.BooleanVar(value=True)
		self.similarity_threshold = tk.DoubleVar(value=0.86)
		self.last_root_path = None # Initialize member variable to store the last selected path
		
		# To be filled by the analysis
		self.current_plan: scaffold_core.Plan | None = None
		self.classifier = file_classifier.FileTypeClassifier()
		self.tree_text = None # Initialized in setup_left_panel
		self.source_code_text = None # Initialized in setup_left_panel
		self.content_text = None # Initialized in setup_left_panel
		self.before_list = None
		self.after_list = None

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
		self.after_tree.tag_configure('overwrite', foreground='#0078D7', font=font.Font(weight='bold'))

		# Configure Treeview tags for the after_list as well
		self.after_list.tag_configure('new', foreground='green')
		self.after_list.tag_configure('conflict', foreground='red', font=font.Font(weight='bold'))
		self.after_list.tag_configure('warning', foreground='#E59400')
		self.after_list.tag_configure('modified_parent', foreground='#DAA520')
		self.after_list.tag_configure('overwrite', foreground='#0078D7', font=font.Font(weight='bold'))

		# Bind window close event to save geometry
		self.root.bind("<Destroy>", lambda event: self._save_window_geometry())

		# Load last root path and update UI elements
		self._load_last_root_path() # New call

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
		# Removed: folder_frame.columnconfigure(0, weight=1)
		
		path_buttons_frame = ttk.Frame(folder_frame)
		path_buttons_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
		path_buttons_frame.columnconfigure(1, weight=1) # Empty column to push buttons right

		self.folder_label = ttk.Label(path_buttons_frame, textvariable=self.target_root_path, relief="sunken", padding=3, width=50) # Fixed width
		self.target_root_path.set("No folder selected.")
		self.folder_label.grid(row=0, column=0, sticky="w", padx=(0, 5)) # Left-aligned, no expansion
		
		self.browse_button = ttk.Button(path_buttons_frame, text="Browse...", command=self.on_browse_folder, width=8)
		self.browse_button.grid(row=0, column=2, padx=(0, 5))

		self.prev_dir_button = ttk.Button(path_buttons_frame, text="Prev", command=self.on_previous_folder, width=5, state=tk.DISABLED)
		self.prev_dir_button.grid(row=0, column=3, padx=(0, 5))

		self.clear_button = ttk.Button(path_buttons_frame, text="Clear", command=self.on_clear_data, width=5)
		self.clear_button.grid(row=0, column=4)

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
		
		self.tree_text.insert("1.0", DEFAULT_TREE_TEMPLATE)

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

		self.load_test_data_button = ttk.Button(actions_subframe, text="Load Test Data", command=self.on_load_test_data)
		self.load_test_data_button.grid(row=1, column=0, columnspan=2, padx=2, pady=(5,0), sticky="ew")

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

		# --- Before Pane ---
		before_pane_frame = ttk.LabelFrame(diff_paned, text="Before (Current State)")
		before_pane_frame.rowconfigure(0, weight=1)
		before_pane_frame.columnconfigure(0, weight=1)
		diff_paned.add(before_pane_frame, weight=1)

		before_notebook = ttk.Notebook(before_pane_frame)
		before_notebook.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
		
		before_tree_frame = ttk.Frame(before_notebook)
		before_tree_frame.rowconfigure(0, weight=1)
		before_tree_frame.columnconfigure(0, weight=1)
		self.before_tree = self.create_treeview(before_tree_frame, show="tree")
		before_notebook.add(before_tree_frame, text="Tree")
		
		before_list_frame = ttk.Frame(before_notebook)
		before_list_frame.rowconfigure(0, weight=1)
		before_list_frame.columnconfigure(0, weight=1)
		self.before_list = self.create_treeview(before_list_frame, show="tree") # Keep 'tree' for icons
		before_notebook.add(before_list_frame, text="List")

		# --- After Pane ---
		after_pane_frame = ttk.LabelFrame(diff_paned, text="After (Planned State)")
		after_pane_frame.rowconfigure(0, weight=1)
		after_pane_frame.columnconfigure(0, weight=1)
		diff_paned.add(after_pane_frame, weight=1)
		
		after_notebook = ttk.Notebook(after_pane_frame)
		after_notebook.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

		after_tree_frame = ttk.Frame(after_notebook)
		after_tree_frame.rowconfigure(0, weight=1)
		after_tree_frame.columnconfigure(0, weight=1)
		self.after_tree = self.create_treeview(after_tree_frame, show="tree")
		after_notebook.add(after_tree_frame, text="Tree")

		after_list_frame = ttk.Frame(after_notebook)
		after_list_frame.rowconfigure(0, weight=1)
		after_list_frame.columnconfigure(0, weight=1)
		self.after_list = self.create_treeview(after_list_frame, show="tree") # Keep 'tree' for icons
		after_notebook.add(after_list_frame, text="Apply Tree")

		# Bind selection event
		self.before_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
		self.after_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
		self.before_list.bind("<<TreeviewSelect>>", self.on_tree_select)
		self.after_list.bind("<<TreeviewSelect>>", self.on_tree_select)

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
	
	def create_treeview(self, parent: ttk.Frame, show: str = "tree") -> ttk.Treeview:
		"""Helper to create and configure a Treeview widget."""
		tree = ttk.Treeview(parent, show=show)
		tree.grid(row=0, column=0, sticky="nsew")
		
		scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
		scrollbar.grid(row=0, column=1, sticky="ns")
		tree.config(yscrollcommand=scrollbar.set)
		
		return tree
		
	# --- Event Handlers ---

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
			self._clear_tree(self.before_list)
			self._clear_tree(self.after_list)
		else:
			self.target_root_path.set(message) # message is the resolved path on success
			self._save_last_root_path(message) # Save the successfully selected path
			self.recompute_button.config(state=tk.NORMAL)
			self._populate_before_tree(Path(message))
			self._clear_tree(self.after_tree)
			self._clear_tree(self.after_list)
			self.apply_button.config(state=tk.DISABLED)


	def on_recompute(self):
		"""Handles the 'Recompute Diff' button click."""
		root_path_str = self.target_root_path.get()
		if not root_path_str or not Path(root_path_str).is_dir():
			messagebox.showerror("Error", "Please select a valid root folder first.")
			return

		root_path = Path(root_path_str)
		
		tree_input = self.tree_text.get("1.0", "end-1c")
		source_code_input = self.source_code_text.get("1.0", "end-1c")
		
		# Combine the inputs as expected by scaffold_core.generate_plan
		# The core logic expects the tree definition and then potentially content blocks
		# if the source code tab is used for defining content.
		# A simple concatenation should work if the format expects it.
		text_input = tree_input + "\n" + source_code_input

		if not text_input.strip():
			messagebox.showinfo("Info", "Both the Scaffold Tree and Source Code editors are empty. Nothing to compute.")
			return

		config = {
			"DRY_RUN": self.dry_run.get(),
			"ENABLE_SIMILARITY_SCAN": self.enable_similarity_scan.get(),
			"SIMILARITY_RATIO_THRESHOLD": self.similarity_threshold.get(),
			"NORMALIZE_LOWER": True,
			"NORMALIZE_REMOVE_NONALNUM": True,
			"SCAN_INCLUDE_EXTENSIONS": {
				".h", ".hpp", ".cpp", ".c", ".cs",
				".Build.cs", ".Target.cs", ".uproject", ".uplugin"
			}
		}

		# --- Unified Planning ---
		self.current_plan = scaffold_core.generate_plan(root_path, text_input, config)
		
		# --- Logging ---
		self.log_text.config(state=tk.NORMAL)
		self.log_text.delete('1.0', tk.END)
		self.log_text.config(state=tk.DISABLED)

		if self.current_plan.errors:
			self._log("Plan generation finished with errors:", "error")
			for err in self.current_plan.errors:
				self._log(f"- {err}", "error")
			messagebox.showerror("Planning Error", f"Errors found during planning:\n\n{self.current_plan.errors[0]}")
		else:
			self._log("Plan generated successfully.", "success")
			num_new_dirs = len([p for p, s in self.current_plan.path_states.items() if s == 'new' and p in self.current_plan.planned_dirs])
			num_new_files = len([p for p, s in self.current_plan.path_states.items() if s == 'new' and p in self.current_plan.planned_files])
			num_overwrite_files = len([s for s in self.current_plan.path_states.values() if s == 'overwrite'])
			self._log(f"- Planned new directories: {num_new_dirs}", "info")
			self._log(f"- Planned new files: {num_new_files}", "info")
			self._log(f"- Planned overwritten files: {num_overwrite_files}", "info")

		# Log migration warnings if any
		if self.current_plan.migration_warnings:
			self._log("Content migration warnings:", "warn")
			for warn in self.current_plan.migration_warnings:
				self._log(f"- {warn}", "warn")

		# --- UI Updates ---
		self._populate_before_tree(root_path)
		self._populate_after_tree(self.current_plan)

		if self.current_plan.has_conflicts:
			messagebox.showwarning("Conflicts Found", "Path conflicts were detected. 'Apply' is disabled.\nCheck the 'After' view for items marked in red.")
			self.apply_button.config(state=tk.DISABLED)
		elif not self.current_plan.errors:
			self.apply_button.config(state=tk.NORMAL)
			self.notebook.select(0) # Switch to diff view
		else:
			self.apply_button.config(state=tk.DISABLED)


	def on_apply(self):
		"""Handles the 'Apply Scaffold' button click."""
		if not self.current_plan or self.current_plan.has_conflicts:
			messagebox.showerror("Cannot Apply", "There is no valid plan to apply, or the plan has conflicts. Please recompute.")
			return

		is_dry_run = self.dry_run.get()
		num_new_files = len([p for p, s in self.current_plan.path_states.items() if s == 'new' and p in self.current_plan.planned_files])
		num_overwrite_files = len([p for p, s in self.current_plan.path_states.items() if s == 'overwrite'])
		num_dirs = len([p for p, s in self.current_plan.path_states.items() if s == 'new' and p in self.current_plan.planned_dirs])

		dialog_icon = messagebox.INFO # Default blue 'i'
		dialog_title = "Confirm Apply"

		if is_dry_run:
			msg = "This is a DRY RUN. No files will be written.\n\n"
			msg += f"Action Summary:\n- Create: {num_dirs} directories, {num_new_files} files\n- Overwrite: {num_overwrite_files} files\n\n"
			msg += "Proceed with logging the simulation?"
			dialog_icon = messagebox.WARNING # Red exclamation mark
			dialog_title = "Confirm Apply (DRY RUN)"
		else:
			msg = f"This will create {num_dirs} directories, create {num_new_files} files, and overwrite {num_overwrite_files} files.\n\n"
			msg += "Are you sure you want to proceed?"

		if messagebox.askyesno(dialog_title, msg, icon=dialog_icon):
			# Add an additional confirmation for overwrites if not in dry run
			if not is_dry_run and num_overwrite_files > 0:
				overwrite_msg = f"WARNING: {num_overwrite_files} existing file(s) will be OVERWRITTEN.\nThis action cannot be undone.\n\nAre you absolutely sure you want to proceed?"
				if not messagebox.askyesno("Confirm Overwrite", overwrite_msg, icon=messagebox.WARNING):
					return # User cancelled the overwrite confirmation
				
			self.notebook.select(1) # Switch to log tab
			self.recompute_button.config(state=tk.DISABLED)
			self.apply_button.config(state=tk.DISABLED)
			
			self.root.after(100, self._execute_scaffold)

	def on_tree_select(self, event: tk.Event):
		"""Handles selection changes in either the 'Before' or 'After' tree."""
		widget = event.widget
		selection = widget.selection()
		if not selection:
			return

		item_id = selection[0]
		values = widget.item(item_id, "values")
		if not values:
			return # Should not happen for file/dir items
			
		path_str = values[0]
		path = Path(path_str)

		content_to_show = ""
		source_info = ""

		try:
			# Determine if this is a directory
			is_dir = path.is_dir()
			if widget == self.after_tree and not is_dir:
				if self.current_plan and self.current_plan.path_states.get(path) in ("new", "overwrite"):
					is_dir = path in self.current_plan.planned_dirs
				else: # Fallback for existing items in after tree
					is_dir = path.is_dir()
			
			if is_dir:
				self.content_text.delete("1.0", tk.END)
				self.content_text.insert("1.0", f"Directory selected:\n{path}")
				self.editor_notebook.select(2) # Switch to Content tab
				return

			# It's a file, determine which tree and get content
			if widget == self.after_tree and self.current_plan:
				# For "After" tree, content might be in the plan
				planned_content = self.current_plan.file_contents.get(path.resolve()) # Use resolve() for lookup
				if planned_content is not None:
					content_to_show = planned_content
					source_info = f"--- PLANNED CONTENT (PREVIEW) ---\nFile: {path}\n"
				elif path.exists():
					content_to_show = path.read_text(encoding='utf-8', errors='replace')
					source_info = f"--- EXISTING CONTENT ---\nFile: {path}\n"
				else: # New, empty file from tree scaffold
					content_to_show = ""
					source_info = f"--- NEW EMPTY FILE (PLANNED) ---\nFile: {path}\n"
			else: # "Before" tree or no plan
				if path.exists():
					content_to_show = path.read_text(encoding='utf-8', errors='replace')
					source_info = f"--- CURRENT CONTENT ---\nFile: {path}\n"
				else:
					# This can happen if file was deleted after 'before' tree was populated
					content_to_show = ""
					source_info = f"--- FILE NOT FOUND ---\nFile: {path}\n"

		except Exception as e:
			content_to_show = f"Error reading file content:\n{e}"

		# Update the content view
		self.content_text.delete("1.0", tk.END)
		self.content_text.insert("1.0", source_info + "="*40 + "\n" + content_to_show)
		self.editor_notebook.select(2) # Switch to Content tab

	def on_load_test_data(self):
		"""Loads content from test_tree.txt and test_data.txt into respective editors."""
		test_tree_path = Path("test_tree.txt")
		test_data_path = Path("test_data.txt")

		try:
			# Load test_tree.txt into Scaffold Tree view
			if test_tree_path.exists():
				with open(test_tree_path, "r", encoding="utf-8") as f:
					tree_content = f.read()
				self.tree_text.delete("1.0", tk.END)
				self.tree_text.insert("1.0", tree_content)
				self._log(f"Loaded '{test_tree_path}' into Scaffold Tree.", "info")
			else:
				messagebox.showwarning("File Not Found", f"'{test_tree_path}' not found in the current directory.")
				self._log(f"Warning: '{test_tree_path}' not found.", "warn")

			# Load test_data.txt into Source Code view
			if test_data_path.exists():
				with open(test_data_path, "r", encoding="utf-8") as f:
					data_content = f.read()
				self.source_code_text.delete("1.0", tk.END)
				self.source_code_text.insert("1.0", data_content)
				self._log(f"Loaded '{test_data_path}' into Source Code.", "info")
			else:
				messagebox.showwarning("File Not Found", f"'{test_data_path}' not found in the current directory.")
				self._log(f"Warning: '{test_data_path}' not found.", "warn")

		except Exception as e:
			messagebox.showerror("Error Loading Data", f"An error occurred while loading test data: {e}")
			self._log(f"Error loading test data: {e}", "error")

	def on_clear_data(self):
		"""Handles the 'Clear' button click to reset runtime data."""
		self._log("Clearing all editor content and planned data...", "info")

		# Reset configuration variables to defaults
		self.dry_run.set(True)
		self.enable_similarity_scan.set(True)
		self.similarity_threshold.set(0.86)

		# Clear text editors and reset to default template for tree_text
		self.tree_text.delete("1.0", tk.END)
		self.tree_text.insert("1.0", DEFAULT_TREE_TEMPLATE)
		self.source_code_text.delete("1.0", tk.END)
		self.content_text.delete("1.0", tk.END)

		# Clear internal plan data
		self.current_plan = None

		# Clear Treeview widgets
		self._clear_tree(self.before_tree)
		self._clear_tree(self.after_tree)
		self._clear_tree(self.before_list)
		self._clear_tree(self.after_list)

		# Disable action buttons
		self.recompute_button.config(state=tk.DISABLED)
		self.apply_button.config(state=tk.DISABLED)

		self._log("Runtime data cleared.", "info")

	# --- Helper Methods ---

	def _load_window_geometry(self):
		"""Loads window geometry from config.json if available, with validation."""
		config_path = Path.cwd() / CONFIG_FILE
		loaded_geometry = None

		if config_path.exists():
			try:
				with open(config_path, "r", encoding="utf-8") as f:
					config = json.load(f)
					if "geometry" in config:
						loaded_geometry = config["geometry"]
			except Exception as e:
				print(f"Error loading window geometry from config: {e}")

		if loaded_geometry:
			try:
				# Geometry format: "WxH+X+Y"
				match = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", loaded_geometry)
				if match:
					width, height, x, y = map(int, match.groups())
					
					# Basic validation: ensure dimensions are not too small and position is not extremely off-screen
					min_width, min_height = 300, 200 # A reasonable minimum size
					max_negative_coord = -1000 # Allow some negative coords for multi-monitor setups

					if width >= min_width and height >= min_height and x > max_negative_coord and y > max_negative_coord:
						self.root.geometry(loaded_geometry)
					else:
						print(f"Loaded geometry '{loaded_geometry}' failed validation. Using default.")
						self.root.geometry(DEFAULT_GEOMETRY)
				else:
					print(f"Loaded geometry string '{loaded_geometry}' has invalid format. Using default.")
					self.root.geometry(DEFAULT_GEOMETRY)
			except Exception as e:
				print(f"Error parsing loaded geometry '{loaded_geometry}': {e}. Using default.")
				self.root.geometry(DEFAULT_GEOMETRY)
		else:
			# If no geometry was loaded or file didn't exist, ensure default is applied
			self.root.geometry(DEFAULT_GEOMETRY)


	def _save_window_geometry(self):
		"""Saves current window geometry to config.json."""
		config_path = Path.cwd() / CONFIG_FILE
		try:
			config = {}
			if config_path.exists():
				with open(config_path, "r", encoding="utf-8") as f:
					config = json.load(f)
			
			config["geometry"] = self.root.geometry()
			
			with open(config_path, "w", encoding="utf-8") as f:
				json.dump(config, f, indent=4)
		except Exception as e:
			print(f"Error saving window geometry: {e}") # Print to console as GUI might be closing

	def _load_last_root_path(self):
		"""Loads the last selected root path from config.json and updates UI."""
		config_path = Path.cwd() / CONFIG_FILE
		self.last_root_path = None

		if config_path.exists():
			try:
				with open(config_path, "r", encoding="utf-8") as f:
					config = json.load(f)
					if "last_root_path" in config:
						path_str = config["last_root_path"]
						if Path(path_str).is_dir(): # Only load if it's a valid directory
							self.last_root_path = path_str
			except Exception as e:
				print(f"Error loading last root path from config: {e}")
		
		# Update button state based on whether a valid last path was loaded
		if self.last_root_path:
			self.prev_dir_button.config(state=tk.NORMAL)
		else:
			self.prev_dir_button.config(state=tk.DISABLED)

	def _save_last_root_path(self, path: str):
		"""Saves the given path as the last selected root path to config.json."""
		config_path = Path.cwd() / CONFIG_FILE
		try:
			config = {}
			if config_path.exists():
				with open(config_path, "r", encoding="utf-8") as f:
					config = json.load(f)
			
			config["last_root_path"] = path
			
			with open(config_path, "w", encoding="utf-8") as f:
				json.dump(config, f, indent=4)
			self.last_root_path = path # Update internal state
			self.prev_dir_button.config(state=tk.NORMAL) # Enable button
		except Exception as e:
			print(f"Error saving last root path: {e}")

	def on_previous_folder(self):
		"""Handles the 'Prev' button click to use the last selected folder."""
		if self.last_root_path and Path(self.last_root_path).is_dir():
			# Validate the path first, similar to on_browse_folder
			is_valid, message = self._validate_path(self.last_root_path)
			if is_valid:
				self.target_root_path.set(message)
				self.recompute_button.config(state=tk.NORMAL)
				self._populate_before_tree(Path(message))
				self._clear_tree(self.after_tree)
				self.apply_button.config(state=tk.DISABLED)
			else:
				messagebox.showerror("Invalid Folder", f"The previously saved folder is no longer valid: {message}")
				self.last_root_path = None # Clear invalid path
				self.prev_dir_button.config(state=tk.DISABLED)
				self.target_root_path.set("No folder selected.")
				self.recompute_button.config(state=tk.DISABLED)
				self._clear_tree(self.before_tree)
				self._clear_tree(self.after_tree)
		else:
			self.prev_dir_button.config(state=tk.DISABLED)
			messagebox.showinfo("No Previous Folder", "No valid previous folder found.")

	def _write_execution_log(self, stats: dict, is_dry_run: bool, captured_logs: list):
		"""Writes a comprehensive execution log to a timestamped file."""
		log_path = Path.cwd() / LOG_DIR
		log_path.mkdir(exist_ok=True)

		timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		log_filename = log_path / f"scaffold_execution_{timestamp}.log"

		tree_content = self.tree_text.get("1.0", tk.END).strip()
		source_content = self.source_code_text.get("1.0", tk.END).strip()

		summary_header = (
			f"{'DRY RUN' if is_dry_run else 'EXECUTION'} SUMMARY\n"
			f"New Directories: {stats['dirs_created']}\n"
			f"New Files: {stats['files_created']}\n"
			f"Overwritten Files: {stats['files_overwritten']}\n"
			f"Directory Errors: {stats['dirs_error']}\n"
			f"File Errors: {stats['files_error']}\n"
		)

		log_entries = [
			f"Execution Log - {datetime.datetime.now().isoformat()}",
			"=" * 80,
			summary_header,
			"=" * 80,
			"\n--- detail ---\n",
		]

		# Add captured raw logs
		for message, level in captured_logs:
			log_entries.append(f"[{level.upper()}] {message}")
			
		# Add original input content for context
		log_entries.extend([
			"\n" + "=" * 80,
			"Scaffold Tree Content (Input):",
			"=" * 80,
			tree_content,
			"",
			"=" * 80,
			"Source Code Content (Input):",
			"=" * 80,
			source_content,
			"=" * 80,
		])

		try:
			with open(log_filename, "w", encoding="utf-8") as f:
				f.write("\n".join(log_entries))
			# This log message now goes to the GUI buffer
			self._log(f"Execution details logged to: {log_filename}", "info")
		except Exception as e:
			self._log(f"Error writing execution log: {e}", "error")

	def _log(self, message: str, level: str = "info", buffer_list: list = None):
		"""Appends a message to the log widget or a buffer list."""
		if buffer_list is not None:
			buffer_list.append((message, level))
			return

		self.log_text.config(state=tk.NORMAL)
		
		# Simple colored logging
		tag = f"log_{level}"
		if not hasattr(self, f"configured_{tag}"): # Check if tag is already configured
			color = "black"
			if level == "error": color = "red"
			elif level == "warn": color = "#E59400"
			elif level == "success": color = "green"
			elif level == "skip": color = "gray"
			self.log_text.tag_configure(tag, foreground=color)
			# Store the fact that this tag has been configured
			setattr(self, f"configured_{tag}", True) 

		self.log_text.insert(tk.END, message + '\n', tag)
		self.log_text.see(tk.END)
		self.log_text.config(state=tk.DISABLED)
		self.root.update_idletasks()
		
	def _execute_scaffold(self):
		"""Performs the actual file and directory creation."""
		plan = self.current_plan
		is_dry_run = self.dry_run.get()

		# Create a buffer to capture logs temporarily
		captured_logs = []
		
		# Store the original _log method and temporarily override it
		original_log_method = self._log
		# All calls to self._log within this function will now append to captured_logs
		self._log = lambda msg, level="info": original_log_method(msg, level, buffer_list=captured_logs)

		self._log("="*60)
		
		if is_dry_run:
			self._log("Starting scaffold simulation (DRY RUN)...", "warn")
		else:
			self._log("Starting scaffold operation...", "info")
		
		# Calculate total lines of content that will be written
		total_content_lines = sum(len(content.splitlines()) for content in plan.file_contents.values())

		# Log a brief summary of what is about to happen
		num_planned_new_dirs = len([p for p in plan.planned_dirs if plan.path_states.get(p) == 'new'])
		num_planned_new_files = len([p for p in plan.planned_files if plan.path_states.get(p) == 'new'])
		num_planned_overwrite_files = len([p for p in plan.planned_files if plan.path_states.get(p) == 'overwrite'])

		self._log(f"\nPlanned Actions Summary:")
		self._log(f"- New directories: {num_planned_new_dirs}")
		self._log(f"- New files: {num_planned_new_files}")
		self._log(f"- Overwritten files: {num_planned_overwrite_files}")
		self._log(f"- Total lines of content to be written: {total_content_lines} lines")

		self._log("="*60)

		stats = {"dirs_created": 0, "dirs_skipped": 0, "dirs_error": 0, "files_created": 0, "files_overwritten": 0, "files_skipped": 0, "files_error": 0}

		# Create directories first
		# Sorting ensures parent directories are created before children
		for path in sorted(list(plan.planned_dirs), key=lambda p: len(p.parts)):
			state = plan.path_states.get(path)
			if state == "new":
				ok, created, skipped = self._ensure_dir(path, is_dry_run)
				if ok:
					if created: stats["dirs_created"] += 1
					if skipped: stats["dirs_skipped"] += 1
				else:
					stats["dirs_error"] += 1
			elif state == "exists":
				self._log(f"[SKIP DIR]  {path}", "skip")
				stats["dirs_skipped"] += 1

		# Create/overwrite files
		for path in sorted(list(plan.planned_files), key=lambda p: len(p.parts)):
			state = plan.path_states.get(path)
			content = plan.file_contents.get(path.resolve()) # Use resolve() for lookup

			if state == "new" or state == "overwrite":
				is_overwrite = state == "overwrite"
				ok, created, skipped = self._ensure_file(path, is_dry_run, content, is_overwrite)
				if ok:
					if created and not is_overwrite: stats["files_created"] += 1
					if created and is_overwrite: stats["files_overwritten"] += 1
					if skipped: stats["files_skipped"] += 1
				else:
					stats["files_error"] += 1
			elif state == "exists":
				self._log(f"[SKIP FILE] {path}", "skip")
				stats["files_skipped"] += 1
		
		self._log("\n" + "="*25 + " SUMMARY " + "="*26)
		self._log(f"- Dirs created: {stats['dirs_created']}, skipped: {stats['dirs_skipped']}, errors: {stats['dirs_error']}")
		self._log(f"- Files created: {stats['files_created']}, overwritten: {stats['files_overwritten']}, skipped: {stats['files_skipped']}, errors: {stats['files_error']}")
		
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

		# Write the comprehensive file log before assembling the GUI log
		self._write_execution_log(stats, is_dry_run, captured_logs)
			
		# --- Final Log Assembly ---
		# Restore the original _log method to write to the widget directly
		self._log = original_log_method

		self.log_text.config(state=tk.NORMAL)
		self.log_text.delete("1.0", tk.END) # Clear the log widget for final output
		
		summary_header = (
			f"{'DRY RUN' if is_dry_run else 'EXECUTION'} SUMMARY\n"
			f"New Directories: {stats['dirs_created']}\n"
			f"New Files: {stats['files_created']}\n"
			f"Overwritten Files: {stats['files_overwritten']}\n"
		)
		
		# Insert the summary header and separator
		self._log(summary_header, "info")
		self._log("\n--- detail ---\n")

		# Insert all captured detailed logs, applying original tags
		for message, level in captured_logs:
			self._log(message, level)
		
		self.log_text.config(state=tk.DISABLED)
			
		# Finalize
		self.recompute_button.config(state=tk.NORMAL)
		self.apply_button.config(state=tk.NORMAL if plan and not plan.has_conflicts else tk.DISABLED)
		self._populate_before_tree(plan.root_path) # Refresh the 'before' view
		self._populate_after_tree(plan) # Refresh the 'after' view with the same plan
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

	def _ensure_file(self, path: Path, dry_run: bool, content: str | None, is_overwrite: bool) -> tuple[bool, bool, bool]:
		"""(ok, created, skipped)"""
		verb = "[OVERWRITE]" if is_overwrite else "[CREATE]"
		
		# Safeguard: if we think we're creating, but it exists, log as skip.
		if not is_overwrite and path.exists():
			self._log(f"[SKIP FILE] {path} (already exists)", "skip")
			return True, False, True

		log_level = "info" if content is not None else "success" # Different color for content files
		self._log(f"{verb:<11} {path}", log_level)

		if not dry_run:
			try:
				# Ensure parent directory exists first
				path.parent.mkdir(parents=True, exist_ok=True)
				# Open with "w" to create or overwrite.
				# Use write_text for simplicity and correct encoding.
				path.write_text(content or "", encoding='utf-8')
				
				# --- Hardcoded fix for the "2 newlines" bug (verbatim content post-processing) ---
				# This section is specifically to address the user report that sometimes an extra newline
				# appears in the final file output, even when the content written is identical.
				# It is implemented to preserve the exact verbatim content from the parser,
				# as requested by the user, while correcting for platform-specific implicit newline additions.
				#
				# DO NOT REMOVE. This is critical for the ".md 파일의 ### 블록 내용 처리 (Verbatim) 처리용"
				# to ensure the final file on disk is perfectly identical to the parsed content,
				# especially addressing the "\n 2줄 생기는 버그" (2 newlines appearing bug).
				try:
					# Read the file back in binary mode to accurately check line endings
					written_binary_content = path.read_bytes()
					# Convert original content to binary to compare line endings
					original_binary_content = (content or "").encode('utf-8')

					# Determine if an extra newline (LF or CRLF) was implicitly added
					extra_newline_added = False
					
					if written_binary_content.endswith(b'\r\n') and not original_binary_content.endswith(b'\r\n'):
						# File ends with CRLF, but original content did not.
						# This means an extra CRLF was added.
						extra_newline_added = True
						truncate_bytes = 2 # For CRLF
					elif written_binary_content.endswith(b'\n') and not original_binary_content.endswith(b'\n'):
						# File ends with LF, but original content did not (and also not CRLF).
						# This means an extra LF was added.
						extra_newline_added = True
						truncate_bytes = 1 # For LF
					
					if extra_newline_added:
						# Truncate the file to remove the implicitly added newline
						with open(path, 'wb') as f:
							f.write(written_binary_content[:-truncate_bytes])
						self._log(f"[FIX] Hardcoded: Removed implicit extra newline from {path}", "warn")

				except Exception as fix_e:
					self._log(f"[ERROR] Hardcoded newline fix failed for {path}: {fix_e}", "error")
				# --- End hardcoded fix ---
			except Exception as e:
				self._log(f"[ERROR] write file failed: {path} | {e}", "error")
				return False, False, False
		return True, True, False

	def _validate_path(self, path: str) -> tuple[bool, str]:
		"""Calls the external validator script and returns (is_valid, message)."""
		process = None
		try:
			# Ensure python executable is the same one running this script
			python_exe = sys.executable
			# On Windows, prefer pythonw.exe to avoid console window
			if sys.platform == 'win32' and python_exe.endswith('python.exe'):
				python_exe = python_exe.replace("python.exe", "pythonw.exe")
			
			validator_script = Path(__file__).parent / "Scripts" / "Utils" / "folder_selection_validator.py"
			
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
		except json.JSONDecodeError as e:
			stdout_str = process.stdout if (process and process.stdout) else "(no output)"
			return False, f"Could not parse response from validator script. Output: {stdout_str}. Error: {str(e)}"
		except Exception as e:
			return False, f"An unexpected error occurred during validation: {e}"

	def _clear_tree(self, tree: ttk.Treeview):
		"""Removes all items from a treeview."""
		for item in tree.get_children():
			tree.delete(item)

	def _populate_before_tree(self, root_path: Path):
		"""Fills the 'Before' treeview with the contents of the root_path."""
		self._clear_tree(self.before_tree)
		self._clear_tree(self.before_list)
		
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
			# Populate Tree View
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
				# Populate List View (only files)
				relative_path = path.relative_to(root_path)
				self.before_list.insert("", "end", text=f"{icon} {relative_path}", values=[str(path)])

	def _populate_after_tree(self, plan: scaffold_core.Plan):
		"""Renders the generated plan in the 'After' treeview and listview."""
		self._clear_tree(self.after_tree)
		self._clear_tree(self.after_list)
		if not plan:
			return
		root_path = plan.root_path

		# Calculate modified parent directories (for coloring)
		# This needs to be done once before populating both treeviews
		modified_parent_dirs = set()
		all_relevant_planned_paths = plan.planned_dirs.union(plan.planned_files)
		for p in all_relevant_planned_paths:
			state = plan.path_states.get(p)
			if state in ('new', 'overwrite', 'conflict_file', 'conflict_dir'):
				current_parent = p.parent
				while current_parent != root_path and current_parent.is_relative_to(root_path):
					# If parent itself is not directly a new/overwrite/conflict, but contains one, mark it.
					if plan.path_states.get(current_parent) not in ('new', 'conflict_file', 'conflict_dir', 'exists'): # Also include 'exists' to not override explicit states
						modified_parent_dirs.add(current_parent)
					current_parent = current_parent.parent


		# Populate the main 'After (Planned State)' tree
		self._populate_treeview_from_plan(self.after_tree, plan, root_path, 
										  lambda p, plan_obj, mpd: True, modified_parent_dirs, auto_open_modified=True)
		
		# Populate the 'Apply Tree' (after_list)
		self._populate_treeview_from_plan(self.after_list, plan, root_path, 
										  lambda p, plan_obj, mpd: plan_obj.path_states.get(p) in ('new', 'overwrite', 'conflict_file', 'conflict_dir') or p in mpd, modified_parent_dirs, auto_open_modified=True)


	def _populate_treeview_from_plan(self, tree_widget: ttk.Treeview, plan_obj: scaffold_core.Plan, root_path_param: Path, filter_func, modified_parent_dirs: set, auto_open_modified: bool):
		dir_nodes = {}

		# 1. Insert the root node
		icon = self.classifier.classify_path(root_path_param)
		root_node_id = tree_widget.insert("", "end", text=f"{icon} {root_path_param.name}", open=True, values=[str(root_path_param)])
		dir_nodes[root_path_param] = root_node_id

		# Gather all relevant paths (directories and files) from the plan and filesystem
		all_paths_to_consider = set(plan_obj.planned_dirs).union(plan_obj.planned_files)
		try:
			for p in root_path_param.rglob('*'):
				all_paths_to_consider.add(p)
		except Exception:
			pass # Ignore filesystem errors

		# Sort paths to ensure parents are processed before children
		sorted_paths = sorted(list(all_paths_to_consider), key=lambda p: (len(p.parts), p.name.lower()))
		
		# Filtered set of paths that actually get inserted into the treeview
		inserted_paths = set()

		for path in sorted_paths:
			# Skip root, already handled
			if path == root_path_param:
				continue
			
			# Determine if this path should be included based on the filter
			should_include = filter_func(path, plan_obj, modified_parent_dirs)

			if should_include:
				# Ensure all ancestors of this 'should_include' path are in the treeview and opened
				ancestors_to_process = []
				p_check = path.parent
				while p_check != root_path_param:
					if p_check in dir_nodes: # Found an ancestor already in our map, break and process collected ancestors
						break
					ancestors_to_process.append(p_check)
					p_check = p_check.parent
				ancestors_to_process.reverse() # Process from root towards child

				for ancestor_path in ancestors_to_process:
					parent_of_ancestor_id = dir_nodes.get(ancestor_path.parent)
					if parent_of_ancestor_id is None:
						parent_of_ancestor_id = root_node_id # Fallback to root if parent not yet processed

					intermediate_icon = self.classifier.classify_path(ancestor_path, is_planned_dir=ancestor_path.is_dir() or ancestor_path in plan_obj.planned_dirs)
					intermediate_tags = []
					# Tagging parents if they contain modified items
					if ancestor_path in modified_parent_dirs:
						intermediate_tags.append('modified_parent')
					
					# If ancestor not in dir_nodes, insert it, always opened if auto_open_modified
					if ancestor_path not in dir_nodes:
						node = tree_widget.insert(parent_of_ancestor_id, "end", text=f"{intermediate_icon} {ancestor_path.name}", open=auto_open_modified, tags=intermediate_tags, values=[str(ancestor_path)])
						dir_nodes[ancestor_path] = node
					else: # If ancestor already exists, ensure it's open if auto_open_modified
						if auto_open_modified:
							tree_widget.item(dir_nodes[ancestor_path], open=True)
				
				# After ensuring all ancestors are inserted/opened, insert the actual item
				parent_node_id = dir_nodes.get(path.parent)
				if not parent_node_id:
					parent_node_id = root_node_id # Should not happen with the ancestor processing above, but for safety

				tags = []
				state = plan_obj.path_states.get(path)
				if state == 'new': tags.append('new')
				elif state == 'overwrite': tags.append('overwrite')
				elif state == 'conflict_file': tags.append('conflict')
				elif state == 'conflict_dir': tags.append('conflict')
				# Apply modified_parent tag if applicable to the item itself
				if path in modified_parent_dirs: tags.append('modified_parent')
				
				icon = self.classifier.classify_path(path, is_planned_dir=path.is_dir() or path in plan_obj.planned_dirs)
				
				# Determine if the current item (if it's a directory) should be opened
				item_is_directory = path.is_dir() or path in plan_obj.planned_dirs
				should_open_this_item = auto_open_modified and item_is_directory
				
				tree_widget.insert(parent_node_id, "end", text=f"{icon} {path.name}", tags=tags, values=[str(path)], open=should_open_this_item)
				
				if item_is_directory:
					dir_nodes[path] = tree_widget.get_children(parent_node_id)[-1]
				# inserted_paths.add(path) # No longer needed with new parent handling







def main():
	"""Main entry point for the GUI application."""
	try:
		root = tk.Tk()
		ScaffoldApp(root)
		root.mainloop()
	except Exception as e:
		messagebox.showerror("Fatal Error", f"An unhandled exception occurred: {e}")

if __name__ == "__main__":
	main()