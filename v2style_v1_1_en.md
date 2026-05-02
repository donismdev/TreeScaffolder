# Text Patch Format Manual v1.1

## 0. Purpose

This format is a patch format for safely modifying text files.

This format does not understand concepts such as C++, Unreal, includes, functions, classes, or enums.

Its target is only text files.

Therefore, it only handles the following operations.

```text
1. Overwrite the entire contents of a file
2. Replace specific text inside a file
3. Insert text after specific text inside a file
4. Insert text at the top of a file
5. Insert text at the bottom of a file
6. Remove specific text
7. Clear the entire contents of a file
8. Clear all contents after a specific line
```

Important restrictions:

```text
A file deletion feature must never be provided.
No keyword for deleting a file itself must be created.
No file move feature must be created.
No directory deletion feature must be created.
```

---

# 1. Basic Form

Every keyword must have a BEGIN / END pair.

Form:

```text
@@@KEYWORD_BEGIN {{Parameter}}
content
@@@KEYWORD_END
```

Example:

```text
@@@FIND_BEGIN {{None}}
PendingInteractionRequest.Reset();
@@@FIND_END
```

Single-line keywords are forbidden.

Forbidden:

```text
@@@FIND
@@@REPLACE
@@@PATCH_END used alone
@@@DELETE_FILE
```

Allowed:

```text
@@@FIND_BEGIN {{None}}
text to find
@@@FIND_END
```

---

# 2. Parameter Rules

The `{{...}}` area is called the Parameter.

Example:

```text
@@@PATCH_BEGIN {{Root}}/Source/ModeMercenary/Public/Runtime/MercenaryGameSessionRuntime.h
```

Here, `{{Root}}/Source/ModeMercenary/Public/Runtime/MercenaryGameSessionRuntime.h` is the Parameter.

## 2.1 A Parameter Must Always Exist

Every BEGIN keyword must have a Parameter.

If no Parameter is needed, the following must be used:

```text
{{None}}
```

Example:

```text
@@@FIND_BEGIN {{None}}
text to find
@@@FIND_END
```

## 2.2 File Path Parameters

Keywords that require a file path must use paths based on `{{Root}}`.

Example:

```text
@@@FILE_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp
```

Forbidden:

```text
C:/Users/...
Source/Example/..
../Source/Example/..
../Source/Example/...
```

## 2.3 Meaningless Concept-Name Parameters Are Forbidden

Concept names such as the following must not be used.

```text
{{IncludeSection}}
{{PublicFunctionSection}}
{{DelegateSection}}
{{PrivateArea}}
{{TargetFunction}}
{{SomeBlock}}
```

Reason:

```text
The tool does not understand C++ structure.
The tool does not know concepts such as include, public, delegate, or function.
The actual reference point is only the text inside FIND.
Concept-name Parameters can easily become decorative labels invented by AI.
```

Therefore, if the Parameter is not a file path, almost always use:

```text
{{None}}
```

---

# 3. Supported Keyword List

Only the following keywords are supported.

```text
@@@FILE_BEGIN {{Root}}/Path
@@@FILE_END

@@@PATCH_BEGIN {{Root}}/Path
@@@PATCH_END

@@@FIND_BEGIN {{None}}
@@@FIND_END

@@@REPLACE_BEGIN {{None}}
@@@REPLACE_END

@@@INSERT_AFTER_BEGIN {{None}}
@@@INSERT_AFTER_END

@@@INSERT_TOP_BEGIN {{None}}
@@@INSERT_TOP_END

@@@INSERT_BOTTOM_BEGIN {{None}}
@@@INSERT_BOTTOM_END

@@@REMOVE_BEGIN {{None}}
@@@REMOVE_END

@@@CLEAR_FILE_BEGIN {{Root}}/Path
@@@CLEAR_FILE_END

@@@CLEAR_AFTER_BEGIN {{None}}
@@@CLEAR_AFTER_END

@@@COMMENT_BEGIN {{None}}
@@@COMMENT_END
```

