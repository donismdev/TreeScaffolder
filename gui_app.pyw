# -*- coding: utf-8 -*-
"""
gui_app.py

A Windows GUI application designed as a Prompt Helper for LLM workflows.
Optimizes project scaffolding by prioritizing Source Code analysis, 
providing visual diffs, and ensuring safe file system operations.
Built with tkinter and ttk.
"""
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from Scripts.Core import scaffold_core
from Scripts.Utils import file_classifier
from Scripts.UI.panels import create_left_panel, create_right_panel, setup_styles, init_fonts, configure_tree_tags
from Scripts.UI.tree_populator import populate_before_tree, populate_after_tree, _clear_tree as clear_tree_function
from Scripts.UI import app_utils
from Scripts.UI import key_bindings
from Scripts.UI import shortcut_hints
from Scripts.Utils.i18n import t
from Scripts.UI import action_handler
from Scripts.Utils import logger

from Scripts.UI.action_handler import DEV_DIR, RESOURCE_DIR

# --- Constants ---
APP_TITLE = "Tree Scaffolder v0.8.0"
LOG_DIR = "Log"

if (DEV_DIR / "config.json").exists():
    CONFIG_FILE = str(DEV_DIR / "config.json")
else:
    CONFIG_FILE = str(RESOURCE_DIR / "config.json")

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
        logger.debug("ScaffoldApp.__init__ started")
        self.root = root
        self.root.title(t("ui.title"))
        self.root.geometry(DEFAULT_GEOMETRY)
        self.root.minsize(800, 600)
        
        # --- Constants ---
        self.LOG_DIR = LOG_DIR
        self.CONFIG_FILE = CONFIG_FILE
        self.DEFAULT_GEOMETRY = DEFAULT_GEOMETRY
        self.DEFAULT_TREE_TEMPLATE = DEFAULT_TREE_TEMPLATE

        # --- Style Configuration ---
        self.style = ttk.Style()
        self.style.theme_use('vista')

        # --- Member Variables ---
        self.target_root_path = tk.StringVar(value=t("ui.no_folder_selected"))
        self.grep_root_path = tk.StringVar(value=t("ui.no_folder_selected"))
        self.dry_run = tk.BooleanVar(value=True)
        self.open_folder_after_apply = tk.BooleanVar(value=False)
        self.create_gitkeep = tk.BooleanVar(value=False)
        self.show_recovery_after_overwrite = tk.BooleanVar(value=True)
        self.enable_similarity_scan = tk.BooleanVar(value=True)
        self.show_console = tk.BooleanVar(value=False)
        
        # Load initial config to get threshold and other non-geometry settings
        config_data = app_utils.load_config(self.CONFIG_FILE)
        self.similarity_threshold = tk.DoubleVar(value=config_data.get("SIMILARITY_RATIO_THRESHOLD", 0.86))
        self.last_root_path = None
        self.last_grep_root_path = None

        self.current_plan: scaffold_core.Plan | None = None
        self.classifier = file_classifier.FileTypeClassifier()
        self.tree_text = None
        self.source_code_text = None
        self.content_text = None
        self.before_tree = None
        self.after_tree = None
        self.before_list = None
        self.after_list = None
        self.before_notebook = None
        self.after_notebook = None
        self.editor_notebook = None
        self.analysis_notebook = None
        self.before_tree_map = {}
        self.before_list_map = {}
        self.after_tree_map = {}
        self.after_list_map = {}
        self.selected_paths = {} # Track checked state in After View: {Path: bool}
        self.last_selected_after_item = None 
        self._in_selection_sync = False 
        self.before_cache = {} 
        self._scaffold_applied = False
        self.widget_map = {} # Map action names to UI widgets for shortcut hints
        self.key_bindings_map = key_bindings._load_key_bindings_config()

        # --- Main Layout ---
        self.sidebar = ttk.Frame(self.root, width=40)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        init_fonts(self)
        self._create_sidebar()

        self.tool_frames = {}
        self._setup_scaffold_tool()
        self._setup_grep_tool()

        configure_tree_tags(self)

        # --- Event-based setup ---
        self.editor_notebook.bind("<<NotebookTabChanged>>", lambda e: action_handler.on_editor_tab_changed(self, e))
        action_handler.on_editor_tab_changed(self, None) 

        self.root.bind("<Destroy>", lambda event: app_utils.save_app_window_geometry(self) if event.widget == self.root else None)
        app_utils.load_app_window_geometry(self) 
        app_utils.set_console_visibility(self.show_console.get())
        app_utils.load_last_root_path(self, target="scaffold")
        app_utils.load_last_root_path(self, target="grep")
        key_bindings.setup_key_bindings(self)
        
        # --- Shortcut Hint Setup ---
        self.hint_manager = shortcut_hints.ShortcutHintManager(self)
        self.root.bind("<KeyPress-Alt_L>", self.hint_manager.show_hints)
        self.root.bind("<KeyPress-Alt_R>", self.hint_manager.show_hints)
        self.root.bind("<KeyRelease-Alt_L>", self.hint_manager.hide_hints)
        self.root.bind("<KeyRelease-Alt_R>", self.hint_manager.hide_hints)
        self.root.bind("<FocusOut>", self.hint_manager.hide_hints)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        action_handler.update_debug_ui(self)
        self.switch_tool("scaffold")
        logger.debug("ScaffoldApp.__init__ completed")

    # --- Tool Switcher Logic ---

    def _create_sidebar(self):
        """Creates the vertical sidebar with tool buttons."""
        self.sidebar.config(padding=(5, 10))
        
        # Style for the sidebar buttons to look like vertical tabs
        self.style.configure("Sidebar.TButton", font=("Segoe UI", 9), padding=5)
        
        # Tool 1: Tree Scaffold
        self.scaffold_btn = ttk.Button(self.sidebar, text=t("ui.tab_scaffold_tree"), style="Sidebar.TButton", command=lambda: self.switch_tool("scaffold"))
        self.scaffold_btn.pack(fill=tk.X, pady=2)
        
        # Tool 2: Grep & Merge
        self.grep_btn = ttk.Button(self.sidebar, text=t("ui.tab_grep"), style="Sidebar.TButton", command=lambda: self.switch_tool("grep"))
        self.grep_btn.pack(fill=tk.X, pady=2)

    def _setup_scaffold_tool(self):
        """Initializes the existing Tree Scaffold tool layout."""
        scaffold_frame = ttk.Frame(self.main_container)
        self.tool_frames["scaffold"] = scaffold_frame

        self.main_paned_window = tk.PanedWindow(scaffold_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        self.main_paned_window.pack(fill=tk.BOTH, expand=True)

        self.left_frame = ttk.Frame(self.main_paned_window, padding=5)
        self.main_paned_window.add(self.left_frame, stretch="always", minsize=400)

        self.right_frame = ttk.Frame(self.main_paned_window)
        self.main_paned_window.add(self.right_frame, stretch="always", minsize=400)

        create_left_panel(self)
        create_right_panel(self)

    def _setup_grep_tool(self):
        """Initializes the new Grep & Merge tool layout."""
        from Scripts.UI.panels import create_grep_panel
        grep_frame = ttk.Frame(self.main_container)
        # Don't pack it yet, switch_tool will handle it
        self.tool_frames["grep"] = grep_frame
        create_grep_panel(self, grep_frame)

    def switch_tool(self, tool_key):
        """Switches the visible tool in the main container."""
        for key, frame in self.tool_frames.items():
            if key == tool_key:
                frame.pack(fill=tk.BOTH, expand=True)
                # Highlight active button (using a custom style would be better, but simple state for now)
                if key == "scaffold":
                    self.scaffold_btn.state(['pressed'])
                    self.grep_btn.state(['!pressed'])
                else:
                    self.grep_btn.state(['pressed'])
                    self.scaffold_btn.state(['!pressed'])
            else:
                frame.pack_forget()

    def on_closing(self):
        """Finalizes the session log and closes the application."""
        logger.finalize_session_log()
        self.root.destroy()

    # --- Wrapped Event Handlers (Delegate to action_handler) ---
    def on_browse_folder(self): action_handler.on_browse_folder(self)
    def on_previous_folder(self): action_handler.on_previous_folder(self)
    def on_recompute(self, silent=False): return action_handler.on_recompute(self, silent)
    def on_apply(self): action_handler.on_apply(self)
    def on_clear_data(self): action_handler.on_clear_data(self)
    def on_load_test_data(self): action_handler.on_load_test_data(self)
    def on_options(self): action_handler.on_options(self)
    def on_recovery(self): action_handler.on_recovery(self)
    def on_escape_pressed(self, event=None): action_handler.on_escape_pressed(self, event)
    def on_before_select(self, event): action_handler.on_before_select(self, event)
    def on_after_select(self, event): action_handler.on_after_select(self, event)
    def _on_after_tree_click(self, event): action_handler.on_after_tree_click(self, event)
    def _on_after_tree_double_click(self, event): action_handler.on_after_tree_double_click(self, event)
    def _on_after_tree_space(self, event): return action_handler.on_after_tree_space(self, event)

    def refresh_ui(self):
        """Re-initializes the UI components to apply language changes."""
        current_tree = self.tree_text.get("1.0", tk.END)
        current_source = self.source_code_text.get("1.0", tk.END)
        current_root = self.target_root_path.get()
        
        for child in self.root.winfo_children():
            if isinstance(child, tk.Toplevel): continue
            child.destroy()

        self.root.title(t("ui.title"))
        self.widget_map = {} 

        # --- Re-setup Sidebar Layout ---
        self.sidebar = ttk.Frame(self.root, width=40)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        init_fonts(self)
        self._create_sidebar()

        self.tool_frames = {}
        self._setup_scaffold_tool()
        
        # Re-initialize other tools if any
        if hasattr(self, "_setup_grep_tool"):
            self._setup_grep_tool()

        if self.last_root_path:
            self.prev_dir_button.config(state=tk.NORMAL)

        self.tree_text.delete("1.0", tk.END)
        self.tree_text.insert("1.0", current_tree)
        self.source_code_text.delete("1.0", tk.END)
        self.source_code_text.insert("1.0", current_source)
        self.target_root_path.set(current_root)

        self.editor_notebook.bind("<<NotebookTabChanged>>", lambda e: action_handler.on_editor_tab_changed(self, e))
        action_handler.on_editor_tab_changed(self, None)

        key_bindings.setup_key_bindings(self)
        self.hint_manager = shortcut_hints.ShortcutHintManager(self)
        configure_tree_tags(self)

if __name__ == "__main__":
    logger.setup_runtime_logging(CONFIG_FILE, LOG_DIR)
    root = tk.Tk()
    app = ScaffoldApp(root)
    root.mainloop()
