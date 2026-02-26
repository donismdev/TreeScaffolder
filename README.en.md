> ⚠️ **Warning**: This tool modifies the file system directly. You **MUST** use it with a version control system like **Git or SVN** to ensure data safety. (반드시 **Git, SVN** 등과 함께 사용해야 합니다.)

[English](README.en.md) | [한국어](README.ko.md)

# 🌲 Tree Scaffolder User Guide

"Tree Scaffolder" is a tool that easily and safely creates actual folders and files on your computer based on blueprints written in text (tree structures and file contents). You can quickly configure your desired development environment with just a few clicks, without having to manually create complex file structures. Don't worry if you're not familiar with programming! You can easily follow along with this guide.

---

## ✨ Key Features

*   **Text-Based Design**: Intuitively manage folder structures and file contents by writing them in text.
*   **Visual Comparison (Diff View)**: Check the changes in folder structure before and after scaffolding (file creation) at a glance. It provides a preview of which files will be created or changed depending on where you click.
*   **Interactive Item Selection & Sync**: Selectively apply specific items using checkboxes (`☑`/`☐`) in the After view. Clicking an item in the After view instantly locates and expands it in the Before view.
*   **Intuitive Focus Highlight**: Clearly distinguish whether you are checking the Before or After view through blue (active) and gray (inactive) color coding.
*   **Safe Operation**: Prevents accidental modification of important system folders and displays a warning message with a detailed summary of changes before overwriting existing files.
*   **Shortcut Support**: Quickly execute frequently used functions with shortcuts, and shortcut hints appear on the screen when you press the `Alt` key.
*   **Log Recording**: All operation history can be checked in detailed logs, which helps identify the cause when problems occur.

---

## 🚀 How to Use

### Step 1: Run the Application

Start the "Tree Scaffolder" program by running the `gui_app.py` file.

```bash
python gui_app.py
```

### Step 2: Select File Creation Location (`1. Select Target Root Folder`)

Select the base folder to start the scaffolding (folder and file creation) task.

1.  **Click `Browse...` button**: Find and select the desired folder.
2.  **Click `Prev` button**: Quickly return to the folder you worked on previously.
3.  **Click `Clear` button**: Clear the selected folder information and return to the initial state.

> 💡 **Note**: Important system folders (e.g., `C:\Windows`, `Program Files`, etc.) are protected to prevent accidental selection. Use with confidence.

### Step 3: Design Folder Structure (`2. Define Scaffold Tree`)

Write the desired folder and file structure in text in the 'Scaffold Tree' editor at the top left.

*   **`@ROOT {{Root}}`**: Always start with this sentence, which means the top-level folder of the scaffolding. The `{{Root}}` part is replaced with the actual selected target folder name.
*   **Strict Indentation (Python Style)**:
    *   **Do not mix Tabs (	) and Spaces**: Just like Python, mixing tabs and spaces in one tree will cause an error. Choose one and stick with it.
    *   **Consistent Units**: The number of spaces you indent first (e.g., 2 or 4 spaces) becomes the standard for that tree. All lines must be indented by multiples of this standard.
*   **Distinguish Folders and Files**:
    *   If you add `/` or `` (slash/backslash) to the end of the name, it is recognized as a **folder**. (e.g., `MyFolder/`)
    *   If there is no folder indication at the end of the name, it is recognized as a **file**. (e.g., `MyFile.txt`)

**Example:**

```
@ROOT {{Root}}

{{Root}}/
    ProjectX/
        Source/
            Core/
                Module.h
            Public/
        README.md
```

### Step 4: Write File Content (`Source Code` Tab)

Write the actual contents of the file you want to create in the 'Source Code' tab editor. You must indicate the start and end of the file content with special markers: `@@@FILE_BEGIN` and `@@@FILE_END`.

*   **`@@@FILE_BEGIN [File Path]`**: Start writing file content with this sentence. In the `[File Path]` part, accurately enter the path of the file defined in 'Scaffold Tree', starting from `@ROOT`.
*   **`@@@FILE_END`**: Finish writing file content with this sentence.

