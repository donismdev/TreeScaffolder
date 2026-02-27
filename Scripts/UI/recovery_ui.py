# -*- coding: utf-8 -*-
"""
recovery_ui.py

A separate window for selecting and applying recovery logs.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import re
from Scripts.Utils.i18n import t
from Scripts.Core import scaffold_core
from Scripts.UI import app_utils

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
        self.window.geometry("600x400")
        self.window.minsize(500, 300)
        self.window.grab_set()
        self.window.focus_set()

        self.window.bind("<Escape>", lambda e: self._on_close())
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        self.setup_ui()
        self.refresh_log_list()

    def _on_close(self):
        RecoveryWindow._instance = None
        self.window.destroy()

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=t("ui.recovery_title"), font=("Segoe UI", 11, "bold")).pack(pady=(0, 5))
        ttk.Label(main_frame, text=t("ui.recovery_desc") if "ui.recovery_desc" in t("ui") else "Select a recovery log to restore.", font=("Segoe UI", 9), foreground="gray").pack(pady=(0, 10))

        # List of recovery logs
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.log_tree = ttk.Treeview(list_frame, columns=("filename", "date"), show="headings", selectmode="browse")
        self.log_tree.heading("filename", text="File Name")
        self.log_tree.heading("date", text="Date Modified")
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

        self.restore_btn = ttk.Button(btn_frame, text=t("ui.restore") if "ui.restore" in t("ui") else "Load Selected", state=tk.DISABLED, command=self._on_restore)
        self.restore_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text=t("ui.refresh") if "ui.refresh" in t("ui") else "Refresh", command=self.refresh_log_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=t("ui.close"), command=self._on_close).pack(side=tk.RIGHT, padx=5)

    def refresh_log_list(self):
        """Finds all scaffold_recovery_*.txt files in the Log directory."""
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

        log_dir = Path.cwd() / self.app.LOG_DIR
        if not log_dir.exists():
            return

        files = list(log_dir.glob("scaffold_recovery_*.txt"))
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
            messagebox.showerror("Error", "Selected log file no longer exists.")
            self.refresh_log_list()
            return

        try:
            # --- 0. Full Clear Before Loading (Prevent mixing with stale data) ---
            self.app.on_clear_data()
            
            content = file_path.read_text(encoding='utf-8')
            
            # --- 1. Extract Target Root from Comment block ---
            target_root_str = None
            # Look for "Target Root Folder: <path>" pattern
            root_match = re.search(r'Target Root Folder:\s*(.*)$', content, re.MULTILINE)
            if root_match:
                target_root_str = root_match.group(1).strip()

            # --- 2. Set Target Root Path in Main App ---
            if target_root_str:
                self.app.target_root_path.set(target_root_str)
                self.app._save_last_root_path(target_root_str)
                # Refresh 'Before' view
                self.app._populate_before_tree(Path(target_root_str))

            # --- 3. Paste to Source Code Editor ---
            self.app.source_code_text.delete("1.0", tk.END)
            self.app.source_code_text.insert("1.0", content)
            self.app.source_code_text.edit_modified(True) # Trigger modified event
            
            # Switch to Source Code Tab
            self.app.editor_notebook.select(1)

            # --- 4. Trigger Recompute (Compute Diff) ---
            # We close the window first so user can see the progress in log
            self._on_close()
            from Scripts.UI import action_handler
            action_handler.handle_recovery_loaded(self.app, file_path.name)
            self.app.root.after(100, lambda: self.app.on_recompute(silent=False))

            app_utils.log_message(self.app, f"Recovery data loaded from: {file_path.name}", "success")

        except Exception as e:
            messagebox.showerror("Recovery Error", f"Failed to load recovery data:\n{e}")

def show_recovery(parent, app_instance):
    RecoveryWindow(parent, app_instance)
