# -*- coding: utf-8 -*-
"""
gui_app.py

A Windows GUI application for scaffolding projects from a tree text description.
Provides a tree editor, safe folder selection, a before/after diff view,
and logging. Built with tkinter and ttk.
"""
import datetime
import json
import logging
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font

from Scripts.Core import scaffold_core
from Scripts.Utils import file_classifier
from Scripts.Core.v2_parser import V2ParserError
from Scripts.UI.panels import create_left_panel, create_right_panel
from Scripts.UI.tree_populator import populate_before_tree, populate_after_tree
from Scripts.UI import app_utils
from Scripts.UI import scaffold_runner
from Scripts.UI import key_bindings
from Scripts.UI import shortcut_hints # Added import
from Scripts.UI.tree_populator import _clear_tree as clear_tree_function # Import as different name

# --- Constants ---
APP_TITLE = "Tree Scaffolder v1.1"
LOG_DIR = "Log"
CONFIG_FILE = "Resources/config.json"
DEFAULT_GEOMETRY = "1200x700"
DEFAULT_TREE_TEMPLATE = """# =========================================================
# - Use @ROOT to define the logical root marker.
# - The first node must be that marker, ending with a '/'.
# - Indent with TABS or 4-SPACES.
# =========================================================

@ROOT {{Root}}

{{Root}}/
"""

# ... (after imports) ...

# Global variable to hold loggers
console_logger_instance = None
editor_logger_instance = None


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        # Filter out Tkinter messages or empty lines from print()
        if buf.strip() and "Tkinter is no longer supported" not in buf:
            for line in buf.rstrip().splitlines():
                if line:
                    self.logger.log(self.log_level, line)

    def flush(self):
        pass


