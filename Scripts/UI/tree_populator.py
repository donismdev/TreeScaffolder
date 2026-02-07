# -*- coding: utf-8 -*-
"""
tree_populator.py

Logic for populating the Treeview widgets in the Tree Scaffolder GUI.
"""
from pathlib import Path
from tkinter import messagebox, ttk

def _clear_tree(tree: ttk.Treeview):
    """Removes all items from a treeview."""
    for item in tree.get_children():
        tree.delete(item)

def populate_before_tree(app, root_path: Path):
    """Fills the 'Before' treeview with the contents of the root_path."""
    _clear_tree(app.before_tree)
    _clear_tree(app.before_list)
    
    # Insert the root directory
    icon = app.classifier.classify_path(root_path)
    root_node = app.before_tree.insert("", "end", text=f"{icon} {root_path.name}", open=True, values=[str(root_path)])
    
    # Dictionary to keep track of parent nodes in the treeview
    dir_nodes = {str(root_path): root_node}
    
    all_paths = []
    try:
        # Security: prevent walking up from the root path
        for p in root_path.rglob('*'):
            all_paths.append(p)
    except Exception as e:
        messagebox.showerror("Error Reading Directory", f"Could not read the directory contents: {e}")
        return

    # Sort paths to ensure parents are created before children and consistent ordering
    all_paths.sort(key=lambda p: (len(p.parts), p.name.lower()))

    for path in all_paths:
        # Populate Tree View
        parent_path_str = str(path.parent)
        parent_node_id = dir_nodes.get(parent_path_str)
        
        if parent_node_id is None:
            continue

        icon = app.classifier.classify_path(path)
        if path.is_dir():
            node = app.before_tree.insert(parent_node_id, "end", text=f"{icon} {path.name}", open=False, values=[str(path)])
            dir_nodes[str(path)] = node
        else:
            app.before_tree.insert(parent_node_id, "end", text=f"{icon} {path.name}", values=[str(path)])
            # Populate List View (only files)
            relative_path = path.relative_to(root_path)
            app.before_list.insert("", "end", text=f"{icon} {relative_path}", values=[str(path)])

def populate_after_tree(app, plan):
    """Renders the generated plan in the 'After' treeview and listview."""
    _clear_tree(app.after_tree)
    _clear_tree(app.after_list)
    if not plan:
        return
    root_path = plan.root_path

    # Calculate modified parent directories (for coloring)
    modified_parent_dirs = set()
    # Get all unique paths that are part of the plan, including those with content
    all_involved_paths = set(plan.planned_dirs).union(plan.planned_files)
    all_involved_paths.update(plan.file_contents.keys()) # Include files from file_contents

    for p_obj in all_involved_paths:
        # Ensure p_obj is a Path object for consistency
        p_path = p_obj if isinstance(p_obj, Path) else Path(p_obj)

        state = plan.path_states.get(p_path)
        
        # A path contributes to modified parents if its current state is 'new', 'overwrite', or 'conflict'
        if state in ('new', 'overwrite', 'conflict_file', 'conflict_dir'):
            current_parent = p_path.parent
            while current_parent != root_path and current_parent.is_relative_to(root_path):
                modified_parent_dirs.add(current_parent)
                current_parent = current_parent.parent
            # Also add the root_path itself if it's an ancestor and contains modified children
            if root_path in p_path.parents:
                modified_parent_dirs.add(root_path)

    # Populate the main 'After (Planned State)' tree
    _populate_treeview_from_plan(app, app.after_tree, plan, root_path, 
                                     lambda p, plan_obj, mpd: True, modified_parent_dirs, auto_open_modified=True)
    
    # Populate the 'Apply Tree' (after_list)
    _populate_treeview_from_plan(app, app.after_list, plan, root_path, 
                                     lambda p, plan_obj, mpd: plan_obj.path_states.get(p) in ('new', 'overwrite', 'conflict_file', 'conflict_dir') or p in mpd, modified_parent_dirs, auto_open_modified=True)

def _populate_treeview_from_plan(app, tree_widget: ttk.Treeview, plan_obj, root_path_param: Path, filter_func, modified_parent_dirs: set, auto_open_modified: bool):
    dir_nodes = {}

    # 1. Insert the root node
    icon = app.classifier.classify_path(root_path_param)
    root_node_id = tree_widget.insert("", "end", text=f"{icon} {root_path_param.name}", open=True, values=[str(root_path_param)])
    dir_nodes[root_path_param] = root_node_id

    # Gather all relevant paths
    all_paths_to_consider = set(plan_obj.planned_dirs).union(plan_obj.planned_files)
    try:
        for p in root_path_param.rglob('*'):
            all_paths_to_consider.add(p)
    except Exception:
        pass

    sorted_paths = sorted(list(all_paths_to_consider), key=lambda p: (len(p.parts), p.name.lower()))
    
    for path in sorted_paths:
        if path == root_path_param:
            continue
        
        should_include = filter_func(path, plan_obj, modified_parent_dirs)

        if should_include:
            ancestors_to_process = []
            p_check = path.parent
            while p_check != root_path_param:
                if p_check in dir_nodes:
                    break
                ancestors_to_process.append(p_check)
                p_check = p_check.parent
            ancestors_to_process.reverse()

            for ancestor_path in ancestors_to_process:
                parent_of_ancestor_id = dir_nodes.get(ancestor_path.parent, root_node_id)

                intermediate_icon = app.classifier.classify_path(ancestor_path, is_planned_dir=ancestor_path.is_dir() or ancestor_path in plan_obj.planned_dirs)
                intermediate_tags = ['modified_parent'] if ancestor_path in modified_parent_dirs else []
                
                if ancestor_path not in dir_nodes:
                    node = tree_widget.insert(parent_of_ancestor_id, "end", text=f"{intermediate_icon} {ancestor_path.name}", open=auto_open_modified, tags=intermediate_tags, values=[str(ancestor_path)])
                    dir_nodes[ancestor_path] = node
                elif auto_open_modified:
                    tree_widget.item(dir_nodes[ancestor_path], open=True)
            
            parent_node_id = dir_nodes.get(path.parent, root_node_id)

            tags = []
            state = plan_obj.path_states.get(path)
            if state == 'new': tags.append('new')
            elif state == 'overwrite': tags.append('overwrite')
            elif state in ('conflict_file', 'conflict_dir'): tags.append('conflict')
            if path in modified_parent_dirs: tags.append('modified_parent')
            
            icon = app.classifier.classify_path(path, is_planned_dir=path.is_dir() or path in plan_obj.planned_dirs)
            
            item_is_directory = path.is_dir() or path in plan_obj.planned_dirs
            should_open_this_item = auto_open_modified and item_is_directory
            
            node_id = tree_widget.insert(parent_node_id, "end", text=f"{icon} {path.name}", tags=tags, values=[str(path)], open=should_open_this_item)
            
            if item_is_directory:
                dir_nodes[path] = node_id