**Example:** How to define the content of the `ProjectX/README.md` file:

```
@@@FILE_BEGIN {{Root}}/ProjectX/README.md
# Getting Started with Project X

This project provides a basic skeleton for developing new features.
Follow these steps to get started:

1. Environment Setup
2. Run Build
3. Test
@@@FILE_END
```

> 💡 **Important**: All content (including line breaks and spaces) between `@@@FILE_BEGIN` and `@@@FILE_END` is saved to the file exactly as written.

> 💡 **Quick Tree Generation Tip: `make tree` button**
> When you select the 'Source Code' tab, the `make tree` button above the editor becomes active. If the `@@@FILE_BEGIN...END` blocks are already written, you can click this button to automatically generate the structure of 'Scaffold Tree' based on those file paths. This is a convenient feature that shortens the process of manually writing the tree structure.

*   **`@@@COMMENT_BEGIN` / `@@@COMMENT_END`**: Content between these tags is completely ignored during scaffolding. You can use it to leave comments or temporary notes.

### Step 5: Check Scaffold Plan (`Compute Diff` button)

Once you have written all the content in the 'Scaffold Tree' and 'Source Code' editors, click the `Compute Diff` button to check the scaffolding plan.

*   **`Before / After Diff` Tab**:
    *   **Before (Current State)**: Shows the file/folder structure of the currently selected target folder.
    *   **After (Planned State)**: Shows the expected file/folder structure after scaffolding via `Compute Diff`.
*   **Check Status by Color**:
    *   **Green (`new`)**: A file/folder to be newly created. Clicking it allows you to preview the content to be created (if defined).
    *   **Teal (`overwrite`)**: A file where the existing content is scheduled to be overwritten with new content. Clicking it allows you to preview the **new content to be changed, not the existing content**.
    *   **Black (No Change)**: An item that is not included in the plan or is identical to the existing one. Clicking it shows the content currently on disk.
    *   **Red (`conflict`)**: An item where an unexpected conflict has occurred (e.g., planned as a file but a folder already exists at that path). Scaffolding cannot be applied if there is any red.

### Step 6: Apply Scaffold (`Apply Scaffold` button)

If you have confirmed that there are no problems with the planned structure in the `After` tab, click the `Apply Scaffold` button to create the actual files and folders.

> ⚠️ **Very Important**: This operation applies changes directly to your computer's file system. Especially for files marked in blue (`overwrite`), the existing content will disappear and be completely replaced with new content. **Always back up important files** and proceed only after careful confirmation.

*   **`Dry Run` Option**: If you check the 'Dry Run (don't write files)' option before clicking `Compute Diff`, you can simulate the plan without actually creating files. Be sure to use it before actual application.
*   **`Open folder after Apply Scaffold` Option**: Automatically opens the created folder after scaffolding is complete.

### Step 7: Check Operation Log (`Log` Tab)

The progress, errors, and warning messages of all scaffolding operations are recorded in detail in the 'Log' tab. If a problem occurs, you can check this log to identify the cause.

---

## 8. Shortcuts

You can quickly execute various functions within the application using keyboard shortcuts.

*   **t**: Load test data (when editor is not focused)
*   **Space**: (In After View) Toggle checkbox for selected item
*   **d**: Compute Diff
*   **f**: Apply Scaffold
*   **v**: Go to previous folder
*   **b**: Browse folder
*   **c**: Clear data
*   **`** (Grave): Cycle analysis panel tabs
*   **1, 2, 3**: Cycle tabs in each area
*   **Alt**: Display shortcut hints (hold to show yellow overlays)

---

## 9. Precautions

*   **Data Backup**: Since the `Apply Scaffold` function can overwrite existing files, please make it a habit to always back up important data in advance.
*   **Utilize `Dry Run`**: Be sure to use the `Dry Run` option to preview all changes before applying the actual scaffolding.

---