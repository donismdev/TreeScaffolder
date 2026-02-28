> ⚠️ **CRITICAL WARNING**: This tool directly modifies the file system. To prevent accidental data loss, it is strongly recommended to use it in environments with **Version Control Systems (Git, SVN, etc.)** or to perform a **backup** before any operation.
>
# TreeScaffolder: Prompt Helper & File System Scaffolder

TreeScaffolder is a tool designed to **maximize LLM prompting efficiency** and safely reflect text-based blueprints onto the **actual file system**.

---

## 🚀 Key Features

*   **Task Assistant**: Eliminates the tedious manual work of copying, pasting, and saving LLM outputs.
*   **Empty Structure Creation**: Instantly create empty folders and shell files based on tree text alone.
*   **Visual Comparison**: Contrast actual disk state with planned changes to prevent mistakes.
*   **Safety Guards**: Protect data through Dry Run simulations and automatic backups.
*   **History Management**: Organize all execution history into folders with unique Job Names.

---

## 📖 Usage (Prompt Workflow)

### 1. Enter Source Code (Source-First)
Paste the source code blocks received from the LLM into the `Source Code` tab. This step alone is enough for the tool to identify the project's folder structure.

### 2. Supplement Tree & Analyze
If you need additional empty folders, write them in the `Scaffold Tree` tab. Then press **Compute Diff (`d`)** to compare with the actual disk.

### 3. Name the Job & Review
Once analysis is complete, press **shortcut `4`** to enter a job name. Review the target items in the `After View` using status colors and checkboxes.

### 4. Apply & Recover
Press **Apply Scaffold (`f`)** to create actual files. If you mistakenly overwrite something, you can always revert it using the **Recovery (`q`)** window.

---

## ⌨️ Essential Shortcuts

*   **d**: Compute Diff (Calculate plan)
*   **4**: Focus Job Name entry field
*   **f**: Apply Scaffold (Execute)
*   **q**: Open Recovery window
*   **r**: Clear all data
*   **e/w**: Load previous folder / Browse new folder
*   **Alt**: Display shortcut hints (Hold)

---

## ⚠️ Precautions

*   **Data Backup**: Always make it a habit to back up important data in advance.
*   **No AI Refactoring**: The code in this project prioritizes empirical safety over performance. Arbitrary AI-driven optimizations are strictly prohibited.

---

## 📧 Support & Bug Reports
*   **Email**: donism.dev@gmail.com
