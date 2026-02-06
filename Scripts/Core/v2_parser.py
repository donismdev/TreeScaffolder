"""
v2_parser.py

A parser for the V2 multipatch format.
The format consists of blocks, where each block starts with '@@@FILE_BEGIN <path>'
and ends with '@@@FILE_END'.
This version extends support to other block types like COMMENT_BEGIN/COMMENT_END,
and ignores content outside or within unrecognized blocks.
"""
import re

from collections import deque

class V2ParserError(Exception):
    """Custom exception for parsing errors."""
    pass

# Define recognized block types. 'FILE' blocks produce output. 'COMMENT' blocks are recognized but ignored in output.
RECOGNIZED_BLOCK_TYPES = {
    "FILE": True,  # True means content should be processed and added to output
    "COMMENT": False, # False means content should be ignored in output
}

def parse_v2_format(text: str, root_marker: str | None = None, root_marker_name: str | None = None) -> list[dict[str, str]]:
    """
    Parses a string in a generalized V2 multipatch format, ignoring text outside recognized blocks.

    Args:
        text: The string containing the patch data.
        root_marker: The placeholder for the root, e.g., '{{Root}}'.
        root_marker_name: The actual name to replace the root marker with (not used here, but for API consistency).

    Returns:
        A list of dictionaries, where each dictionary has 'path' and 'content' keys
        for recognized block types (currently only 'FILE').
    """
    if not text.strip():
        return []

    file_blocks = []
    
    # Regex to find any BEGIN or END tag: @@@<KEYWORD>_BEGIN or @@@<KEYWORD>_END
    # Captures the KEYWORD, whether it's BEGIN or END, and any text after BEGIN on the same line.
    block_tag_pattern = re.compile(
        r"@@@(?P<keyword>[A-Z_]+)_(?P<tag_type>BEGIN|END)" # Base tag match
        r"(?:(?<=BEGIN)\s+(?P<identifier_begin>.*))?"     # Optional: if tag_type is BEGIN, capture rest of line as identifier
    )

    # Find all tags in the text
    all_tags = []
    for match in block_tag_pattern.finditer(text):
        identifier = ""
        if match.group("tag_type") == "BEGIN" and match.group("identifier_begin"):
            identifier = match.group("identifier_begin")
        
        all_tags.append({
            "keyword": match.group("keyword"),
            "type": match.group("tag_type"),
            "identifier_on_line": identifier,
            "start": match.start(),
            "end": match.end(),
            "line_num": text.count('\n', 0, match.start()) + 1
        })

    
    current_block = {
        "active": False,
        "keyword": None,
        "content_start_index": None,
        "path_on_begin_line": None,
        "is_output_block": False,
        "begin_line_num": None
    }

    for tag in all_tags:

        if tag["type"] == "BEGIN":
            # If an output-producing block is active, and we find another BEGIN, it's an error.
            if current_block["active"] and current_block["is_output_block"]:
                raise V2ParserError(
                    f"Nested or unclosed block detected. "
                    f"Block '{current_block['keyword']}' at line {current_block['begin_line_num']} "
                    f"was not closed before new block '{tag['keyword']}' at line {tag['line_num']} began."
                )
            
            # If an ignored block is active, and a new BEGIN starts, we simply treat it as a new block,
            # effectively ending the previous ignored block without an explicit END.
            if current_block["active"] and not current_block["is_output_block"]:

                current_block = {
                    "active": False, "keyword": None, "content_start_index": None,
                    "path_on_begin_line": None, "is_output_block": False, "begin_line_num": None
                }
            
            # Start a new block
            current_block["active"] = True
            current_block["keyword"] = tag["keyword"]
            current_block["is_output_block"] = RECOGNIZED_BLOCK_TYPES.get(tag["keyword"], False)
            current_block["begin_line_num"] = tag["line_num"]
            
            # For 'FILE' blocks, the path can be on the same line as BEGIN.
            # For other block types, 'identifier_on_line' is just extra text on the BEGIN line.
            if tag["keyword"] == "FILE" and tag["identifier_on_line"]:
                current_block["path_on_begin_line"] = tag["identifier_on_line"].strip()
            else:
                current_block["path_on_begin_line"] = None # Explicitly set to None for non-FILE blocks or if no path on line

            # Content starts after the BEGIN tag and its newline
            newline_after_begin = text.find('\n', tag["end"])
            if newline_after_begin == -1: # No newline, block might extend to EOF
                current_block["content_start_index"] = tag["end"]
            else:
                current_block["content_start_index"] = newline_after_begin + 1


        elif tag["type"] == "END":

            # If no block is active, or if the keyword doesn't match, ignore this END tag.
            if not current_block["active"] or tag["keyword"] != current_block["keyword"]:

                continue

            # Matching END tag found. Process the content if it's an output-producing block.
            if current_block["is_output_block"]:
                content_raw = text[current_block["content_start_index"]:tag["start"]]


                path = None
                content = None
                
                if current_block["keyword"] == "FILE":
                    if current_block["path_on_begin_line"]:
                        path = current_block["path_on_begin_line"]
                        content = content_raw

                    else:
                        # Path is the first line of the content_raw
                        content_lines = content_raw.split('\n', 1)
                        if content_lines:
                            path = content_lines[0].strip()
                            if len(content_lines) > 1:
                                content = content_lines[1]
                            else:
                                content = "" # Empty file
                        else:
                            path = ""
                            content = ""


                    
                    if not path:
                        raise V2ParserError(f"FILE_BEGIN block at line {current_block['begin_line_num']} has no path defined.")
                    


                    # Apply root marker replacement
                    if root_marker and path.startswith(root_marker):
                        path = path.replace(root_marker, '', 1).lstrip('/\\')
                    
                    file_blocks.append({'path': path, 'content': content})


            
            # Reset current block state

            current_block = {
                "active": False, "keyword": None, "content_start_index": None,
                "path_on_begin_line": None, "is_output_block": False, "begin_line_num": None
            }

    # After iterating through all tags, check for any unclosed output-producing blocks
    if current_block["active"] and current_block["is_output_block"]:
        raise V2ParserError(
            f"Block '{current_block['keyword']}' began at line {current_block['begin_line_num']} but was never closed."
        )

    return file_blocks

