# -*- coding: utf-8 -*-
"""
options_ui.py

A separate window for application options.
"""
import json
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from Scripts.Utils.i18n import t, set_language, get_current_language
from Scripts.UI import app_utils

def _validate_geometry(geom_str, min_w=400, min_h=500):
    """Validates geometry string and ensures it's within reasonable bounds."""
    try:
        if not geom_str: return False
        # Expected format: WxH+X+Y
        match = re.match(r"(\d+)x(\d+)\+?(-?\d+)\+?(-?\d+)", geom_str)
        if not match: return False
        
        w, h, x, y = map(int, match.groups())
        if w < min_w or h < min_h: return False
        # Loose screen bound check to allow multi-monitor setups
        if x < -5000 or x > 5000 or y < -5000 or y > 5000: return False
        return True
    except: return False

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
        
        # Increased default and min size to ensure buttons are not hidden
        self.window.geometry("450x550")
        self.window.minsize(400, 500)
        self._load_geometry()

        self.window.grab_set()  # Make it modal
        self.window.focus_set() # Set focus to the new window

        # Bind events
        self.window.bind("<Escape>", lambda e: self._on_close())
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.bind("<Destroy>", lambda e: self._save_geometry() if e.widget == self.window else None)

        self.setup_ui()

    def _on_close(self):
        OptionsWindow._instance = None
        from Scripts.UI import action_handler
        action_handler.handle_options_closed(self.app)
        self.window.destroy()

    def _load_config(self):
        return app_utils.load_config(self.app.CONFIG_FILE)

    def _save_config(self, key, value):
        config = self._load_config()
        config[key] = value
        app_utils.save_config(self.app.CONFIG_FILE, config)

    def _load_geometry(self):
        app_utils.load_popup_window_geometry(self.window, self.app.CONFIG_FILE, "options_window_geometry", 400, 500)

    def _save_geometry(self):
        app_utils.save_popup_window_geometry(self.window, self.app.CONFIG_FILE, "options_window_geometry")

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
        
        ttk.Label(debug_frame, text=t("ui.debug_level")).pack(side=tk.LEFT, padx=(0, 10))
        
        from Scripts.Utils import logger
        self.debug_var = tk.IntVar(value=logger.get_log_level())
        debug_combo = ttk.Combobox(debug_frame, textvariable=self.debug_var, values=[0, 1, 2, 3], state="readonly", width=5)
        debug_combo.pack(side=tk.LEFT)
        debug_combo.bind("<<ComboboxSelected>>", self._on_debug_change)

        # Application Settings Section
        settings_group = ttk.LabelFrame(main_frame, text=t("ui.section_3"), padding=10)
        settings_group.pack(fill=tk.X, pady=10)

        # Open Folder after Apply
        self.open_folder_var = tk.BooleanVar(value=self.app.open_folder_after_apply.get())
        def toggle_open_folder():
            from Scripts.UI import action_handler
            val = self.open_folder_var.get()
            self.app.open_folder_after_apply.set(val)
            self._save_config("OPEN_FOLDER_AFTER_APPLY", val)
            action_handler.handle_toggle_open_after(self.app, val)

        ttk.Checkbutton(settings_group, text=t("ui.open_after"), variable=self.open_folder_var, command=toggle_open_folder).pack(anchor="w", pady=2)

        # Create .gitkeep
        self.create_gitkeep_var = tk.BooleanVar(value=self.app.create_gitkeep.get())
        def toggle_gitkeep():
            from Scripts.UI import action_handler
            val = self.create_gitkeep_var.get()
            self.app.create_gitkeep.set(val)
            self._save_config("CREATE_GITKEEP", val)
            action_handler.update_summary(self.app, "gitkeep_on" if val else "gitkeep_off")

        ttk.Checkbutton(settings_group, text=t("ui.create_gitkeep"), variable=self.create_gitkeep_var, command=toggle_gitkeep).pack(anchor="w", pady=2)

        # Similarity Scan Settings
        similarity_frame = ttk.Frame(settings_group)
        similarity_frame.pack(fill=tk.X, pady=5)

        self.sim_scan_var = tk.BooleanVar(value=self.app.enable_similarity_scan.get())
        def toggle_sim_scan():
            from Scripts.UI import action_handler
            val = self.sim_scan_var.get()
            self.app.enable_similarity_scan.set(val)
            self._save_config("ENABLE_SIMILARITY_SCAN", val)
            action_handler.handle_toggle_similarity(self.app, val)

        ttk.Checkbutton(similarity_frame, text=t("ui.similarity_scan"), variable=self.sim_scan_var, command=toggle_sim_scan).pack(anchor="w")

        # Similarity Ratio Slider
        ratio_frame = ttk.Frame(settings_group)
        ratio_frame.pack(fill=tk.X, padx=20, pady=(0, 5))
        
        current_ratio = self.app.similarity_threshold.get()
        self.ratio_label = ttk.Label(ratio_frame, text=f"{t('ui.similarity_ratio')}: {current_ratio:.2f}")
        self.ratio_label.pack(side=tk.LEFT)

        self.ratio_var = tk.DoubleVar(value=current_ratio)
        def on_ratio_move(val):
            val = float(val)
            self.ratio_label.config(text=f"{t('ui.similarity_ratio')}: {val:.2f}")
            self.app.similarity_threshold.set(val)
            self._save_config("SIMILARITY_RATIO_THRESHOLD", val)

        ratio_slider = ttk.Scale(ratio_frame, from_=0.5, to=1.0, variable=self.ratio_var, orient=tk.HORIZONTAL, command=on_ratio_move)
        ratio_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Log Cleanup Section
        config = self._load_config()
        cleanup_frame = ttk.LabelFrame(main_frame, text=t("ui.log_cleanup_title"), padding=10)
        cleanup_frame.pack(fill=tk.X, pady=10)

        limit_frame = ttk.Frame(cleanup_frame)
        limit_frame.pack(fill=tk.X)
        
        limit_label_prefix = t("ui.keep_n_logs")
        self.limit_label = ttk.Label(limit_frame, text=f"{limit_label_prefix} {config.get('log_cleanup_limit', 5)}")
        self.limit_label.pack(side=tk.LEFT)

        self.cleanup_limit_var = tk.IntVar(value=config.get("log_cleanup_limit", 5))
        
        def on_slider_move(val):
            val = int(float(val))
            self.limit_label.config(text=f"{limit_label_prefix} {val}")
            self._save_config("log_cleanup_limit", val)

        limit_slider = ttk.Scale(cleanup_frame, from_=1, to=50, variable=self.cleanup_limit_var, orient=tk.HORIZONTAL, command=on_slider_move)
        limit_slider.pack(fill=tk.X, pady=5)

        cleanup_btn = ttk.Button(cleanup_frame, text=t("ui.cleanup_now"), command=self._on_cleanup_logs)
        cleanup_btn.pack(pady=(5, 0))

        # Close button at the bottom
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text=t("ui.close"), command=self._on_close).pack(side=tk.RIGHT)
        ttk.Label(btn_frame, text=t("ui.esc_to_close"), foreground="gray", font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=10)

    def _on_lang_change(self, event):
        from Scripts.UI import action_handler
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
        from Scripts.UI import action_handler
        new_level = int(self.debug_var.get())
        from Scripts.Utils import logger
        logger.set_log_level(new_level)
        self._save_config("debug_level", new_level)
        # Update UI visibility in the main app
        action_handler.update_debug_ui(self.app)

    def _on_cleanup_logs(self):
        from pathlib import Path
        import os
        import shutil
        import re
        import stat
        from Scripts.Utils import logger
        from datetime import date
        
        limit = self.cleanup_limit_var.get()
        title = t("message.confirm_cleanup_title")
        msg = t("message.confirm_cleanup_msg", n=limit)

        if not messagebox.askyesno(title, msg, icon='warning'):
            return

        # 1. Path Safety: Resolve the absolute path of the Log directory strictly
        try:
            log_dir = (Path.cwd() / "Log").resolve(strict=True)
            if not log_dir.exists() or not log_dir.is_dir():
                logger.debug(f"Cleanup skipped: Log directory '{log_dir}' not found or is not a directory.")
                return
        except Exception as e:
            logger.error(f"Cleanup Safety Critical Error: Could not resolve Log directory: {e}")
            return

        deleted_count = 0
        session_pattern = re.compile(r"^Session_(\d{4})(\d{2})(\d{2})_\d{2}h\d{2}m(_\d+)?$")
        
        # --- Robust Active Session Resolution ---
        active_session_dir = None
        try:
            temp_active = logger.get_session_dir()
            if temp_active:
                # Ensure it's a Path object and exists
                temp_path = Path(temp_active).resolve(strict=False)
                if temp_path.exists():
                    active_session_dir = temp_path
        except Exception:
            pass # Safety fallback

        # ==================== Core Safety & Helper Functions ====================
        def _is_safe_session_dir(path: Path) -> bool:
            """Hyper-strict validation for session folders."""
            try:
                # 1. Type and Symlink Check
                if not path.is_dir() or path.is_symlink():
                    return False

                name = path.name
                match = session_pattern.match(name)
                if not match:
                    return False

                # 2. Date Validation (Must be a real date between 2020-2035)
                try:
                    y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    if not (2020 <= y <= 2035 and 1 <= m <= 12 and 1 <= d <= 31):
                        return False
                    date(y, m, d) # Raises ValueError if invalid date
                except ValueError:
                    return False

                # 3. Path Depth and Parent Verification
                if path.parent.resolve() != log_dir:
                    return False

                abs_path = path.resolve()
                if not abs_path.is_relative_to(log_dir) or abs_path == log_dir:
                    logger.warn(f"Cleanup Safety Block: Outside path {abs_path}")
                    return False

                # Exactly 1 depth below log_dir
                if len(abs_path.relative_to(log_dir).parts) != 1:
                    return False

                # 4. Filesystem Boundary Check
                if log_dir.stat().st_dev != abs_path.stat().st_dev:
                    logger.warn(f"Cleanup Safety Block: Different filesystem detected for {abs_path}")
                    return False
                
                # 5. Active Session Protection
                if active_session_dir and abs_path == active_session_dir:
                    logger.debug(f"Cleanup: Skipping active session {abs_path.name}")
                    return False

                return True
            except Exception as e:
                logger.error(f"Safety check failed for {path}: {e}")
                return False

        def _remove_readonly(func, path, excinfo):
            """Error handler for shutil.rmtree to handle read-only files on Windows."""
            os.chmod(path, stat.S_IWRITE)
            func(path)

        # ==================== Execution ====================
        try:
            all_items = list(log_dir.iterdir())
            session_dirs = [item for item in all_items if _is_safe_session_dir(item)]

            # Sort by modification time (newest first)
            session_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            to_delete_sessions = session_dirs[limit:]
            
            # --- Deletion Preview (Enhanced UX and Safety) ---
            if not to_delete_sessions:
                messagebox.showinfo(t("ui.log_cleanup_title"), t("message.no_old_sessions"))
                return
            
            preview_list = "\n".join([f"• {p.name}" for p in to_delete_sessions])
            preview_msg = t("message.cleanup_preview", count=len(to_delete_sessions), list=preview_list)
            if not messagebox.askyesno(title, preview_msg, icon='warning'):
                return

            for session_path in to_delete_sessions:
                try:
                    # Final verification right before deletion
                    if _is_safe_session_dir(session_path):
                        abs_session = session_path.resolve()
                        # Use onerror handler for read-only files
                        shutil.rmtree(abs_session, onerror=_remove_readonly)
                        deleted_count += 1
                        logger.debug(f"Cleanup: Successfully deleted session folder: {abs_session.name}")
                except Exception as e:
                    logger.error(f"Cleanup: Failed to delete session folder {session_path.name}: {e}")
            
        except Exception as e:
            logger.error(f"Cleanup: Error during directory scanning: {e}")
            messagebox.showerror("Cleanup Error", f"An error occurred during cleanup: {e}")
            return
        
        messagebox.showinfo(t("message.success_title"), t("message.cleanup_success", count=deleted_count))

def show_options(parent, app_instance):
    OptionsWindow(parent, app_instance)
