"""
v2_parser.py

A parser for the V2 multipatch format (v1.1).
The format consists of blocks, where each block starts with '@@@<KEYWORD>_BEGIN {{Parameter}}'
and ends with '@@@<KEYWORD>_END'.
"""
import re
from typing import List, Dict, Any, Optional

class V2ParserError(Exception):
    """Custom exception for parsing errors."""
    pass

RECOGNIZED_KEYWORDS = {
    "FILE", "PATCH", "FIND", "REPLACE", "INSERT_AFTER", "INSERT_TOP", 
    "INSERT_BOTTOM", "REMOVE", "CLEAR_FILE", "CLEAR_AFTER", "COMMENT"
}

# Keywords that can contain other blocks (currently only PATCH)
CONTAINER_KEYWORDS = {"PATCH"}

def _get_parameter(header: Optional[str]) -> str:
    """Extracts the parameter from the header line."""
    if not header:
        return ""
    return header.strip()

def parse_v2_format(text: str) -> List[Dict[str, Any]]:
    """
    Parses a string in the V2 multipatch format v1.1.
    Returns a list of top-level blocks.
    """
    if not text.strip():
        return []

    # Normalize line endings to \n
    text = text.replace('\r\n', '\n')

    # Tokenize the text into markers and content
    # We look for @@@KEYWORD_BEGIN {{Parameter}} and @@@KEYWORD_END
    # The marker must be followed by a newline or the end of the string.
    marker_pattern = re.compile(r"@@@(?P<keyword>[A-Z_]+)_(?P<tag_type>BEGIN|END)(?: (?P<header>.*?))?(?:\n|$)")
    
    tokens = []
    last_pos = 0
    for match in marker_pattern.finditer(text):
        # Content before the marker
        content = text[last_pos:match.start()]
        if content:
            tokens.append(('CONTENT', content))
        
        keyword = match.group("keyword")
        tag_type = match.group("tag_type")
        header = match.group("header")
        
        if keyword not in RECOGNIZED_KEYWORDS:
            # If not a recognized keyword, treat it as normal content?
            # For strictness, we might want to error, but for now let's be flexible
            # unless it looks exactly like our format.
            tokens.append(('CONTENT', match.group(0)))
        else:
            tokens.append(('MARKER', {
                'keyword': keyword,
                'tag_type': tag_type,
                'parameter': _get_parameter(header) if tag_type == "BEGIN" else None,
                'line_num': text.count('\n', 0, match.start()) + 1
            }))
        
        last_pos = match.end()
    
    # Remaining content
    content = text[last_pos:]
    if content:
        tokens.append(('CONTENT', content))

    # Build the block tree
    blocks = []
    stack = [] # Stores (block_dict, start_line_num)

    for t_type, t_value in tokens:
        if t_type == 'CONTENT':
            if stack:
                stack[-1][0]['content'] += t_value
        elif t_type == 'MARKER':
            keyword = t_value['keyword']
            tag_type = t_value['tag_type']
            line_num = t_value['line_num']
            
            if tag_type == 'BEGIN':
                new_block = {
                    'keyword': keyword,
                    'parameter': t_value['parameter'],
                    'content': "",
                    'children': [],
                    'line_num': line_num
                }
                
                # Check for nesting rules
                if stack:
                    parent_block, parent_line = stack[-1]
                    if parent_block['keyword'] not in CONTAINER_KEYWORDS:
                        raise V2ParserError(
                            f"Parsing Error: Block '{keyword}' at line {line_num} cannot be nested inside '{parent_block['keyword']}'."
                        )
                
                stack.append((new_block, line_num))
            
            elif tag_type == 'END':
                if not stack:
                    raise V2ParserError(f"Parsing Error: Unexpected '@@@{keyword}_END' at line {line_num} with no open block.")
                
                closed_block, start_line = stack.pop()
                if closed_block['keyword'] != keyword:
                    raise V2ParserError(
                        f"Parsing Error: Mismatched block tags. Expected '@@@{closed_block['keyword']}_END' but found '@@@{keyword}_END' at line {line_num}."
                    )
                
                # Framing Rule: The newline immediately preceding the END tag is framing, not content.
                if closed_block['content'].endswith('\n'):
                    closed_block['content'] = closed_block['content'][:-1]

                if stack:
                    stack[-1][0]['children'].append(closed_block)
                    # We might want to keep the "naked" content in the parent too, 
                    # but usually for PATCH, content is just the children.
                else:
                    blocks.append(closed_block)

    if stack:
        keyword, line_num = stack[0][0]['keyword'], stack[0][1]
        raise V2ParserError(f"Parsing Error: Block '{keyword}' began at line {line_num} but was never closed.")

    return blocks
