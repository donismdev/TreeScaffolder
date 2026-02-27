> ⚠️ **Warning**: This tool modifies the file system directly. You **MUST** use it with a version control system like **Git or SVN** to ensure data safety. (반드시 **Git, SVN** 등과 함께 사용해야 합니다.)

[English](GUIDE.en.md) | [한국어](GUIDE.ko.md)

# 🌲 Tree Scaffolder Technical Manual

This document provides a detailed explanation of the internal operations, data flow, and core logic of the "Tree Scaffolder" tool for future maintenance and feature additions.

---

## 1. Core Purpose

It is a productivity tool for developers that creates (scaffolds) directories and files at a specified path based on a tree structure and file contents defined in text.

---

## 2. Components (Core Scripts)

-   `gui_app.py`
    -   **Role**: Main GUI application (Tkinter-based).
    -   **Key Features**: Handles user input (tree, source code), root folder selection, calls `scaffold_core`, visualizes results (Diff), executes actual file creation, and displays warning windows before overwriting.

-   `scaffold_core.py`
    -   **Role**: **Core logic** that generates the scaffolding plan.
    -   **Key Features**: Parses input text to create a `NodeItem` list, calls `v2_parser` to extract file contents, analyzes the file system to create a `Plan` object containing create/change/conflict states.
    -   **Characteristic**: **Does not perform direct write operations to the file system (NO I/O).** It only establishes the plan.

-   `v2_parser.py`
    -   **Role**: **V2 format parser** for defining file contents.
    -   **Key Features**: Analyzes `@@@FILE_BEGIN` and `@@@FILE_END` syntax to extract file paths and contents.

-   `scaffold_from_tree.py`
    -   **Role**: **CLI version** that can be run independently without a GUI.
    -   **Key Features**: Reads the `TREE_TEXT` variable within the script, calls `scaffold_core`, and applies it to the file system immediately.

-   `file_classifier.py` / `file_type_icons.json`
    -   **Role**: Determines the file/folder icons to be displayed in the GUI tree view.

-   `folder_selection_validator.py`
    -   **Role**: External script that validates whether the root folder selected in the GUI is not a dangerous path like a system folder.

---

## 3. Input Format

Two types of text input are combined to create one plan.

### 3.1. Scaffold Tree Syntax

-   **Purpose**: Defines directory structure and empty files.
-   **Rules**:
    -   `@ROOT {{Root}}`: Declares the logical root where scaffolding will begin.
    -   **Strict Indentation (Python Style)**:
        -   **Do not mix Tabs (	) and Spaces**: You cannot mix both methods within one tree. Mixing them causes a `TabError`.
        -   **Consistent Unit Usage**: The unit used in the first indentation (e.g., 4 spaces or 2 spaces) becomes the standard unit for that tree. All indentations must be multiples of this unit; otherwise, an `IndentationError` occurs.
    -   If there is a `/` or `` at the end of the name, it is recognized as a directory; otherwise, it is recognized as a file.

    ```
    @ROOT {{Root}}

    {{Root}}/
        NewModule/
            Public/
                NewModule.h
            Private/
                NewModule.cpp
            NewModule.Build.cs
    ```

### 3.2. Block Syntax (V2)

-   **Purpose**: Defines text blocks with specific purposes, such as file contents and comments.
-   **Rules**:
    -   Start defining block content with `@@@<KEYWORD>_BEGIN [Optional Identifier]`. `<KEYWORD>` is a reserved keyword such as `FILE`, `COMMENT`, etc.
    -   End the content definition with `@@@<KEYWORD>_END`. The `KEYWORD` must match the start tag.
    -   **Most Important Rule**: The parser only recognizes blocks clearly wrapped with `@@@..._BEGIN` and `@@@..._END`. **All text outside of the blocks is considered a comment and completely ignored.**
    -   All `BEGIN` and `END` tags must be correctly paired in order, and blocks cannot be nested within other blocks. Violations will cause an error.
    -   The parser uses block contents of recognized keywords like `FILE`, and skips block contents of keywords set to be ignored like `COMMENT`. Blocks of unrecognized keywords are also ignored.

#### Example: File Content Block (`FILE`)

```
@@@FILE_BEGIN {{Root}}/NewModule/NewModule.Build.cs
using UnrealBuildTool;

public class NewModule : ModuleRules
{
    public NewModule(ReadOnlyTargetRules Target) : base(Target)
    {
        // ...
    }
}
@@@FILE_END
```

#### Example: Comment Block (`COMMENT`)

```
This text is ignored.

@@@COMMENT_BEGIN This block is recognized by the parser, but its content is not included in the output.
- Notes on the build process
- Temporarily disabled code
You can write such things here.
@@@COMMENT_END

This text is also ignored.
```

