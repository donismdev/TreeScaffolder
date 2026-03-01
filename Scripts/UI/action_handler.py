# -*- coding: utf-8 -*-
"""
action_handler.py

Centralized handler for user actions.
Updates the UI summary and executes logic for various user triggers.
"""
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import re
from Scripts.Utils.i18n import t
from Scripts.Core import scaffold_core
from Scripts.UI import app_utils
from Scripts.UI import scaffold_runner
from Scripts.Utils import logger
from Scripts.UI.tree_populator import populate_before_tree, populate_after_tree, _clear_tree as clear_tree_function

def update_summary(app, key, **kwargs):
    """Updates the summary label with a localized and formatted message."""
    message = t(f"summary.{key}", **kwargs)
    if hasattr(app, 'summary_label'):
        app.summary_label.config(text=message)

def handle_folder_selected(app, path, method="browse"):
    """Called when a new target folder is selected. method can be 'browse' or 'prev'."""
    rel_path = Path(path).name
    key = "folder_browse" if method == "browse" else "folder_prev"
    update_summary(app, key, path=rel_path)

def handle_test_data_loaded(app, success=True):
    """Called after test data load attempt."""
    key = "test_data_loaded" if success else "test_data_error"
    update_summary(app, key)

def handle_recovery_loaded(app, filename):
    """Called after a recovery log is successfully loaded."""
    update_summary(app, "recovery_loaded", file=filename)

def handle_data_cleared(app):
    """Called after the clear button is pressed."""
    update_summary(app, "data_cleared")

def handle_diff_computed(app, plan):
    """Called after a plan is successfully generated or selection changed."""
    new_files = sum(1 for p, s in plan.path_states.items() if s == 'new' and p in plan.planned_files and app_utils.is_effectively_selected(app, p))
    new_dirs = sum(1 for p, s in plan.path_states.items() if s == 'new' and p in plan.planned_dirs and app_utils.is_effectively_selected(app, p))
    overwrites = sum(1 for p, s in plan.path_states.items() if p in plan.planned_files and s == 'overwrite' and app_utils.is_effectively_selected(app, p))
    
    update_summary(app, "diff_computed", dirs=new_dirs, files=new_files, overwrites=overwrites)

def handle_apply_success(app, is_dry_run=False):
    """Called after the scaffold is applied successfully."""
    key = "apply_dry_run_success" if is_dry_run else "apply_success"
    update_summary(app, key)

def handle_options_opened(app):
    """Called when the options window is opened."""
    update_summary(app, "options_opened")

def handle_options_closed(app):
    """Called when the options window is closed."""
    update_summary(app, "options_closed")

def handle_recovery_opened(app):
    """Called when the recovery window is opened."""
    update_summary(app, "recovery_opened")

def handle_recovery_closed(app):
    """Called when the recovery window is closed."""
    update_summary(app, "recovery_closed")

def handle_toggle_dry_run(app, is_on):
    """Called when the dry run checkbutton is toggled."""
    update_summary(app, "dry_run_on" if is_on else "dry_run_off")

def handle_toggle_similarity(app, is_on):
    """Called when the similarity scan checkbutton is toggled."""
    update_summary(app, "similarity_on" if is_on else "similarity_off")

def handle_toggle_open_after(app, is_on):
    """Called when the open folder after apply checkbutton is toggled."""
    update_summary(app, "open_after_on" if is_on else "open_after_off")

def handle_content_updated(app, editor_type):
    """Called when tree or source code content is updated (e.g., via paste)."""
    if editor_type == "tree":
        update_summary(app, "tree_updated")
    else:
        update_summary(app, "source_updated")

def handle_language_changed(app):
    """Called after UI language is changed."""
    update_summary(app, "language_changed")

def handle_error(app, action_key):
    """Updates the summary to indicate an error in a specific action."""
    update_summary(app, f"error_{action_key}")

# --- Core Action Logic (Moved from gui_app.py) ---

DEV_DIR = Path("Dev")
RESOURCE_DIR = Path("Resources")

