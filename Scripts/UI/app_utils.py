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

def log_message(app, message: str, level: str = "info", buffer_list: list = None):
    """Appends a message to the log widget, a buffer list, and the runtime log file."""
    # Log to the runtime log file first
    if level == "error":
        logging.error(message)
    elif level == "warn":
        logging.warning(message)
    elif level == "debug":
        logging.debug(message)
    else: # "info", "success", "skip", etc.
        logging.info(message)

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
        if level == "error": color = "red"
        elif level == "warn": color = "#E59400"
        elif level == "success": color = "green"
        elif level == "skip": color = "gray"
        elif level == "debug": color = "purple" # Add debug color for GUI
        app.log_text.tag_configure(tag, foreground=color)

    app.log_text.insert(tk.END, message + '\n', tag)
    app.log_text.see(tk.END)
    app.log_text.config(state=tk.DISABLED)
    app.root.update_idletasks()

def load_window_geometry(app):
    """Loads window geometry from config.json if available, with validation."""
    config_path = Path.cwd() / app.CONFIG_FILE
    loaded_geometry = None
    open_folder_after_apply = False # Default value

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "geometry" in config:
                    loaded_geometry = config["geometry"]
                if "OPEN_FOLDER_AFTER_APPLY" in config:
                    open_folder_after_apply = config["OPEN_FOLDER_AFTER_APPLY"]
        except Exception as e:
            print(f"Error loading window geometry from config: {e}")

    app.open_folder_after_apply.set(open_folder_after_apply)

    if loaded_geometry:
        try:
            match = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", loaded_geometry)
            if match:
                width, height, x, y = map(int, match.groups())
                min_width, min_height = 300, 200
                max_negative_coord = -1000

                if width >= min_width and height >= min_height and x > max_negative_coord and y > max_negative_coord:
                    app.root.geometry(loaded_geometry)
                else:
                    app.root.geometry(app.DEFAULT_GEOMETRY)
            else:
                app.root.geometry(app.DEFAULT_GEOMETRY)
        except Exception as e:
            app.root.geometry(app.DEFAULT_GEOMETRY)
    else:
        app.root.geometry(app.DEFAULT_GEOMETRY)

def save_window_geometry(app):
    """Saves current window geometry to config.json."""
    config_path = Path.cwd() / app.CONFIG_FILE
    try:
        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        
        config["geometry"] = app.root.geometry()
        config["OPEN_FOLDER_AFTER_APPLY"] = app.open_folder_after_apply.get()
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving window geometry: {e}")

def load_last_root_path(app):
    """Loads the last selected root path from config.json and updates UI."""
    print("DEBUG: app_utils.load_last_root_path called")
    config_path = Path.cwd() / app.CONFIG_FILE
    app.last_root_path = None

    if config_path.exists():
        print(f"DEBUG: Found config file: {config_path}")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "last_root_path" in config:
                    path_str = config["last_root_path"]
                    print(f"DEBUG: Found last_root_path in config: '{path_str}'")
                    is_dir = Path(path_str).is_dir()
                    print(f"DEBUG: Path('{path_str}').is_dir() = {is_dir}")
                    if is_dir:
                        app.last_root_path = path_str
        except Exception as e:
            print(f"DEBUG: Error loading last root path from config: {e}")
    else:
        print(f"DEBUG: Config file not found at {config_path}")
    
    print(f"DEBUG: Final app.last_root_path = '{app.last_root_path}'")
    if app.last_root_path:
        print("DEBUG: Enabling 'Prev' button.")
        app.prev_dir_button.config(state=tk.NORMAL)
    else:
        print("DEBUG: Disabling 'Prev' button.")
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
        print(f"Error saving last root path: {e}")

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
