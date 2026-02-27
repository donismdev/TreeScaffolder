# -*- coding: utf-8 -*-
"""
options_ui.py

A separate window for application options.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from Scripts.Utils.i18n import t, set_language, get_current_language
from Scripts.UI import action_handler

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
        self.window.geometry("400x450")
        self.window.minsize(350, 400)
        self.window.grab_set()  # Make it modal
        self.window.focus_set() # Set focus to the new window

        # Bind Escape key to close the window
        self.window.bind("<Escape>", lambda e: self._on_close())
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        self.setup_ui()

    def _on_close(self):
        OptionsWindow._instance = None
        action_handler.handle_options_closed(self.app)
        self.window.destroy()

    def _load_config(self):
        import json
        from pathlib import Path
        config_path = Path("Resources/config.json")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self, key, value):
        import json
        from pathlib import Path
        config_path = Path("Resources/config.json")
        config = self._load_config()
        config[key] = value
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass

    def setup_ui(self):
        # Clear current UI if re-running
        for widget in self.window.winfo_children():
            widget.destroy()

        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=t("ui.options_title"), font=("Segoe UI", 11, "bold")).pack(pady=(0, 15))
        
        # Language Selection
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(lang_frame, text=t("ui.language")).pack(side=tk.LEFT, padx=(0, 10))
        
        self.lang_var = tk.StringVar(value=get_current_language())
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=["ko", "en"], state="readonly", width=10)
        lang_combo.pack(side=tk.LEFT)
        lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        # Debug Level Selection
        debug_frame = ttk.Frame(main_frame)
        debug_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(debug_frame, text=t("ui.debug_level") if "ui.debug_level" in t("ui") else "Debug Level").pack(side=tk.LEFT, padx=(0, 10))
        
        from Scripts.Utils import logger
        self.debug_var = tk.IntVar(value=logger.get_log_level())
        debug_combo = ttk.Combobox(debug_frame, textvariable=self.debug_var, values=[0, 1, 2, 3], state="readonly", width=5)
        debug_combo.pack(side=tk.LEFT)
        debug_combo.bind("<<ComboboxSelected>>", self._on_debug_change)

        # Runtime Logging Toggle
        config = self._load_config()
        self.logging_var = tk.BooleanVar(value=config.get("enable_runtime_logging", False))
        logging_check = ttk.Checkbutton(
            main_frame, 
            text=t("ui.runtime_logging"), 
            variable=self.logging_var,
            command=lambda: self._save_config("enable_runtime_logging", self.logging_var.get())
        )
        logging_check.pack(fill=tk.X, pady=(10, 5))

        # Log Cleanup Section
        cleanup_frame = ttk.LabelFrame(main_frame, text=t("ui.log_cleanup_title") if "ui.log_cleanup_title" in t("ui") else "Log Cleanup", padding=10)
        cleanup_frame.pack(fill=tk.X, pady=10)

        limit_frame = ttk.Frame(cleanup_frame)
        limit_frame.pack(fill=tk.X)
        
        limit_label_text = t("ui.keep_n_logs") if "ui.keep_n_logs" in t("ui") else "Keep last N logs:"
        self.limit_label = ttk.Label(limit_frame, text=f"{limit_label_text} {config.get('log_cleanup_limit', 5)}")
        self.limit_label.pack(side=tk.LEFT)

        self.cleanup_limit_var = tk.IntVar(value=config.get("log_cleanup_limit", 5))
        
        def on_slider_move(val):
            val = int(float(val))
            self.limit_label.config(text=f"{limit_label_text} {val}")
            self._save_config("log_cleanup_limit", val)

        limit_slider = ttk.Scale(cleanup_frame, from_=1, to=50, variable=self.cleanup_limit_var, orient=tk.HORIZONTAL, command=on_slider_move)
        limit_slider.pack(fill=tk.X, pady=5)

        cleanup_btn = ttk.Button(cleanup_frame, text=t("ui.cleanup_now") if "ui.cleanup_now" in t("ui") else "Clean up logs", command=self._on_cleanup_logs)
        cleanup_btn.pack(pady=(5, 0))

        # Close button at the bottom
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text=t("ui.close"), command=self._on_close).pack(side=tk.RIGHT)
        ttk.Label(btn_frame, text=t("ui.esc_to_close"), foreground="gray", font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=10)

    def _on_lang_change(self, event):
        new_lang = self.lang_var.get()
        if new_lang != get_current_language():
            set_language(new_lang)
            # Refresh UI of main app
            if hasattr(self.app, 'refresh_ui'):
                self.app.refresh_ui()
                action_handler.handle_language_changed(self.app)
            
            # Update current window strings
            self.window.title(t("ui.options_title"))
            self.setup_ui() 

    def _on_debug_change(self, event):
        new_level = int(self.debug_var.get())
        from Scripts.Utils import logger
        logger.set_log_level(new_level)
        self._save_config("debug_level", new_level)

    def _on_cleanup_logs(self):
        from pathlib import Path
        import os
        
        limit = self.cleanup_limit_var.get()
        title = t("message.confirm_cleanup_title") if "message.confirm_cleanup_title" in t("message") else "Confirm Cleanup"
        msg = t("message.confirm_cleanup_msg") if "message.confirm_cleanup_msg" in t("message") else f"This will delete all but the last {limit} logs of each type.\nAre you sure? This cannot be undone."
        msg = msg.format(n=limit) # Support {n} in translation

        if not messagebox.askyesno(title, msg, icon='warning'):
            return

        log_dir = Path.cwd() / "Log"
        if not log_dir.exists():
            return

        prefixes = ["runtime_", "scaffold_execution_", "scaffold_recovery_"]
        deleted_count = 0
        
        for prefix in prefixes:
            # Find files matching prefix
            files = [f for f in log_dir.glob(f"{prefix}*.log")]
            # Also catch .txt for recovery
            if prefix == "scaffold_recovery_":
                files.extend([f for f in log_dir.glob(f"{prefix}*.txt")])
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only the first 'limit' files
            to_delete = files[limit:]
            for f in to_delete:
                try:
                    f.unlink()
                    deleted_count += 1
                except Exception:
                    pass
        
        messagebox.showinfo(t("message.success_title"), t("message.cleanup_success").format(count=deleted_count) if "message.cleanup_success" in t("message") else f"Successfully deleted {deleted_count} old log files.")

def show_options(parent, app_instance):
    OptionsWindow(parent, app_instance)
