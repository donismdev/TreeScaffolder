"""
v2_parser.py

A parser for the V2 multipatch format.
The format consists of blocks, where each block starts with '@@@<KEYWORD>_BEGIN <path>'
and ends with '@@@<KEYWORD>_END'. This version validates block structure first
and ignores content outside of recognized blocks.
"""
import re

class V2ParserError(Exception):
    """Custom exception for parsing errors."""
    pass

RECOGNIZED_BLOCK_TYPES = {
    "FILE": True,  # True means content should be processed and added to output
    "COMMENT": False, # False means content should be ignored in output
}

def _validate_block_structure(text: str):
    """
    Validates the block structure for all keyword types using a stack.
    Checks for nested blocks, mismatched tags, and unclosed blocks.
    """
    # This pattern finds all BEGIN/END tags for any keyword.
    markers = re.finditer(r"@@@(?P<keyword>[A-Z_]+)_(?P<tag_type>BEGIN|END)", text)
    stack = []
    for match in markers:
        keyword = match.group("keyword")
        tag_type = match.group("tag_type")
        line_num = text.count('\n', 0, match.start()) + 1

        if tag_type == "BEGIN":
            # Enforce a simple no-nesting rule for all block types.
            if stack:
                prev_keyword, prev_line_num = stack[-1]
                raise V2ParserError(
                    f"Parsing Error: Nested block detected. "
                    f"Block '{keyword}' at line {line_num} began before "
                    f"block '{prev_keyword}' from line {prev_line_num} was closed."
                )
            stack.append((keyword, line_num))
        elif tag_type == "END":
            if not stack:
                raise V2ParserError(f"Parsing Error: Unexpected '@@@{keyword}_END' at line {line_num} with no open block.")
            
            prev_keyword, _ = stack.pop()
            if prev_keyword != keyword:
                raise V2ParserError(
                    f"Parsing Error: Mismatched block tags. "
                    f"Expected '@@@{prev_keyword}_END' but found '@@@{keyword}_END' at line {line_num}."
                )
    if stack:
        keyword, line_num = stack[0]
        raise V2ParserError(f"Parsing Error: Block '{keyword}' began at line {line_num} but was never closed.")


def parse_v2_format(text: str, root_marker: str | None = None, root_marker_name: str | None = None) -> list[dict[str, str]]:
    """
    Parses a string in a generalized V2 multipatch format, ignoring text outside recognized blocks.
    """
    if not text.strip():
        return []

    # 1. High-priority validation of the entire block structure.
    _validate_block_structure(text)

    # 2. If validation passes, proceed with extracting content.
    file_blocks = []
    
    block_pattern = re.compile(
        r"@@@(?P<keyword>[A-Z_]+)_BEGIN(?P<header>.*?)\n"
        r"(?P<content>.*?)"
        r"@@@(?P=keyword)_END",
        re.DOTALL
    )

    for match in block_pattern.finditer(text):
        keyword = match.group('keyword')
        
        # Only process blocks that are recognized for output.
        if not RECOGNIZED_BLOCK_TYPES.get(keyword, False):
            continue
        
        header = match.group('header').strip()
        content_raw = match.group('content')
        
        path = None
        content = None

        if keyword == "FILE":
            if header: # Path is on the same line as BEGIN
                path = header
                content = content_raw
            else: # Path is the first line of the content
                try:
                    path, content = content_raw.split('\n', 1)
                    path = path.strip()
                except ValueError: # Content has no newline, so it's all path and empty content
                    path = content_raw.strip()
                    content = ""
            
            if not path:
                line_num = text.count('\n', 0, match.start()) + 1
                raise V2ParserError(f"FILE_BEGIN block at line {line_num} has no path defined.")

            # Apply root marker replacement
            if root_marker and path.startswith(root_marker):
                path = path.replace(root_marker, '', 1).lstrip('/\\')
            
            file_blocks.append({'path': path, 'content': content})

    return file_blocks
