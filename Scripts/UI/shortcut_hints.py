# -*- coding: utf-8 -*-
"""
shortcut_hints.py

Manages the display of keyboard shortcut hints over UI elements.
"""
import tkinter as tk
from tkinter import ttk

class ShortcutHintManager:
    """
    Creates, displays, and hides labels for keyboard shortcuts
    over their corresponding UI widgets.
    """

    def __init__(self, app):
        """
        Initializes the ShortcutHintManager.
        
        Args:
            app: The main ScaffoldApp instance.
        """
        self.app = app
        self._hint_labels = []
        self._key_bindings = self.app.key_bindings_map

    def show_hints(self, event=None):
        """
        Creates and displays shortcut hint labels over the mapped widgets.
        """
        self.hide_hints() # Clear any existing hints
        self.app.root.update_idletasks() # Ensure widget positions are up-to-date

        for key_sequence, binding_config in self._key_bindings.items():
            action_name = binding_config.get("action")
            
            map_key = action_name
            if action_name == "cycle_notebook":
                target_notebook = binding_config.get("target_notebook")
                if target_notebook:
                    map_key = f"{action_name}_{target_notebook}"

            widget = self.app.widget_map.get(map_key)

            if widget and widget.winfo_ismapped():
                # Get the widget's absolute screen coordinates
                widget_x = widget.winfo_rootx()
                widget_y = widget.winfo_rooty()
                
                # Get the root window's absolute screen coordinates
                root_x = self.app.root.winfo_rootx()
                root_y = self.app.root.winfo_rooty()

                # Calculate the position relative to the root window
                x = widget_x - root_x
                y = widget_y - root_y
                
                # Create a hint label as a child of the root window
                hint_label = ttk.Label(
                    self.app.root, 
                    text=key_sequence.upper(), 
                    relief="solid", 
                    background="yellow", 
                    foreground="black",
                    padding=(2, 0)
                )

                # Place the hint label using absolute coordinates within the root window
                hint_label.place(x=x + 5, y=y - 10)
                
                self._hint_labels.append(hint_label)

    def hide_hints(self, event=None):
        """
        Destroys all currently visible shortcut hint labels.
        """
        for label in self._hint_labels:
            label.destroy()
        self._hint_labels = []