def update_debug_ui(app):
    """Shows or hides debug-only UI elements based on current debug_level."""
    from Scripts.Utils import logger
    level = logger.get_log_level()
    
    if level >= 2:
        # Show Check Folder button
        app.check_folder_button.grid(row=0, column=3)
    else:
        app.check_folder_button.grid_forget()

def on_check_folder(app):
    """Recursively counts files and directories in the target root."""
    root_path_str = app.target_root_path.get()
    if not root_path_str or root_path_str == t("ui.no_folder_selected"):
        app_utils.show_notification(app, 'warning', t("message.error_title"), t("message.select_root_first"))
        return

    try:
        root_path = Path(root_path_str)
        if not root_path.is_dir():
            app_utils.show_notification(app, 'error', t("message.error_title"), t("message.root_not_found"))
            return

        stats = app_utils.get_folder_stats(root_path)
        
        info_msg = t("ui.check_folder_result", 
                     name=root_path.name, 
                     dirs=stats["dirs"], 
                     files=stats["files"], 
                     normal=stats["normal"], 
                     gitkeep=stats["gitkeep"], 
                     total=stats["total"])
        
        app_utils.show_notification(app, 'info', t("ui.check_folder"), info_msg)
        
    except Exception as e:
        app_utils.show_notification(app, 'error', t("message.error_title"), f"Error scanning folder: {e}")

def on_browse_folder(app):
    logger.debug("on_browse_folder called")
    path = filedialog.askdirectory(mustexist=True, title=t("ui.section_1"))
    if not path:
        return
    app_utils.verify_and_set_root(app, path, method="browse")
    logger.debug("on_browse_folder completed")

def on_previous_folder(app):
    if app.last_root_path:
        app_utils.verify_and_set_root(app, app.last_root_path, method="prev")

