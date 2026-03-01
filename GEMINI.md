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

## 4. V2 Multipatch Format (@@@ Blocks)

All source code definitions and recovery logs must strictly follow the **V2 Multipatch Format**. This format ensures data integrity and prevents parsing ambiguities.

- **Mandatory Paired Tags**: Every block MUST start with `@@@<KEYWORD>_BEGIN` and end with `@@@<KEYWORD>_END`. Unpaired tags or nested blocks are strictly forbidden.
- **Recognized Keywords**:
    - `FILE`: Used for defining file content. The path (including the `{{Root}}` marker) should follow the BEGIN tag.
    - `COMMENT`: Used for metadata, logs, or instructions. This content is ignored during the scaffold application phase.
- **Path Mapping**: Always use the `{{Root}}` marker at the start of paths within `FILE` blocks (e.g., `@@@FILE_BEGIN {{Root}}/path/to/file.txt`).
- **No Naked Directives in Logs**: Recovery logs and patch files should NOT contain a top-level `@ROOT` directive outside of a `COMMENT` block, as this can confuse the tree parser. Essential metadata (like the target absolute path) must be placed inside `@@@COMMENT` blocks.

## 5. Operational Directives (AI & Developers)

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
