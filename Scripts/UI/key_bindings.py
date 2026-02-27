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
from Scripts.UI import app_utils

# --- Configuration ---
KEYBINDINGS_CONFIG_FILE = "Resources/key_bindings_map.json"

# --- Helper Functions for Actions ---

def _call_method_with_event(method, event):
    return method(event)

def _call_method_without_event(app, method, event):
    focused_widget = app.root.focus_get()
    if isinstance(focused_widget, (tk.Text, tk.Entry)):
        method_name = getattr(method, "__name__", "unknown")
        app_utils.log_message(app, f"Shortcut for '{method_name}' skipped: Text widget focused.", "info")
        return "break"
    return method()

def _on_load_test_data_conditional(app, event):
    focused_widget = app.root.focus_get()
    if isinstance(focused_widget, (tk.Text, tk.Entry)):
        app_utils.log_message(app, "Load test data skipped: Text/Entry widget focused.", "info")
        return 
    app.on_load_test_data()
    return "break"

def _on_cycle_notebook(app, event, target_notebook_name):
    focused_widget = app.root.focus_get()
    if isinstance(focused_widget, (tk.Text, tk.Entry)):
        app_utils.log_message(app, f"Cycle notebook '{target_notebook_name}' skipped: Text/Entry widget focused.", "info")
        return 
        
    try:
        notebook = getattr(app, target_notebook_name)
        if not notebook:
            app_utils.log_message(app, f"Notebook '{target_notebook_name}' not found. Skipping cycle.", "warn")
            return
            
        current_tab_index = notebook.index(notebook.select())
        num_tabs = len(notebook.tabs())
        
        if num_tabs > 0:
            next_tab_index = (current_tab_index + 1) % num_tabs
            notebook.select(next_tab_index)
        else:
            app_utils.log_message(app, f"Notebook '{target_notebook_name}' has no tabs.", "info")
        
    except (AttributeError, tk.TclError) as e:
        print(f"Error cycling notebook '{target_notebook_name}': {e}")
        
    return "break"

# --- Key Binding Loader ---

def _load_key_bindings_config() -> dict:
    config_path = Path(__file__).parent.parent.parent / KEYBINDINGS_CONFIG_FILE
    if not config_path.exists():
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def setup_key_bindings(app):
    bindings_map = _load_key_bindings_config()
    
    action_handlers = {
        "on_load_test_data_conditional": _on_load_test_data_conditional,
        "on_escape_pressed": lambda event: _call_method_with_event(app.on_escape_pressed, event),
        "cycle_notebook": _on_cycle_notebook,
        "on_previous_folder": lambda event: _call_method_without_event(app, app.on_previous_folder, event),
        "on_browse_folder": lambda event: _call_method_without_event(app, app.on_browse_folder, event),
        "on_clear_data": lambda event: _call_method_without_event(app, app.on_clear_data, event),
        "on_recompute": lambda event: _call_method_without_event(app, app.on_recompute, event),
        "on_apply": lambda event: _call_method_without_event(app, app.on_apply, event),
        "on_options": lambda event: _call_method_without_event(app, app.on_options, event),
        "on_recovery": lambda event: _call_method_without_event(app, app.on_recovery, event),
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
            elif action_name == "on_load_test_data_conditional":
                app.root.bind(tk_key_sequence, lambda event, h=handler: h(app, event))
            else: 
                app.root.bind(tk_key_sequence, lambda event, h=handler: h(event))

def key_sequence_to_tk(key_sequence: str) -> str:
    parts = key_sequence.split('+')
    tk_parts = []
    for part in parts:
        p_low = part.lower()
        if p_low == "ctrl": tk_parts.append("Control")
        elif p_low == "alt": tk_parts.append("Alt")
        elif p_low == "shift": tk_parts.append("Shift")
        elif p_low == "space": tk_parts.append("space")
        elif p_low == "grave": tk_parts.append("grave")
        elif p_low == "escape": tk_parts.append("Escape")
        else: tk_parts.append(part)
    
    if len(tk_parts) > 1:
        final_parts = []
        for p in tk_parts:
            if p.lower() in ["control", "alt", "shift", "space", "grave"]:
                final_parts.append(p)
            elif p == "Escape":
                final_parts.append(p)
            elif len(p) == 1 and p.isalpha():
                final_parts.append(p.lower())
            else:
                final_parts.append(p)
        return f"<{'-'.join(final_parts)}>"
    elif len(tk_parts) == 1:
        single_key = tk_parts[0]
        if single_key.lower() == "space": return "<Key-space>"
        elif single_key.lower() == "grave": return "<grave>"
        elif single_key.lower() == "escape": return "<Escape>"
        else: return f"<Key-{single_key}>"
    return key_sequence
