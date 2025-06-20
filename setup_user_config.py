import os
import json
import platform
from utils.jd_connection_utils import detect_os, get_default_jd_path
from utils.logger import log_event, logprint, log_script

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "user_config.json")

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
        logprint(
            f"Config missing: {CONFIG_PATH}",
            action="config_missing",
            status="info"
        )
        return {}
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        logprint(
            "Config loaded successfully.",
            action="config_loaded",
            status="success"
        )
        return cfg
    except Exception as e:
        logprint(
            f"⚠️  Config file exists but could not be read. Starting fresh. Error: {e}",
            action="config_load_failed",
            status="error",
            error_message=str(e)
        )
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        logprint(
            f"✅ Config saved to {CONFIG_PATH}",
            action="config_saved",
            status="success"
        )
    except Exception as e:
        logprint(
            f"❌ Failed to save config: {e}",
            action="config_save_failed",
            status="error",
            error_message=str(e)
        )

def prompt_for_missing(cfg):
    changed = False
    updated_fields = []
    prompted_fields = []
    for field, prompt in REQUIRED_FIELDS.items():
        val = cfg.get(field, "")
        while not val:
            user_val = input(prompt).strip()
            if not user_val and field == "jd_app_path":
                user_val = get_default_jd_path()
            if field == "jd_app_path" and not os.path.exists(user_val):
                logprint(
                    f"❌ Path does not exist: {user_val}",
                    action="invalid_jd_app_path",
                    status="error",
                    extra_info={"jd_app_path": user_val}
                )
                print(f"❌ Path does not exist: {user_val}")
                user_val = ""
            cfg[field] = user_val
            val = user_val
            changed = True
            if user_val:
                logprint(
                    f"Set {field}: {user_val}",
                    action="user_input",
                    status="info",
                    extra_info={field: user_val}
                )
                updated_fields.append(field)
            else:
                prompted_fields.append(field)
    return changed, updated_fields, prompted_fields

def print_config(cfg):
    print("\nCurrent user config:")
    for k, v in cfg.items():
        print(f"  {k}: {v}")

@log_script
def main():
    print(f"Checking for user config at: {CONFIG_PATH}")
    config = load_config()
    changed, updated_fields, prompted_fields = prompt_for_missing(config)
    if changed:
        save_config(config)
    print_config(config)
    logprint(
        f"\nSummary: Fields set: {updated_fields}, fields still missing: {prompted_fields}",
        action="summary",
        status="info",
        extra_info={
            "updated_fields": updated_fields,
            "prompted_fields": prompted_fields
        }
    )
    print("\nUser config setup complete.")

if __name__ == "__main__":
    main()