### 3.3. Editor Toolbar

At the top of the text editor in the "Define Scaffold Tree" panel, there is a toolbar whose status changes dynamically.

-   **Operation Rules**: Buttons on the toolbar are enabled or disabled depending on the currently selected tab ("Scaffold Tree", "Source Code", "Content").
-   **Scaffold Tree / Content Tabs**: All toolbar buttons are disabled.
-   **Source Code Tab**:
    -   `make tree` button is enabled.
    -   **Implicit Merge**: During actual scaffolding execution (`generate_plan`), the text from the "Scaffold Tree" editor and the V2 block information from the "Source Code" editor are **logically merged**. Therefore, files defined only in "Source Code" will be created correctly even if you do not use the `make tree` feature.
    -   **`make tree` Feature**:
        1.  Parses all V2 blocks (`@@@FILE_BEGIN...END`, etc.) currently in the "Source Code" editor.
        2.  Based on all extracted `path` information, automatically generates a new tree structure text suitable for "Scaffold Tree".
        3.  Clears all existing content in "Scaffold Tree" and overwrites it with the newly generated tree text.
        4.  Automatically switches to the "Scaffold Tree" tab after the task is complete so you can check the results immediately.
        5.  This feature is useful for reverse-generating a tree structure from text where V2 blocks are already written.

---

## 4. Data Flow and Execution Order (GUI Based)

1.  **User Input**: User enters content into the "Scaffold Tree" or "Source Code" text areas of the GUI and clicks "Compute Diff".
2.  **Plan Generation (`generate_plan`)**:
    -   `gui_app.py` combines the contents of the two text areas and passes them to the `scaffold_core.generate_plan` function.
    -   `scaffold_core` first parses the tree syntax to plan the basic directory/file structure (`planned_dirs`, `planned_files`).
    -   Then it calls `v2_parser.parse_v2_format` to extract file paths and contents from the V2 syntax and saves them in the `file_contents` dictionary.
    -   Scans the file system to record the current state of planned paths (`new`, `exists`, `overwrite`, `conflict`) in the `path_states` dictionary.
    -   A `Plan` object containing all this information is returned to `gui_app.py`.
3.  **Result Visualization**: `gui_app.py` uses the `Plan` object to draw the "Before" and "After" tree views. Different colors and icons are displayed according to states like `new`, `overwrite`, etc.
    -   **Tree Selection Highlight**: When the user clicks a tree item, that tree view gains focus and is highlighted in **deep blue**. At this time, the selected item in the other tree view turns **gray**, visually distinguishing which tree the content displayed in the `Content` tab came from.
4.  **Apply Scaffold (`on_apply`)**:
    -   User clicks "Apply Scaffold".
    -   **Confirmation Message and Summary**:
        -   **Dry Run Mode**: Informs that actual files will not be created and shows a summary of the number of folders/files/overwrites to be simulated.
        -   **Normal Mode**: With a **strong warning (⚠️)** about actual file system changes, the user is asked to confirm the exact number of items to be created and overwritten.
    -   If the user agrees, the `_execute_scaffold` method is called.
5.  **File System Write (`_execute_scaffold`)**:
    -   Creates planned directories first (`_ensure_dir`).
    -   Then, creates/overwrites planned files (`_ensure_file`).
    -   The `_ensure_file` function writes files using `path.write_text(content, encoding='utf-8')`. This method guarantees **UTF-8 (no BOM)** encoding and completely overwrites the content if an existing file exists.
6.  **Completion**: When all tasks are finished, a log is recorded, and the "Before/After" views are refreshed.

---

## 5. Core Logic Details

### File Overwrite Logic

-   **Decision Criteria**: In `scaffold_core.generate_plan`, when a path (`path`) on the file system already exists (`path.exists()`), is a planned file (`path in plan.planned_files`), and the file content is also defined in V2 format (`path.resolve() in plan.file_contents`), the status of that file becomes `'overwrite'`.
-   **Execution**: When the `is_overwrite` flag is True, the `_ensure_file` function uses `path.write_text()` to open the existing file and overwrite it with new content.

### Block Content Processing (Verbatim)

-   **Rules**: `v2_parser.py` extracts the content between the `@@@<KEYWORD>_BEGIN` and `@@@<KEYWORD>_END` tags **verbatim** without any modification (e.g., removing line breaks, trimming spaces). Therefore, line breaks and space characters entered in the V2 format are reflected exactly in the final result.

---

## 6. Configuration (`config.json`)

A configuration file that controls the operation of the application.

-   `enable_runtime_logging` (boolean)
    -   **`true`**: When the application runs, it creates a `runtime.log` file that records all operations and errors. This log is more detailed than the GUI's log panel and is useful for troubleshooting.
    -   **`false`**: Does not create a `runtime.log` file.

