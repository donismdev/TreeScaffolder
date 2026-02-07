# -*- coding: utf-8 -*-
"""
panels.py

UI panel creation logic for the Tree Scaffolder GUI application.
"""
import tkinter as tk
from tkinter import ttk

def create_left_panel(app):
    """Creates all widgets for the left control panel."""
    app.left_frame.rowconfigure(1, weight=1)
    app.left_frame.columnconfigure(0, weight=1)

    # --- Controls Frame ---
    controls_frame = ttk.Frame(app.left_frame)
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
    controls_frame.columnconfigure(0, weight=1)

    # Folder Selection
    folder_frame = ttk.LabelFrame(controls_frame, text="1. Select Target Root Folder")
    folder_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    
    path_buttons_frame = ttk.Frame(folder_frame)
    path_buttons_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    path_buttons_frame.columnconfigure(1, weight=1)

    app.folder_label = ttk.Label(path_buttons_frame, textvariable=app.target_root_path, relief="sunken", padding=3, width=50)
    app.target_root_path.set("No folder selected.")
    app.folder_label.grid(row=0, column=0, sticky="w", padx=(0, 5))
    
    app.browse_button = ttk.Button(path_buttons_frame, text="Browse...", command=app.on_browse_folder, width=8)
    app.browse_button.grid(row=0, column=2, padx=(0, 5))

    app.prev_dir_button = ttk.Button(path_buttons_frame, text="Prev", command=app.on_previous_folder, width=5, state=tk.DISABLED)
    app.prev_dir_button.grid(row=0, column=3, padx=(0, 5))

    app.clear_button = ttk.Button(path_buttons_frame, text="Clear", command=app.on_clear_data, width=5)
    app.clear_button.grid(row=0, column=4)

    # --- Editor Tabs ---
    editor_tabs_frame = ttk.LabelFrame(app.left_frame, text="2. Define Scaffold Tree")
    editor_tabs_frame.grid(row=1, column=0, sticky="nsew")
    editor_tabs_frame.rowconfigure(0, weight=1)
    editor_tabs_frame.columnconfigure(0, weight=1)

    app.editor_notebook = ttk.Notebook(editor_tabs_frame)
    app.editor_notebook.grid(row=0, column=0, sticky="nsew")

    # --- Scaffold Tree Tab ---
    scaffold_tree_frame = ttk.Frame(app.editor_notebook)
    app.editor_notebook.add(scaffold_tree_frame, text="Scaffold Tree")
    scaffold_tree_frame.rowconfigure(0, weight=1)
    scaffold_tree_frame.columnconfigure(0, weight=1)
    
    app.tree_text = tk.Text(scaffold_tree_frame, wrap=tk.NONE, undo=True, font=app.editor_font, tabs=(app.editor_font.measure('    '),))
    
    tree_yscroller = ttk.Scrollbar(scaffold_tree_frame, orient=tk.VERTICAL, command=app.tree_text.yview)
    tree_xscroller = ttk.Scrollbar(scaffold_tree_frame, orient=tk.HORIZONTAL, command=app.tree_text.xview)
    app.tree_text.config(yscrollcommand=tree_yscroller.set, xscrollcommand=tree_xscroller.set)
    
    app.tree_text.grid(row=0, column=0, sticky="nsew")
    tree_yscroller.grid(row=0, column=1, sticky="ns")
    tree_xscroller.grid(row=1, column=0, sticky="ew")
    
    app.tree_text.insert("1.0", app.DEFAULT_TREE_TEMPLATE)

    # --- Source Code Tab ---
    source_code_frame = ttk.Frame(app.editor_notebook)
    app.editor_notebook.add(source_code_frame, text="Source Code")
    source_code_frame.rowconfigure(0, weight=1)
    source_code_frame.columnconfigure(0, weight=1)

    app.source_code_text = tk.Text(source_code_frame, wrap=tk.NONE, undo=True, font=app.editor_font, tabs=(app.editor_font.measure('    '),))
    
    source_yscroller = ttk.Scrollbar(source_code_frame, orient=tk.VERTICAL, command=app.source_code_text.yview)
    source_xscroller = ttk.Scrollbar(source_code_frame, orient=tk.HORIZONTAL, command=app.source_code_text.xview)
    app.source_code_text.config(yscrollcommand=source_yscroller.set, xscrollcommand=source_xscroller.set)
    
    app.source_code_text.grid(row=0, column=0, sticky="nsew")
    source_yscroller.grid(row=0, column=1, sticky="ns")
    source_xscroller.grid(row=1, column=0, sticky="ew")

    # --- Content Tab ---
    content_frame = ttk.Frame(app.editor_notebook)
    app.editor_notebook.add(content_frame, text="Content")
    content_frame.rowconfigure(0, weight=1)
    content_frame.columnconfigure(0, weight=1)

    app.content_text = tk.Text(content_frame, wrap=tk.NONE, undo=True, font=app.editor_font, tabs=(app.editor_font.measure('    '),))
    
    content_yscroller = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=app.content_text.yview)
    content_xscroller = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=app.content_text.xview)
    app.content_text.config(yscrollcommand=content_yscroller.set, xscrollcommand=content_xscroller.set)
    
    app.content_text.grid(row=0, column=0, sticky="nsew")
    content_yscroller.grid(row=0, column=1, sticky="ns")
    content_xscroller.grid(row=1, column=0, sticky="ew")

    # --- Settings & Actions Frame ---
    settings_frame = ttk.LabelFrame(app.left_frame, text="3. Settings & Actions")
    settings_frame.grid(row=2, column=0, sticky="ew", pady=5)
    settings_frame.columnconfigure(1, weight=1)

    # Settings
    ttk.Checkbutton(settings_frame, text="Dry Run (don't write files)", variable=app.dry_run).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
    ttk.Checkbutton(settings_frame, text="Scan for similar names", variable=app.enable_similarity_scan).grid(row=1, column=0, columnspan=2, sticky="w", padx=5)

    ttk.Label(settings_frame, text="Similarity Ratio:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    ttk.Scale(settings_frame, from_=0.5, to=1.0, variable=app.similarity_threshold, orient=tk.HORIZONTAL).grid(row=2, column=1, sticky="ew", padx=5)

    ttk.Checkbutton(settings_frame, text="Open folder after Apply Scaffold", variable=app.open_folder_after_apply).grid(row=3, column=0, columnspan=2, sticky="w", padx=5)
    
    # Action Buttons
    actions_subframe = ttk.Frame(settings_frame)
    actions_subframe.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
    actions_subframe.columnconfigure((0, 1), weight=1)

    app.recompute_button = ttk.Button(actions_subframe, text="Compute Diff", command=app.on_recompute, state=tk.DISABLED)
    app.recompute_button.grid(row=0, column=0, padx=2, sticky="ew")

    app.apply_button = ttk.Button(actions_subframe, text="Apply Scaffold", command=app.on_apply, state=tk.DISABLED)
    app.apply_button.grid(row=0, column=1, padx=2, sticky="ew")

    app.load_test_data_button = ttk.Button(actions_subframe, text="Load Test Data", command=app.on_load_test_data)
    app.load_test_data_button.grid(row=1, column=0, columnspan=2, padx=2, pady=(5,0), sticky="ew")


def create_treeview(parent: ttk.Frame, show: str = "tree") -> ttk.Treeview:
    """Helper to create and configure a Treeview widget."""
    tree = ttk.Treeview(parent, show=show)
    tree.grid(row=0, column=0, sticky="nsew")
    
    scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    tree.config(yscrollcommand=scrollbar.set)
    
    return tree

def create_right_panel(app):
    """Creates the notebook for showing diffs and logs."""
    app.notebook = ttk.Notebook(app.right_frame)
    app.notebook.pack(fill=tk.BOTH, expand=True)

    # --- Diff View ---
    diff_frame = ttk.Frame(app.notebook, padding=5)
    app.notebook.add(diff_frame, text="Before / After Diff")
    diff_frame.rowconfigure(0, weight=1)
    diff_frame.columnconfigure(0, weight=1)

    diff_paned = ttk.PanedWindow(diff_frame, orient=tk.HORIZONTAL)
    diff_paned.grid(row=0, column=0, sticky="nsew")

    # --- Before Pane ---
    before_pane_frame = ttk.LabelFrame(diff_paned, text="Before (Current State)")
    before_pane_frame.rowconfigure(0, weight=1)
    before_pane_frame.columnconfigure(0, weight=1)
    diff_paned.add(before_pane_frame, weight=1)

    app.before_notebook = ttk.Notebook(before_pane_frame)
    app.before_notebook.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
    
    before_tree_frame = ttk.Frame(app.before_notebook)
    before_tree_frame.rowconfigure(0, weight=1)
    before_tree_frame.columnconfigure(0, weight=1)
    app.before_tree = create_treeview(before_tree_frame, show="tree")
    app.before_notebook.add(before_tree_frame, text="Tree")
    
    before_list_frame = ttk.Frame(app.before_notebook)
    before_list_frame.rowconfigure(0, weight=1)
    before_list_frame.columnconfigure(0, weight=1)
    app.before_list = create_treeview(before_list_frame, show="tree")
    app.before_notebook.add(before_list_frame, text="List")

    # --- After Pane ---
    after_pane_frame = ttk.LabelFrame(diff_paned, text="After (Planned State)")
    after_pane_frame.rowconfigure(0, weight=1)
    after_pane_frame.columnconfigure(0, weight=1)
    diff_paned.add(after_pane_frame, weight=1)
    
    app.after_notebook = ttk.Notebook(after_pane_frame)
    app.after_notebook.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

    after_tree_frame = ttk.Frame(app.after_notebook)
    after_tree_frame.rowconfigure(0, weight=1)
    after_tree_frame.columnconfigure(0, weight=1)
    app.after_tree = create_treeview(after_tree_frame, show="tree")
    app.after_notebook.add(after_tree_frame, text="Tree")

    after_list_frame = ttk.Frame(app.after_notebook)
    after_list_frame.rowconfigure(0, weight=1)
    after_list_frame.columnconfigure(0, weight=1)
    app.after_list = create_treeview(after_list_frame, show="tree")
    app.after_notebook.add(after_list_frame, text="Apply Tree")

    # Bind selection event
    app.before_tree.bind("<<TreeviewSelect>>", app.on_tree_select)
    app.after_tree.bind("<<TreeviewSelect>>", app.on_tree_select)
    app.before_list.bind("<<TreeviewSelect>>", app.on_tree_select)
    app.after_list.bind("<<TreeviewSelect>>", app.on_tree_select)

    # --- Log View ---
    log_frame = ttk.Frame(app.notebook, padding=5)
    app.notebook.add(log_frame, text="Log")
    log_frame.rowconfigure(0, weight=1)
    log_frame.columnconfigure(0, weight=1)

    app.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9))
    app.log_text.grid(row=0, column=0, sticky="nsew")
    log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=app.log_text.yview)
    log_scrollbar.grid(row=0, column=1, sticky="ns")
    app.log_text.config(yscrollcommand=log_scrollbar.set)
