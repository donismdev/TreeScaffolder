# -*- coding: utf-8 -*-
"""
v2_parser.py

A parser for the V2 multipatch format.
The format consists of blocks, where each block starts with '@@@FILE_BEGIN <path>'
and ends with '@@@FILE_END'.
"""
import re

class V2ParserError(Exception):
    """Custom exception for parsing errors."""
    pass

def parse_v2_format(text: str, root_marker: str | None = None, root_marker_name: str | None = None) -> list[dict[str, str]]:
    """
    Parses a string in the V2 multipatch format, ignoring text outside blocks.

    Args:
        text: The string containing the patch data.
        root_marker: The placeholder for the root, e.g., '{{Root}}'.
        root_marker_name: The actual name to replace the root marker with (not used here, but for API consistency).

    Returns:
        A list of dictionaries, where each dictionary has 'path' and 'content' keys.
    """
    if not text.strip():
        return []

    # Regex to find all blocks. It's non-greedy and handles newlines.
    pattern = re.compile(r'@@@FILE_BEGIN\s+(.*?)\n(.*?)\s*@@@FILE_END', re.DOTALL)
    
    file_blocks = []
    
    for match in pattern.finditer(text):
        path = match.group(1).strip()
        content = match.group(2)

        if not path:
            # This is unlikely with the regex but good practice.
            continue

        # Replace the root marker if provided.
        if root_marker and path.startswith(root_marker):
            # We just remove the marker and the leading slash, the root path will be prepended later.
            path = path.replace(root_marker, '', 1).lstrip('/\\')

        file_blocks.append({'path': path, 'content': content})
    
    # Check for hanging FILE_BEGIN
    last_pos = 0
    if (match := list(pattern.finditer(text))):
        last_pos = match[-1].end()
    
    remaining_text = text[last_pos:]
    if '@@@FILE_BEGIN' in remaining_text and '@@@FILE_END' not in remaining_text:
        raise V2ParserError("A FILE_BEGIN block was found without a matching FILE_END at the end of the text.")

    return file_blocks

if __name__ == '__main__':
    # Example usage and testing
    test_text_mixed = r"""
# Some scaffold tree text here
@ROOT {{Root}}

{{Root}}/
    some_dir/
        some_file.txt

 @@@FILE_BEGIN {{Root}}/MercenaryMode/MercenaryMode.Build.cs
Test content 1
 @@@FILE_END
 
Some other text to be ignored.

 @@@FILE_BEGIN MercenaryMode/Public/MercenaryModeCore.h
Test content 2
 @@@FILE_END
"""
    print("--- Testing mixed format with root marker ---")
    try:
        parsed = parse_v2_format(test_text_mixed, root_marker="{{Root}}")
        assert len(parsed) == 2
        assert parsed[0]['path'] == 'MercenaryMode/MercenaryMode.Build.cs'
        assert parsed[0]['content'] == 'Test content 1'
        assert parsed[1]['path'] == 'MercenaryMode/Public/MercenaryModeCore.h' # No marker to replace
        assert parsed[1]['content'] == 'Test content 2'
        print("OK")
    except V2ParserError as e:
        print(f"FAILED: {e}")

    test_text_fail_no_end = r"""
 @@@FILE_BEGIN path/to/file.txt
Some content here.
"""
    print("\n--- Testing missing FILE_END ---")
    try:
        parse_v2_format(test_text_fail_no_end)
        print("OK (no error, just ignores the block)")
    except V2ParserError as e:
        print(f"FAILED: {e}") # Should not fail with the new logic, but we added a check for hanging blocks.
        
    # Test for the hanging block at the very end
    test_text_fail_hanging = r"""
    @@@FILE_BEGIN good/path.txt
    Content
    @@@FILE_END
    @@@FILE_BEGIN bad/path.txt
    Hanging content
    """
    print("\n--- Testing hanging FILE_END ---")
    try:
        parse_v2_format(test_text_fail_hanging)
        print("FAILED: Expected an error.")
    except V2ParserError as e:
        print(f"OK, caught expected error: {e}")