def on_recompute(app, silent=False):
    logger.debug(f"on_recompute called (silent={silent})")
    root_path_str = app.target_root_path.get()
    if not root_path_str or root_path_str == t("ui.no_folder_selected") or not Path(root_path_str).is_dir():
        messagebox.showerror(t("message.error_title"), t("message.select_root_first"))
        return False

    # --- CRITICAL: Clear stale data before new analysis ---
    app.log_text.config(state=tk.NORMAL)
    app.log_text.delete("1.0", tk.END)
    app.log_text.config(state=tk.DISABLED)
    
    app.content_text.delete("1.0", tk.END)
    clear_tree_function(app.after_tree)
    clear_tree_function(app.after_list)
    # ------------------------------------------------------

    root_path = Path(root_path_str)
    text_input = app.tree_text.get("1.0", "end-1c") + "\n" + app.source_code_text.get("1.0", "end-1c")
    if not text_input.strip():
        messagebox.showinfo("Info", t("message.empty_editors"))
        return False
    config = {
        "DRY_RUN": app.dry_run.get(),
        "ENABLE_SIMILARITY_SCAN": app.enable_similarity_scan.get(),
        "SIMILARITY_RATIO_THRESHOLD": app.similarity_threshold.get(),
    }

    # Clear caches before recomputing to ensure fresh data
    app.before_cache = {}
    app.after_cache = {}

    app.current_plan = scaffold_core.generate_plan(root_path, text_input, config)
    
    # --- 0. Update Source Code with Source Structure Comment ---
    if app.current_plan:
        # Use source-only reconstruction instead of unified
        reconstructed_tree = scaffold_core.reconstruct_source_only_tree(app.current_plan)
        if reconstructed_tree:
            source_content = app.source_code_text.get("1.0", tk.END).rstrip()
            
            comment_header = "@@@COMMENT_BEGIN Source Code Structure"
            comment_footer = "@@@COMMENT_END"
            
            # Find and replace either old 'Unified' or new 'Source Code' comment if it exists
            pattern = re.compile(rf"@@@COMMENT_BEGIN (Unified Scaffold|Source Code) Structure[\s\S]*?{comment_footer}")
            new_comment_block = f"\n\n{comment_header}\n{reconstructed_tree}\n{comment_footer}"
            
            if pattern.search(source_content):
                new_source = pattern.sub(new_comment_block.strip(), source_content)
            else:
                new_source = source_content + new_comment_block
            
            # Use a flag to avoid triggering handle_content_updated recursively
            app.source_code_text.edit_modified(False)
            app.source_code_text.delete("1.0", tk.END)
            app.source_code_text.insert("1.0", new_source.strip() + "\n")
            app.source_code_text.edit_modified(False)
            logger.debug("Source Code editor updated with source structure.")

    # --- 0. Filter selected_paths to remove stale entries ---
    if app.current_plan:
        all_involved = app.current_plan.planned_dirs.union(app.current_plan.planned_files)
        app.selected_paths = {p: s for p, s in app.selected_paths.items() if p in all_involved}
    
    # --- 1. Log 초기화 및 준비 (Silent가 아닐 때만) ---
    if not silent:
        app.log_text.config(state=tk.NORMAL)
        app.log_text.delete('1.0', tk.END)
        app.log_text.config(state=tk.DISABLED)
    
    # --- 2. 일반 오류 확인 ---
    if app.current_plan.errors:
        if silent:
            app.log_text.config(state=tk.NORMAL)
            app.log_text.delete('1.0', tk.END)
            app.log_text.config(state=tk.DISABLED)

        action_source = "Test Data" if silent else "Editor"
        app_utils.log_message(app, f"\n[ERROR] Plan generation failed during {action_source} processing:", "error")
        for err in app.current_plan.errors:
            app_utils.log_message(app, f"- {err}", "error")
        
        clear_tree_function(app.after_tree)
        clear_tree_function(app.after_list)
        app.apply_button.config(state=tk.DISABLED)
        
        # Enhanced error feedback: Show the first error in the message box
        first_error = app.current_plan.errors[0] if app.current_plan.errors else "Unknown error"
        error_title = t("message.error_title")
        error_msg = f"{t('summary.error_diff')}\n\n[Error]: {first_error}"
        
        messagebox.showerror(error_title, error_msg)
        app.analysis_notebook.select(1)
        
        if silent:
            handle_test_data_loaded(app, success=False)
        else:
            handle_error(app, "diff")
        return False
    else:
        if not silent:
            app_utils.log_message(app, t("log.recompute_success"), "success")

    # --- 3. 유사성 경고 확인 ---
    if app.current_plan.similarity_warnings:
        app_utils.log_message(app, f"\n{t('log.similar_warning')}", "warn")
        app_utils.log_message(app, t("log.similar_desc"), "warn")
        for planned_path, candidates in app.current_plan.similarity_warnings.items():
            rel_planned = planned_path.relative_to(root_path)
            app_utils.log_message(app, f"- Target: {rel_planned}", "warn")
            for exist_name, ratio, exist_paths in candidates:
                app_utils.log_message(app, f"  ? Similar to: '{exist_name}' (Match: {ratio:.1%})", "warn")

    # --- 4. 동일 내용 및 안내 사항 확인 ---
    if not silent:
        identical_files = [p for p, s in app.current_plan.path_states.items() if s == 'identical']
        if identical_files:
            app_utils.log_message(app, f"\n{t('log.identical_info')}", "warn")
            app_utils.log_message(app, t("log.identical_desc"), "warn")
            for p in identical_files:
                app_utils.log_message(app, f"- {p.relative_to(root_path)}", "warn")

    # --- 5. 정상 진행 시 UI 업데이트 ---
    populate_before_tree(app, root_path)
    populate_after_tree(app, app.current_plan)
    
    # Enable job name entry after successful recompute
    app.editor_entry.config(state=tk.NORMAL)
    
    if app.current_plan.has_conflicts:
        messagebox.showwarning(t("message.conflicts_found_title"), t("message.conflicts_msg"))
        app.apply_button.config(state=tk.DISABLED)
        return False
    else:
        app.apply_button.config(state=tk.NORMAL)
        handle_diff_computed(app, app.current_plan)
        app.analysis_notebook.select(0)
        return True

