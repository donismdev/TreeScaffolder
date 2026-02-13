# -*- coding: utf-8 -*-
"""
key_bindings.py

Manages keyboard shortcuts for the Tree Scaffolder GUI application.
Loads key mappings from a JSON configuration file.
"""
import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# --- Configuration ---
KEYBINDINGS_CONFIG_FILE = "Resources/key_bindings_map.json"

# --- Helper Functions for Actions ---

# Helper to call methods based on whether they expect an event object
def _call_method_with_event(method, event):
    return method(event)

def _call_method_without_event(method, event):
    # 'event' is received from Tkinter bind, but the method doesn't need it.
    app = method.__self__
    focused_widget = app.root.focus_get()

    if isinstance(focused_widget, (tk.Text, tk.Entry)):
        if hasattr(app, '_log'):
            app._log(f"Shortcut for '{method.__name__}' skipped: Text widget focused.", "info")
        return "break"

    return method()

def _on_load_test_data_conditional(app, event):
    """
    Handles the Spacebar press event.
    Triggers on_load_test_data if focus is NOT on a text/entry widget.
    """
    app._log("Attempting to load test data...", "info")
    focused_widget = app.root.focus_get()
    if isinstance(focused_widget, (tk.Text, tk.Entry)):
        app._log("Load test data skipped: Text/Entry widget focused.", "info")
        return # Do not trigger if focus is on a text input widget
    app.on_load_test_data()
    return "break" # Prevent default spacebar behavior (e.g., scrolling)

def _on_cycle_notebook(app, event, target_notebook_name):
    """
    Handles cycling through tabs of a given ttk.Notebook widget.
    Only triggers if focus is NOT on a text input widget.
    
    Args:
        app: The main ScaffoldApp instance.
        event: The Tkinter event object.
        target_notebook_name (str): The name of the notebook widget attribute on the app instance.
    """
    app._log(f"Attempting to cycle notebook '{target_notebook_name}'...", "info")
    focused_widget = app.root.focus_get()
    if isinstance(focused_widget, (tk.Text, tk.Entry)):
        app._log(f"Cycle notebook '{target_notebook_name}' skipped: Text/Entry widget focused.", "info")
        return # Do not trigger if focus is on a text input widget
        
    try:
        notebook = getattr(app, target_notebook_name)
        if not notebook:
            app._log(f"Notebook '{target_notebook_name}' not found or is None. Skipping cycle.", "warning")
            return
            
        current_tab_index = notebook.index(notebook.select())
        num_tabs = len(notebook.tabs())
        
        if num_tabs > 0:
            next_tab_index = (current_tab_index + 1) % num_tabs
            notebook.select(next_tab_index)
            app._log(f"Successfully cycled notebook '{target_notebook_name}' to tab {next_tab_index}.", "info")
        else:
            app._log(f"Notebook '{target_notebook_name}' has no tabs. Skipping cycle.", "info")
        
    except (AttributeError, tk.TclError) as e:
        # Handle cases where the widget doesn't exist or has no tabs
        print(f"WARNING: Error cycling notebook '{target_notebook_name}': {e}") # Keeping this print for now
        pass
        
    return "break"

# --- Key Binding Loader ---

def _load_key_bindings_config() -> dict:
    """
    Loads key bindings from the JSON configuration file.
    """
    config_path = Path(__file__).parent.parent.parent / KEYBINDINGS_CONFIG_FILE
    if not config_path.exists():
        print(f"WARNING: Key bindings config file not found at {config_path}. Using empty bindings.")
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not decode key bindings config file {config_path}: {e}")
        return {}
    except Exception as e:
        print(f"ERROR: Unexpected error loading key bindings config {config_path}: {e}")
        return {}

