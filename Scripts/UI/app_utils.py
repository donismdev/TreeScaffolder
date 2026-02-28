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
    # If editor_logger is not configured, messages won't go to runtime.log here.
    # They will still go to app.log_text below.

    if buffer_list is not None:
        buffer_list.append((message, level))
        return

    # Ensure app.log_text is accessible and configured
    if not hasattr(app, 'log_text') or app.log_text is None:
        # Fallback to print if log_text is not yet initialized (should not happen in normal flow)
        print(f"[{level.upper()}]: {message}")
        return

    app.log_text.config(state=tk.NORMAL)
    
    tag = f"log_{level}"
    # Configure tag only if not already configured
    if tag not in app.log_text.tag_names(): # Use tag_names() for robustness
        color = "black"
        font_weight = "normal"
        if level == "error": color = "red"
        elif level == "warn": color = "#E59400"
        elif level == "success": color = "green"
        elif level == "skip": color = "gray"
        elif level == "debug": color = "purple"
        elif level == "overwrite": 
            color = "#0078D7" # Blue
            font_weight = "bold"
        
        # Get current font and modify it
        current_font = app.log_text.cget("font")
        # In Tkinter, if font is a string like 'Consolas 9', we can modify it
        # but a safer way for bolding is using a tuple or a font object.
        # Since we have app.editor_font, but log_text has its own.
        log_font = ("Consolas", 10, "bold") if font_weight == "bold" else ("Consolas", 9)
        
        app.log_text.tag_configure(tag, foreground=color, font=log_font)

    app.log_text.insert(tk.END, message + '\n', tag)
    app.log_text.see(tk.END)
    app.log_text.config(state=tk.DISABLED)
    app.root.update_idletasks()

def load_window_geometry(app):
    """Loads window geometry and sash positions from config.json if available, with validation."""
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
                if "geometry" in config:
                    loaded_geometry = config["geometry"]
                if "OPEN_FOLDER_AFTER_APPLY" in config:
                    open_folder_after_apply = config["OPEN_FOLDER_AFTER_APPLY"]
                if "window_state" in config:
                    window_state_loaded = config["window_state"]
                if "main_sash_pos" in config:
                    main_sash_pos_loaded = config["main_sash_pos"]
                if "diff_sash_pos" in config:
                    diff_sash_pos_loaded = config["diff_sash_pos"]
        except Exception as e:
            logger.error(f"Error loading window config: {e}")
            # Ensure config is initialized to an empty dict if loading fails to prevent KeyErrors
            config = {}
    else:
        config = {} # Initialize config as empty if file doesn't exist

    logger.debug(f"Loaded geometry from config: {loaded_geometry}, state: {window_state_loaded}")

    app.open_folder_after_apply.set(open_folder_after_apply)

    # Determine the geometry to apply
    geometry_to_apply = app.DEFAULT_GEOMETRY
    logger.debug(f"Applying geometry: {geometry_to_apply}")
    if loaded_geometry:
        try:
            match = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", loaded_geometry)
            if match:
                width, height, x, y = map(int, match.groups())
                min_width, min_height = 300, 200
                max_negative_coord = -1000 # Allow slight negative coordinates for multi-monitor setups

                # Ensure dimensions are reasonable and position is not excessively off-screen
                if width >= min_width and height >= min_height and x > max_negative_coord and y > max_negative_coord:
                    geometry_to_apply = loaded_geometry
                else:
                    # Invalid geometry, revert to default and mark for saving
                    logger.warn(f"Loaded geometry '{loaded_geometry}' is invalid. Using default.")
            else:
                # Malformed geometry string, revert to default and mark for saving
                logger.warn(f"Loaded geometry string '{loaded_geometry}' is malformed. Using default.")
        except Exception as e:
            # Error during parsing, revert to default and mark for saving
            logger.error(f"Error parsing loaded geometry '{loaded_geometry}': {e}. Using default.")
    
    app.root.geometry(geometry_to_apply)
    logger.debug(f"After applying geometry, current: {app.root.geometry()}")

    # Apply window state (e.g., 'zoomed')
    if window_state_loaded in ['normal', 'zoomed', 'iconic']: # Tkinter states
        logger.debug(f"Applying window state: {window_state_loaded}")
        try:
            app.root.state(window_state_loaded)
        except tk.TclError as e:
            logger.warn(f"Could not apply window state '{window_state_loaded}': {e}. Setting to 'normal'.")
            app.root.state('normal')
            config["window_state"] = 'normal' # Update config if state fails
        logger.debug(f"After applying state, current state: {app.root.state()}")

    # Ensure widgets are updated so their sizes are available for sash positioning
    app.root.update_idletasks()

    # Load main_sash_pos
    if hasattr(app, 'main_paned_window') and app.main_paned_window.winfo_exists():
        paned_width = app.main_paned_window.winfo_width()
        if isinstance(main_sash_pos_loaded, int) and 0 < main_sash_pos_loaded < paned_width:
            app.main_paned_window.sash_place(0, main_sash_pos_loaded, 0)
        else:
            default_pos = paned_width // 3 # Default to 1/3 of the width for main panel
            if default_pos > 0: # Ensure default position is valid
                app.main_paned_window.sash_place(0, default_pos, 0)
                config["main_sash_pos"] = default_pos
            else:
                config["main_sash_pos"] = 0 # Fallback for very small initial widths

    # Load diff_sash_pos
    if hasattr(app, 'diff_paned_window') and app.diff_paned_window.winfo_exists():
        # The actual width for diff_paned_window is the width of its parent frame in diff_frame
        diff_frame_width = app.diff_paned_window.master.winfo_width()
        
        if isinstance(diff_sash_pos_loaded, int) and 0 < diff_sash_pos_loaded < diff_frame_width:
            app.diff_paned_window.sash_place(0, diff_sash_pos_loaded, 0)
        else:
            default_pos = diff_frame_width // 2 # Default to half for diff panel
            if default_pos > 0: # Ensure default position is valid
                app.diff_paned_window.sash_place(0, default_pos, 0)
                config["diff_sash_pos"] = default_pos
            else:
                config["diff_sash_pos"] = 0 # Fallback for very small initial widths
    
    # If any defaults were set or state was adjusted, save the config
    if loaded_geometry != geometry_to_apply or window_state_loaded != app.root.state() or \
       "main_sash_pos" in config or "diff_sash_pos" in config: # Check if sashes were defaulted
        try:
            # Ensure we're saving the *current* state if defaults were applied
            config["geometry"] = app.root.geometry()
            config["window_state"] = app.root.state()

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving updated config with default geometry/state/sash positions: {e}")

