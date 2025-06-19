import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import re
import gspread
from google.oauth2.service_account import Credentials
from utils.filename_generator import generate_ifl_filename
from utils.jd_connection_utils import (
    ensure_jd_running_and_connected,
    load_user_config
)



BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # <- go up one from /sheet/
USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")

SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "private", "stalkrorgsheetapi-4feb1ec20bbe.json")
ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")

# --- Extract YouTube ID ---
def extract_youtube_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

# --- Extract Job Number ---
def extract_job_number(sheet_title):
    match = re.match(r'([0-9]{4,})(?:L)?', sheet_title)
    return match.group(1) if match else None

def main():
    cfg = load_user_config(USER_CONFIG_PATH)
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_url(cfg["sheet_url"])
    worksheet = sheet.worksheet(cfg["last_tab"])
    job_number = extract_job_number(sheet.title) or "0000"
    rows = worksheet.get_all_values()
    header = rows[0]
    data_rows = rows[1:]
    col_map = {key: idx for idx, key in enumerate(header)}

    # Use the JD utility for connection
    ok, device = ensure_jd_running_and_connected(cfg, USER_CONFIG_PATH, ORG_SECRETS_PATH)
    if not ok or not device:
        print("❌ JD device not found.")
        return

    for i, row in enumerate(data_rows):
        url = row[col_map.get("URL", -1)]
        title = row[col_map.get("Title", -1)]
        channel = row[col_map.get("User", -1)]
        yt_id = extract_youtube_id(url)
        if not url or not yt_id or not title:
            continue
        filename = generate_ifl_filename(
            youtube_id=yt_id,
            channel=channel,
            job_number=job_number,
            resolution="1080",
            researcher_initials=cfg["initials"],
            description="DESCRIPTION"
        )
        print(f"📤 Sending {url} as {filename}")
        device.linkgrabber.add_links([{
            "autostart": True,
            "links": url,
            "packageName": filename,
            "destinationFolder": cfg["download_dir"]
        }])

if __name__ == "__main__":
    main()