def on_apply(app):
    """Executes the plan if root path is valid and user confirms."""
    logger.debug("on_apply called")
    
    # --- [STRICT SECURITY LOCKDOWN ROUTINE] ---
    # Perform physical check IMMEDIATELY before showing any confirmation popups
    root_path_str = app.target_root_path.get()
    import os
    
    # We use os.path.exists + os.path.isdir for the most 'raw' check possible
    if not root_path_str or not os.path.exists(root_path_str) or not os.path.isdir(root_path_str):
        # Security Lockdown
        messagebox.showerror(t("message.error_title"), t("message.root_not_found"))
        
        # Reset UI & Reset Config (Lockdown)
        app.target_root_path.set(t("ui.no_folder_selected"))
        app.prev_dir_button.config(state=tk.DISABLED)
        app.recompute_button.config(state=tk.DISABLED)
        app.apply_button.config(state=tk.DISABLED)
        app.last_root_path = ""
        app_utils.save_last_root_path(app, "")
        
        # Clear Views
        clear_tree_function(app.before_tree)
        clear_tree_function(app.before_list)
        clear_tree_function(app.after_tree)
        clear_tree_function(app.after_list)
        
        logger.warn(f"Security Lockdown: Root path '{root_path_str}' no longer exists physically. Aborting.")
        return
    # ------------------------------------------

    # 2. Existing Validation and Confirmation
    if not app.current_plan or app.current_plan.has_conflicts:
        messagebox.showerror("Cannot Apply", "No valid plan or plan has conflicts.")
        return

    is_dry_run = app.dry_run.get()
    
    # --- Helper for counting effectively selected items ---
    def is_effectively_selected(path):
        if not app.selected_paths.get(path, True):
            return False
        root_path = app.current_plan.root_path
        parent = path.parent
        while parent != root_path and parent.is_relative_to(root_path):
            if parent in app.selected_paths and not app.selected_paths[parent]:
                return False
            parent = parent.parent
        return True

    # 변경 사항 카운트 (체크박스 선택 상태 반영)
    new_files = sum(1 for p, s in app.current_plan.path_states.items() 
                    if s == 'new' and p in app.current_plan.planned_files and is_effectively_selected(p))
    new_dirs = sum(1 for p, s in app.current_plan.path_states.items() 
                   if s == 'new' and p in app.current_plan.planned_dirs and is_effectively_selected(p))
    overwrites = sum(1 for p, s in app.current_plan.path_states.items() 
                     if s == 'overwrite' and is_effectively_selected(p))

    if is_dry_run:
        title = t("message.confirm_dry_run_title")
        msg = t("message.confirm_dry_run_msg", dirs=new_dirs, files=new_files, overwrites=overwrites)
        confirmed = messagebox.askyesno(title, msg)
    else:
        title = t("message.confirm_apply_title")
        msg = t("message.confirm_apply_msg", dirs=new_dirs, files=new_files, overwrites=overwrites)
        confirmed = messagebox.askyesno(title, msg, icon='warning')

    if confirmed:
        # --- Handle Job Name ---
        job_name = app.editor_entry_var.get().strip()
        placeholder = t("ui.job_name_placeholder")
        
        # New: Warning for empty job name (including if it's still the placeholder)
        if not job_name or job_name == placeholder:
            if not messagebox.askyesno(t("message.error_title"), t("message.job_name_empty")):
                # If user says no, abort apply so they can enter a name
                app.recompute_button.config(state=tk.NORMAL)
                app.apply_button.config(state=tk.NORMAL)
                return
            job_name = "Unnamed_Job"

        if logger.is_job_name_used(job_name):
            # If name exists, append counter automatically
            base_name = job_name if job_name else "unnamed"
            counter = 2
            new_name = f"{base_name}_{counter}"
            while logger.is_job_name_used(new_name):
                counter += 1
                new_name = f"{base_name}_{counter}"
            
            messagebox.showwarning(t("message.error_title"), f"Job name '{job_name}' already used in this session.\nRenaming to '{new_name}' for this execution.")
            job_name = new_name
            app.editor_entry_var.set(job_name)

        app.analysis_notebook.select(1)
        app.recompute_button.config(state=tk.DISABLED)
        app.apply_button.config(state=tk.DISABLED)
        # Store current job name on app for the runner to pick up
        app._current_job_name = job_name
        app.root.after(100, lambda: scaffold_runner.execute_scaffold(app))
    logger.debug("on_apply completed")

