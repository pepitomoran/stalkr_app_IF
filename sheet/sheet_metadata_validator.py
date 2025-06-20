import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import re
import gspread
from google.oauth2.service_account import Credentials
import requests
import isodate
from utils.logger import log_event, logprint, log_script

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "private", "stalkrorgsheetapi-4feb1ec20bbe.json")
ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")

REQUIRED_FIELDS = [
    "initials", "device", "download_dir", "sheet_url", "last_tab", "log_level"
]

def load_user_config():
    if not os.path.exists(USER_CONFIG_PATH):
        logprint(
            f"❌ No user config at {USER_CONFIG_PATH}",
            action="user_config_missing",
            status="error",
            error_message=f"No user config at {USER_CONFIG_PATH}"
        )
        return None
    with open(USER_CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    missing = [field for field in REQUIRED_FIELDS if not cfg.get(field)]
    for field in missing:
        cfg[field] = input(f"Enter {field}: ").strip()
    if missing:
        with open(USER_CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    return cfg

def load_org_secrets():
    if not os.path.exists(ORG_SECRETS_PATH):
        logprint(
            f"❌ org_secrets.json not found at {ORG_SECRETS_PATH}",
            action="org_secrets_missing",
            status="error",
            error_message=f"org_secrets.json not found at {ORG_SECRETS_PATH}"
        )
        return None
    with open(ORG_SECRETS_PATH, "r") as f:
        try:
            secrets = json.load(f)
            return secrets
        except Exception as e:
            logprint(
                f"❌ Could not read org_secrets.json: {e}",
                action="org_secrets_read_failed",
                status="error",
                error_message=str(e)
            )
            return None

def extract_youtube_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

def fetch_youtube_metadata(video_id, api_key):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,contentDetails",
        "id": video_id,
        "key": api_key
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        logprint(
            f"❌ YouTube API error: {response.status_code}, {response.text}",
            action="youtube_api_error",
            status="error",
            error_message=f"{response.status_code}: {response.text}",
            extra_info={"video_id": video_id}
        )
        return None
    data = response.json()
    items = data.get("items", [])
    if not items:
        logprint(
            f"❌ No video found for ID {video_id}.",
            action="youtube_no_video_found",
            status="warning",
            error_message=f"No video for ID {video_id}"
        )
        return None
    snippet = items[0]["snippet"]
    details = items[0]["contentDetails"]

    try:
        duration = isodate.parse_duration(details.get("duration", ""))
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            parsed_duration = f"{hours:02}:{minutes:02}:{seconds:02}"
        else:
            parsed_duration = f"{minutes:02}:{seconds:02}"
    except Exception:
        parsed_duration = details.get("duration", "")

    return {
        "title": snippet.get("title"),
        "channel": snippet.get("channelTitle"),
        "publishedAt": snippet.get("publishedAt", "").split("T")[0],
        "duration": parsed_duration
    }

def get_sheet(cfg):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(cfg["sheet_url"])
    worksheet_name = cfg.get("last_tab", "")

    if worksheet_name:
        try:
            sheet = spreadsheet.worksheet(worksheet_name)
            print(f"✅ Using tab: '{worksheet_name}'")
        except gspread.exceptions.WorksheetNotFound:
            print(f"❌ Tab '{worksheet_name}' not found in this Google Sheet.")
            all_tabs = [ws.title for ws in spreadsheet.worksheets()]
            print("Available tabs:")
            for idx, tab in enumerate(all_tabs, 1):
                print(f"{idx}: {tab}")
            while True:
                try:
                    tab_idx = int(input(f"Select a tab by number (1-{len(all_tabs)}): ")) - 1
                    assert 0 <= tab_idx < len(all_tabs)
                    break
                except (ValueError, AssertionError):
                    print("Invalid selection. Please try again.")
            sheet = spreadsheet.get_worksheet(tab_idx)
            cfg["last_tab"] = all_tabs[tab_idx]
            with open(USER_CONFIG_PATH, "w") as f:
                json.dump(cfg, f, indent=2)
            print(f"✅ Updated 'last_tab' in config to: {cfg['last_tab']}")
    else:
        all_tabs = [ws.title for ws in spreadsheet.worksheets()]
        print("No tab specified in config.")
        print("Available tabs:")
        for idx, tab in enumerate(all_tabs, 1):
            print(f"{idx}: {tab}")
        while True:
            try:
                tab_idx = int(input(f"Select a tab by number (1-{len(all_tabs)}): ")) - 1
                assert 0 <= tab_idx < len(all_tabs)
                break
            except (ValueError, AssertionError):
                print("Invalid selection. Please try again.")
        sheet = spreadsheet.get_worksheet(tab_idx)
        cfg["last_tab"] = all_tabs[tab_idx]
        with open(USER_CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"✅ Updated 'last_tab' in config to: {cfg['last_tab']}")
    return sheet

@log_script
def main():
    cfg = load_user_config()
    if not cfg:
        return
    secrets = load_org_secrets()
    if not secrets or not secrets.get("youtube_api_key"):
        return
    api_key = secrets["youtube_api_key"]

    sheet = get_sheet(cfg)
    rows = sheet.get_all_values()
    header = rows[0]
    data_rows = rows[1:]

    col_map = {name: idx for idx, name in enumerate(header)}
    must_have = ["URL", "Title", "User", "date", "duration", "Researcher Notes"]

    rows_scanned = len(data_rows)
    cells_updated = 0
    columns_added = []

    # Add missing columns
    for col in must_have:
        if col not in col_map:
            logprint(
                f"⚠️ Column '{col}' missing! Please add it manually to the Sheet header before running this script.",
                action="missing_column",
                status="error",
                error_message=f"Missing column: {col}"
            )
            columns_added.append(col)
            # Optionally: Add column with API if you want automatic add

    youtube_id_map = {}
    for i, row in enumerate(data_rows):
        url = row[col_map["URL"]]
        yt_id = extract_youtube_id(url)
        if yt_id:
            youtube_id_map.setdefault(yt_id, []).append(i+2)

    for i, row in enumerate(data_rows):
        row_num = i + 2
        url = row[col_map["URL"]]
        yt_id = extract_youtube_id(url)
        if not url or row[col_map["Title"]].startswith("If clip ID is found"):
            continue

        if yt_id and len(youtube_id_map[yt_id]) > 1:
            sheet.format(f"{chr(65+col_map['URL'])}{row_num}", {"backgroundColor": {"red": 1, "green": 0.8, "blue": 0}})
            logprint(
                f"⛔ Duplicate ID in row {row_num} (also in rows: {', '.join(map(str, youtube_id_map[yt_id]))})",
                action="duplicate_found",
                status="warning",
                sheet_row=row_num,
                extra_info={"yt_id": yt_id, "rows": youtube_id_map[yt_id]}
            )
        else:
            sheet.format(f"{chr(65+col_map['URL'])}{row_num}", {"backgroundColor": {"red": 1, "green": 1, "blue": 1}})

        if yt_id and api_key:
            meta = fetch_youtube_metadata(yt_id, api_key)
            if meta:
                sheet.update_cell(row_num, col_map["Title"]+1, meta["title"]);      cells_updated += 1
                sheet.update_cell(row_num, col_map["User"]+1, meta["channel"]);    cells_updated += 1
                sheet.update_cell(row_num, col_map["date"]+1, meta["publishedAt"]);cells_updated += 1
                sheet.update_cell(row_num, col_map["duration"]+1, meta["duration"]);cells_updated += 1

    # --- Summary log ---
    logprint(
        f"\nSummary: {rows_scanned} rows scanned, {cells_updated} cells updated, columns added: {columns_added}",
        action="summary",
        status="info",
        extra_info={
            "rows_scanned": rows_scanned,
            "cells_updated": cells_updated,
            "columns_added": columns_added
        }
    )

if __name__ == "__main__":
    main()
