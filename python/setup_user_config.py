import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "user_config.json")

REQUIRED_FIELDS = {
    "initials": "Enter your initials (e.g. pm): ",
    "device": "Enter your JDownloader device name (e.g. JDownloader@pepitostalkr): ",
    "download_dir": "Enter default download folder (absolute path): ",
    "sheet_url": "Enter Google Sheet URL: ",
    "last_tab": "Enter last-used Sheet tab name (or leave blank): ",
    "log_level": "Set log level (DEBUG/INFO/WARNING/ERROR): "
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
        if not val:
            user_val = input(prompt).strip()
            cfg[field] = user_val
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
