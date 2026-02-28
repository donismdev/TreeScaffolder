# -*- coding: utf-8 -*-
"""
scaffold_runner.py

Scaffolding execution logic for the Tree Scaffolder GUI application.
"""
import datetime
import os
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from Scripts.UI import app_utils
from Scripts.UI import action_handler
from Scripts.UI.tree_populator import populate_before_tree, populate_after_tree
from Scripts.Utils import logger
from Scripts.Utils.i18n import t
from Scripts.Core import scaffold_core

def _is_excluded_by_parent(app, path):
    """Checks if any parent directory of the path is unchecked in selected_paths."""
    plan = app.current_plan
    if not plan: return False
    
    parent = path.parent
    root_path = plan.root_path
    
    while parent != root_path and parent.is_relative_to(root_path):
        if parent in app.selected_paths and not app.selected_paths[parent]:
            return True
        parent = parent.parent
    return False

def _is_effectively_selected(app, path):
    """Checks if a path is directly or indirectly (via parent) unchecked."""
    if not app.selected_paths.get(path, True):
        return False
    return not _is_excluded_by_parent(app, path)

def execute_scaffold(app):
    """Performs the actual file and directory creation."""
    plan = app.current_plan
    is_dry_run = app.dry_run.get()
    
    captured_logs = []
    
    # Internal logging helper that also captures logs for the file write
    def log_exec(msg, level="info"):
        app_utils.log_message(app, msg, level, buffer_list=captured_logs)
        # Also log to UI directly
        app_utils.log_message(app, msg, level)

    logger.notify_scaffold_executed(is_dry_run)
    log_exec("="*60)
    
    if is_dry_run:
        log_exec("Starting scaffold simulation (DRY RUN)...", "warn")
    else:
        # --- FINAL PHYSICAL SAFETY CHECK ---
        try:
            if not plan.root_path.resolve(strict=True).is_dir():
                raise FileNotFoundError()
        except:
            log_exec(f"[CRITICAL ERROR] Target root folder disappeared: {plan.root_path}", "error")
            messagebox.showerror(t("message.error_title"), t("message.root_not_found"))
            return
        log_exec("Starting scaffold operation...", "info")
    
    # Only count lines from files that are effectively selected
    total_content_lines = sum(
        len(content.splitlines()) 
        for path, content in plan.file_contents.items() 
        if _is_effectively_selected(app, path)
    )

    num_planned_new_dirs = len([p for p in plan.planned_dirs if plan.path_states.get(p) == 'new' and _is_effectively_selected(app, p)])
    num_planned_new_files = len([p for p in plan.planned_files if plan.path_states.get(p) == 'new' and _is_effectively_selected(app, p)])
    num_planned_overwrite_files = len([p for p in plan.planned_files if plan.path_states.get(p) == 'overwrite' and _is_effectively_selected(app, p)])

    log_exec(f"\nPlanned Actions Summary:")
    log_exec(f"- New directories: {num_planned_new_dirs}")
    log_exec(f"- New files: {num_planned_new_files}")
    log_exec(f"- Overwritten files: {num_planned_overwrite_files}")
    log_exec(f"- Total lines of content to be written: {total_content_lines} lines")
    log_exec("="*60)

    stats = {"dirs_created": 0, "dirs_skipped": 0, "dirs_error": 0, "files_created": 0, "files_overwritten": 0, "files_skipped": 0, "files_error": 0}
    successful_paths = []
    # Collect original contents for recovery log
    overwritten_backups = {} 

    for path in sorted(list(plan.planned_dirs), key=lambda p: len(p.parts)):
        state = plan.path_states.get(path)

        # Check if user deselected this path OR if any parent is deselected
        if (path in app.selected_paths and not app.selected_paths[path]) or _is_excluded_by_parent(app, path):
            log_exec(f"[USER SKIP] {path}", "skip")
            stats["dirs_skipped"] += 1
            continue

        if state == "new":
            ok, created, skipped = _ensure_dir(app, path, is_dry_run, log_exec)
            if ok:
                if created:
                    stats["dirs_created"] += 1
                    successful_paths.append(path)
                if skipped: stats["dirs_skipped"] += 1
            else:
                stats["dirs_error"] += 1
        elif state == "exists":
            log_exec(f"[SKIP DIR]  {path}", "skip")
            stats["dirs_skipped"] += 1

    for path in sorted(list(plan.planned_files), key=lambda p: len(p.parts)):
        state = plan.path_states.get(path)
        content = plan.file_contents.get(path.resolve())

        # Check if user deselected this path OR if any parent is deselected
        if (path in app.selected_paths and not app.selected_paths[path]) or _is_excluded_by_parent(app, path):
            log_exec(f"[USER SKIP] {path}", "skip")
            stats["files_skipped"] += 1
            continue

        if state == "new" or state == "overwrite":
            is_overwrite = state == "overwrite"
            
            # --- PRE-READ FOR RECOVERY LOG ---
            # Robust check for existence before overwriting
            try:
                phys_path = path.resolve()
                if is_overwrite and not is_dry_run and phys_path.exists() and phys_path.is_file():
                    overwritten_backups[path] = phys_path.read_text(encoding='utf-8', errors='replace')
            except Exception:
                if is_overwrite and not is_dry_run:
                    overwritten_backups[path] = "(Could not read original content)"

            # Pass correct level for logging based on state
            log_level = "overwrite" if is_overwrite else "success"
            ok, created, skipped = _ensure_file(app, path, is_dry_run, content, is_overwrite, log_exec, log_level)
            if ok:
                if created:
                    if is_overwrite:
                        stats["files_overwritten"] += 1
                    else:
                        stats["files_created"] += 1
                    successful_paths.append(path)
                if skipped: stats["files_skipped"] += 1
            else:
                stats["files_error"] += 1
        elif state == "identical":
            log_exec(f"[SKIP FILE] {path} (Identical content)", "skip")
            stats["files_skipped"] += 1
        elif state == "exists":
            log_exec(f"[SKIP FILE] {path}", "skip")
            stats["files_skipped"] += 1

    # Determine which paths were effectively selected for the final log
    applied_paths = set()
    for p in plan.planned_dirs.union(plan.planned_files):
        if _is_effectively_selected(app, p):
            applied_paths.add(p)

    log_exec("\n" + "="*25 + " SUMMARY " + "="*26)
    log_exec(f"- Dirs created: {stats['dirs_created']}, skipped: {stats['dirs_skipped']}, errors: {stats['dirs_error']}")
    log_exec(f"- Files created: {stats['files_created']}, overwritten: {stats['files_overwritten']}, skipped: {stats['files_skipped']}, errors: {stats['files_error']}")
    
    if plan.duplicate_warnings or plan.similarity_warnings:
        log_exec("\n--- Warnings ---", "warn")
        log_exec(f"- Duplicate name warnings: {len(plan.duplicate_warnings)}", "warn")
        log_exec(f"- Similar name warnings: {len(plan.similarity_warnings)}", "warn")

    log_exec("="*60)
    if stats["dirs_error"] > 0 or stats["files_error"] > 0:
        log_exec("Operation finished with errors.", "error")
    else:
        log_exec("Operation finished successfully.", "success")
        
        if not is_dry_run:
            for path in successful_paths:
                if path.is_dir():
                    plan.path_states[path] = 'exists'
                elif path.is_file():
                    try:
                        actual_content = path.read_text(encoding='utf-8', errors='replace')
                        planned_content = plan.file_contents.get(path.resolve())
                        
                        norm_actual = (actual_content or "").replace('\r\n', '\n')
                        norm_planned = (planned_content or "").replace('\r\n', '\n')

                        norm_actual_lines = [line.rstrip() for line in norm_actual.splitlines()]
                        norm_planned_lines = [line.rstrip() for line in norm_planned.splitlines()]

                        while norm_actual_lines and not norm_actual_lines[-1]:
                            norm_actual_lines.pop()
                        while norm_planned_lines and not norm_planned_lines[-1]:
                            norm_planned_lines.pop()
                        
                        final_norm_actual = "\n".join(norm_actual_lines)
                        final_norm_planned = "\n".join(norm_planned_lines)

                        if final_norm_actual == final_norm_planned:
                            plan.path_states[path] = 'identical'
                            log_exec(f"Successfully verified content for {path}. State set to 'identical'.", "debug")
                        else:
                            log_exec(f"Content verification failed for {path}. State not updated. Current state: {plan.path_states.get(path)}", "warn")
                            
                    except Exception as e:
                        log_exec(f"Could not verify file content for {path}: {e}", "error")

        if app.open_folder_after_apply.get():
            try:
                log_exec(t("sys.opening_folder", path=plan.root_path), "info")
                path_str = str(plan.root_path)
                if sys.platform == "win32":
                    os.startfile(path_str)
                elif sys.platform == "darwin": 
                    subprocess.Popen(["open", path_str])
                else: 
                    subprocess.Popen(["xdg-open", path_str])
            except Exception as e:
                err_msg = t("sys.open_folder_error", e=e)
                log_exec(err_msg, "error")
                # Also show a popup since this is a user-requested action that failed
                messagebox.showwarning(t("message.error_title"), err_msg)

    _write_execution_log(app, plan, stats, is_dry_run, captured_logs, applied_paths)
    
    # CRITICAL: Always check if we have backups to write, and ensure it's NOT a dry run
    if not is_dry_run and len(overwritten_backups) > 0:
        log_exec(f"Generating recovery log for {len(overwritten_backups)} files...", "info")
        recovery_file = _write_recovery_v2_log(app, overwritten_backups)
        
        # Show custom scrollable notification window
        if recovery_file:
            from Scripts.UI import recovery_ui
            recovery_ui.show_recovery_notification(app, list(overwritten_backups.keys()), recovery_file)
    elif not is_dry_run:
        log_exec("No files were overwritten; skipping recovery log generation.", "debug")
        
    app.log_text.config(state="normal")
    app.log_text.delete("1.0", "end")
    
    summary_header = (
        f"{'DRY RUN' if is_dry_run else 'EXECUTION'} SUMMARY\n"
        f"New Directories: {stats['dirs_created']}\n"
        f"New Files: {stats['files_created']}\n"
        f"Overwritten Files: {stats['files_overwritten']}\n"
    )
    
    app_utils.log_message(app, summary_header, "info")
    app_utils.log_message(app, "\n--- detail ---\n", "info")

    for message, level in captured_logs:
        app_utils.log_message(app, message, level)
    
    app.log_text.config(state="disabled")
        
    # Re-enable recompute always
    app.recompute_button.config(state="normal")
    
    # After Dry Run: Allow user to click Apply again (for real this time)
    # After Real Apply: Keep disabled to prevent accidental double-execution
    if is_dry_run and plan and not plan.has_conflicts:
        app.apply_button.config(state="normal")
    else:
        app.apply_button.config(state="disabled")
    
    populate_before_tree(app, plan.root_path)
    populate_after_tree(app, plan) # Refresh After View to reflect 'exists' state
    
    if stats["dirs_error"] > 0 or stats["files_error"] > 0:
        action_handler.handle_error(app, "apply")
    else:
        action_handler.handle_apply_success(app, is_dry_run=is_dry_run)
        
    app.analysis_notebook.select(0)

