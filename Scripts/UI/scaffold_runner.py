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

def execute_scaffold(app):
    """Performs the actual file and directory creation."""
    plan = app.current_plan
    is_dry_run = app.dry_run.get()
    job_name = getattr(app, '_current_job_name', "")
    
    captured_logs = []
    
    # Internal logging helper that also captures logs for the file write
    def log_exec(msg, level="info"):
        app_utils.log_message(app, msg, level, buffer_list=captured_logs)
        # Also log to UI directly
        app_utils.log_message(app, msg, level)

    logger.notify_scaffold_executed(is_dry_run, job_name=job_name)
    log_exec("="*60)
    
    if is_dry_run:
        log_exec(f"Starting scaffold simulation (DRY RUN) [Job: {job_name if job_name else '(Unnamed)'}]...", "warn")
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
        if app_utils.is_effectively_selected(app, path)
    )

    num_planned_new_dirs = len([p for p in plan.planned_dirs if plan.path_states.get(p) == 'new' and app_utils.is_effectively_selected(app, p)])
    num_planned_new_files = len([p for p in plan.planned_files if plan.path_states.get(p) == 'new' and app_utils.is_effectively_selected(app, p)])
    num_planned_overwrite_files = len([p for p in plan.planned_files if plan.path_states.get(p) == 'overwrite' and app_utils.is_effectively_selected(app, p)])

    log_exec(f"\nPlanned Actions Summary:")
    log_exec(f"- New directories: {num_planned_new_dirs}")
    log_exec(f"- New files: {num_planned_new_files}")
    log_exec(f"- Overwritten files: {num_planned_overwrite_files}")
    log_exec(f"- Total lines of content to be written: {total_content_lines} lines")
    log_exec("="*60)

    stats = {
        "dirs_created": 0, "dirs_skipped": 0, "dirs_error": 0, 
        "files_created": 0, "files_overwritten": 0, "files_skipped": 0, "files_error": 0,
        "gitkeep_created": 0
    }
    successful_paths = []
    gitkeep_paths = []
    # Collect original contents for recovery log
    overwritten_backups = {} 

    for path in sorted(list(plan.planned_dirs), key=lambda p: len(p.parts)):
        state = plan.path_states.get(path)

        # Check if user deselected this path OR if any parent is deselected
        if (path in app.selected_paths and not app.selected_paths[path]) or app_utils.is_excluded_by_parent(app, path):
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
        if (path in app.selected_paths and not app.selected_paths[path]) or app_utils.is_excluded_by_parent(app, path):
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

    # --- NEW: Create .gitkeep in empty planned folders ---
    if app.create_gitkeep.get():
        for dir_path in plan.planned_dirs:
            if not _is_effectively_selected(app, dir_path):
                continue
                
            has_planned_child = False
            for file_path in plan.planned_files:
                if _is_effectively_selected(app, file_path) and file_path.is_relative_to(dir_path):
                    has_planned_child = True
                    break
            
            if has_planned_child:
                continue

            has_phys_files = False
            if dir_path.exists() and dir_path.is_dir():
                try:
                    if any(dir_path.iterdir()):
                        has_phys_files = True
                except:
                    pass
            
            if has_phys_files:
                continue

            gitkeep_path = dir_path / ".gitkeep"
            if not gitkeep_path.exists():
                try:
                    if not is_dry_run:
                        gitkeep_path.write_bytes(b"")
                    log_exec(f"[GITKEEP]   {gitkeep_path}", "success")
                    stats["gitkeep_created"] += 1
                    gitkeep_paths.append(gitkeep_path)
                except Exception as e:
                    log_exec(f"[ERROR] failed to create .gitkeep in {dir_path}: {e}", "error")

    log_exec("\n" + "="*25 + " SUMMARY " + "="*26)
    log_exec(f"- Dirs created: {stats['dirs_created']}, skipped: {stats['dirs_skipped']}, errors: {stats['dirs_error']}")
    log_exec(f"- Files created: {stats['files_created']}, overwritten: {stats['files_overwritten']}, skipped: {stats['files_skipped']}, errors: {stats['files_error']}")
    if stats["gitkeep_created"] > 0:
        log_exec(f"- .gitkeep created: {stats['gitkeep_created']}")
    
    if plan.duplicate_warnings or plan.similarity_warnings:
        log_exec("\n--- Warnings ---", "warn")
        log_exec(f"- Duplicate name warnings: {len(plan.duplicate_warnings)}", "warn")
        log_exec(f"- Similar name warnings: {len(plan.similarity_warnings)}", "warn")

    log_exec("="*60)
    if stats["dirs_error"] > 0 or stats["files_error"] > 0:
        log_exec("Operation finished with errors.", "error")
    else:
        log_exec("Operation finished successfully.", "success")

    # --- LOG GENERATION ---
    # We write the log AFTER success message but BEFORE updating path_states
    _write_execution_log(app, plan, stats, is_dry_run, captured_logs, successful_paths, gitkeep_paths, job_name)

    if not (stats["dirs_error"] > 0 or stats["files_error"] > 0):
        if not is_dry_run:
            for path in successful_paths:
                if path.is_dir():
                    plan.path_states[path] = 'exists'
                elif path.is_file():
                    try:
                        actual_content = path.read_text(encoding='utf-8', errors='replace')
                        planned_content = plan.file_contents.get(path.resolve())
                        if scaffold_core.is_content_identical(actual_content, planned_content):
                            plan.path_states[path] = 'identical'
                    except:
                        pass

        if app.open_folder_after_apply.get():
            try:
                path_str = str(plan.root_path)
                if sys.platform == "win32": os.startfile(path_str)
                elif sys.platform == "darwin": subprocess.Popen(["open", path_str])
                else: subprocess.Popen(["xdg-open", path_str])
            except:
                pass

    if not is_dry_run and len(overwritten_backups) > 0:
        recovery_file = _write_recovery_v2_log(app, overwritten_backups)
        if recovery_file:
            from Scripts.UI import recovery_ui
            recovery_ui.show_recovery_notification(app.root, app, list(overwritten_backups.keys()), recovery_file)
        
    app.log_text.config(state="normal")
    app.log_text.delete("1.0", "end")
    
    status_str = "EXECUTED (DRY RUN)" if is_dry_run else "EXECUTED (REAL)"
    display_name = f" [job name : {job_name}]" if job_name else ""
    
    app_utils.log_message(app, "="*40, "info")
    app_utils.log_message(app, f"SCAFFOLD APPLY STATUS: {status_str}{display_name}", "info")
    app_utils.log_message(app, "="*40 + "\n", "info")

    summary_header = (
        f"{'DRY RUN' if is_dry_run else 'EXECUTION'} SUMMARY\n"
        f"New Directories: {stats['dirs_created']}\n"
        f"New Files: {stats['files_created']}\n"
        f"Overwritten Files: {stats['files_overwritten']}\n"
    )
    if stats.get("gitkeep_created", 0) > 0:
        summary_header += f".gitkeep Created: {stats['gitkeep_created']}\n"
    
    app_utils.log_message(app, summary_header, "info")
    app_utils.log_message(app, "\n--- detail ---\n", "info")

    for message, level in captured_logs:
        app_utils.log_message(app, message, level)
    
    app.log_text.config(state="disabled")
    app.recompute_button.config(state="normal")
    
    if is_dry_run and plan and not plan.has_conflicts:
        app.apply_button.config(state="normal")
    else:
        app.apply_button.config(state="disabled")
    
    populate_before_tree(app, plan.root_path)
    populate_after_tree(app, plan) 
    
    if stats["dirs_error"] > 0 or stats["files_error"] > 0:
        action_handler.handle_error(app, "apply")
    else:
        action_handler.handle_apply_success(app, is_dry_run=is_dry_run)
        
    app.analysis_notebook.select(0)

