# -*- coding: utf-8 -*-
"""
recovery_ui.py

A separate window for selecting and applying recovery logs.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import re
import json
from Scripts.Utils.i18n import t
from Scripts.Core import scaffold_core
from Scripts.UI import app_utils

def _validate_geometry(geom_str, min_w=400, min_h=300):
    """Validates geometry string and ensures it's within screen bounds."""
    try:
        if not geom_str: return False
        # Expected format: WxH+X+Y
        match = re.match(r"(\d+)x(\d+)\+?(-?\d+)\+?(-?\d+)", geom_str)
        if not match: return False
        
        w, h, x, y = map(int, match.groups())
        if w < min_w or h < min_h: return False
        if x < -5000 or x > 5000 or y < -5000 or y > 5000: return False
        return True
    except: return False

class RecoveryWindow:
    _instance = None

    def __init__(self, parent, app_instance):
        if RecoveryWindow._instance and RecoveryWindow._instance.window.winfo_exists():
            RecoveryWindow._instance.window.lift()
            RecoveryWindow._instance.window.focus_force()
            return
        
        RecoveryWindow._instance = self
        self.app = app_instance
        self.window = tk.Toplevel(parent)
        self.window.title(t("ui.recovery_title"))
        
        # Initial default
        self.window.geometry("600x400")
        self.window.minsize(500, 300)
        self._load_geometry()

        self.window.grab_set()
        self.window.focus_set()

        self.window.bind("<Escape>", lambda e: self._on_close())
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.bind("<Destroy>", lambda e: self._save_geometry() if e.widget == self.window else None)

        self.setup_ui()
        self.refresh_log_list()

    def _load_geometry(self):
        try:
            config_path = Path("Resources/config.json")
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    geom = config.get("recovery_window_geometry")
                    if _validate_geometry(geom, 500, 300):
                        self.window.geometry(geom)
        except: pass

    def _save_geometry(self):
        try:
            config_path = Path("Resources/config.json")
            config = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            
            config["recovery_window_geometry"] = self.window.geometry()
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except: pass

    def _on_close(self):
        RecoveryWindow._instance = None
        from Scripts.UI import action_handler
        action_handler.handle_recovery_closed(self.app)
        self.window.destroy()

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=t("ui.recovery_title"), font=("Segoe UI", 11, "bold")).pack(pady=(0, 5))
        ttk.Label(main_frame, text=t("ui.recovery_desc"), font=("Segoe UI", 9), foreground="gray").pack(pady=(0, 10))

        # List of recovery logs
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.log_tree = ttk.Treeview(list_frame, columns=("filename", "date"), show="headings", selectmode="browse")
        self.log_tree.heading("filename", text=t("ui.recovery_filename"))
        self.log_tree.heading("date", text=t("ui.recovery_date"))
        self.log_tree.column("filename", width=300)
        self.log_tree.column("date", width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_tree.bind("<<TreeviewSelect>>", self._on_select_change)
        self.log_tree.bind("<Double-1>", self._on_double_click)

        # Action Buttons
        btn_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        btn_frame.pack(fill=tk.X)

        self.restore_btn = ttk.Button(btn_frame, text=t("ui.restore"), state=tk.DISABLED, command=self._on_restore)
        self.restore_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text=t("ui.refresh"), command=self.refresh_log_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=t("ui.close"), command=self._on_close).pack(side=tk.RIGHT, padx=5)

    def refresh_log_list(self):
        """Finds all scaffold_recovery_*.txt files in the Log directory and its subdirectories."""
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

        log_dir = Path.cwd() / self.app.LOG_DIR
        if not log_dir.exists():
            return

        # Search recursively (**) to find files inside Session_* folders
        files = list(log_dir.rglob("scaffold_recovery_*.txt"))
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        for f in files:
            mtime = f.stat().st_mtime
            from datetime import datetime
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            self.log_tree.insert("", tk.END, values=(f.name, date_str), tags=(str(f),))

    def _on_select_change(self, event):
        selection = self.log_tree.selection()
        if selection:
            self.restore_btn.config(state=tk.NORMAL)
        else:
            self.restore_btn.config(state=tk.DISABLED)

    def _on_double_click(self, event):
        item_id = self.log_tree.identify_row(event.y)
        if item_id:
            self._on_restore()

    def _on_restore(self):
        selection = self.log_tree.selection()
        if not selection:
            return
        
        item = self.log_tree.item(selection[0])
        file_path = Path(item["tags"][0])
        
        if not file_path.exists():
            messagebox.showerror(t("message.error_title"), t("sys.recovery_file_missing"))
            self.refresh_log_list()
            return

        try:
            from Scripts.UI import action_handler
            # --- 0. Full Clear Before Loading (Prevent mixing with stale data) ---
            action_handler.on_clear_data(self.app)
            
            content = file_path.read_text(encoding='utf-8')
            
            # --- 1. Extract Target Root from Comment block ---
            target_root_str = None
            # Look for "Target Root Folder: <path>" pattern
            root_match = re.search(r'Target Root Folder:\s*(.*)$', content, re.MULTILINE)
            if root_match:
                target_root_str = root_match.group(1).strip()

            # --- 2. Set Target Root Path in Main App ---
            if target_root_str:
                app_utils.verify_and_set_root(self.app, target_root_str, method="recovery")

            # --- 3. Paste to Source Code Editor ---
            self.app.source_code_text.delete("1.0", tk.END)
            self.app.source_code_text.insert("1.0", content)
            self.app.source_code_text.edit_modified(True) # Trigger modified event
            
            # Switch to Source Code Tab
            self.app.editor_notebook.select(0) # Changed from 1 to 0 because Source Code is now first

            # --- 4. Trigger Recompute (Compute Diff) ---
            # We close the window first so user can see the progress in log
            self._on_close()
            from Scripts.UI import action_handler
            action_handler.handle_recovery_loaded(self.app, file_path.name)
            self.app.root.after(100, lambda: action_handler.on_recompute(self.app, silent=False))

            app_utils.log_message(self.app, t("summary.recovery_loaded", file=file_path.name), "success")

        except Exception as e:
            messagebox.showerror(t("sys.recovery_error_title"), t("sys.recovery_error_msg", e=e))