def _write_execution_log(app, plan, stats: dict, is_dry_run: bool, captured_logs: list, applied_paths: set):
    """Writes a comprehensive execution log to a timestamped file."""
    log_path = logger.get_session_dir()
    if not log_path:
        log_path = Path.cwd() / app.LOG_DIR
    log_path.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%Hh%Mm")
    log_filename = log_path / f"scaffold_execution_{timestamp}.log"
    counter = 1
    while log_filename.exists():
        log_filename = log_path / f"scaffold_execution_{timestamp}_{counter}.log"
        counter += 1

    tree_content = app.tree_text.get("1.0", "end").strip()
    source_content = app.source_code_text.get("1.0", "end").strip()

    # --- Reconstructed Tree Sections ---
    # 1. Full Plan with Annotations (Identical/Exists marks)
    unified_tree_text = scaffold_core.reconstruct_tree_string(plan, show_annotations=True)
    
    # 2. Actually Applied (Only if filtering occurred)
    full_planned_paths = plan.planned_dirs.union(plan.planned_files)
    all_selected = (len(full_planned_paths) == len(applied_paths))
    
    applied_structure_text = ""
    if not all_selected:
        applied_structure_text = scaffold_core.reconstruct_tree_string(plan, filter_paths=applied_paths, show_annotations=False)

    summary_header = (
        f"{'DRY RUN' if is_dry_run else 'EXECUTION'} SUMMARY\n"
        f"- New Directories: {stats['dirs_created']}\n"
        f"- New Files: {stats['files_created']}\n"
        f"- Overwritten Files: {stats['files_overwritten']}\n"
        f"- Directory Errors: {stats['dirs_error']}\n"
        f"- File Errors: {stats['files_error']}\n"
    )

    status_str = "EXECUTED (DRY RUN)" if is_dry_run else "EXECUTED (REAL)"
    status_header = [
        "========================================",
        f"SCAFFOLD APPLY STATUS: {status_str}",
        "========================================",
        ""
    ]

    log_entries = status_header + [
        f"Execution Log - {datetime.datetime.now().isoformat()}",
        "=" * 80,
        "Unified Scaffold Structure (Full Plan):",
        "=" * 80,
        unified_tree_text,
        "",
        summary_header,
        "=" * 80,
    ]

    if applied_structure_text:
        log_entries.extend([
            "\n" + "=" * 80,
            "Actually Applied Structure (Filtered by Checkboxes):",
            "=" * 80,
            applied_structure_text,
            ""
        ])

    log_entries.append("\n--- detail ---\n")
    for message, level in captured_logs:
        log_entries.append(f"[{level.upper()}] {message}")
        
    log_entries.extend([
        "\n" + "=" * 80,
        "Scaffold Tree Content (Input):",
        "=" * 80,
        tree_content,
        "",
        "=" * 80,
        "Source Code Content (Input):",
        "=" * 80,
        source_content,
        "=" * 80,
    ])

    try:
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(log_entries))
        app_utils.log_message(app, t("sys.log_saved", path=log_filename), "info")
    except Exception as e:
        app_utils.log_message(app, f"Error writing execution log: {e}", "error")