class ScaffoldApp:
    """The main application class for the Tree Scaffolder GUI."""

    def __init__(self, root: tk.Tk):
        print("DEBUG: ScaffoldApp.__init__ started") # Debug print
        self.root = root
        self.root.title(APP_TITLE)
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
        self.setup_styles()

        # --- Member Variables ---
        self.target_root_path = tk.StringVar()
        self.dry_run = tk.BooleanVar(value=True)
        self.open_folder_after_apply = tk.BooleanVar(value=False)
        self.enable_similarity_scan = tk.BooleanVar(value=True)
        self.similarity_threshold = tk.DoubleVar(value=0.86)
        self.last_root_path = None

        self.current_plan: scaffold_core.Plan | None = None
        self.classifier = file_classifier.FileTypeClassifier()
        self.tree_text = None
        self.source_code_text = None
        self.content_text = None
        self.before_list = None
        self.after_list = None
        self.before_notebook = None
        self.after_notebook = None
        
        self.widget_map = {} # Map action names to UI widgets for shortcut hints
        self.key_bindings_map = key_bindings._load_key_bindings_config() # Load keybindings for hint manager

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
        self.style.configure('new.Treeview', foreground='green', font=self.treeview_item_font)
        self.style.configure('conflict.Treeview', foreground='red', font=self.treeview_item_font)
        self.style.configure('warning.Treeview', foreground='#E59400', font=self.treeview_item_font)
        self.before_tree.tag_configure('new', foreground='green', font=self.treeview_item_font)
        self.after_tree.tag_configure('new', foreground='green', font=self.treeview_item_font)
        self.after_tree.tag_configure('conflict', foreground='red', font=self.treeview_item_font)
        self.after_tree.tag_configure('warning', foreground='#E59400', font=self.treeview_item_font)
        self.after_tree.tag_configure('modified_parent', foreground='#DAA520', font=self.treeview_item_font)
        self.after_tree.tag_configure('overwrite', foreground='#0078D7', font=self.treeview_item_font)
        self.after_list.tag_configure('new', foreground='green', font=self.treeview_item_font)
        self.after_list.tag_configure('conflict', foreground='red', font=self.treeview_item_font)
        self.after_list.tag_configure('warning', foreground='#E59400', font=self.treeview_item_font)
        self.after_list.tag_configure('modified_parent', foreground='#DAA520', font=self.treeview_item_font)
        self.after_list.tag_configure('overwrite', foreground='#0078D7', font=self.treeview_item_font)

        self.root.bind("<Destroy>", lambda event: self._save_window_geometry())
        app_utils.load_last_root_path(self)
        key_bindings.setup_key_bindings(self)
        
        # --- Shortcut Hint Setup ---
        self.hint_manager = shortcut_hints.ShortcutHintManager(self)
        self.root.bind("<KeyPress-Alt_L>", self.hint_manager.show_hints)
        self.root.bind("<KeyPress-Alt_R>", self.hint_manager.show_hints)
        self.root.bind("<KeyRelease-Alt_L>", self.hint_manager.hide_hints)
        self.root.bind("<KeyRelease-Alt_R>", self.hint_manager.hide_hints)

        print("DEBUG: ScaffoldApp.__init__ completed") # Debug print

    def setup_styles(self):
        # Custom Fonts
        self.editor_font = font.Font(family="Consolas", size=10)
        self.app_button_font = font.Font(family="Segoe UI", size=9)
        self.treeview_item_font = font.Font(family="Segoe UI", size=11)

        # Style Configuration
        self.style.map("Treeview", background=[('selected', '#0078D7')])
        self.style.configure('TButton', font=self.app_button_font)

    def setup_left_panel(self):
        print("DEBUG: Calling create_left_panel") # Debug print
        create_left_panel(self)
        print("DEBUG: create_left_panel completed") # Debug print

    def setup_right_panel(self):
        print("DEBUG: Calling create_right_panel") # Debug print
        create_right_panel(self)
        print("DEBUG: create_right_panel completed") # Debug print

    # --- Event Handlers ---
    def on_browse_folder(self):
        print("DEBUG: on_browse_folder called") # Debug print
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
            self.target_root_path.set(message)
            self._save_last_root_path(message)
            self.recompute_button.config(state=tk.NORMAL)
            self._populate_before_tree(Path(message))
            self._clear_tree(self.after_tree)
            self._clear_tree(self.after_list)
            self.apply_button.config(state=tk.DISABLED)
        print("DEBUG: on_browse_folder completed") # Debug print

    def on_recompute(self):
        print("DEBUG: on_recompute called") # Debug print
        root_path_str = self.target_root_path.get()
        if not root_path_str or not Path(root_path_str).is_dir():
            messagebox.showerror("Error", "Please select a valid root folder first.")
            return
        root_path = Path(root_path_str)
        text_input = self.tree_text.get("1.0", "end-1c") + "\n" + self.source_code_text.get("1.0", "end-1c")
        if not text_input.strip():
            messagebox.showinfo("Info", "Both editors are empty. Nothing to compute.")
            return
        config = {
            "DRY_RUN": self.dry_run.get(),
            "ENABLE_SIMILARITY_SCAN": self.enable_similarity_scan.get(),
            "SIMILARITY_RATIO_THRESHOLD": self.similarity_threshold.get(),
        }
        self.current_plan = scaffold_core.generate_plan(root_path, text_input, config)
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
        self._populate_before_tree(root_path)
        self._populate_after_tree(self.current_plan)
        if self.current_plan.has_conflicts:
            messagebox.showwarning("Conflicts Found", "Conflicts were detected. 'Apply' is disabled.")
            self.apply_button.config(state=tk.DISABLED)
        elif not self.current_plan.errors:
            self.apply_button.config(state=tk.NORMAL)
            self.notebook.select(0)
        else:
            self.apply_button.config(state=tk.DISABLED)
        print("DEBUG: on_recompute completed") # Debug print

    def on_apply(self):
        print("DEBUG: on_apply called") # Debug print
        if not self.current_plan or self.current_plan.has_conflicts:
            messagebox.showerror("Cannot Apply", "No valid plan or plan has conflicts.")
            return
        if messagebox.askyesno("Confirm Apply", "This will create and overwrite files. Are you sure?"):
            self.notebook.select(1)
            self.recompute_button.config(state=tk.DISABLED)
            self.apply_button.config(state=tk.DISABLED)
            self.root.after(100, self._execute_scaffold)
        print("DEBUG: on_apply completed") # Debug print

    def on_tree_select(self, event: tk.Event):
        print("DEBUG: on_tree_select called") # Debug print
        widget = event.widget
        selection = widget.selection()
        if not selection: return
        item_id = selection[0]
        values = widget.item(item_id, "values")
        if not values: return
        path = Path(values[0])
        content_to_show, source_info = "", ""
        try:
            is_dir = path.is_dir() or (self.current_plan and path in self.current_plan.planned_dirs)
            if is_dir:
                self.content_text.delete("1.0", tk.END)
                self.content_text.insert("1.0", f"Directory selected:\n{path}")
                self.editor_notebook.select(2)
                return
            if widget == self.after_tree and self.current_plan:
                planned_content = self.current_plan.file_contents.get(path.resolve())
                if planned_content is not None:
                    content_to_show, source_info = planned_content, f"--- PLANNED CONTENT ---\nFile: {path}\n"
                elif path.exists():
                    content_to_show, source_info = path.read_text(encoding='utf-8', errors='replace'), f"--- EXISTING CONTENT ---\nFile: {path}\n"
            elif path.exists():
                content_to_show, source_info = path.read_text(encoding='utf-8', errors='replace'), f"--- CURRENT CONTENT ---\nFile: {path}\n"
        except Exception as e:
            content_to_show = f"Error reading file content:\n{e}"
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", source_info + "="*40 + "\n" + content_to_show)
        self.editor_notebook.select(2)
        print("DEBUG: on_tree_select completed") # Debug print

    def on_load_test_data(self):
        print("DEBUG: on_load_test_data called") # Debug print
        try:
            for file, text_widget in [("Resources/test_tree.txt", self.tree_text), ("Resources/test_data.txt", self.source_code_text)]:
                if Path(file).exists():
                    text_widget.delete("1.0", tk.END)
                    text_widget.insert("1.0", Path(file).read_text(encoding="utf-8"))
                    self._log(f"Loaded '{file}'.", "info")
                else:
                    messagebox.showwarning("File Not Found", f"'{file}' not found.")
        except Exception as e:
            messagebox.showerror("Error Loading Data", f"An error occurred: {e}")
        print("DEBUG: on_load_test_data completed") # Debug print

    def on_clear_data(self):
        print("DEBUG: on_clear_data called") # Debug print
        app_utils.log_message(self, "Clearing all editor content and planned data...", "info")
        self.dry_run.set(True)
        self.enable_similarity_scan.set(True)
        self.similarity_threshold.set(0.86)
        self.tree_text.delete("1.0", tk.END)
        self.tree_text.insert("1.0", self.DEFAULT_TREE_TEMPLATE)
        self.source_code_text.delete("1.0", tk.END)
        self.content_text.delete("1.0", tk.END)
        self.current_plan = None
        for tree in [self.before_tree, self.after_tree, self.before_list, self.after_list]:
            self._clear_tree(tree)
        self.recompute_button.config(state=tk.DISABLED)
        self.apply_button.config(state=tk.DISABLED)
        app_utils.log_message(self, "Runtime data cleared.", "info")
        print("DEBUG: on_clear_data completed") # Debug print

    def on_previous_folder(self):
        print("DEBUG: on_previous_folder called") # Debug print
        if self.last_root_path and Path(self.last_root_path).is_dir():
            is_valid, message = self._validate_path(self.last_root_path)
            if is_valid:
                self.target_root_path.set(message)
                self.recompute_button.config(state=tk.NORMAL)
                self._populate_before_tree(Path(message))
                self._clear_tree(self.after_tree)
                self.apply_button.config(state=tk.DISABLED)
            else:
                messagebox.showerror("Invalid Folder", f"Previous folder is no longer valid: {message}")
                self.last_root_path = None
                self.prev_dir_button.config(state=tk.DISABLED)
        else:
            messagebox.showinfo("No Previous Folder", "No valid previous folder found.")
        print("DEBUG: on_previous_folder completed") # Debug print

    def on_escape_pressed(self, event=None):
        """Resets focus to the root window, effectively taking focus away from specific widgets."""
        print("DEBUG: on_escape_pressed called, resetting focus.")
        self.root.focus_set()
        return "break" # Prevent further propagation of the Escape key

    # --- Helper Method Stubs ---
    def _load_window_geometry(self): app_utils.load_window_geometry(self)
    def _save_window_geometry(self): app_utils.save_window_geometry(self)
    def _load_last_root_path(self): app_utils.load_last_root_path(self)
    def _save_last_root_path(self, path: str): app_utils.save_last_root_path(self, path)
    def _validate_path(self, path: str) -> tuple[bool, str]: return app_utils.validate_path(path)
    def _log(self, message: str, level: str = "info", buffer_list: list = None): app_utils.log_message(self, message, level, buffer_list)
    def _execute_scaffold(self): scaffold_runner.execute_scaffold(self)
    def _clear_tree(self, tree: ttk.Treeview): clear_tree_function(tree) # Using the aliased import
    def _populate_before_tree(self, root_path: Path): populate_before_tree(self, root_path)
    def _populate_after_tree(self, plan: scaffold_core.Plan): populate_after_tree(self, plan)