Unsupported keywords:

```text
@@@DELETE_FILE_BEGIN
@@@DELETE_FILE_END

@@@MOVE_FILE_BEGIN
@@@MOVE_FILE_END

@@@DELETE_DIRECTORY_BEGIN
@@@DELETE_DIRECTORY_END

@@@INCLUDE_ADD_BEGIN
@@@ADD_FUNCTION_BEGIN
@@@REPLACE_STRUCT_BEGIN
@@@REPLACE_CLASS_BEGIN
```

This format is a file/text modification format, not a C++ structure modification format.

---

# 4. No File Deletion Principle

A file deletion feature must never be added.

Forbidden keywords:

```text
@@@DELETE_FILE_BEGIN
@@@DELETE_FILE_END

@@@MOVE_FILE_BEGIN
@@@MOVE_FILE_END

@@@DELETE_DIRECTORY_BEGIN
@@@DELETE_DIRECTORY_END
```

Reason for prohibition:

```text
If a Parameter is interpreted incorrectly, the wrong file may be deleted.
If path calculation fails, files in completely unintended areas may be deleted.
If an automation tool makes a mistake, the recovery cost is too high.
A patch format must be safe, so destructive operations are not provided.
```

Even when a file should be removed, the actual file must not be deleted.

The only possible alternatives are:

```text
1. Make the file contents empty.
2. Remove part of the file contents.
3. Overwrite the file contents with new contents.
4. Let the user delete the file manually.
```

In other words, the tool must not delete the file itself from the file system.

---

# 5. FILE

Overwrites the entire contents of a file.

Form:

```text
@@@FILE_BEGIN {{Root}}/Path/File.h
entire file contents
@@@FILE_END
```

Meaning:

```text
Replaces the contents of the target file with the full contents inside the block.
```

Rules:

```text
Do not provide only part of the file.
FILE always means overwriting the entire file.
Place exactly one blank line immediately above @@@FILE_END.
Place two blank lines between files.
```

Caution:

```text
FILE is a powerful overwrite operation.
The tool should provide a backup or change preview before applying it.
The tool must verify that the path is inside {{Root}}.
```

---

# 6. PATCH

Modifies part of a file.

Form:

```text
@@@PATCH_BEGIN {{Root}}/Path/File.h
patch contents
@@@PATCH_END
```

Keywords available inside PATCH:

```text
@@@FIND_BEGIN / @@@FIND_END
@@@REPLACE_BEGIN / @@@REPLACE_END
@@@INSERT_AFTER_BEGIN / @@@INSERT_AFTER_END
@@@INSERT_TOP_BEGIN / @@@INSERT_TOP_END
@@@INSERT_BOTTOM_BEGIN / @@@INSERT_BOTTOM_END
@@@REMOVE_BEGIN / @@@REMOVE_END
@@@CLEAR_AFTER_BEGIN / @@@CLEAR_AFTER_END
@@@COMMENT_BEGIN / @@@COMMENT_END
```

PATCH does not delete files.  
PATCH only modifies file contents.

---

# 7. FIND

Finds the text that acts as the reference point for a modification.

Form:

```text
@@@FIND_BEGIN {{None}}
text to find
@@@FIND_END
```

Example:

```text
@@@FIND_BEGIN {{None}}
PendingInteractionRequest.Reset();
@@@FIND_END
```

FIND is usually followed by one of the following:

```text
REPLACE
INSERT_AFTER
REMOVE
CLEAR_AFTER
```

Caution:

```text
FIND is text-based.
The tool does not parse C++ syntax.
If the same FIND text appears multiple times, it is dangerous.
The default application policy is: "success only when exactly one match is found."
```

---

# 8. REPLACE

Replaces the text found by the previous FIND with new text.

Form:

```text
@@@FIND_BEGIN {{None}}
old text
@@@FIND_END
@@@REPLACE_BEGIN {{None}}
new text
@@@REPLACE_END
```