def on_clear_data(app):
    logger.debug("on_clear_data called")
    app_utils.log_message(app, t("log.clearing_data"), "info")
    app.dry_run.set(True)
    app.create_gitkeep.set(False)
    app.enable_similarity_scan.set(True)
    app.similarity_threshold.set(0.86)
    app.tree_text.delete("1.0", tk.END)
    app.tree_text.insert("1.0", app.DEFAULT_TREE_TEMPLATE)
    app.source_code_text.delete("1.0", tk.END)
    app.content_text.delete("1.0", tk.END)
    app.target_root_path.set(t("ui.no_folder_selected"))
    
    app.current_plan = None
    app.before_cache = {}
    app.after_cache = {}
    app.selected_paths = {}
    
    clear_tree_function(app.before_tree)
    clear_tree_function(app.after_tree)
    clear_tree_function(app.before_list)
    clear_tree_function(app.after_list)
    
    app.recompute_button.config(state=tk.DISABLED)
    app.apply_button.config(state=tk.DISABLED)
    # Reset job name entry with placeholder
    app.editor_entry.config(state=tk.NORMAL)
    placeholder = t("ui.job_name_placeholder")
    app.editor_entry_var.set(placeholder)
    app.editor_entry.config(foreground='grey')
    app.editor_entry.config(state=tk.DISABLED)
    
    handle_data_cleared(app)

def on_load_test_data(app):
    logger.debug("on_load_test_data called")
    # Identify sample files
    try:
        # Clear log
        app.log_text.config(state=tk.NORMAL)
        app.log_text.delete('1.0', tk.END)
        app.log_text.config(state=tk.DISABLED)

        # Priority: Check Dev first (Development/Local), then Resources (Production/Git)
        # This allows local testing without polluting the production resources.
        structure_file = DEV_DIR / "sample_structure.txt"
        if not structure_file.exists():
            structure_file = RESOURCE_DIR / "sample_structure.txt"
            
        blueprint_file = DEV_DIR / "sample_blueprint.txt"
        if not blueprint_file.exists():
            blueprint_file = RESOURCE_DIR / "sample_blueprint.txt"

        for file_path, text_widget in [(structure_file, app.tree_text), (blueprint_file, app.source_code_text)]:
            if file_path.exists():
                text_widget.delete("1.0", tk.END)
                text_widget.insert("1.0", file_path.read_text(encoding="utf-8"))
            else:
                messagebox.showwarning(t("message.error_title"), t("message.no_test_data", file=str(file_path)))
        
        # Validation Logic
        root_path_str = app.target_root_path.get()
        if root_path_str and root_path_str != t("ui.no_folder_selected") and Path(root_path_str).is_dir():
            root_path = Path(root_path_str)
            text_input = app.tree_text.get("1.0", "end-1c") + "\n" + app.source_code_text.get("1.0", "end-1c")
            config = {
                "DRY_RUN": app.dry_run.get(),
                "ENABLE_SIMILARITY_SCAN": app.enable_similarity_scan.get(),
                "SIMILARITY_RATIO_THRESHOLD": app.similarity_threshold.get(),
            }
            val_plan = scaffold_core.generate_plan(root_path, text_input, config)
            if val_plan.errors:
                app_utils.log_message(app, f"\n[ERROR] {t('log.test_data_error')} (Validation Failed):", "error")
                for err in val_plan.errors:
                    app_utils.log_message(app, f"- {err}", "error")
                handle_test_data_loaded(app, success=False)
                app.analysis_notebook.select(1)
                return

        clear_tree_function(app.after_tree)
        clear_tree_function(app.after_list)
        app.apply_button.config(state=tk.DISABLED)

        # Tab Switching Logic (Prioritize Source Code at Index 0)
        tree_content = app.tree_text.get("1.0", "end-1c").strip()
        source_content = app.source_code_text.get("1.0", "end-1c").strip()
        
        # Check if contents are effectively empty (ignoring comments/whitespace)
        is_tree_effectively_empty = not tree_content or all(line.strip().startswith("#") or not line.strip() for line in tree_content.splitlines())
        is_source_effectively_empty = not source_content
        
        if is_source_effectively_empty and not is_tree_effectively_empty:
            # Only switch to Scaffold Tree (Index 1) if Source is empty and Tree has data
            app.editor_notebook.select(1)
        else:
            # Default to Source Code (Index 0) if it has data or if both are empty
            app.editor_notebook.select(0)

        app_utils.log_message(app, t("log.load_test_data_success"), "success")
        handle_test_data_loaded(app, success=True)
                
    except Exception as e:
        app_utils.log_message(app, f"Error loading test data: {e}", "error")
        messagebox.showerror(t("message.error_title"), f"An error occurred: {e}")
        handle_test_data_loaded(app, success=False)