def _write_recovery_v2_log(app, overwritten_backups: dict):
    """Writes a V2-style recovery log containing original contents of overwritten files."""
    log_path = logger.get_session_dir()
    if not log_path:
        log_path = Path.cwd() / app.LOG_DIR
    log_path.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%Hh%Mm")
    recovery_filename = log_path / f"scaffold_recovery_{timestamp}.txt"
    counter = 1
    while recovery_filename.exists():
        recovery_filename = log_path / f"scaffold_recovery_{timestamp}_{counter}.txt"
        counter += 1

    plan = app.current_plan
    root_path = plan.root_path

    log_entries = [
        "@@@COMMENT_BEGIN",
        "SCAFFOLD EXECUTION RECOVERY LOG",
        f"Date: {datetime.datetime.now().isoformat()}",
        f"Target Root Folder: {root_path}",
        f"Number of Overwritten Files: {len(overwritten_backups)}",
        "Instructions: This file contains the original content of files that were overwritten.",
        "You can use these blocks to restore previous versions if needed.",
        "@@@COMMENT_END",
        ""
    ]

    for path, content in overwritten_backups.items():
        try:
            rel_path = path.relative_to(root_path).as_posix()
            display_path = f"{{{{Root}}}}/{rel_path}"
        except ValueError:
            display_path = str(path)
            
        log_entries.append(f"@@@FILE_BEGIN {display_path}")
        log_entries.append(content)
        if content and not content.endswith('\n'):
            log_entries.append("")
        log_entries.append(f"@@@FILE_END {display_path}")
        log_entries.append("")

    try:
        with open(recovery_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(log_entries))
        app_utils.log_message(app, t("sys.recovery_saved", path=recovery_filename), "success")
        return recovery_filename
    except Exception as e:
        app_utils.log_message(app, t("sys.recovery_save_error", e=e), "error")
        return None

def _ensure_dir(app, path: Path, dry_run: bool, log_exec) -> tuple[bool, bool, bool]:
    """(ok, created, skipped)"""
    if path.exists():
        log_exec(f"[SKIP DIR]  {path}", "skip")
        return True, False, True

    log_exec(f"[MKDIR]     {path}", "success")
    if not dry_run:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log_exec(f"[ERROR] mkdir failed: {path} | {e}", "error")
            return False, False, False
    return True, True, False

def _ensure_file(app, path: Path, dry_run: bool, content: str | None, is_overwrite: bool, log_exec, log_level: str = "success") -> tuple[bool, bool, bool]:
    """(ok, created, skipped)"""
    verb = "[OVERWRITE]" if is_overwrite else "[CREATE]"
    
    if not is_overwrite and path.exists():
        log_exec(f"[SKIP FILE] {path} (already exists)", "skip")
        return True, False, True

    log_exec(f"{verb:<11} {path}", log_level)

    if not dry_run:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            final_content = (content or "").replace('\r\n', '\n').replace('\n', '\r\n')
            path.write_bytes(final_content.encode('utf-8'))
        except Exception as e:
            log_exec(f"[ERROR] write file failed: {path} | {e}", "error")
            return False, False, False
    return True, True, False
