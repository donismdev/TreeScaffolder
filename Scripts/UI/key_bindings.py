# -*- coding: utf-8 -*-
"""
key_bindings.py

Manages keyboard shortcuts for the Tree Scaffolder GUI application.
"""
import tkinter as tk

def setup_key_bindings(app):
    """
    Sets up global and widget-specific keyboard shortcuts.
    
    Args:
        app: The main ScaffoldApp instance.
    """
    # Global binding for Spacebar to trigger Load Test Data
    # Only trigger if focus is NOT on a text widget or entry widget
    app.root.bind("<space>", lambda event: _handle_space_press(app, event))
    
    # Global binding for Escape to reset focus
    app.root.bind("<Escape>", app.on_escape_pressed)

    # Bindings for cycling through notebook tabs
    app.root.bind("<grave>", lambda event: _handle_notebook_cycle(app, event, 'notebook'))
    app.root.bind("1", lambda event: _handle_notebook_cycle(app, event, 'before_notebook'))
    app.root.bind("2", lambda event: _handle_notebook_cycle(app, event, 'after_notebook'))
    app.root.bind("3", lambda event: _handle_notebook_cycle(app, event, 'editor_notebook'))

def _handle_notebook_cycle(app, event, notebook_widget_name):
    """
    Handles cycling through tabs of a given ttk.Notebook widget.
    
    Args:
        app: The main ScaffoldApp instance.
        event: The Tkinter event object.
        notebook_widget_name (str): The name of the notebook widget on the app instance (e.g., 'notebook', 'editor_notebook').
    """
    focused_widget = app.root.focus_get()
    if isinstance(focused_widget, (tk.Text, tk.Entry)):
        return # Do not trigger if focus is on a text input widget
        
    try:
        notebook = getattr(app, notebook_widget_name)
        if not notebook:
            return
            
        current_tab_index = notebook.index(notebook.select())
        num_tabs = len(notebook.tabs())
        
        if num_tabs > 0: # Prevent division by zero if no tabs
            next_tab_index = (current_tab_index + 1) % num_tabs
            notebook.select(next_tab_index)
        
    except (AttributeError, tk.TclError):
        # Handle cases where the widget doesn't exist or has no tabs
        pass
        
    return "break"

def _handle_space_press(app, event):
    """
    Handles the spacebar press event.
    Triggers on_load_test_data if focus is not on a text/entry widget.
    """
    focused_widget = app.root.focus_get()
    # Check if the focused widget is a Text widget (e.g., editors, log_text)
    # or an Entry widget (e.g., target_root_path entry)
    if isinstance(focused_widget, (tk.Text, tk.Entry)):
        return # Do not trigger if focus is on a text input widget

    # Trigger the on_load_test_data method
    app.on_load_test_data()
    # Prevent default spacebar behavior (e.g., scrolling)
    return "break"