Example:

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp
@@@FIND_BEGIN {{None}}
PendingInteractionRequest.Reset();
@@@FIND_END
@@@REPLACE_BEGIN {{None}}
PendingInteractionRequest.Reset();
PendingReturnOpportunity = FMercenaryReturnOpportunity();
@@@REPLACE_END
@@@PATCH_END
```

Application meaning:

```text
Finds the old text and replaces it with the new text.
```

---

# 9. INSERT_AFTER

Inserts new text immediately after the text found by the previous FIND.

Form:

```text
@@@FIND_BEGIN {{None}}
reference text
@@@FIND_END
@@@INSERT_AFTER_BEGIN {{None}}
text to add
@@@INSERT_AFTER_END
```

Example:

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h
@@@FIND_BEGIN {{None}}
int32 Value = 0;
@@@FIND_END
@@@INSERT_AFTER_BEGIN {{None}}
int32 NextValue = 0;
@@@INSERT_AFTER_END
@@@PATCH_END
```

Application meaning:

```text
Finds the reference text and inserts the additional text immediately after it.
```

INSERT_BEFORE is not created.

Reason:

```text
To reduce the number of features.
Most cases can be solved by choosing an earlier reference text and using INSERT_AFTER.
The more keywords there are, the more unstable the format becomes.
```

---

# 10. INSERT_TOP

Inserts text at the very top of a file.

Form:

```text
@@@PATCH_BEGIN {{Root}}/Path/File.h
@@@INSERT_TOP_BEGIN {{None}}
text to add
@@@INSERT_TOP_END
@@@PATCH_END
```

Meaning:

```text
Adds text to the very beginning of the file.
```

Caution:

```text
The tool does not understand C++ syntax.
Even if the text is inserted above #pragma once, the tool does not judge that.
The tool inserts exactly what the user provided at the top of the file.
```

---

# 11. INSERT_BOTTOM

Inserts text at the very bottom of a file.

Form:

```text
@@@PATCH_BEGIN {{Root}}/Path/File.cpp
@@@INSERT_BOTTOM_BEGIN {{None}}
text to add
@@@INSERT_BOTTOM_END
@@@PATCH_END
```

Meaning:

```text
Adds text to the very end of the file.
```

Caution:

```text
The tool should normalize the final newline safely.
Even if the existing file has no newline at the end, the resulting file should end with a newline.
```

---

# 12. REMOVE

Removes the text found by the previous FIND.

Form:

```text
@@@FIND_BEGIN {{None}}
text to remove
@@@FIND_END
@@@REMOVE_BEGIN {{None}}
@@@REMOVE_END
```

Example:

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp
@@@FIND_BEGIN {{None}}
DebugOnlyFunction();
@@@FIND_END
@@@REMOVE_BEGIN {{None}}
@@@REMOVE_END
@@@PATCH_END
```

Meaning:

```text
Removes the text found by FIND from the file contents.
```

Rules:

```text
The REMOVE body is left empty.
The removal target is the content of the previous FIND.
Apply only when exactly one match is found.
```

---

# 13. CLEAR_FILE

Clears the entire contents of a file.

Form:

```text
@@@CLEAR_FILE_BEGIN {{Root}}/Path/File.h
@@@CLEAR_FILE_END
```

Meaning:

```text
Keeps the file itself, but deletes all contents inside it.
The result is an empty file.
```

Important:

```text
CLEAR_FILE is not file deletion.
The file must remain in the file system.
Only its contents become empty.
```

Safety rules:

```text
The tool must warn before applying CLEAR_FILE.
The tool must verify that the target path is inside {{Root}}.
The tool must verify that the target is a file.
The tool must never apply this to a directory.
The tool should create a backup before applying it whenever possible.
The tool should provide a change preview before applying it.
```

Recommended double-check or triple-check:

```text
First check: Is the path inside {{Root}}?
Second check: Is the target an actual file?
Third check: Did the user explicitly specify CLEAR_FILE?
```

---

# 14. CLEAR_AFTER

`CLEAR_AFTER` searches from the top of the file downward, finds the first occurrence of the text specified by `FIND`, and clears everything below it.

Form:

```text
@@@PATCH_BEGIN {{Root}}/Path/File.h
@@@FIND_BEGIN {{None}}
reference text
@@@FIND_END
@@@CLEAR_AFTER_BEGIN {{None}}
@@@CLEAR_AFTER_END
@@@PATCH_END
```

Meaning:

```text
Searches for the FIND text from the top of the file.
The first found FIND text remains in the result.
The line containing the first found FIND text also remains in the result.
All content below that line is deleted.
```

Example:

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h
@@@FIND_BEGIN {{None}}
#include "CoreMinimal.h"
@@@FIND_END
@@@CLEAR_AFTER_BEGIN {{None}}
@@@CLEAR_AFTER_END
@@@PATCH_END
```

