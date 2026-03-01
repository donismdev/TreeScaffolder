# -*- coding: utf-8 -*-
"""
recovery_ui.py

A separate window for selecting and applying recovery logs.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import re
import datetime
from Scripts.Utils.i18n import t
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
        app_utils.load_popup_window_geometry(self.window, self.app.CONFIG_FILE, "recovery_window_geometry", 500, 300)

    def _save_geometry(self):
        app_utils.save_popup_window_geometry(self.window, self.app.CONFIG_FILE, "recovery_window_geometry")

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
        
        # Buttons
        btn_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text=t("ui.close"), command=self._on_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=t("ui.apply"), command=self.on_apply_recovery).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=t("ui.refresh"), command=self.refresh_log_list).pack(side=tk.LEFT, padx=5)

    def refresh_log_list(self):
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        
        log_dir = Path(self.app.LOG_DIR)
        if not log_dir.exists():
            return
            
        logs = []
        # Search for both legacy (recovery_v2_*) and current (scaffold_recovery_*) patterns
        patterns = ["recovery_v2_*.txt", "scaffold_recovery_*.txt"]
        
        # 1. Search in root Log directory
        for pattern in patterns:
            for recovery_file in log_dir.glob(pattern):
                self._add_log_to_list(recovery_file, logs, "Log")

        # 2. Search in Session folders
        for session_folder in log_dir.glob("Session_*"):
            if not session_folder.is_dir(): continue
            for pattern in patterns:
                for recovery_file in session_folder.glob(pattern):
                    self._add_log_to_list(recovery_file, logs, session_folder.name)
                
        # Sort by mtime descending
        logs.sort(key=lambda x: x["mtime"], reverse=True)
        
        for log in logs:
            self.log_tree.insert("", tk.END, values=(log["filename"], log["date"]), tags=(str(log["path"]),))

    def _add_log_to_list(self, file_path: Path, log_list: list, display_parent: str):
        """Helper to add a log file to the list with formatted metadata."""
        if not file_path.is_file(): return
        
        mtime = file_path.stat().st_mtime
        date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        log_list.append({
            "path": file_path,
            "filename": f"{display_parent}/{file_path.name}",
            "date": date_str,
            "mtime": mtime
        })

    def _on_select_change(self, event):
        pass # Optional: Add preview logic here if needed

    def on_apply_recovery(self):
        selected = self.log_tree.selection()
        if not selected:
            messagebox.showwarning(t("message.no_log_selected_title"), t("message.no_log_selected_msg"))
            return
            
        item = self.log_tree.item(selected[0])
        log_path = Path(item["tags"][0])
        
        if messagebox.askyesno(t("message.confirm_recovery_title"), t("message.confirm_recovery_msg")):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Extract root path
                root_path_str = None
                comment_pattern = re.compile(r"@@@COMMENT_BEGIN\n(.*?)\n@@@COMMENT_END", re.DOTALL)
                for comment_match in comment_pattern.finditer(content):
                    comment_content = comment_match.group(1)
                    root_match = re.search(r"@ROOT\s+([^{\s}]+|{{[\w-]+}})", comment_content)
                    if root_match:
                        root_path_str = root_match.group(1)
                        break
                
                if root_path_str and messagebox.askyesno(t("ui.recovery_title"), t("message.recovery_set_root", path=root_path_str)):
                    app_utils.verify_and_set_root(self.app, root_path_str, method="recovery")

                if hasattr(self.app, 'tree_text'):
                    self.app.tree_text.delete("1.0", tk.END)
                    self.app.tree_text.insert("1.0", content)
                    from Scripts.UI import action_handler
                    action_handler.handle_recovery_loaded(self.app, item["values"][0])
                
                self._on_close()
            except Exception as e:
                messagebox.showerror("Recovery Error", f"Failed to load recovery log: {e}")

class RecoveryNotificationWindow:
    """A small window that pops up after a scaffold to show what was backed up."""
    def __init__(self, parent, app_instance, backed_up_paths, log_path):
        self.app = app_instance
        self.window = tk.Toplevel(parent)
        self.window.title(t("ui.recovery_notify_title"))
        self.window.geometry("450x350")
        self._load_geometry()
        
        self.setup_ui(backed_up_paths, log_path)

    def _load_geometry(self):
        app_utils.load_popup_window_geometry(self.window, self.app.CONFIG_FILE, "recovery_notify_geometry", 400, 300)

    def _save_geometry(self):
        app_utils.save_popup_window_geometry(self.window, self.app.CONFIG_FILE, "recovery_notify_geometry")

    def setup_ui(self, backed_up_paths, log_path):
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.window.bind("<Destroy>", lambda e: self._save_geometry() if e.widget == self.window else None)

        ttk.Label(main_frame, text=t("ui.recovery_notify_title"), font=("Segoe UI", 11, "bold")).pack(pady=(0, 5))
        ttk.Label(main_frame, text=t("ui.recovery_notify_desc"), wraplength=400).pack(pady=(0, 10))

        # Log path info
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(path_frame, text=f"{t('ui.recovery_log_path')}:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        
        log_name_label = ttk.Label(path_frame, text=log_path.name, foreground="blue", cursor="hand2")
        log_name_label.pack(side=tk.LEFT, padx=5)

        # List of files
        list_label = ttk.Label(main_frame, text=t("ui.recovery_backed_up_files"), font=("Segoe UI", 9, "bold"))
        list_label.pack(anchor="w", pady=(10, 2))

        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.text_area = tk.Text(text_frame, height=8, font=("Consolas", 9), wrap=tk.NONE)
        scrollbar_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        scrollbar_x = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.text_area.xview)
        
        self.text_area.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(fill=tk.X)

        file_list = []
        for p in backed_up_paths:
            if self.app.current_plan:
                try:
                    rel = p.relative_to(self.app.current_plan.root_path)
                    file_list.append(f"{{{{Root}}}}/{rel}")
                except ValueError:
                    file_list.append(str(p))
            else:
                file_list.append(str(p))

        self.text_area.insert("1.0", "\n".join(file_list))
        self.text_area.config(state=tk.DISABLED)

        ttk.Button(main_frame, text=t("ui.close"), command=self.window.destroy).pack(side=tk.BOTTOM, pady=(5, 0))
        self.window.bind("<Escape>", lambda e: self.window.destroy())

def show_recovery_notification(parent, app_instance, backed_up_paths, log_path):
    RecoveryNotificationWindow(parent, app_instance, backed_up_paths, log_path)

def show_recovery(parent, app_instance):
    RecoveryWindow(parent, app_instance)
