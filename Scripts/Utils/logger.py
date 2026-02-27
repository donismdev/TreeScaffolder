import logging
import json
import sys
from pathlib import Path

# Log Levels:
# 0: Release (Errors and critical info only)
# 1: Info (Key application milestones)
# 2: Debug (Detailed flow information)
# 3: Trace (Everything)

_log_level = 1  # Default

def set_log_level(level: int):
    global _log_level
    # Clamp level between 0 and 3, default to 1 if invalid
    if not isinstance(level, int) or not (0 <= level <= 3):
        _log_level = 1
    else:
        _log_level = level

def get_log_level() -> int:
    return _log_level

def _get_logger():
    # Use console_output if it has handlers (set up by gui_app.py)
    # otherwise fallback to a default logger
    logger = logging.getLogger('console_output')
    if not logger.handlers:
        # Check if we should add a console handler as fallback
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            logger.setLevel(logging.DEBUG)
    return logger

def error(message: str):
    _get_logger().error(message)

def warn(message: str):
    if _log_level >= 0:
        _get_logger().warning(message)

def info(message: str):
    if _log_level >= 1:
        _get_logger().info(message)

def debug(message: str):
    if _log_level >= 2:
        _get_logger().debug(message)

def trace(message: str):
    if _log_level >= 3:
        _get_logger().debug(f"[TRACE] {message}")

def load_config_and_set_level(config_path: Path):
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                level = config.get("debug_level", 1)
                set_log_level(level)
    except Exception:
        pass