Before applying:

```cpp
#pragma once
#include "CoreMinimal.h"
#include "SomethingElse.h"

struct FExample{};
```

After applying:

```cpp
#pragma once
#include "CoreMinimal.h"
```

Rules:

```text
The CLEAR_AFTER body is left empty.
The FIND text remains in the result.
The line containing the FIND text also remains in the result.
Only the first match found when searching from the top of the file is used.
Only the content below the first matching line is removed.
Even if the FIND text appears multiple times, only the first match is used as the reference point.
If the FIND text is not found, the operation is not applied and is treated as a failure.
```

Safety rules:

```text
The tool must warn before applying CLEAR_AFTER.
The tool must fail if the FIND text is not found.
The tool should show a preview of the first matching position and the number of lines to be deleted.
The tool should notify the user that the result may become much shorter than intended.
The tool should create a backup before applying it whenever possible.
```

---

# 15. COMMENT

A memo for the patch applier.

Form:

```text
@@@COMMENT_BEGIN {{None}}
memo content
@@@COMMENT_END
```

Meaning:

```text
COMMENT is not an actual file modification.
The tool does not apply COMMENT.
The tool may only display COMMENT in logs or preview descriptions.
```

Do not put long explanations in the Parameter.  
Put long explanations in the COMMENT body.

---

# 16. Safety Rules

## 16.1 Absolutely Forbidden

The tool must never perform the following operations.

```text
File deletion
Directory deletion
File move
Directory move
Modification outside {{Root}}
Wildcard path modification
Relative path escape modification
```

Forbidden examples:

```text
../
..\
{{Root}}/../
*
?
C:/Users/...
/Users/...
/home/...
```

## 16.2 Path Safety Checks

Only the following keywords receive file paths.

```text
@@@FILE_BEGIN {{Root}}/Path
@@@PATCH_BEGIN {{Root}}/Path
@@@CLEAR_FILE_BEGIN {{Root}}/Path
```

Every file path must satisfy the following conditions.

```text
It must start with {{Root}}.
It must not be able to escape outside {{Root}}.
It must not contain relative path escape.
It must not contain wildcards.
It must be a file, not a directory.
```

## 16.3 Matching Safety Checks

Operations that use FIND must, by default, match exactly once.

Target operations:

```text
REPLACE
INSERT_AFTER
REMOVE
CLEAR_AFTER
```

Match result:

```text
0 matches: failure
1 match: can be applied
2 or more matches: failure
```

Reason:

```text
When identical text appears in multiple places, the wrong location may be modified.
```

## 16.4 Safety Checks for Destructive Content Changes

The following operations have a high risk of content loss, so they require separate safety checks.

```text
FILE
CLEAR_FILE
CLEAR_AFTER
REMOVE
```

Recommended safety checks:

```text
1. Verify that the path is inside {{Root}}.
2. Verify that the target is a file.
3. Generate a change preview before applying.
4. Create a backup of the existing file.
5. Verify that the user explicitly specified the operation.
6. Show a separate warning for CLEAR_FILE / CLEAR_AFTER.
```

---