def save_window_geometry(app):
    """Saves current window geometry and sash positions to config.json."""
    config_path = Path.cwd() / app.CONFIG_FILE
    try:
        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        
        config["geometry"] = app.root.geometry()
        config["window_state"] = app.root.state() # New: save window state
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
    logger.debug("app_utils.load_last_root_path called")
    config_path = Path.cwd() / app.CONFIG_FILE
    app.last_root_path = None

    if config_path.exists():
        logger.debug(f"Found config file: {config_path}")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "last_root_path" in config:
                    path_str = config["last_root_path"]
                    logger.debug(f"Found last_root_path in config: '{path_str}'")
                    is_dir = Path(path_str).is_dir()
                    logger.debug(f"Path('{path_str}').is_dir() = {is_dir}")
                    if is_dir:
                        app.last_root_path = path_str
        except Exception as e:
            logger.debug(f"Error loading last root path from config: {e}")
    else:
        logger.debug(f"Config file not found at {config_path}")
    
    logger.debug(f"Final app.last_root_path = '{app.last_root_path}'")
    if app.last_root_path:
        logger.debug("Enabling 'Prev' button.")
        app.prev_dir_button.config(state=tk.NORMAL)
    else:
        logger.debug("Disabling 'Prev' button.")
        app.prev_dir_button.config(state=tk.DISABLED)

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
    """Quick check for path existence, directory type, and basic accessibility."""
    if not path_str:
        return False, "No path provided."
    try:
        p = Path(path_str).resolve(strict=True)
        if not p.is_dir():
            return False, f"Path exists but is not a directory: {path_str}"
        # Basic write test (optional, but good for robust check)
        return True, str(p)
    except (FileNotFoundError, PermissionError) as e:
        return False, f"Path inaccessible or not found: {e}"
    except Exception as e:
        return False, f"Unexpected error checking path: {e}"

def verify_and_set_root(app, path_str: str, method: str = "browse") -> bool:
    """Centralized logic to validate a path and update the app's root folder state."""
    from Scripts.UI.action_handler import handle_folder_selected
    from Scripts.UI.tree_populator import populate_before_tree, _clear_tree as clear_tree_function
    
    is_valid, result = validate_path(path_str)
    if not is_valid:
        messagebox.showerror(t("message.invalid_folder_title"), result)
        # If the failure happened during 'prev' or 'recovery', it means the stored path is stale
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

    # Path is valid, update app state
    app.target_root_path.set(result)
    save_last_root_path(app, result)
    app.recompute_button.config(state=tk.NORMAL)
    populate_before_tree(app, Path(result))
    
    # Reset subsequent analysis views
    clear_tree_function(app.after_tree)
    clear_tree_function(app.after_list)
    app.apply_button.config(state=tk.DISABLED)
    
    handle_folder_selected(app, result, method=method)
    return True

def validate_path(path: str) -> tuple[bool, str]:
    """Calls the external validator script and returns (is_valid, message)."""
    process = None
    try:
        python_exe = sys.executable
        if sys.platform == 'win32' and python_exe.endswith('python.exe'):
            python_exe = python_exe.replace("python.exe", "pythonw.exe")
        
        validator_script = Path(__file__).parent.parent / "Utils" / "folder_selection_validator.py"
        
        if not validator_script.exists():
            return False, "folder_selection_validator.py not found in the script directory."

        run_kwargs = {'capture_output': True, 'text': True, 'check': True}
        if sys.platform == 'win32':
            run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        process = subprocess.run([python_exe, str(validator_script), path], **run_kwargs)
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
