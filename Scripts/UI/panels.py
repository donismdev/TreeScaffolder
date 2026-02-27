# -*- coding: utf-8 -*-
"""
panels.py

UI panel creation logic for the Tree Scaffolder GUI application.
"""
import tkinter as tk
from tkinter import ttk, font
from Scripts.UI import options_ui
from Scripts.Utils.i18n import t
from Scripts.UI import action_handler
from Scripts.Utils import logger

def init_fonts(app):
    """Initializes basic fonts for the application."""
    if not hasattr(app, 'editor_font'):
        app.editor_font = font.Font(family="Consolas", size=10)
    if not hasattr(app, 'treeview_item_font'):
        app.treeview_item_font = font.Font(family="Segoe UI", size=9)
    if not hasattr(app, 'treeview_bold_font'):
        # Slightly larger (size 11) and bold for modified/new/conflict items
        app.treeview_bold_font = font.Font(family="Segoe UI", size=11, weight="bold")

def configure_tree_tags(app):
    """Configures tags for all tree widgets. Call after widgets are created."""
    # Ensure fonts are initialized
    init_fonts(app)
        
    for tree in [app.before_tree, app.after_tree, app.before_list, app.after_list]:
        if tree:
            # Highlight colored items with the larger bold font
            tree.tag_configure('new', foreground='green', font=app.treeview_bold_font)
            tree.tag_configure('overwrite', foreground='#4682B4', font=app.treeview_bold_font) # Steel Blue
            tree.tag_configure('conflict', foreground='red', font=app.treeview_bold_font)
            tree.tag_configure('warning', foreground='#E59400', font=app.treeview_bold_font)
            # Parent folders containing changes should also be yellowish-orange
            tree.tag_configure('modified_parent', foreground='#E59400', font=app.treeview_bold_font)

def setup_styles(app):
    """Legacy helper that does both (if possible)."""
    init_fonts(app)
    configure_tree_tags(app)