if __name__ == '__main__':
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

 @@@COMMENT_BEGIN This is a comment block
This content should be ignored in the output.
It can span multiple lines.
 @@@COMMENT_END

Another line to ignore.

 @@@FILE_BEGIN MercenaryMode/Public/MercenaryModeCore.h
path-on-next-line-test
Test content 2
 @@@FILE_END

@@@FILE_BEGIN path/on/same/line.txt This is the path
Test content 3
 @@@FILE_END

@@@UNKNOWN_BEGIN some_identifier
This is an unknown block type.
Its content should also be ignored.
@@@UNKNOWN_END

Final ignored text.
"""
    print("--- Testing mixed format with root marker and new block types ---")
    try:
        parsed = parse_v2_format(test_text_mixed, root_marker="{{Root}}")
        assert len(parsed) == 3
        assert parsed[0]['path'] == 'MercenaryMode/MercenaryMode.Build.cs'
        assert parsed[0]['content'] == 'Test content 1\n '
        assert parsed[1]['path'] == 'MercenaryMode/Public/MercenaryModeCore.h'
        assert parsed[1]['content'] == 'path-on-next-line-test\nTest content 2\n '
        assert parsed[2]['path'] == 'path/on/same/line.txt This is the path'
        assert parsed[2]['content'] == 'Test content 3\n '
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
        print("FAILED: Expected an error for unclosed FILE block.")
    except V2ParserError as e:
        print(f"OK, caught expected error: {e}")
        
    test_text_fail_hanging_output_block = r"""
    @@@FILE_BEGIN good/path.txt
    Content
    @@@FILE_END
    @@@FILE_BEGIN bad/path.txt
    Hanging content
    """
    print("\n--- Testing hanging FILE_BEGIN (output block) ---")
    try:
        parse_v2_format(test_text_fail_hanging_output_block)
        print("FAILED: Expected an error for unclosed FILE block.")
    except V2ParserError as e:
        print(f"OK, caught expected error: {e}")

    test_text_unclosed_comment = r"""
    @@@FILE_BEGIN file.txt
    file content
    @@@FILE_END
    @@@COMMENT_BEGIN
    unclosed comment
    """
    print("\n--- Testing unclosed COMMENT_BEGIN (ignored block) ---")
    try:
        parsed = parse_v2_format(test_text_unclosed_comment)
        assert len(parsed) == 1
        assert parsed[0]['path'] == 'file.txt'
        print("OK (no error, comment block ignored)")
    except V2ParserError as e:
        print(f"FAILED: {e}")

    test_text_mismatched_end = r"""
    @@@FILE_BEGIN file.txt
    file content
    @@@COMMENT_END
    """
    print("\n--- Testing mismatched END tag ---")
    try:
        parse_v2_format(test_text_mismatched_end)
        print("FAILED: Expected an error for unclosed FILE block.")
    except V2ParserError as e:
        print(f"OK, caught expected error: {e}")

    test_text_unrecognized_block_unclosed = r"""
    @@@FILE_BEGIN file.txt
    file content
    @@@FILE_END
    @@@SOME_OTHER_BEGIN
    some other content
    """
    print("\n--- Testing unrecognized unclosed block ---")
    try:
        parsed = parse_v2_format(test_text_unrecognized_block_unclosed)
        assert len(parsed) == 1
        assert parsed[0]['path'] == 'file.txt'
        print("OK (no error, unrecognized block ignored)")
    except V2ParserError as e:
        print(f"FAILED: {e}")