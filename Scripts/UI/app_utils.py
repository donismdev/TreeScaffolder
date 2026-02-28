# -*- coding: utf-8 -*-
"""
app_utils.py

Utility functions for the Tree Scaffolder GUI application, including logging,
window geometry management, and path validation.
"""
import json
import logging
import re
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from Scripts.Utils import logger
from Scripts.Utils.i18n import t

def show_notification(app, ntype: str, title: str, message: str, icon: str = None) -> bool:
    """
    Centralized notification handler. 
    Abstraction layer for messagebox to allow easier unit testing (Mocking).
    ntype: 'info', 'warning', 'error', 'yesno'
    """
    if ntype == 'info':
        messagebox.showinfo(title, message)
        return True
    elif ntype == 'warning':
        messagebox.showwarning(title, message)
        return True
    elif ntype == 'error':
        messagebox.showerror(title, message)
        return True
    elif ntype == 'yesno':
        return messagebox.askyesno(title, message, icon=icon if icon else 'question')
    return False

def get_folder_stats(path: Path) -> dict:
    """
    Pure logic function to count contents of a folder.
    Returns statistics about files, directories, and .gitkeep files.
    """
    stats = {"files": 0, "dirs": 0, "gitkeep": 0, "normal": 0, "total": 0}
    try:
        for item in path.rglob('*'):
            if item.is_file():
                stats["files"] += 1
                if item.name == ".gitkeep":
                    stats["gitkeep"] += 1
                else:
                    stats["normal"] += 1
            elif item.is_dir():
                stats["dirs"] += 1
        stats["total"] = stats["files"] + stats["dirs"]
    except Exception:
        pass # Errors handled by caller
    return stats

def log_message(app, message: str, level: str = "info", buffer_list: list = None):
    """Appends a message to the log widget, a buffer list, and the runtime log file."""
    # Log to the dedicated editor runtime log file
    editor_logger = logging.getLogger('editor_output')
    if editor_logger.handlers: # Check if the logger has handlers (i.e., is configured)
        if level == "error":
            editor_logger.error(message)
        elif level == "warn":
            editor_logger.warning(message)
        elif level == "debug":
            editor_logger.debug(message)
        else: # "info", "success", "skip", etc.
            editor_logger.info(message)

    if buffer_list is not None:
        buffer_list.append((message, level))
        return

    if not hasattr(app, 'log_text') or app.log_text is None:
        print(f"[{level.upper()}]: {message}")
        return

    app.log_text.config(state=tk.NORMAL)
    tag = f"log_{level}"
    if tag not in app.log_text.tag_names():
        color = "black"
        font_weight = "normal"
        if level == "error": color = "red"
        elif level == "warn": color = "#E59400"
        elif level == "success": color = "green"
        elif level == "skip": color = "gray"
        elif level == "debug": color = "purple"
        elif level == "overwrite": 
            color = "#0078D7"
            font_weight = "bold"
        
        log_font = ("Consolas", 10, "bold") if font_weight == "bold" else ("Consolas", 9)
        app.log_text.tag_configure(tag, foreground=color, font=log_font)

    app.log_text.insert(tk.END, message + '\n', tag)
    app.log_text.see(tk.END)
    app.log_text.config(state=tk.DISABLED)
    app.root.update_idletasks()

def load_window_geometry(app):
    """Loads window geometry and sash positions from config.json if available."""
    config_path = Path.cwd() / app.CONFIG_FILE
    loaded_geometry = None
    open_folder_after_apply = False
    main_sash_pos_loaded = None
    diff_sash_pos_loaded = None
    window_state_loaded = None

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "geometry" in config: loaded_geometry = config["geometry"]
                if "OPEN_FOLDER_AFTER_APPLY" in config: open_folder_after_apply = config["OPEN_FOLDER_AFTER_APPLY"]
                if "window_state" in config: window_state_loaded = config["window_state"]
                if "main_sash_pos" in config: main_sash_pos_loaded = config["main_sash_pos"]
                if "diff_sash_pos" in config: diff_sash_pos_loaded = config["diff_sash_pos"]
        except Exception as e:
            logger.error(f"Error loading window config: {e}")
            config = {}
    else:
        config = {}

    app.open_folder_after_apply.set(open_folder_after_apply)
    geometry_to_apply = app.DEFAULT_GEOMETRY
    if loaded_geometry:
        try:
            match = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", loaded_geometry)
            if match:
                width, height, x, y = map(int, match.groups())
                if width >= 300 and height >= 200: geometry_to_apply = loaded_geometry
        except: pass
    
    app.root.geometry(geometry_to_apply)
    if window_state_loaded in ['normal', 'zoomed', 'iconic']:
        try: app.root.state(window_state_loaded)
        except: app.root.state('normal')

    app.root.update_idletasks()

    if hasattr(app, 'main_paned_window') and app.main_paned_window.winfo_exists():
        paned_width = app.main_paned_window.winfo_width()
        if isinstance(main_sash_pos_loaded, int) and 0 < main_sash_pos_loaded < paned_width:
            app.main_paned_window.sash_place(0, main_sash_pos_loaded, 0)
        else:
            default_pos = paned_width // 3
            if default_pos > 0: app.main_paned_window.sash_place(0, default_pos, 0)

    if hasattr(app, 'diff_paned_window') and app.diff_paned_window.winfo_exists():
        diff_frame_width = app.diff_paned_window.master.winfo_width()
        if isinstance(diff_sash_pos_loaded, int) and 0 < diff_sash_pos_loaded < diff_frame_width:
            app.diff_paned_window.sash_place(0, diff_sash_pos_loaded, 0)
        else:
            default_pos = diff_frame_width // 2
            if default_pos > 0: app.diff_paned_window.sash_place(0, default_pos, 0)