def create_left_panel(app):
    """Creates all widgets for the left control panel."""
    app.left_frame.rowconfigure(1, weight=1)
    app.left_frame.columnconfigure(0, weight=1)

    # --- Controls Frame ---
    controls_frame = ttk.Frame(app.left_frame)
    controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
    controls_frame.columnconfigure(0, weight=1)

    # Folder Selection
    folder_frame = ttk.LabelFrame(controls_frame, text=t("ui.section_1"))
    folder_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    
    path_buttons_frame = ttk.Frame(folder_frame)
    path_buttons_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    
    # 가중치 설정: 0번 열(라벨)만 늘어나게 하고, 1, 2번 열(버튼)은 고정
    path_buttons_frame.columnconfigure(0, weight=1)
    path_buttons_frame.columnconfigure(1, weight=0)
    path_buttons_frame.columnconfigure(2, weight=0)

    app.folder_label = ttk.Label(path_buttons_frame, textvariable=app.target_root_path, relief="sunken", padding=3)
    app.target_root_path.set(t("ui.no_folder_selected"))
    # sticky="ew"를 주어 라벨이 0번 열을 꽉 채우게 함
    app.folder_label.grid(row=0, column=0, sticky="ew", padx=(0, 5))
    
    app.browse_button = ttk.Button(path_buttons_frame, text=t("ui.browse"), command=app.on_browse_folder, width=12)
    app.browse_button.grid(row=0, column=1, padx=(0, 5))
    app.widget_map["on_browse_folder"] = app.browse_button

    app.prev_dir_button = ttk.Button(path_buttons_frame, text=t("ui.prev"), command=app.on_previous_folder, width=8, state=tk.DISABLED)
    app.prev_dir_button.grid(row=0, column=2)
    app.widget_map["on_previous_folder"] = app.prev_dir_button

    # --- Editor Tabs ---
    editor_tabs_frame = ttk.LabelFrame(app.left_frame, text=t("ui.section_2"))
    editor_tabs_frame.grid(row=1, column=0, sticky="nsew")
    editor_tabs_frame.columnconfigure(0, weight=1) # Make sure the column expands

    # --- New Button Bar ---
    button_bar_frame = ttk.Frame(editor_tabs_frame)
    button_bar_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 5))

    # Add 4 placeholder buttons and store them on the app instance
    app.editor_buttons = []
    for i in range(4):
        button = ttk.Button(button_bar_frame, text="")
        button.pack(side="left", padx=2)
        app.editor_buttons.append(button)

    # --- Notebook ---
    app.editor_notebook = ttk.Notebook(editor_tabs_frame)
    app.editor_notebook.grid(row=1, column=0, sticky="nsew") # Notebook is now in row 1
    editor_tabs_frame.rowconfigure(1, weight=1) # Configure row 1 to expand
    app.widget_map["cycle_notebook_editor_notebook"] = app.editor_notebook

    # --- Scaffold Tree Tab ---
    scaffold_tree_frame = ttk.Frame(app.editor_notebook)
    app.editor_notebook.add(scaffold_tree_frame, text=t("ui.tab_scaffold_tree"))
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
    
    # Bind change events
    app.tree_text.bind("<<Modified>>", lambda e: action_handler.handle_content_updated(app, "tree") if app.tree_text.edit_modified() and app.tree_text.edit_modified(False) else None)

    # --- Source Code Tab ---
    source_code_frame = ttk.Frame(app.editor_notebook)
    app.editor_notebook.add(source_code_frame, text=t("ui.tab_source_code"))
    source_code_frame.rowconfigure(0, weight=1)
    source_code_frame.columnconfigure(0, weight=1)

    app.source_code_text = tk.Text(source_code_frame, wrap=tk.NONE, undo=True, font=app.editor_font, tabs=(app.editor_font.measure('    '),))
    
    source_yscroller = ttk.Scrollbar(source_code_frame, orient=tk.VERTICAL, command=app.source_code_text.yview)
    source_xscroller = ttk.Scrollbar(source_code_frame, orient=tk.HORIZONTAL, command=app.source_code_text.xview)
    app.source_code_text.config(yscrollcommand=source_yscroller.set, xscrollcommand=source_xscroller.set)
    
    app.source_code_text.grid(row=0, column=0, sticky="nsew")
    source_yscroller.grid(row=0, column=1, sticky="ns")
    source_xscroller.grid(row=1, column=0, sticky="ew")

    app.source_code_text.bind("<<Modified>>", lambda e: action_handler.handle_content_updated(app, "source") if app.source_code_text.edit_modified() and app.source_code_text.edit_modified(False) else None)

    # --- Content Tab ---
    content_frame = ttk.Frame(app.editor_notebook)
    app.editor_notebook.add(content_frame, text=t("ui.tab_content"))
    content_frame.rowconfigure(0, weight=1)
    content_frame.columnconfigure(0, weight=1)

    app.content_text = tk.Text(content_frame, wrap=tk.NONE, undo=True, font=app.editor_font, tabs=(app.editor_font.measure('    '),))
    app.content_text.tag_configure("warning", foreground="red", font=("Segoe UI", 10, "bold"))
    
    content_yscroller = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=app.content_text.yview)
    content_xscroller = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=app.content_text.xview)
    app.content_text.config(yscrollcommand=content_yscroller.set, xscrollcommand=content_xscroller.set)
    
    app.content_text.grid(row=0, column=0, sticky="nsew")
    content_yscroller.grid(row=0, column=1, sticky="ns")
    content_xscroller.grid(row=1, column=0, sticky="ew")

    # --- Settings & Actions Frame ---
    settings_frame = ttk.LabelFrame(app.left_frame, text=t("ui.section_3"))
    settings_frame.grid(row=2, column=0, sticky="ew", pady=5)
    settings_frame.columnconfigure(1, weight=1)

    # Settings
    ttk.Checkbutton(settings_frame, text=t("ui.dry_run"), variable=app.dry_run, 
                    command=lambda: action_handler.handle_toggle_dry_run(app, app.dry_run.get())).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
    ttk.Checkbutton(settings_frame, text=t("ui.similarity_scan"), variable=app.enable_similarity_scan,
                    command=lambda: action_handler.handle_toggle_similarity(app, app.enable_similarity_scan.get())).grid(row=1, column=0, columnspan=2, sticky="w", padx=5)

    ttk.Label(settings_frame, text=t("ui.similarity_ratio")).grid(row=2, column=0, sticky="w", padx=5, pady=2)
    ttk.Scale(settings_frame, from_=0.5, to=1.0, variable=app.similarity_threshold, orient=tk.HORIZONTAL).grid(row=2, column=1, sticky="ew", padx=5)

    ttk.Checkbutton(settings_frame, text=t("ui.open_after"), variable=app.open_folder_after_apply,
                    command=lambda: action_handler.handle_toggle_open_after(app, app.open_folder_after_apply.get())).grid(row=3, column=0, columnspan=2, sticky="w", padx=5)
    
    # Action Buttons
    actions_subframe = ttk.Frame(settings_frame)
    actions_subframe.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
    actions_subframe.columnconfigure((0, 1), weight=1)

    app.recompute_button = ttk.Button(actions_subframe, text=t("ui.compute_diff"), command=app.on_recompute, state=tk.DISABLED)
    app.recompute_button.grid(row=0, column=0, padx=2, sticky="ew")
    app.widget_map["on_recompute"] = app.recompute_button

    app.apply_button = ttk.Button(actions_subframe, text=t("ui.apply_scaffold"), command=app.on_apply, state=tk.DISABLED)
    app.apply_button.grid(row=0, column=1, padx=2, sticky="ew")
    app.widget_map["on_apply"] = app.apply_button

    app.load_test_data_button = ttk.Button(actions_subframe, text=t("ui.load_test_data"), command=app.on_load_test_data)
    app.load_test_data_button.grid(row=1, column=0, columnspan=2, padx=2, pady=(5,0), sticky="ew")
    app.widget_map["on_load_test_data_conditional"] = app.load_test_data_button


