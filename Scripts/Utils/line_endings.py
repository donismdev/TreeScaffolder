# -*- coding: utf-8 -*-
"""
line_endings.py

Centralized utility for handling line endings (LF vs CRLF).
Ensures consistency across the parser, core logic, and file I/O.
"""
import os
import platform

def ensure_lf(text: str) -> str:
    """
    Normalizes all line endings in the text to LF (\n).
    Handles CRLF (\r\n) and CR (\r).
    """
    if text is None:
        return ""
    return text.replace('\r\n', '\n').replace('\r', '\n')

def ensure_native(text: str) -> str:
    """
    Converts LF (\n) line endings to the system's native format.
    On Windows, this results in CRLF (\r\n).
    """
    if text is None:
        return ""
    
    # 1. First, bring everything to a clean LF state
    clean_text = ensure_lf(text)
    
    # 2. On Windows, replace all LF with CRLF
    if platform.system() == "Windows":
        return clean_text.replace('\n', '\r\n')
    
    return clean_text

def normalize_for_comparison(text: str) -> str:
    """
    Standardizes text for literal comparison by stripping 
    surrounding whitespace and ensuring LF.
    """
    return ensure_lf(text).strip()
