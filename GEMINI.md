# Engineering Mandates & Architectural Decisions

This document contains foundational mandates for the TreeScaffolder project. These rules take absolute precedence over general workflows.

## 1. Strict Separation of Truths (Diff View)

The application maintains a rigorous boundary between the current state of the file system and the proposed scaffolding plan.

### 1.1. Before View (The Physical Truth)
- **Source**: Must ALWAYS and ONLY read directly from the physical disk using `path.read_text()`.
- **Purpose**: To show exactly what exists on the machine at this moment.
- **Constraint**: Never display planned or recovered content in this view. If a file doesn't exist on disk, it must clearly state so.

### 1.2. After View (The Planned Truth)
- **Source**: Must ALWAYS and ONLY read from the application's memory (`current_plan.file_contents`), which is derived from the UI Editors.
- **Purpose**: To show the world as it *will* be after applying the scaffold.
- **Mandate - No Fallback**: **NEVER** fall back to reading from the disk if a file is not found in the plan. If the plan doesn't define content for a file, the view must state "(No changes planned)" or similar. Falling back to disk content in the After View creates a "False Positive" where the user thinks a file is correctly planned when it is actually just an existing file.

## 2. Event Handling & Synchronization

### 2.1. Selection Synchronization
- When an item is selected in the **After View**, the application automatically selects the corresponding item in the **Before View**.
- **Implementation**: This must be guarded by the `_in_selection_sync` flag to prevent recursive event loops and "Event Fighting," where the Before View's selection event accidentally overwrites the content tab with disk data while the user is trying to inspect the plan.

## 3. Path Matching Logic
- When looking up content in `file_contents`, always use **case-insensitive string comparison of resolved absolute paths**.
- **Reason**: Windows environments often have inconsistencies with casing and relative path resolutions. String-based matching ensures that recovery logs (which often use relative paths) correctly map to the internal plan.

## 4. Operational Directives (AI & Developers)

To maintain project stability and integrity, all contributors must adhere to these rules:

-   **Preserve Existing Functionality**: DO NOT modify or refactor existing features unless it is strictly necessary to fulfill a specific requirement.
-   **Minimal Intervention**: Always prefer the smallest possible change. Avoid "cleanup" or "stylistic refactoring" of unrelated code blocks.
-   **Strict Scope**: Only implement what is requested. Do not add "just-in-case" features or expand the scope without explicit instruction.
-   **Bug Reporting**: If a critical bug or logical flaw is discovered in existing code, report it immediately (log it or notify the user) rather than silently attempting a large-scale fix that might break dependencies.
-   **Empirical Validation**: Any change to the core logic must be verified with a test script or manual walkthrough before completion.
