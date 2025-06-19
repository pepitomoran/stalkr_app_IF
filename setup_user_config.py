import os
import json
import platform
from utils.jd_connection_utils import detect_os, get_default_jd_path


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "user_config.json")

def detect_os():
    plat = platform.system().lower()
    if "darwin" in plat or "mac" in plat:
        return "mac"
    if "windows" in plat:
        return "win"
    if "linux" in plat:
        return "linux"
    return "unknown"

def get_default_jd_path():
    os_type = detect_os()
    if os_type == "mac":
        return "/Applications/JDownloader2.app"
    elif os_type == "win":
        return r"C:\Program Files\JDownloader2\JDownloader2.exe"
    else:
        return "/path/to/JDownloader2"

REQUIRED_FIELDS = {
    "initials": "Enter your initials (e.g. pm): ",
    "device": "Enter your JDownloader device name (e.g. JDownloader@pepitostalkr): ",
    "download_dir": "Enter default download folder (absolute path): ",
    "sheet_url": "Enter Google Sheet URL: ",
    "last_tab": "Enter last-used Sheet tab name (or leave blank): ",
    "log_level": "Set log level (DEBUG/INFO/WARNING/ERROR): ",
    "jd_app_path": f"Enter path to JDownloader app (default: {get_default_jd_path()}): "
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        try:
            return json.load(f)
        except Exception:
            print("⚠️  Config file exists but could not be read. Starting fresh.")
            return {}

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"✅ Config saved to {CONFIG_PATH}")

def prompt_for_missing(cfg):
    changed = False
    for field, prompt in REQUIRED_FIELDS.items():
        val = cfg.get(field, "")
        while not val:
            user_val = input(prompt).strip()
            if not user_val and field == "jd_app_path":
                user_val = get_default_jd_path()
            if field == "jd_app_path" and not os.path.exists(user_val):
                print(f"❌ Path does not exist: {user_val}")
                user_val = ""
            cfg[field] = user_val
            val = user_val
            changed = True
    return changed

def print_config(cfg):
    print("\nCurrent user config:")
    for k, v in cfg.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    print(f"Checking for user config at: {CONFIG_PATH}")
    config = load_config()
    if prompt_for_missing(config):
        save_config(config)
    print_config(config)
    print("\nUser config setup complete.")
