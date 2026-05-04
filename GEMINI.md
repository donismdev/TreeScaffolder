# TreeScaffolder Engineering Mandates

This document contains foundational mandates for the TreeScaffolder project. These rules take absolute precedence over general workflows and performance optimizations. **Safety and data integrity are the primary objectives.**

## 1. Strict Isolation of Truths (Data Source Separation)

The application must treat the current state of the filesystem (Before) and the proposed scaffolding plan (After) as two entirely independent universes.

### 1.1 Before View (The Physical Truth)
- **Source**: Must ALWAYS and ONLY read from the physical disk and the `before_cache`.
- **Mandate**: NEVER reference the `current_plan` or any planned data within this view.
- **Purpose**: To show exactly what exists on the machine at this moment.

### 1.2 After View (The Planned Truth)
- **Source**: Must ALWAYS and ONLY read from the application's memory (`file_contents`) and the `after_cache`.
- **Mandate - No Fallback**: NEVER fall back to reading from the disk if a file is not found in the plan. If the plan doesn't define content for a file, the view must state "(No changes planned)" or similar. Falling back to disk content in the After View creates a "False Positive" where the user thinks a file is correctly planned when it is actually just an existing file.
- **Purpose**: To show the world exactly as it *will* be after applying the scaffold.

### 1.3 Cache Isolation
- **Mandate**: The `Before View` and `After View` must use entirely separate caching mechanisms (`before_cache` and `after_cache`).
- **Reasoning**: Sharing a cache between the two views leads to "truth contamination" where physical disk state could be misinterpreted as planned state. Independent caches are a critical defense against AI logic errors.
- **Source Labeling**: Every content display MUST explicitly label its source (e.g., `PHYSICAL CONTENT (Before View)` or `EXISTING CONTENT (After View)`). Never use generic labels that obscure which view's data is being displayed.

## 2. Handler Isolation (No Callback Merging)

- **Mandate**: The event handlers for the Before View (`on_before_select`) and the After View (`on_after_select`) must remain **physically separate functions**.
- **Prohibition**: NEVER merge these handlers into a single function with conditional branches. Even if the logic appears similar, separate callbacks are required to ensure that programmatic synchronization (e.g., the After View selecting a node in the Before View) does not trigger unintended side effects or data overwrites.
- **Reasoning**: In a single-threaded GUI environment (Tkinter), physical separation of callbacks is the most reliable way to prevent recursive event loops ("Event Fighting") and ensure that the "Planned Truth" is never accidentally overwritten by the "Physical Truth."

## 3. No Event Synchronization (Avoid Event Fighting)

- **Mandate**: Do NOT implement selection synchronization between the Before Tree and the After Tree.
- **Reasoning**: Selecting an item in one view must never trigger a selection event in the other. Synchronization leads to recursive event loops ("Event Fighting") and data pollution where one view's logic accidentally overwrites the content display of the other.

## 3. Safety and Integrity Over Performance

- **Priority**: Reliability and data correctness are infinitely more important than speed or memory efficiency.
- **Caching Strategy**: Each view maintains its own independent cache (`before_cache` and `after_cache`). These caches must be purged only during full recomputations (`on_recompute`) or data clears (`on_clear_data`).
- **Path Matching**: Due to Windows-specific casing and resolution inconsistencies, all path comparisons must be performed using the lowercase string representation of the `resolve()`'d absolute path.

## 4. V2 Multipatch Format v1.1 (@@@ Blocks)

All source code definitions and recovery logs must strictly follow the **V2 Multipatch Format v1.1**. This format ensures data integrity and prevents parsing ambiguities.

- **Mandatory Paired Tags**: Every block MUST start with `@@@<KEYWORD>_BEGIN {{Parameter}}` and end with `@@@<KEYWORD>_END`. Unpaired tags or nested blocks are forbidden (except for operations inside `PATCH`).
- **Mandatory Parameters**: Every BEGIN tag must have a `{{Parameter}}`. If no parameter is needed, use `{{None}}`.
- **Supported Keywords**:
    - `FILE_BEGIN {{Root}}/Path` / `FILE_END`: Overwrites entire file.
    - `PATCH_BEGIN {{Root}}/Path` / `PATCH_END`: Modifies part of a file.
    - `FIND_BEGIN {{None}}` / `FIND_END`: Context for subsequent operations.
    - `REPLACE_BEGIN {{None}}` / `REPLACE_END`: Replaces found text.
    - `INSERT_AFTER_BEGIN {{None}}` / `INSERT_AFTER_END`: Inserts after found text.
    - `INSERT_BEFORE_BEGIN {{None}}` / `INSERT_BEFORE_END`: Inserts before found text.
    - `INSERT_TOP_BEGIN {{None}}` / `INSERT_TOP_END`: Inserts at file start.
    - `INSERT_BOTTOM_BEGIN {{None}}` / `INSERT_BOTTOM_END`: Inserts at file end.
    - `REMOVE_BEGIN {{None}}` / `REMOVE_END`: Removes found text.
    - `CLEAR_FILE_BEGIN {{Root}}/Path` / `CLEAR_FILE_END`: Empties file content.
    - `CLEAR_AFTER_BEGIN {{None}}` / `CLEAR_AFTER_END`: Clears everything after found text.
    - `COMMENT_BEGIN {{None}}` / `COMMENT_END`: Metadata or logs.