def setup_runtime_logging():
    global console_logger_instance, editor_logger_instance
    """Reads config and sets up a file logger if enabled."""
    print("DEBUG: setup_runtime_logging started.")
    try:
        config_file_path = Path.cwd() / CONFIG_FILE
        print(f"DEBUG: Attempting to open config file: {config_file_path}")
        with open(config_file_path, "r") as f:
            config = json.load(f)
        print(f"DEBUG: Config loaded successfully. enable_runtime_logging: {config.get('enable_runtime_logging', False)}")
        
        if config.get("enable_runtime_logging", False):
            log_path_dir = Path.cwd() / LOG_DIR
            log_path_dir.mkdir(exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            runtime_log_filename = log_path_dir / f"runtime_{timestamp}.log"

            # --- Setup Console Logger ---
            console_logger_instance = logging.getLogger('console_output')
            console_logger_instance.setLevel(logging.DEBUG)
            console_file_handler = logging.FileHandler(runtime_log_filename, mode='w', encoding='utf-8')
            console_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            console_logger_instance.addHandler(console_file_handler)
            console_logger_instance.propagate = False # Prevent messages from going to root logger

            # --- Setup Editor Logger ---
            editor_logger_instance = logging.getLogger('editor_output')
            editor_logger_instance.setLevel(logging.DEBUG)
            editor_file_handler = logging.FileHandler(runtime_log_filename, mode='a', encoding='utf-8') # Append to the same file
            editor_file_handler.setFormatter(logging.Formatter('--- editor log ---\n%(asctime)s - %(levelname)s - %(message)s'))
            editor_logger_instance.addHandler(editor_file_handler)
            editor_logger_instance.propagate = False # Prevent messages from going to root logger

            # Redirect stdout and stderr
            sys.stdout = StreamToLogger(console_logger_instance, logging.INFO)
            sys.stderr = StreamToLogger(console_logger_instance, logging.ERROR)

            console_logger_instance.info(f"--- console ---\nRuntime logging enabled, log file: {runtime_log_filename}")
        else:
            print("DEBUG: Runtime logging disabled in config.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"DEBUG: Could not set up runtime logger: {e} (FileNotFoundError or JSONDecodeError)")
    except Exception as e:
        print(f"DEBUG: An unexpected error occurred during runtime logger setup: {e}")
    print("DEBUG: setup_runtime_logging completed.")

def main():
    setup_runtime_logging() # Set up the logger first
    try:
        root = tk.Tk()
        ScaffoldApp(root)
        root.mainloop()
    except Exception as e:
        if console_logger_instance: # Check if console logger was successfully set up
            console_logger_instance.critical(f"FATAL: Caught unhandled exception in main: {e}", exc_info=True)
        else:
            print(f"FATAL: Caught unhandled exception in main (logger not initialized): {e}")
        messagebox.showerror("Fatal Error", f"An unhandled exception occurred: {e}")

if __name__ == "__main__":
    main()