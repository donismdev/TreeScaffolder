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
    app.root.bind("<Escape>", app.on_escape_pressed) # Add this line

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
