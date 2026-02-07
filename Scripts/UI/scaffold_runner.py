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
from Scripts.UI import app_utils # Import app_utils for logging

def execute_scaffold(app):
    """Performs the actual file and directory creation."""
    plan = app.current_plan
    is_dry_run = app.dry_run.get()
    
    captured_logs = []
    # Temporarily override _log method to capture logs for file writing
    original_log_method = app._log
    app._log = lambda msg, level="info": app_utils.log_message(app, msg, level, buffer_list=captured_logs)

    app._log("="*60)
    
    if is_dry_run:
        app._log("Starting scaffold simulation (DRY RUN)...", "warn")
    else:
        app._log("Starting scaffold operation...", "info")
    
    total_content_lines = sum(len(content.splitlines()) for content in plan.file_contents.values())

    num_planned_new_dirs = len([p for p in plan.planned_dirs if plan.path_states.get(p) == 'new'])
    num_planned_new_files = len([p for p in plan.planned_files if plan.path_states.get(p) == 'new'])
    num_planned_overwrite_files = len([p for p in plan.planned_files if plan.path_states.get(p) == 'overwrite'])

    app._log(f"\nPlanned Actions Summary:")
    app._log(f"- New directories: {num_planned_new_dirs}")
    app._log(f"- New files: {num_planned_new_files}")
    app._log(f"- Overwritten files: {num_planned_overwrite_files}")
    app._log(f"- Total lines of content to be written: {total_content_lines} lines")
    app._log("="*60)

    stats = {"dirs_created": 0, "dirs_skipped": 0, "dirs_error": 0, "files_created": 0, "files_overwritten": 0, "files_skipped": 0, "files_error": 0}
    successful_paths = []

    for path in sorted(list(plan.planned_dirs), key=lambda p: len(p.parts)):
        state = plan.path_states.get(path)
        if state == "new":
            ok, created, skipped = _ensure_dir(app, path, is_dry_run, successful_paths)
            if ok:
                if created:
                    stats["dirs_created"] += 1
                    successful_paths.append(path)
                if skipped: stats["dirs_skipped"] += 1
            else:
                stats["dirs_error"] += 1
        elif state == "exists":
            app._log(f"[SKIP DIR]  {path}", "skip")
            stats["dirs_skipped"] += 1

    for path in sorted(list(plan.planned_files), key=lambda p: len(p.parts)):
        state = plan.path_states.get(path)
        content = plan.file_contents.get(path.resolve())

        if state == "new" or state == "overwrite":
            is_overwrite = state == "overwrite"
            ok, created, skipped = _ensure_file(app, path, is_dry_run, content, is_overwrite, successful_paths)
            if ok:
                if created and not is_overwrite:
                    stats["files_created"] += 1
                    successful_paths.append(path)
                if created and is_overwrite:
                    stats["files_overwritten"] += 1
                    successful_paths.append(path)
                if skipped: stats["files_skipped"] += 1
            else:
                stats["files_error"] += 1
        elif state == "exists":
            app._log(f"[SKIP FILE] {path}", "skip")
            stats["files_skipped"] += 1
    
    app._log("\n" + "="*25 + " SUMMARY " + "="*26)
    app._log(f"- Dirs created: {stats['dirs_created']}, skipped: {stats['dirs_skipped']}, errors: {stats['dirs_error']}")
    app._log(f"- Files created: {stats['files_created']}, overwritten: {stats['files_overwritten']}, skipped: {stats['files_skipped']}, errors: {stats['files_error']}")
    
    if plan.duplicate_warnings or plan.similarity_warnings:
        app._log("\n--- Warnings ---", "warn")
        app._log(f"- Duplicate name warnings: {len(plan.duplicate_warnings)}", "warn")
        app._log(f"- Similar name warnings: {len(plan.similarity_warnings)}", "warn")

    app._log("="*60)
    if stats["dirs_error"] > 0 or stats["files_error"] > 0:
        app._log("Operation finished with errors.", "error")
    else:
        app._log("Operation finished successfully.", "success")
        # If it was a real run, update the plan's state to reflect what was written
        if not is_dry_run:
            for path in successful_paths:
                if path.is_dir():
                    plan.path_states[path] = 'exists'
                elif path.is_file():
                    try:
                        actual_content = path.read_text(encoding='utf-8', errors='replace')
                        planned_content = plan.file_contents.get(path.resolve())
                        
                        # Normalize line endings (CRLF to LF) and handle None vs empty string
                        norm_actual = (actual_content or "").replace('\r\n', '\n')
                        norm_planned = (planned_content or "").replace('\r\n', '\n')
                        
                        if norm_actual == norm_planned:
                            plan.path_states[path] = 'exists'
                            app._log(f"Successfully verified content for {path}. State set to 'exists'. Current state: {plan.path_states.get(path)}", "debug")
                        else:
                            app._log(f"Content verification failed for {path}. State not updated. Current state: {plan.path_states.get(path)}", "warn")
                            
                    except Exception as e:
                        app._log(f"Could not verify file content for {path}: {e}", "error")

        if app.open_folder_after_apply.get():
            try:
                app._log(f"Opening folder: {plan.root_path}", "info")
                # Cross-platform way to open the file explorer
                if sys.platform == "win32":
                    os.startfile(plan.root_path)
                elif sys.platform == "darwin": # macOS
                    subprocess.Popen(["open", plan.root_path])
                else: # Linux and other UNIX-like
                    subprocess.Popen(["xdg-open", plan.root_path])
            except Exception as e:
                app._log(f"Failed to open folder: {e}", "error")

    _write_execution_log(app, stats, is_dry_run, captured_logs, original_log_method)
        
    # Restore original _log method
    app._log = original_log_method

    app.log_text.config(state="normal")
    app.log_text.delete("1.0", "end")
    
    # Re-insert summary into actual log_text
    summary_header = (
        f"{'DRY RUN' if is_dry_run else 'EXECUTION'} SUMMARY\n"
        f"New Directories: {stats['dirs_created']}\n"
        f"New Files: {stats['files_created']}\n"
        f"Overwritten Files: {stats['files_overwritten']}\n"
    )
    
    app._log(summary_header, "info")
    app._log("\n--- detail ---\n")

    for message, level in captured_logs:
        app._log(message, level)
    
    app.log_text.config(state="disabled")
        
    app.recompute_button.config(state="normal")
    app.apply_button.config(state="normal" if plan and not plan.has_conflicts else "disabled")
    app._populate_before_tree(plan.root_path)
    app._populate_after_tree(plan)
    app.notebook.select(0)

