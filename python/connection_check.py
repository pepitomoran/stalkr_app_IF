import os
import json
import getpass

import gspread
from google.oauth2.service_account import Credentials
import myjdapi

# --- Config locations ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "user_config.json")
DEFAULT_CREDENTIALS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "private", "stalkrorgsheetapi-4feb1ec20bbe.json"))
ORG_SECRETS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "private", "org_secrets.json"))


# --- Required fields ---
REQUIRED_FIELDS = {
    "initials": "Enter your initials (e.g. pm): ",
    "device": "Enter your JDownloader device name (e.g. JDownloader@pepitostalkr): ",
    "download_dir": "Enter default download folder (absolute path): ",
    "sheet_url": "Enter Google Sheet URL: ",
    "last_tab": "Enter last-used Sheet tab name (or leave blank): ",
    "log_level": "Set log level (DEBUG/INFO/WARNING/ERROR): "
}

def load_org_secrets():
    if not os.path.exists(ORG_SECRETS_PATH):
        print(f"❌ org_secrets.json not found at {ORG_SECRETS_PATH}")
        return None
    with open(ORG_SECRETS_PATH, "r") as f:
        try:
            return json.load(f)
        except Exception:
            print("❌ Could not read org_secrets.json.")
            return None


def load_user_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        try:
            return json.load(f)
        except Exception:
            print("⚠️  Could not read config file. Starting fresh.")
            return {}

def save_user_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

def prompt_for_missing(cfg):
    changed = False
    for field, prompt in REQUIRED_FIELDS.items():
        if not cfg.get(field, ""):
            user_val = input(prompt).strip()
            cfg[field] = user_val
            changed = True
    return changed

def print_config(cfg):
    print("\nCurrent user config:")
    for k, v in cfg.items():
        print(f"  {k}: {v}")

def check_google_sheet(cfg):
    print("\n[GOOGLE SHEETS TEST]")
    credentials_path = DEFAULT_CREDENTIALS_PATH
    if not os.path.exists(credentials_path):
        print(f"❌ Service account credentials not found at: {credentials_path}")
        return False
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(cfg["sheet_url"])
        print(f"✅ Connected to Google Sheet: {sheet.title}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Google Sheet: {e}")
        return False

def check_myjdownloader(cfg):
    print("\n[MYJDOWNLOADER TEST]")
    secrets = load_org_secrets()
    if not secrets or not secrets.get("myjd_email") or not secrets.get("myjd_password"):
        print("❌ MyJDownloader credentials missing in org_secrets.json.")
        return False
    email = secrets["myjd_email"]
    password = secrets["myjd_password"]
    try:
        jd = myjdapi.Myjdapi()
        print("Connecting to MyJDownloader...")
        jd.connect(email, password)
        jd.update_devices()
        device = jd.get_device(cfg["device"])
        if not device:
            print(f"❌ Device '{cfg['device']}' not found!")
            return False
        print(f"✅ Connected to MyJDownloader device: {cfg['device']}")
        return True
    except Exception as e:
        print(f"❌ MyJDownloader connection failed: {e}")
        return False


if __name__ == "__main__":
    print(f"Checking user config at: {CONFIG_PATH}")
    config = load_user_config()
    if prompt_for_missing(config):
        save_user_config(config)
    print_config(config)

    sheet_ok = check_google_sheet(config)
    myjd_ok = check_myjdownloader(config)

    print("\n--- CONNECTION STATUS SUMMARY ---")
    print(f"Google Sheet:      {'✅ OK' if sheet_ok else '❌ ERROR'}")
    print(f"MyJDownloader:     {'✅ OK' if myjd_ok else '❌ ERROR'}")

    if sheet_ok and myjd_ok:
        print("All connections successful! Ready for the next stage.")
    else:
        print("Check errors above. Fix config/credentials and try again.")