def on_options(app):
    from Scripts.UI import options_ui
    handle_options_opened(app)
    options_ui.show_options(app.root, app)

def on_recovery(app):
    from Scripts.UI import recovery_ui
    handle_recovery_opened(app)
    recovery_ui.show_recovery(app.root, app)

def on_escape_pressed(app, event=None):
    """Resets focus to the root window."""
    app.root.focus_set()
    app_utils.log_message(app, "Focus reset to root.", "info")

# --- View Selection Logic ---

def on_after_tree_focus_out(app, event):
    """Resets the last clicked item tracking when focus leaves the tree."""
    app._after_tree_last_clicked = None

def _update_content_panel(app, source_info_lines: list, content: str, is_warning: bool = False):
    """
    Helper to update the content panel with a fixed-height header 
    and visual newline markers.
    """
    app.content_text.config(state=tk.NORMAL)
    app.content_text.delete("1.0", tk.END)
    
    # 1. Insert Header (Ensure exactly 4 lines including separator)
    header_lines = source_info_lines[:3]
    while len(header_lines) < 3:
        header_lines.append("")
    
    for line in header_lines:
        app.content_text.insert(tk.END, line + "\n")
    app.content_text.insert(tk.END, "="*40 + "\n") # Line 4: Separator
    
    # 2. Insert Body with Newline Markers
    if is_warning:
        app.content_text.insert(tk.END, content, "warning")
    else:
        # Split content but keep newline information
        lines = content.splitlines(keepends=True)
        for line in lines:
            if line.endswith('\n'):
                # Insert text without the actual newline first
                app.content_text.insert(tk.END, line[:-1])
                # Insert the visual mark
                app.content_text.insert(tk.END, "↵", "newline_mark")
                # Finally insert the real newline
                app.content_text.insert(tk.END, "\n")
            else:
                # Last line might not have a newline
                app.content_text.insert(tk.END, line)
                
    app.content_text.config(state=tk.DISABLED) # Keep it read-only
    app.editor_notebook.select(2)

def on_before_select(app, event: tk.Event):
    # CRITICAL: If this selection was triggered programmatically by After View, 
    # ignore it to prevent overwriting the Content Panel with 'Before' info.
    if getattr(app, '_in_selection_sync', False):
        return

    widget = event.widget
    widget.focus_set()
    selection = widget.selection()
    if not selection: return
    item_id = selection[0]
    values = widget.item(item_id, "values")
    if not values: return
    path = Path(values[0])
    
    try:
        if path.is_dir():
            _update_content_panel(app, ["--- DIRECTORY ---", "", f"Path: {path}"], "")
        else:
            if path not in app.before_cache:
                app.before_cache[path] = path.read_text(encoding='utf-8', errors='replace')
            content = app.before_cache[path]
            header = ["--- PHYSICAL CONTENT (Before View) ---", "", f"File: {path}"]
            _update_content_panel(app, header, content)
    except Exception as e:
        _update_content_panel(app, ["--- ERROR ---"], f"Error loading content: {e}")