def _write_execution_log(app, stats: dict, is_dry_run: bool, captured_logs: list, original_log_method):
    """Writes a comprehensive execution log to a timestamped file."""
    log_path = Path.cwd() / app.LOG_DIR
    log_path.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = log_path / f"scaffold_execution_{timestamp}.log"

    tree_content = app.tree_text.get("1.0", "end").strip()
    source_content = app.source_code_text.get("1.0", "end").strip()

    summary_header = (
        f"{'DRY RUN' if is_dry_run else 'EXECUTION'} SUMMARY\n"
        f"New Directories: {stats['dirs_created']}\n"
        f"New Files: {stats['files_created']}\n"
        f"Overwritten Files: {stats['files_overwritten']}\n"
        f"Directory Errors: {stats['dirs_error']}\n"
        f"File Errors: {stats['files_error']}\n"
    )

    log_entries = [
        f"Execution Log - {datetime.datetime.now().isoformat()}",
        "=" * 80,
        summary_header,
        "=" * 80,
        "\n--- detail ---\n",
    ]

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
        # Use the original _log method for this final log message,
        # otherwise, it would try to write to captured_logs which is not what we want here.
        original_log_method(f"Execution details logged to: {log_filename}", "info")
    except Exception as e:
        original_log_method(f"Error writing execution log: {e}", "error")

def _ensure_dir(app, path: Path, dry_run: bool, successful_paths: list) -> tuple[bool, bool, bool]:
    """(ok, created, skipped)"""
    if path.exists():
        app._log(f"[SKIP DIR]  {path}", "skip")
        return True, False, True

    app._log(f"[MKDIR]     {path}", "info")
    if not dry_run:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            app._log(f"[ERROR] mkdir failed: {path} | {e}", "error")
            return False, False, False
    return True, True, False

def _ensure_file(app, path: Path, dry_run: bool, content: str | None, is_overwrite: bool, successful_paths: list) -> tuple[bool, bool, bool]:
    """(ok, created, skipped)"""
    verb = "[OVERWRITE]" if is_overwrite else "[CREATE]"
    
    if not is_overwrite and path.exists():
        app._log(f"[SKIP FILE] {path} (already exists)", "skip")
        return True, False, True

    log_level = "info" if content is not None else "success"
    app._log(f"{verb:<11} {path}", log_level)

    if not dry_run:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content or "", encoding='utf-8')
            
            try:
                written_binary_content = path.read_bytes()
                original_binary_content = (content or "").encode('utf-8')

                extra_newline_added = False
                if written_binary_content.endswith(b'\r\n') and not original_binary_content.endswith(b'\r\n'):
                    extra_newline_added = True
                    truncate_bytes = 2
                elif written_binary_content.endswith(b'\n') and not original_binary_content.endswith(b'\n'):
                    extra_newline_added = True
                    truncate_bytes = 1
                
                if extra_newline_added:
                    with open(path, 'wb') as f:
                        f.write(written_binary_content[:-truncate_bytes])
                    app._log(f"[FIX] Hardcoded: Removed implicit extra newline from {path}", "warn")

            except Exception as fix_e:
                app._log(f"[ERROR] Hardcoded newline fix failed for {path}: {fix_e}", "error")
        except Exception as e:
            app._log(f"[ERROR] write file failed: {path} | {e}", "error")
            return False, False, False
    return True, True, False