class RecoveryNotificationWindow:
    """A window that shows a list of files that were backed up after an overwrite."""
    def __init__(self, app, backed_up_paths, log_path):
        self.window = tk.Toplevel(app.root)
        self.window.title(t("sys.recovery_notify_title"))
        self.window.geometry("500x400")
        self.window.minsize(400, 300)
        self._load_geometry()

        self.window.transient(app.root)
        self.window.grab_set()
        self.window.bind("<Destroy>", lambda e: self._save_geometry() if e.widget == self.window else None)

        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(main_frame, text="✅ " + t("sys.recovery_notify_title"), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))
        ttk.Label(main_frame, text=t("sys.recovery_notify_msg"), font=("Segoe UI", 9), wraplength=450, justify=tk.LEFT).pack(anchor="w", pady=(0, 10))
        
        ttk.Label(main_frame, text=f"Location: {log_path.name}", font=("Consolas", 9), foreground="blue").pack(anchor="w", pady=(0, 5))
        ttk.Label(main_frame, text=f"Total {len(backed_up_paths)} files have been backed up:", font=("Segoe UI", 9)).pack(anchor="w")

        # List Area with Scrollbar (Using Text for a "dry" look and copyability)
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.text_area = tk.Text(list_frame, wrap=tk.NONE, font=("Consolas", 9), bg="#f0f0f0", padx=5, pady=5)
        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        scrollbar_x = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.text_area.xview)
        
        self.text_area.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Add files to text area
        root_path_str = app.target_root_path.get()
        try:
            root_path = Path(root_path_str).resolve()
        except:
            root_path = None

        file_list = []
        for p in sorted(backed_up_paths):
            try:
                # Try to show relative path for readability
                if root_path and p.is_relative_to(root_path):
                    file_list.append(str(p.relative_to(root_path)))
                else:
                    file_list.append(str(p))
            except:
                file_list.append(str(p))

        self.text_area.insert("1.0", "\n".join(file_list))
        self.text_area.config(state=tk.DISABLED) # Read-only but allows selection/copy

        # Close button
        ttk.Button(main_frame, text=t("ui.close"), command=self.window.destroy).pack(side=tk.BOTTOM, pady=(5, 0))

        self.window.bind("<Escape>", lambda e: self.window.destroy())

    def _load_geometry(self):
        try:
            config_path = Path("Resources/config.json")
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    geom = config.get("recovery_notify_geometry")
                    if _validate_geometry(geom, 400, 300):
                        self.window.geometry(geom)
        except: pass

    def _save_geometry(self):
        try:
            config_path = Path("Resources/config.json")
            config = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            
            config["recovery_notify_geometry"] = self.window.geometry()
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except: pass

def show_recovery_notification(parent, backed_up_paths, log_path):
    RecoveryNotificationWindow(parent, backed_up_paths, log_path)

def show_recovery(parent, app_instance):
    RecoveryWindow(parent, app_instance)
