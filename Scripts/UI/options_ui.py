# -*- coding: utf-8 -*-
"""
options_ui.py

A separate window for application options.
"""
import tkinter as tk
from tkinter import ttk

class OptionsWindow:
    _instance = None

    def __init__(self, parent):
        if OptionsWindow._instance and OptionsWindow._instance.window.winfo_exists():
            OptionsWindow._instance.window.lift()
            OptionsWindow._instance.window.focus_force()
            return
        
        OptionsWindow._instance = self
        self.window = tk.Toplevel(parent)
        self.window.title("Options")
        self.window.geometry("400x300")
        self.window.minsize(300, 200)
        self.window.grab_set()  # Make it modal
        self.window.focus_set() # Set focus to the new window

        # Bind Escape key to close the window
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Application Options", font=("Segoe UI", 12, "bold")).pack(pady=(0, 20))
        
        # Placeholder content
        ttk.Label(main_frame, text="Settings will be added here.").pack()

        # Close button at the bottom
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        ttk.Button(btn_frame, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)
        ttk.Label(btn_frame, text="(Esc to close)", foreground="gray").pack(side=tk.RIGHT, padx=10)

def show_options(parent):
    OptionsWindow(parent)
