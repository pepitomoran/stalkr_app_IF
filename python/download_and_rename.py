# download_and_rename.py

import os
import sys
import json
import re
import gspread
from google.oauth2.service_account import Credentials
import myjdapi

# === Import our filename generator ===
from utils.filename_generator import generate_ifl_filename

# --- Config Paths ---
BASE_DIR = os.path.dirname(__file__)
USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")
SERVICE_ACCOUNT_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "private", "stalkrorgsheetapi-4feb1ec20bbe.json"))
ORG_SECRETS_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "private", "org_secrets.json"))

# --- Load User Config ---
def load_config():
    if not os.path.exists(USER_CONFIG_PATH):
        print("❌ User config not found. Run setup_user_config.py first.")
        sys.exit(1)
    with open(USER_CONFIG_PATH, "r") as f:
        return json.load(f)

# --- Extract YouTube ID ---
def extract_youtube_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

# --- Extract Job Number from Sheet Name ---
def extract_job_number(sheet_title):
    match = re.match(r'([0-9]{4,})(?:L)?', sheet_title)
    return match.group(1) if match else None

# --- MyJDownloader Connection ---
def connect_myjd(cfg):
    if not os.path.exists(ORG_SECRETS_PATH):
        print("❌ org_secrets.json not found.")
        return None

    with open(ORG_SECRETS_PATH, "r") as f:
        secrets = json.load(f)
    email = secrets.get("myjd_email")
    password = secrets.get("myjd_password")
    if not email or not password:
        print("❌ Missing myjd_email or myjd_password in org_secrets.json")
        return None

    jd = myjdapi.Myjdapi()
    print("🔌 Connecting to MyJDownloader...")
    jd.connect(email, password)
    jd.update_devices()
    device = jd.get_device(cfg["device"])
    if not device:
        print(f"❌ Device {cfg['device']} not found!")
        return None
    print(f"✅ Connected to device: {cfg['device']}")
    return device

# --- Main ---
def main():
    cfg = load_config()
    print(f"👤 User: {cfg['initials']}  |  Device: {cfg['device']}\n")

    # Auth with Sheets
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)

    # Open Sheet & Tab
    sheet = client.open_by_url(cfg["sheet_url"])
    worksheet = sheet.worksheet(cfg["last_tab"])
    job_number = extract_job_number(sheet.title) or "0000"

    rows = worksheet.get_all_values()
    header = rows[0]
    data_rows = rows[1:]
    col_map = {key: idx for idx, key in enumerate(header)}

    print(f"📄 Sheet: {sheet.title} | Tab: {cfg['last_tab']}")
    print(f"🔍 Found {len(data_rows)} rows. Parsing valid YouTube links...\n")

    # Connect to MyJDownloader
    device = connect_myjd(cfg)
    if not device:
        print("Aborting: could not connect to JDownloader device.")
        return

    for i, row in enumerate(data_rows):
        url = row[col_map.get("URL", -1)]
        channel = row[col_map.get("User", -1)]
        yt_id = extract_youtube_id(url)

        if not url or not yt_id or channel.lower().startswith("if clip id is found"):
            continue

        resolution = "1080"  # hardcoded for now
        description = "DESCRIPTION"

        filename = generate_ifl_filename(
            youtube_id=yt_id,
            channel=channel,
            job_number=job_number,
            resolution=resolution,
            researcher_initials=cfg["initials"],
            description=description
        )

        print(f"▶ Row {i+2}: {filename}")
        print(f"📤 Sending to JDownloader: {url}")

        try:
            device.linkgrabber.add_links([{
                "autostart": True,
                "links": url,
                "packageName": filename,
                "destinationFolder": cfg["download_dir"]
            }])
        except Exception as e:
            print(f"❌ Failed to send link to JDownloader: {e}")

if __name__ == "__main__":
    main()