def create_treeview(parent: ttk.Frame, show: str = "tree") -> ttk.Treeview:
    """Helper to create and configure a Treeview widget."""
    tree = ttk.Treeview(parent, show=show)
    tree.grid(row=0, column=0, sticky="nsew")
    
    scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    tree.config(yscrollcommand=scrollbar.set)
    
    return tree

def create_right_panel(app):
    """Creates the analysis and summary panels in the right frame."""
    app.right_frame.rowconfigure(0, weight=1)
    app.right_frame.columnconfigure(0, weight=1)

    # 4. Analysis (Diff & Log) LabelFrame
    app.diff_group = ttk.LabelFrame(app.right_frame, text=t("ui.section_4"))
    app.diff_group.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 2))
    app.diff_group.rowconfigure(0, weight=1)
    app.diff_group.columnconfigure(0, weight=1)

    # Analysis Notebook inside Section 4
    app.analysis_notebook = ttk.Notebook(app.diff_group)
    app.analysis_notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    app.widget_map["cycle_notebook_analysis_notebook"] = app.analysis_notebook
    
    # --- Tab 1: Diff View ---
    diff_tab_frame = ttk.Frame(app.analysis_notebook)
    app.analysis_notebook.add(diff_tab_frame, text=t("ui.tab_diff_view"))
    diff_tab_frame.rowconfigure(0, weight=1)
    diff_tab_frame.columnconfigure(0, weight=1)

    app.diff_paned_window = tk.PanedWindow(diff_tab_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
    app.diff_paned_window.grid(row=0, column=0, sticky="nsew")

    # --- Before Pane ---
    before_pane_frame = ttk.LabelFrame(app.diff_paned_window, text=t("ui.before_pane"))
    before_pane_frame.rowconfigure(0, weight=1)
    before_pane_frame.columnconfigure(0, weight=1)
    app.diff_paned_window.add(before_pane_frame, stretch="always", minsize=200)

    app.before_notebook = ttk.Notebook(before_pane_frame)
    app.before_notebook.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
    app.widget_map["cycle_notebook_before_notebook"] = app.before_notebook
    
    before_tree_frame = ttk.Frame(app.before_notebook)
    before_tree_frame.rowconfigure(0, weight=1)
    before_tree_frame.columnconfigure(0, weight=1)
    app.before_tree = create_treeview(before_tree_frame, show="tree")
    app.before_notebook.add(before_tree_frame, text=t("ui.tree_view"))
    
    before_list_frame = ttk.Frame(app.before_notebook)
    before_list_frame.rowconfigure(0, weight=1)
    before_list_frame.columnconfigure(0, weight=1)
    app.before_list = create_treeview(before_list_frame, show="tree")
    app.before_notebook.add(before_list_frame, text=t("ui.list_view"))

    # --- After Pane ---
    after_pane_frame = ttk.LabelFrame(app.diff_paned_window, text=t("ui.after_pane"))
    after_pane_frame.rowconfigure(0, weight=1)
    after_pane_frame.columnconfigure(0, weight=1)
    app.diff_paned_window.add(after_pane_frame, stretch="always", minsize=200)
    
    app.after_notebook = ttk.Notebook(after_pane_frame)
    app.after_notebook.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
    app.widget_map["cycle_notebook_after_notebook"] = app.after_notebook

    after_tree_frame = ttk.Frame(app.after_notebook)
    after_tree_frame.rowconfigure(0, weight=1)
    after_tree_frame.columnconfigure(0, weight=1)
    app.after_tree = create_treeview(after_tree_frame, show="tree")
    app.after_notebook.add(after_tree_frame, text=t("ui.tree_view"))

    after_list_frame = ttk.Frame(app.after_notebook)
    after_list_frame.rowconfigure(0, weight=1)
    after_list_frame.columnconfigure(0, weight=1)
    app.after_list = create_treeview(after_list_frame, show="tree")
    app.after_notebook.add(after_list_frame, text=t("ui.apply_tree"))

    # --- Tab 2: Log View ---
    log_tab_frame = ttk.Frame(app.analysis_notebook)
    app.analysis_notebook.add(log_tab_frame, text=t("ui.tab_log"))
    log_tab_frame.rowconfigure(0, weight=1)
    log_tab_frame.columnconfigure(0, weight=1)

    app.log_text = tk.Text(log_tab_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9))
    app.log_text.grid(row=0, column=0, sticky="nsew")
    log_scrollbar = ttk.Scrollbar(log_tab_frame, orient=tk.VERTICAL, command=app.log_text.yview)
    log_scrollbar.grid(row=0, column=1, sticky="ns")
    app.log_text.config(yscrollcommand=log_scrollbar.set)

    # 5. Summary LabelFrame
    app.summary_group = ttk.LabelFrame(app.right_frame, text=t("ui.section_5"))
    app.summary_group.grid(row=1, column=0, sticky="ew", padx=5, pady=(2, 5))
    app.summary_group.columnconfigure(0, weight=1)
    
    app.summary_label = ttk.Label(app.summary_group, text=t("ui.no_plan"), padding=5)
    app.summary_label.grid(row=0, column=0, sticky="w")

    # Buttons Container on the right
    summary_btns_frame = ttk.Frame(app.summary_group)
    summary_btns_frame.grid(row=0, column=1, padx=5)

    app.option_button = ttk.Button(summary_btns_frame, text=t("ui.option"), width=12, command=app.on_options)
    app.option_button.pack(side="left", padx=2)
    app.widget_map["on_options"] = app.option_button

    # Recovery button
    app.recovery_button = ttk.Button(summary_btns_frame, text=t("ui.recovery_btn"), width=12, command=app.on_recovery)
    app.recovery_button.pack(side="left", padx=2)
    app.widget_map["on_recovery"] = app.recovery_button
    
    app.clear_button = ttk.Button(summary_btns_frame, text=t("ui.clear"), command=app.on_clear_data, width=8)
    app.clear_button.pack(side="left", padx=2)
    app.widget_map["on_clear_data"] = app.clear_button

    # Bind selection events to separate handlers to ensure absolute isolation
    app.before_tree.bind("<<TreeviewSelect>>", app.on_before_select)
    app.before_list.bind("<<TreeviewSelect>>", app.on_before_select)
    app.after_tree.bind("<<TreeviewSelect>>", app.on_after_select)
    app.after_list.bind("<<TreeviewSelect>>", app.on_after_select)

    # Bind click for toggle logic (Single and Double click)
    for event_type in ["<Button-1>", "<Double-1>"]:
        app.after_tree.bind(event_type, lambda e: app._on_after_tree_click(e) if hasattr(app, "_on_after_tree_click") else None, add="+")
        app.after_list.bind(event_type, lambda e: app._on_after_tree_click(e) if hasattr(app, "_on_after_tree_click") else None, add="+")

    # Bind Space for toggle logic
    app.after_tree.bind("<space>", lambda e: app._on_after_tree_space(e) if hasattr(app, "_on_after_tree_space") else None)
    app.after_list.bind("<space>", lambda e: app._on_after_tree_space(e) if hasattr(app, "_on_after_tree_space") else None)

    # Reset toggle state when focus leaves
    app.after_tree.bind("<FocusOut>", lambda e: action_handler.on_after_tree_focus_out(app, e))
    app.after_list.bind("<FocusOut>", lambda e: action_handler.on_after_tree_focus_out(app, e))

    # Disable default double-click expand/collapse for all tree views
    for tree in [app.before_tree, app.before_list]:
        tree.bind("<Double-1>", lambda e: "break")
    
    for tree in [app.after_tree, app.after_list]:
        # Bind Double-1 to break AFTER our custom handler runs to stop expansion
        tree.bind("<Double-1>", lambda e: "break", add="+")
