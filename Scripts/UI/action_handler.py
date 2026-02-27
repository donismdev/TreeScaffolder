# -*- coding: utf-8 -*-
"""
action_handler.py

Centralized handler for user actions.
Updates the UI summary and executes logic for various user triggers.
"""
from pathlib import Path
from Scripts.Utils.i18n import t

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
    # Only count items that are selected AND not excluded by an unchecked parent
    def is_effectively_selected(path):
        # 1. Check if the item itself is unchecked
        if not app.selected_paths.get(path, True):
            return False
            
        # 2. Check if any parent is unchecked (matching _is_excluded_by_parent logic)
        root_path = plan.root_path
        parent = path.parent
        while parent != root_path and parent.is_relative_to(root_path):
            if parent in app.selected_paths and not app.selected_paths[parent]:
                return False
            parent = parent.parent
        return True

    new_files = sum(1 for p, s in plan.path_states.items() if s == 'new' and p in plan.planned_files and is_effectively_selected(p))
    new_dirs = sum(1 for p, s in plan.path_states.items() if s == 'new' and p in plan.planned_dirs and is_effectively_selected(p))
    overwrites = sum(1 for p, s in plan.path_states.items() if p in plan.planned_files and s == 'overwrite' and is_effectively_selected(p))
    
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

def handle_make_tree_result(app, success=True):
    """Called after make tree from source code action."""
    key = "make_tree_success" if success else "make_tree_error"
    update_summary(app, key)

def handle_language_changed(app):
    """Called after UI language is changed."""
    update_summary(app, "language_changed")

def handle_error(app, action_key):
    """Updates the summary to indicate an error in a specific action."""
    update_summary(app, f"error_{action_key}")