def on_after_select(app, event: tk.Event):
    widget = event.widget
    widget.focus_set()
    selection = widget.selection()
    if not selection: return
    item_id = selection[0]
    values = widget.item(item_id, "values")
    if not values: return
    path = Path(values[0])
    
    try:
        if not app.current_plan: return
        
        # --- Visual Navigation (One-way: After -> Before) ---
        app._in_selection_sync = True
        try:
            path_str = str(path)
            if path_str in app.before_tree_map:
                node = app.before_tree_map[path_str]
                parent = app.before_tree.parent(node)
                while parent:
                    app.before_tree.item(parent, open=True)
                    parent = app.before_tree.parent(parent)
                app.before_tree.selection_set(node)
                app.before_tree.see(node)
            if path_str in app.before_list_map:
                node = app.before_list_map[path_str]
                app.before_list.selection_set(node)
                app.before_list.see(node)
        finally:
            app.root.after(50, lambda: setattr(app, '_in_selection_sync', False))

        # --- Data Loading ---
        state = app.current_plan.path_states.get(path)
        is_actually_planned_dir = any(str(p.resolve()).lower() == str(path.resolve()).lower() for p in app.current_plan.planned_dirs) if app.current_plan.planned_dirs else False
        is_dir = is_actually_planned_dir or (path.exists() and path.is_dir())
        
        if is_dir:
            _update_content_panel(app, ["--- PLANNED DIRECTORY ---", f"State: {state}", f"Path: {path}"], "")
            return

        if state in ('new', 'overwrite', 'conflict_file', 'conflict_dir', 'identical', 'exists'):
            planned_content = _get_planned_content(app, path)
            if planned_content is not None:
                # Check if this is an empty overwrite
                is_empty_warn = (state == 'overwrite' and not planned_content.strip())
                content = t("summary.empty_overwrite_warn") if is_empty_warn else planned_content
                header = ["--- PLANNED CONTENT (Memory) ---", f"State: {state}", f"File: {path}"]
                _update_content_panel(app, header, content, is_warning=is_empty_warn)
            elif (state in ('identical', 'exists')) and path.exists() and path.is_file():
                if path not in app.after_cache:
                    app.after_cache[path] = path.read_text(encoding='utf-8', errors='replace')
                header = ["--- EXISTING CONTENT (After View) ---", f"State: {state}", f"File: {path}"]
                _update_content_panel(app, header, app.after_cache[path])
            elif state in ('identical', 'exists'):
                _update_content_panel(app, ["--- NO CONTENT ---", f"State: {state}", f"File: {path}"], "(No content defined in plan)")
            else:
                _update_content_panel(app, ["--- NEW FILE (Empty) ---", f"State: {state}", f"File: {path}"], "")
        else:
            _update_content_panel(app, ["--- FILE NOT PLANNED ---", "", f"File: {path}"], "")

    except Exception as e:
        _update_content_panel(app, ["--- ERROR ---"], f"Error loading content: {e}")

def _get_planned_content(app, path: Path) -> str | None:
    if not app.current_plan: return None
    try:
        res_path = path.resolve()
    except Exception:
        res_path = path
    
    content = app.current_plan.file_contents.get(res_path)
    if content is not None: return content
    content = app.current_plan.file_contents.get(path)
    if content is not None: return content

    target_lower = str(res_path).lower()
    for p_obj, p_content in app.current_plan.file_contents.items():
        try:
            if str(p_obj.resolve()).lower() == target_lower:
                return p_content
        except Exception:
            if str(p_obj).lower() == target_lower:
                return p_content
    return None

# --- Selection Checkbox Logic ---

def on_after_tree_click(app, event):
    tree = event.widget
    item_id = tree.identify_row(event.y)
    if not item_id: return
    
    # Get current selection before this click is processed by Treeview
    current_selection = tree.selection()
    
    # Initialize tracking variable if it doesn't exist
    if not hasattr(app, '_after_tree_last_clicked'):
        app._after_tree_last_clicked = None

    # Toggle only if:
    # 1. The item is already selected
    # 2. It was also the last item we clicked in this focus session
    if item_id in current_selection and app._after_tree_last_clicked == item_id:
        _toggle_path_selection(app, tree, item_id)
    
    # Update tracking
    app._after_tree_last_clicked = item_id

