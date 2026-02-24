# -*- coding: utf-8 -*-
"""
options_ui.py

A separate window for application options.
"""
import tkinter as tk
from tkinter import ttk
from Scripts.Utils.i18n import t, set_language, get_current_language

class OptionsWindow:
    _instance = None

    def __init__(self, parent, app_instance):
        if OptionsWindow._instance and OptionsWindow._instance.window.winfo_exists():
            OptionsWindow._instance.window.lift()
            OptionsWindow._instance.window.focus_force()
            return
        
        OptionsWindow._instance = self
        self.app = app_instance
        self.window = tk.Toplevel(parent)
        self.window.title(t("ui.options_title"))
        self.window.geometry("400x350")
        self.window.minsize(300, 250)
        self.window.grab_set()  # Make it modal
        self.window.focus_set() # Set focus to the new window

        # Bind Escape key to close the window
        self.window.bind("<Escape>", lambda e: self._on_close())
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        self.setup_ui()

    def _on_close(self):
        OptionsWindow._instance = None
        self.window.destroy()

    def setup_ui(self):
        # Clear current UI if re-running
        for widget in self.window.winfo_children():
            widget.destroy()

        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=t("ui.options_title"), font=("Segoe UI", 12, "bold")).pack(pady=(0, 20))
        
        # Language Selection
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(lang_frame, text=t("ui.language")).pack(side=tk.LEFT, padx=(0, 10))
        
        self.lang_var = tk.StringVar(value=get_current_language())
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=["ko", "en"], state="readonly", width=10)
        lang_combo.pack(side=tk.LEFT)
        lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        ttk.Label(main_frame, text=t("ui.options_desc")).pack(pady=20)

        # Close button at the bottom
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        ttk.Button(btn_frame, text=t("ui.close"), command=self._on_close).pack(side=tk.RIGHT)
        ttk.Label(btn_frame, text=t("ui.esc_to_close"), foreground="gray").pack(side=tk.RIGHT, padx=10)

    def _on_lang_change(self, event):
        new_lang = self.lang_var.get()
        if new_lang != get_current_language():
            set_language(new_lang)
            # Refresh UI of main app
            if hasattr(self.app, 'refresh_ui'):
                self.app.refresh_ui()
            
            # Update current window strings
            self.window.title(t("ui.options_title"))
            self.setup_ui() 

def show_options(parent, app_instance):
    OptionsWindow(parent, app_instance)