def save_window_geometry(app):
    """Saves current window geometry and sash positions to config.json."""
    config_path = Path.cwd() / app.CONFIG_FILE
    try:
        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        
        config["geometry"] = app.root.geometry()
        config["window_state"] = app.root.state()
        config["OPEN_FOLDER_AFTER_APPLY"] = app.open_folder_after_apply.get()

        if hasattr(app, 'main_paned_window') and app.main_paned_window.winfo_exists():
            config["main_sash_pos"] = app.main_paned_window.sash_coord(0)[0]
        
        if hasattr(app, 'diff_paned_window') and app.diff_paned_window.winfo_exists():
            config["diff_sash_pos"] = app.diff_paned_window.sash_coord(0)[0]
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving window config: {e}")

def load_last_root_path(app):
    """Loads the last selected root path from config.json and updates UI."""
    config_path = Path.cwd() / app.CONFIG_FILE
    app.last_root_path = None
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "last_root_path" in config:
                    path_str = config["last_root_path"]
                    if Path(path_str).is_dir(): app.last_root_path = path_str
        except: pass
    
    if app.last_root_path: app.prev_dir_button.config(state=tk.NORMAL)
    else: app.prev_dir_button.config(state=tk.DISABLED)

def save_last_root_path(app, path: str):
    """Saves the given path as the last selected root path to config.json."""
    config_path = Path.cwd() / app.CONFIG_FILE
    try:
        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        config["last_root_path"] = path
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        app.last_root_path = path
        app.prev_dir_button.config(state=tk.NORMAL)
    except Exception as e:
        logger.error(f"Error saving last root path: {e}")

def is_path_accessible(path_str: str) -> tuple[bool, str]:
    """Quick check for path existence and directory type."""
    if not path_str: return False, "No path provided."
    try:
        p = Path(path_str).resolve(strict=True)
        if not p.is_dir(): return False, f"Not a directory: {path_str}"
        return True, str(p)
    except Exception as e:
        return False, str(e)

def verify_and_set_root(app, path_str: str, method: str = "browse") -> bool:
    """Centralized logic to validate a path and update the app's root folder state."""
    from Scripts.UI.action_handler import handle_folder_selected
    from Scripts.UI.tree_populator import populate_before_tree, _clear_tree as clear_tree_function
    
    is_valid, result = validate_path(path_str)
    if not is_valid:
        show_notification(app, 'error', t("message.invalid_folder_title"), result)
        if method in ("prev", "recovery"):
            app.target_root_path.set(t("ui.no_folder_selected"))
            app.last_root_path = ""
            save_last_root_path(app, "")
            app.prev_dir_button.config(state=tk.DISABLED)
            app.recompute_button.config(state=tk.DISABLED)
            app.apply_button.config(state=tk.DISABLED)
            clear_tree_function(app.before_tree)
            clear_tree_function(app.before_list)
        return False

    app.target_root_path.set(result)
    save_last_root_path(app, result)
    app.recompute_button.config(state=tk.NORMAL)
    populate_before_tree(app, Path(result))
    clear_tree_function(app.after_tree)
    clear_tree_function(app.after_list)
    app.apply_button.config(state=tk.DISABLED)
    handle_folder_selected(app, result, method=method)
    return True

def validate_path(path: str) -> tuple[bool, str]:
    """Calls the external validator script and returns (is_valid, message)."""
    try:
        python_exe = sys.executable
        if sys.platform == 'win32' and python_exe.endswith('python.exe'):
            python_exe = python_exe.replace("python.exe", "pythonw.exe")
        validator_script = Path(__file__).parent.parent / "Utils" / "folder_selection_validator.py"
        if not validator_script.exists(): return False, "Validator script missing."
        run_kwargs = {'capture_output': True, 'check': True}
        if sys.platform == 'win32': run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        process = subprocess.run([python_exe, str(validator_script), path], **run_kwargs)
        result = json.loads(process.stdout.decode('utf-8', errors='replace'))
        if result["ok"]: return True, result["resolved_path"]
        else: return False, "\n".join(result["errors"])
    except Exception as e:
        return False, str(e)