def on_after_tree_space(app, event):
    tree = event.widget
    selection = tree.selection()
    if not selection: return "break"
    _toggle_path_selection(app, tree, selection[0])
    return "break"

def _toggle_path_selection(app, tree, item_id):
    values = tree.item(item_id, "values")
    if not values: return
    path = Path(values[0])
    if path not in app.selected_paths: return
    new_state = not app.selected_paths[path]
    _set_path_selection_sync(app, path, new_state)
    if new_state: _select_parents_sync(app, path)
    if app.current_plan: handle_diff_computed(app, app.current_plan)

def _select_parents_sync(app, path: Path):
    current = path.parent
    if not app.current_plan or current == app.current_plan.root_path: return
    if current in app.selected_paths and not app.selected_paths[current]:
        app.selected_paths[current] = True
        _update_node_visual_sync(app, current, True)
    _select_parents_sync(app, current)

def _set_path_selection_sync(app, path: Path, state: bool):
    if path in app.selected_paths:
        app.selected_paths[path] = state
        _update_node_visual_sync(app, path, state)
    if app.current_plan:
        for p in app.current_plan.planned_dirs.union(app.current_plan.planned_files):
            if p.parent == path:
                _set_path_selection_sync(app, p, state)

def _update_node_visual_sync(app, path: Path, state: bool):
    path_str = str(path)
    check_char = "☑" if state else "☐"
    if hasattr(app, 'after_tree_map') and path_str in app.after_tree_map:
        node_id = app.after_tree_map[path_str]
        current_text = app.after_tree.item(node_id, "text")
        if current_text.startswith("☑") or current_text.startswith("☐"):
            app.after_tree.item(node_id, text=check_char + current_text[1:])
    if hasattr(app, 'after_list_map') and path_str in app.after_list_map:
        node_id = app.after_list_map[path_str]
        current_text = app.after_list.item(node_id, "text")
        if current_text.startswith("☑") or current_text.startswith("☐"):
            app.after_list.item(node_id, text=check_char + current_text[1:])

# --- Editor Tab Logic ---

def on_paste_with_limit(app, event):
    """Intercepts paste events to check for excessive text size."""
    widget = event.widget
    try:
        clipboard_content = app.root.clipboard_get()
        # Limit set to 3 million characters (~3MB)
        LIMIT = 3_000_000
        
        if len(clipboard_content) > LIMIT:
            size_mb = len(clipboard_content) / (1024 * 1024)
            messagebox.showwarning(
                t("message.error_title"),
                f"Clipboard content is too large ({size_mb:.1f}MB).\n"
                f"Maximum allowed size is {LIMIT/1_000_000:.0f}MB to prevent freezing."
            )
            return "break" # Abort paste
            
        # Allow normal paste if within limit
        # The default Text widget paste will happen after this if we don't return "break"
        # However, to be safe and consistent, we can manually trigger the paste
        # but returning nothing allows the default event handler to proceed.
        return None
        
    except tk.TclError:
        # Happens if clipboard is empty or contains non-text data
        return None

def on_editor_tab_changed(app, event):
    """Updates the editor control bar based on the active tab."""
    # We always show the entry widget in all tabs for consistent layout
    if hasattr(app, 'editor_entry'):
        app.editor_entry.pack(side="left", fill="x", expand=True, padx=2)

def focus_job_name(app):
    """Sets focus to the job name entry widget."""
    if hasattr(app, 'editor_entry'):
        if str(app.editor_entry.cget("state")) == "normal":
            app.editor_entry.focus_set()
            # Select all text for easy replacement if it's not the placeholder
            placeholder = t("ui.job_name_placeholder")
            if app.editor_entry_var.get() != placeholder:
                app.editor_entry.selection_range(0, tk.END)
                app.editor_entry.icursor(tk.END)
        else:
            # Entry is disabled, meaning no valid plan exists
            messagebox.showwarning(t("message.error_title"), t("message.compute_first_job"))