def _write_execution_log(app, plan, stats: dict, is_dry_run: bool, captured_logs: list, successful_paths: list, gitkeep_paths: list, job_name: str):
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

    full_planned_paths = plan.planned_dirs.union(plan.planned_files)
    unchecked_paths = set()
    for p in full_planned_paths:
        if not app_utils.is_effectively_selected(app, p):
            unchecked_paths.add(p)

    unified_tree_text = scaffold_core.reconstruct_tree_string(
        plan, show_annotations=True, unchecked_paths=unchecked_paths
    )
    
    actual_written_paths = set()
    for p in successful_paths:
        curr = p
        while curr != plan.root_path and curr.is_relative_to(plan.root_path):
            actual_written_paths.add(curr)
            curr = curr.parent
            
    applied_structure_text = ""
    if not actual_written_paths:
        applied_structure_text = "(No new or updated files were applied in this execution.)"
    else:
        applied_structure_text = scaffold_core.reconstruct_tree_string(
            plan, filter_paths=actual_written_paths, show_annotations=False
        )

    gitkeep_structure_text = ""
    if gitkeep_paths:
        gk_tree_paths = set()
        for p in gitkeep_paths:
            curr = p
            while curr != plan.root_path and curr.is_relative_to(plan.root_path):
                gk_tree_paths.add(curr)
                curr = curr.parent
        
        original_planned_files = plan.planned_files.copy()
        try:
            plan.planned_files.update(gitkeep_paths)
            gitkeep_structure_text = scaffold_core.reconstruct_tree_string(
                plan, filter_paths=gk_tree_paths, show_annotations=False
            )
        finally:
            plan.planned_files = original_planned_files

    applied_details = []
    for p in successful_paths:
        state = plan.path_states.get(p)
        action = "[DIR]" if p in plan.planned_dirs else ("[OVERWRITE]" if state == "overwrite" else "[FILE]")
        try:
            rel = p.relative_to(plan.root_path)
            applied_details.append(f"{action:<12} {{Root}}/{rel.as_posix()}")
        except:
            applied_details.append(f"{action:<12} {p}")
    
    for p in gitkeep_paths:
        try:
            rel = p.relative_to(plan.root_path)
            applied_details.append(f"{'[GITKEEP]':<12} {{Root}}/{rel.as_posix()}")
        except:
            applied_details.append(f"{'[GITKEEP]':<12} {p}")
            
    applied_details_text = "\n".join(applied_details) if applied_details else "(No changes were applied.)"

    summary_header = (
        f"{'DRY RUN' if is_dry_run else 'EXECUTION'} SUMMARY\n"
        f"- New Directories: {stats['dirs_created']}\n"
        f"- New Files: {stats['files_created']}\n"
        f"- Overwritten Files: {stats['files_overwritten']}\n"
        f"- .gitkeep Created: {stats.get('gitkeep_created', 0)}\n"
        f"- Directory Errors: {stats['dirs_error']}\n"
        f"- File Errors: {stats['files_error']}\n"
    )

    status_str = "EXECUTED (DRY RUN)" if is_dry_run else "EXECUTED (REAL)"
    display_name = f" [job name : {job_name}]" if job_name else ""
    
    status_header = [
        "========================================",
        f"SCAFFOLD APPLY STATUS: {status_str}{display_name}",
        "========================================",
        ""
    ]

    # DEVELOPER NOTICE: The following sections (Status, Summary) are intentionally
    # duplicated at both the top and bottom of the log file to ensure visibility
    # regardless of where the user starts reading (top-down or bottom-up).
    # This is a UX design choice, NOT a duplication bug.
    
    log_entries = status_header + [
        f"Execution Log - {datetime.datetime.now().isoformat()}",
        "=" * 80,
        summary_header,
        "=" * 80,
    ]

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
        "",
        "@@@COMMENT_BEGIN Actually Applied Detail Overview",
        t("log_sections.applied_detail_desc"),
        applied_details_text,
        "@@@COMMENT_END",
        "",
        "Unified Scaffold Structure (Full Plan):",
        t("log_sections.unified_tree_desc"),
        "=" * 80,
        unified_tree_text,
        "",
        "@@@COMMENT_BEGIN FINAL BRIEFING",
        f"SCAFFOLD APPLY STATUS: {status_str}{display_name}",
        f"- New Directories: {stats['dirs_created']}",
        f"- New Files: {stats['files_created']}",
        f"- Overwritten Files: {stats['files_overwritten']}",
        f"- .gitkeep Created: {stats.get('gitkeep_created', 0)}",
        f"- Total Errors: {stats['dirs_error'] + stats['files_error']}",
        "@@@COMMENT_END"
    ])

    if applied_structure_text:
        log_entries.extend([
            "",
            "@@@COMMENT_BEGIN Actually Applied Structure (Newly Created/Updated Only)",
            t("log_sections.applied_structure_desc"),
            applied_structure_text,
            "@@@COMMENT_END"
        ])

    if gitkeep_structure_text:
        log_entries.extend([
            "",
            "@@@COMMENT_BEGIN Actually Applied .gitkeep Structure",
            t("log_sections.gitkeep_structure_desc"),
            gitkeep_structure_text,
            "@@@COMMENT_END"
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
        log_entries.append(content if content is not None else "")
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
            raw_content = content or ""
            temp_content = raw_content.replace('\r\n', '\n').replace('\r', '\n')
            final_content = temp_content.replace('\n', '\r\n')
            path.write_bytes(final_content.encode('utf-8'))
        except Exception as e:
            log_exec(f"[ERROR] write file failed: {path} | {e}", "error")
            return False, False, False
    return True, True, False
