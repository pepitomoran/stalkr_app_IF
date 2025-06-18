import os
import json
import re
import gspread
from google.oauth2.service_account import Credentials
import requests
import isodate

# --- Config locations ---
USER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "user_config.json")
CREDENTIALS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "private", "stalkrorgsheetapi-4feb1ec20bbe.json"))
ORG_SECRETS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "private", "org_secrets.json"))

# --- Required fields for user config ---
REQUIRED_FIELDS = [
    "initials", "device", "download_dir", "sheet_url", "last_tab", "log_level"
]

def load_user_config():
    if not os.path.exists(USER_CONFIG_PATH):
        print(f"❌ No user config at {USER_CONFIG_PATH}")
        return None
    with open(USER_CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    # Prompt for any missing fields
    missing = [field for field in REQUIRED_FIELDS if not cfg.get(field)]
    for field in missing:
        cfg[field] = input(f"Enter {field}: ").strip()
    if missing:
        with open(USER_CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    return cfg

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
        print(f"❌ YouTube API error: {response.status_code}, {response.text}")
        return None
    data = response.json()
    items = data.get("items", [])
    if not items:
        print("❌ No video found for this ID.")
        return None
    snippet = items[0]["snippet"]
    details = items[0]["contentDetails"]

    # Parse duration from ISO 8601 to "hh:mm:ss"
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
            # Update last_tab in config for next time
            cfg["last_tab"] = all_tabs[tab_idx]
            with open(USER_CONFIG_PATH, "w") as f:
                json.dump(cfg, f, indent=2)
            print(f"✅ Updated 'last_tab' in config to: {cfg['last_tab']}")
    else:
        # No last_tab set; prompt user to select one
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

def main():
    cfg = load_user_config()
    if not cfg:
        print("No user config found or setup aborted.")
        return

    secrets = load_org_secrets()
    if not secrets or not secrets.get("youtube_api_key"):
        print("❌ YouTube API key missing in org_secrets.json.")
        return
    api_key = secrets["youtube_api_key"]

    sheet = get_sheet(cfg)
    rows = sheet.get_all_values()
    header = rows[0]
    data_rows = rows[1:]

    # Identify column indices dynamically
    col_map = {name: idx for idx, name in enumerate(header)}
    # Ensure these columns exist, add if not present
    must_have = ["URL", "Title", "User", "date", "duration", "Researcher Notes"]
    for col in must_have:
        if col not in col_map:
            print(f"⚠️ Column '{col}' missing! Please add it manually to the Sheet header before running this script.")
            return

    # Build map of YouTube IDs for duplicate checking
    youtube_id_map = {}
    for i, row in enumerate(data_rows):
        url = row[col_map["URL"]]
        yt_id = extract_youtube_id(url)
        if yt_id:
            youtube_id_map.setdefault(yt_id, []).append(i+2) # +2 for sheet row numbers

    updates = 0
    duplicates = 0

    for i, row in enumerate(data_rows):
        row_num = i + 2 # Sheet rows are 1-indexed, header is row 1
        url = row[col_map["URL"]]
        yt_id = extract_youtube_id(url)
        notes = []
        # Skip empty rows or special instruction rows
        if not url or row[col_map["Title"]].startswith("If clip ID is found"):
            continue

        # Duplicate check
        if yt_id and len(youtube_id_map[yt_id]) > 1:
            sheet.format(f"{chr(65+col_map['URL'])}{row_num}", {"backgroundColor": {"red": 1, "green": 0.8, "blue": 0}})
            notes.append(f"⛔ Duplicate ID (also in rows: {', '.join(map(str, youtube_id_map[yt_id]))})")
            duplicates += 1
        else:
            sheet.format(f"{chr(65+col_map['URL'])}{row_num}", {"backgroundColor": {"red": 1, "green": 1, "blue": 1}})

        # === Fetch and write YouTube metadata ===
        if yt_id and api_key:
            meta = fetch_youtube_metadata(yt_id, api_key)
            if meta:
                sheet.update_cell(row_num, col_map["Title"]+1, meta["title"])
                sheet.update_cell(row_num, col_map["User"]+1, meta["channel"])
                sheet.update_cell(row_num, col_map["date"]+1, meta["publishedAt"])
                sheet.update_cell(row_num, col_map["duration"]+1, meta["duration"])
                notes.append("Updated metadata from YouTube API")

        if notes:
            sheet.update_cell(row_num, col_map["Researcher Notes"]+1, "; ".join(notes))
            updates += 1

    print(f"\nScanned {len(data_rows)} rows.")
    print(f"Flagged {duplicates} duplicates.")
    print(f"Updated {updates} rows with warnings/notes and YouTube metadata.")
    print("Done.")

if __name__ == "__main__":
    main()
