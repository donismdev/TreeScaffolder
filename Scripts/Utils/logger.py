import logging
import json
import sys
import datetime
from pathlib import Path

# Log Levels:
# 0: Release (Errors and critical info only)
# 1: Info (Key application milestones)
# 2: Debug (Detailed flow information)
# 3: Trace (Everything)

_log_level = 1  # Default
_dry_run_count = 0
_real_run_count = 0
_session_jobs = [] # List of (type, name) tuples
_runtime_log_path = None
_error_log_path = None
_session_dir = None

class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        # Filter out Tkinter messages or empty lines from print()
        if buf.strip() and "Tkinter is no longer supported" not in buf:
            for line in buf.rstrip().splitlines():
                if line:
                    self.logger.log(self.log_level, line)

    def flush(self):
        pass

class LazyFileHandler(logging.FileHandler):
    """FileHandler that only opens/creates the file when the first record is emitted."""
    def __init__(self, filename, mode='a', encoding=None, delay=True):
        # Setting delay=True prevents file creation at init
        super().__init__(filename, mode, encoding, delay)

    def emit(self, record):
        super().emit(record)

def set_log_level(level: int):
    global _log_level
    # Clamp level between 0 and 3, default to 1 if invalid
    if not isinstance(level, int) or not (0 <= level <= 3):
        _log_level = 1
    else:
        _log_level = level

def get_log_level() -> int:
    return _log_level

def get_session_dir() -> Path | None:
    return _session_dir

def notify_scaffold_executed(is_dry_run: bool, job_name: str = ""):
    global _dry_run_count, _real_run_count, _session_jobs
    run_type = "DRY RUN" if is_dry_run else "REAL"
    if is_dry_run:
        _dry_run_count += 1
    else:
        _real_run_count += 1
    _session_jobs.append((run_type, job_name))

def is_job_name_used(name: str) -> bool:
    """Checks if a job name has already been used in this session."""
    return any(job[1] == name for job in _session_jobs)

def get_formatted_status() -> str:
    """Returns a summary string of executions in the current session with job names."""
    if not _session_jobs:
        return "NOT EXECUTED"
    
    # Core stats
    parts = []
    if _dry_run_count > 0:
        parts.append(f"DRY RUN x{_dry_run_count}")
    if _real_run_count > 0:
        parts.append(f"REAL x{_real_run_count}")
    
    base_status = "EXECUTED (" + ", ".join(parts) + ")"
    
    # Detail list of jobs
    job_details = []
    for run_type, name in _session_jobs:
        job_details.append(f"[{run_type}] [job name : {name}]" if name else f"[{run_type}] (Unnamed)")
    
    return f"{base_status}\nJobs: " + ", ".join(job_details)

def finalize_session_log():
    """Prepends the scaffold execution status to the beginning of the runtime log file and cleans up empty error logs."""
    global _runtime_log_path, _error_log_path
    
    try:
        # Shutdown logging to release file handles
        logging.shutdown()
        
        # 1. Prepend status to runtime log
        if _runtime_log_path and _runtime_log_path.exists():
            status_str = get_formatted_status()
            content = _runtime_log_path.read_text(encoding='utf-8')
            header = f"========================================\n"
            header += f"SCAFFOLD APPLY STATUS: {status_str}\n"
            header += f"========================================\n\n"
            _runtime_log_path.write_text(header + content, encoding='utf-8')

        # 2. Cleanup error log if empty
        if _error_log_path and _error_log_path.exists():
            if _error_log_path.stat().st_size == 0:
                _error_log_path.unlink()
                
    except Exception as e:
        print(f"Failed to finalize session log: {e}")

def _get_logger():
    # Use console_output if it has handlers (set up by setup_runtime_logging)
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

def setup_runtime_logging(config_file, log_dir):
    """Sets up a file logger in a session-specific directory."""
    global _runtime_log_path, _session_dir
    try:
        config_file_path = Path.cwd() / config_file
        # Load level from config
        load_config_and_set_level(config_file_path)

        # Always initialize console_logger_instance so logger.py can find it
        console_logger_instance = logging.getLogger('console_output')
        console_logger_instance.setLevel(logging.DEBUG)
        console_logger_instance.propagate = False

        # Create session directory
        log_base_dir = Path.cwd() / log_dir
        log_base_dir.mkdir(exist_ok=True)
        
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%Hh%Mm")
        
        # Determine unique session directory name
        session_dir = log_base_dir / f"Session_{timestamp}"
        counter = 2
        while session_dir.exists():
            session_dir = log_base_dir / f"Session_{timestamp}_{counter}"
            counter += 1
            
        session_dir.mkdir(exist_ok=True)
        _session_dir = session_dir
        
        # Use the folder's name for the log file base to keep it consistent
        session_id = session_dir.name.replace('Session_', '')
        runtime_log_filename = session_dir / f"runtime_{session_id}.log"
        error_log_filename = session_dir / f"runtime_error_{session_id}.log"
        _runtime_log_path = runtime_log_filename
        _error_log_path = error_log_filename

        # --- Main Runtime Log (All levels) ---
        console_file_handler = logging.FileHandler(runtime_log_filename, mode='w', encoding='utf-8')
        console_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        console_logger_instance.addHandler(console_file_handler)

        # --- Dedicated Error Log (ERROR level and above only) ---
        # Using LazyFileHandler with delay=True to avoid creating empty files
        error_file_handler = LazyFileHandler(error_log_filename, mode='w', encoding='utf-8', delay=True)
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        console_logger_instance.addHandler(error_file_handler)

        # --- Setup Editor Logger ---
        editor_logger_instance = logging.getLogger('editor_output')
        editor_logger_instance.setLevel(logging.DEBUG)
        
        # Editor messages to main log
        editor_file_handler = logging.FileHandler(runtime_log_filename, mode='a', encoding='utf-8')
        editor_file_handler.setFormatter(logging.Formatter('--- editor log ---\n%(asctime)s - %(levelname)s - %(message)s'))
        editor_logger_instance.addHandler(editor_file_handler)
        
        # Editor messages to error log (filtered, also lazy)
        editor_error_handler = LazyFileHandler(error_log_filename, mode='a', encoding='utf-8', delay=True)
        editor_error_handler.setLevel(logging.ERROR)
        editor_error_handler.setFormatter(logging.Formatter('--- editor error ---\n%(asctime)s - %(levelname)s - %(message)s'))
        editor_logger_instance.addHandler(editor_error_handler)
        
        editor_logger_instance.propagate = False

        # Redirect stdout and stderr to the logger
        sys.stdout = StreamToLogger(console_logger_instance, logging.INFO)
        sys.stderr = StreamToLogger(console_logger_instance, logging.ERROR)
        
        info(f"Runtime logging enabled (Session). Log file: {runtime_log_filename}")

    except Exception as e:
        print(f"Failed to setup logging: {e}")