---

## 7. Keyboard Shortcuts

The application supports keyboard shortcuts defined in the `Resources/key_bindings_map.json` file.
The list of currently defined shortcuts is as follows:

| Key Sequence   | Action                          | Description                                                                 |
| :------------- | :------------------------------ | :-------------------------------------------------------------------------- |
| `t`            | `Load Test Data`                | Loads test data (only when no text/entry widget is focused). |
| `Space`        | `Toggle Selection`              | (In After View) Toggles the checkbox for the selected item. |
| `Escape`       | `Reset Focus`                   | Resets focus to the root window.                             |
| `` ` `` (Grave)| `Cycle Main Notebook Tabs`      | Cycles through main notebook tabs (when not focused on text). |
| `1`            | `Cycle Before Notebook Tabs`    | Cycles through 'Before' panel tabs.                          |
| `2`            | `Cycle After Notebook Tabs`     | Cycles through 'After' panel tabs.                           |
| `3`            | `Cycle Editor Notebook Tabs`    | Cycles through 'Editor' panel tabs.                          |
| `v`            | `Previous Folder`               | Returns to the previously selected root folder.               |
| `b`            | `Browse Folder`                 | Opens folder browser for a new root folder.                  |
| `c`            | `Clear Data`                    | Clears all editor content and planned data.                  |
| `d`            | `Compute Diff`                  | Calculates the scaffolding plan based on current inputs.      |
| `f`            | `Apply Scaffold`                | Applies the scaffolding plan to the file system.             |

---

## 8. Interactive Features & Analysis Details

### 8.1. Individual Item Selection in After View (Checkboxes)
- **Purpose**: Allows users to selectively apply specific files or folders from the plan, enabling incremental scaffolding.
- **Display**: Checkboxes (`☑`/`☐`) appear in front of items marked as New, Overwrite, or Conflict.
- **Interaction**:
    - **Re-click to Toggle**: Clicking an already selected item a second time toggles its checkbox. (The first click is for viewing content and syncing).
    - **Spacebar**: Toggle the checkbox of the currently focused item in the After View using the Spacebar.
- **Recursive Logic**:
    - **Parent Selection**: Checking a child item automatically checks all its ancestors required to create the path.
    - **Parent Deselection**: Unchecking a parent folder automatically skips all its descendants during the execution phase.
- **Summary Updates**: Changing a checkbox state immediately updates the counts (folders/files) in the bottom `Summary` panel.

### 8.2. Before/After View Synchronization
- **Feature**: Clicking an item in the After View automatically finds, expands, and selects the same path in the Before View. This allows users to quickly see where the planned changes sit within the current project structure.
- **Restriction**: Double-clicking to expand/collapse the tree is disabled to ensure stable single-click/re-click interactions. Use the arrow icons on the left to expand or collapse nodes.

### 7.1. Shortcut Binding Rules and Limitations

Refer to the following rules and limitations when defining shortcuts in the `Resources/key_bindings_map.json` file.

-   **General Keys**: Most alphabets (`a`~`z`), numbers (`0`~`9`), and special characters (`-`, `=`, `,`, etc.) can be bound as single keys.
-   **Special Keys**:
    -   Special keys such as `Space`, `Escape`, and `Grave` (backtick, `` ` ``) can be bound in the form specified above.
    -   Function keys from `F1` to `F12` (such as `F5`) can also be bound.
-   **Modifier Keys**:
    -   `Control` (`Ctrl`), `Alt`, and `Shift` keys are used in combination with other keys rather than performing functions alone (e.g., `Control+S`, `Alt+F`, `Shift+Escape`).
    -   When using modifier keys in `key_bindings_map.json`, connect them with `+` (e.g., `"Control+S"`).
    -   **Particularity of the `Alt` Key**:
        -   The `Alt` key is often reserved for various system functions, such as menu activation, at the operating system level.
        -   In this application, pressing the `Alt` key alone is used for the feature that displays shortcut hints active on the current screen. Therefore, the `Alt` key alone or some shortcuts combined with the `Alt` key may not work as expected or may conflict with system functions.
        -   For example, even if you specify a shortcut containing the `Alt` key, such as `"Alt"` or `"Alt+C"`, Tkinter or the operating system may intercept that event. Therefore, it is not recommended to use the `Alt` key as a main action shortcut.

-   **Impossible Bindings**:
    -   Mouse click events (`<Button-1>`, `<Double-Button-1>`, etc.) are currently difficult to map directly as shortcuts through `key_bindings_map.json`.
    -   Due to limitations of Tkinter and the operating system, some key combinations may be impossible to bind or may show inconsistent behavior.

This document is a guide for the shortcut notation used in the `key_bindings_map.json` file.