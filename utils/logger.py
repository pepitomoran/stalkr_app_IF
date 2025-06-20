# utils/logger.py

import os
import csv
import datetime
import json

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FIELDS = [
    "timestamp",
    "user_initials",
    "script",
    "action",
    "filename",
    "status",
    "error_message",
    "sheet_row",
    "extra_info"
]

def ensure_logs_dir():
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR, exist_ok=True)

def log_event(
    script,
    action,
    filename=None,
    status=None,
    error_message=None,
    sheet_row=None,
    extra_info=None,
    user_initials=None
):
    ensure_logs_dir()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    log_path = os.path.join(LOGS_DIR, f"{now[:10]}.log.csv")

    # Try to read user initials from config if not supplied (optional: import config loader)
    if user_initials is None:
        try:
            from utils.jd_connection_utils import load_user_config
            BASE_DIR = os.path.dirname(os.path.dirname(__file__))
            cfg = load_user_config(os.path.join(BASE_DIR, "config", "user_config.json"))
            user_initials = cfg.get("initials", "na")
        except Exception:
            user_initials = "na"

    row = {
        "timestamp": now,
        "user_initials": user_initials,
        "script": script,
        "action": action,
        "filename": filename,
        "status": status,
        "error_message": error_message,
        "sheet_row": sheet_row,
        "extra_info": json.dumps(extra_info) if extra_info else ""
    }
    # Write header if file does not exist
    write_header = not os.path.exists(log_path)
    with open(log_path, "a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

import os

def logprint(message, action, status="info", error_message=None, sheet_row=None, extra_info=None):
    script = os.path.basename(__file__)
    print(message)
    log_event(
        script=script,
        action=action,
        status=status,
        error_message=error_message,
        sheet_row=sheet_row,
        extra_info=extra_info
    )

def log_script(func):
    import os
    def wrapper(*args, **kwargs):
        script = os.path.basename(__file__)
        log_event(script=script, action="script_start", status="info")
        try:
            result = func(*args, **kwargs)
            log_event(script=script, action="script_end", status="success")
            return result
        except Exception as e:
            log_event(script=script, action="fatal_error", status="error", error_message=str(e))
            print(f"❌ Fatal error: {e}")
            raise
    return wrapper