def setup_key_bindings(app):
    """
    Sets up global and widget-specific keyboard shortcuts based on a configuration file.
    
    Args:
        app: The main ScaffoldApp instance.
    """
    bindings_map = _load_key_bindings_config()
    
    # Map action names from JSON to actual functions/methods
    action_handlers = {
        "on_load_test_data_conditional": _on_load_test_data_conditional,
        "on_escape_pressed": lambda event: _call_method_with_event(app.on_escape_pressed, event),
        "cycle_notebook": _on_cycle_notebook,
        "on_previous_folder": lambda event: _call_method_without_event(app.on_previous_folder, event),
        "on_browse_folder": lambda event: _call_method_without_event(app.on_browse_folder, event),
        "on_clear_data": lambda event: _call_method_without_event(app.on_clear_data, event),
        "on_recompute": lambda event: _call_method_without_event(app.on_recompute, event),
        "on_apply": lambda event: _call_method_without_event(app.on_apply, event),
    }

    for key_sequence, binding_config in bindings_map.items():
        action_name = binding_config.get("action")
        handler = action_handlers.get(action_name)

        if handler:
            tk_key_sequence = key_sequence_to_tk(key_sequence)

            if action_name == "cycle_notebook":
                target_notebook = binding_config.get("target_notebook")
                if target_notebook:
                    app.root.bind(tk_key_sequence, lambda event, h=handler, tn=target_notebook: h(app, event, tn))
                else:
                    print(f"WARNING: 'target_notebook' missing for cycle_notebook action for key {key_sequence}")
            elif action_name == "on_load_test_data_conditional":
                app.root.bind(tk_key_sequence, lambda event, h=handler: h(app, event))
            else: # Direct method call or simple handler (now always wrapped to handle event argument)
                app.root.bind(tk_key_sequence, lambda event, h=handler: h(event))
        else:
            print(f"WARNING: No handler found for action '{action_name}' for key '{key_sequence}'.")

def key_sequence_to_tk(key_sequence: str) -> str:
    """
    Converts a common key sequence string (e.g., "Ctrl+S") to Tkinter format (e.g., "<Control-s>").
    Handles simple modifiers and special keys.
    """
    parts = key_sequence.split('+')
    tk_parts = []

    for part in parts:
        if part.lower() == "ctrl":
            tk_parts.append("Control")
        elif part.lower() == "alt":
            tk_parts.append("Alt")
        elif part.lower() == "shift":
            tk_parts.append("Shift")
        else: # Handle all other keys
            if part.lower() == "space":
                tk_parts.append("space") # Tkinter expects lowercase "space"
            elif part.lower() == "grave":
                tk_parts.append("grave") # Tkinter expects lowercase "grave"
            elif part.lower() == "escape":
                tk_parts.append("Escape") # Tkinter expects capitalized "Escape"
            else: # All other single keys, numbers, F-keys, etc.
                tk_parts.append(part) # Keep original case for now
    
    if len(tk_parts) > 1: # E.g., <Control-s>
        # Ensure non-modifier keys are lowercased if they are single letters (e.g., <Control-s>)
        # And ensure special keys like Escape keep their case (e.g., <Control-Escape>)
        final_parts = []
        for p in tk_parts:
            if p.lower() in ["control", "alt", "shift", "space", "grave"]: # These are special or should be lowercase
                final_parts.append(p)
            elif p == "Escape": # Explicitly keep Escape capitalized
                final_parts.append(p)
            elif len(p) == 1 and p.isalpha(): # Single letter, lowercase it
                final_parts.append(p.lower())
            else: # Numbers, F-keys, other symbols, keep as is
                final_parts.append(p)
        return f"<{'-'.join(final_parts)}>"
    elif len(tk_parts) == 1:
        single_key = tk_parts[0]
        # For single keys, use <Key-X> format for robustness
        # Except for space and grave which seem to be standard as <space> and <grave>
        if single_key.lower() == "space":
            return "<Key-space>"
        elif single_key.lower() == "grave":
            return "<grave>"
        elif single_key.lower() == "escape": # Escape is working with <Escape>, so let's stick to it.
            return "<Escape>" # Using capitalized for consistency with Tkinter docs
        else:
            # For all other single keys (1, 2, 3, F5, etc.)
            return f"<Key-{single_key}>" # e.g., <Key-1>, <Key-F5>
    return key_sequence # Fallback (should not be reached)