# 17. Output Examples

## 17.1 Overwrite an Entire File

```text
@@@FILE_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h
#pragma once

#include "CoreMinimal.h"

struct FExampleTypes final
{
	int32 Value = 0;

	bool IsValid() const
	{
		return Value > 0;
	}
};

@@@FILE_END
```

## 17.2 Replace Text

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp
@@@FIND_BEGIN {{None}}
Value = 1;
@@@FIND_END
@@@REPLACE_BEGIN {{None}}
Value = 2;
@@@REPLACE_END
@@@PATCH_END
```

## 17.3 Insert After Text

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp
@@@FIND_BEGIN {{None}}
Initialize();
@@@FIND_END
@@@INSERT_AFTER_BEGIN {{None}}
Refresh();
@@@INSERT_AFTER_END
@@@PATCH_END
```

## 17.4 Insert at the Top of a File

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp
@@@INSERT_TOP_BEGIN {{None}}
// Generated by patch tool
@@@INSERT_TOP_END
@@@PATCH_END
```

## 17.5 Insert at the Bottom of a File

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp
@@@INSERT_BOTTOM_BEGIN {{None}}
void DebugExample(){}
@@@INSERT_BOTTOM_END
@@@PATCH_END
```

## 17.6 Remove Text

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Private/Example.cpp
@@@FIND_BEGIN {{None}}
DebugOnlyFunction();
@@@FIND_END
@@@REMOVE_BEGIN {{None}}
@@@REMOVE_END
@@@PATCH_END
```

## 17.7 Clear the Entire Contents of a File

```text
@@@CLEAR_FILE_BEGIN {{Root}}/Source/Example/Private/OldStub.cpp
@@@CLEAR_FILE_END
```

## 17.8 Clear Everything After Specific Text

```text
@@@PATCH_BEGIN {{Root}}/Source/Example/Public/ExampleTypes.h
@@@FIND_BEGIN {{None}}
#include "CoreMinimal.h"
@@@FIND_END
@@@CLEAR_AFTER_BEGIN {{None}}
@@@CLEAR_AFTER_END
@@@PATCH_END
```

---

# 18. Final Fixed Summary

Use only the following final keywords.

```text
@@@FILE_BEGIN {{Root}}/Path
@@@FILE_END

@@@PATCH_BEGIN {{Root}}/Path
@@@PATCH_END

@@@FIND_BEGIN {{None}}
@@@FIND_END

@@@REPLACE_BEGIN {{None}}
@@@REPLACE_END

@@@INSERT_AFTER_BEGIN {{None}}
@@@INSERT_AFTER_END

@@@INSERT_TOP_BEGIN {{None}}
@@@INSERT_TOP_END

@@@INSERT_BOTTOM_BEGIN {{None}}
@@@INSERT_BOTTOM_END

@@@REMOVE_BEGIN {{None}}
@@@REMOVE_END

@@@CLEAR_FILE_BEGIN {{Root}}/Path
@@@CLEAR_FILE_END

@@@CLEAR_AFTER_BEGIN {{None}}
@@@CLEAR_AFTER_END

@@@COMMENT_BEGIN {{None}}
@@@COMMENT_END
```

Keywords that must never be created:

```text
@@@DELETE_FILE_BEGIN
@@@DELETE_FILE_END

@@@MOVE_FILE_BEGIN
@@@MOVE_FILE_END

@@@DELETE_DIRECTORY_BEGIN
@@@DELETE_DIRECTORY_END
```

Core principles:

```text
This format is a text modification format.
It does not understand C++ structure.
There is absolutely no file deletion feature.
Even when a file needs to be removed, only the file contents are cleared.
File paths must always be based on {{Root}}.
Parameters that are not file paths are almost always {{None}}.
FIND-based operations are applied only when exactly one match is found.
CLEAR_FILE and CLEAR_AFTER are treated as dangerous operations and require double-checks or triple-checks.
To prevent accidental deletion, the tool must never include a file deletion feature.
```