- **Safety Rules**:
    - **Exactly One Match**: Operations using `FIND` (REPLACE, INSERT_AFTER, REMOVE, CLEAR_AFTER) MUST only apply if exactly one match is found in the target content.
    - **No Deletion**: Destructive operations (CLEAR_FILE, REMOVE) only modify content; they NEVER delete the file itself from the filesystem.
    - **Path Mapping**: Always use the `{{Root}}` marker at the start of paths within `FILE`, `PATCH`, and `CLEAR_FILE` blocks.
- **No Naked Directives in Logs**: Recovery logs and patch files should NOT contain a top-level `@ROOT` directive outside of a `COMMENT` block. Essential metadata must be placed inside `@@@COMMENT` blocks.

## 5. Mandatory Verification & Testing

To ensure 100% data integrity and prevent regressions in the core V2 processing logic, the following protocol is MANDATORY:

- **Test Runner**: The primary test entry point is `main_tester.py`. It automatically discovers and executes all test suites in the `TestCase/` folder.
- **Verification Protocol**: For every modification to `Scripts/Core/v2_parser.py` or `Scripts/Core/scaffold_core.py`, the developer (or AI) MUST run `python main_tester.py`.
- **Test Case Maintenance**:
    - **Update**: If logic changes intentionally, corresponding test cases in existing files (e.g., `TestCase/test_v2_v1_1.py`) must be updated.
    - **Add**: For significant new features or critical bug fixes, a NEW test file must be added (e.g., `TestCase/test_v2_new_feature.py`). NEVER delete existing test files.
    - **Documentation**: Every test case MUST include a docstring or comment explaining exactly **why** it is being tested and what behavior it validates.
- **Reporting Requirement**: Completion of a task involving V2 logic is NOT valid until the test results from `main_tester.py` (e.g., "ALL TESTS PASSED SUCCESSFULLY!") are explicitly reported to the user.
- **Literal Integrity Check**: Any test failure regarding "Literal" content or "Framing" (especially newline handling) must be treated as a critical blocker. The tool must never ship with logic that alters user content by even a single byte.

## 6. Operational Directives (AI & Developers)

### 5.1. AI Refactoring & Optimization Prohibition (CRITICAL)
- **Mandate**: NEVER attempt to "clean up," "refactor," or "optimize" existing logic based on AI-standard best practices.
- **Reasoning**: This application performs high-risk file operations (deletion/overwriting). The existing code contains numerous **empirical and exceptional cases** handled through trial and error. AI-driven "simplification" has historically resulted in a **100% failure rate**, breaking critical edge cases (e.g., source-only plans, indentation logic).
- **Aesthetics vs. Safety**: Functional correctness and data integrity are infinitely more important than "clean" or "idiomatic" code. Do not touch logic that is already working, even if it looks redundant or "ugly" by AI standards.
- **Performance**: High performance is NOT a priority. The operation complexity is low enough that safety-first, "slow" logic is preferred over optimized but fragile alternatives.
- **No Trust**: Do not trust your (AI) internal sense of "better" code. Adhere literally to existing patterns.

### 5.2. Preservation of Functionality
- **Preserve Existing Functionality**: DO NOT modify or refactor existing features unless it is strictly necessary to fulfill a specific requirement. Avoid "premature optimization" or stylistic "cleanup" of unrelated code blocks.
- **Minimal Intervention**: Always prefer the smallest possible change. Surgical updates are required to minimize the risk of regression.
- **Strict Scope**: Only implement what is explicitly requested. Do not add "just-in-case" features or expand the scope without instruction.
- **Bug Reporting & Feedback**: If a critical bug or logical flaw is discovered in the existing codebase, **report it immediately to the user and wait for feedback** before attempting a fix. Do not silently perform large-scale corrections that might break hidden dependencies.
- **Empirical Validation**: Any change to the core logic must be verified with a test script or manual walkthrough before completion.
