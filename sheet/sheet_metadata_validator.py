import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import re
import gspread
from google.oauth2.service_account import Credentials
import requests
import isodate
from utils.logger import logprint, log_event, log_script

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "private", "stalkrorgsheetapi-4feb1ec20bbe.json")
ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")

# --- Extract YouTube ID ---
def extract_youtube_id(url):
    if not url or not isinstance(url, str):
        return None
    # Find v= or youtu.be/ or /embed/
    match = re.search(r'(?:v=|youtu\.be/|/embed/|/shorts/)([0-9A-Za-z_-]{11})', url)
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
        return None
    data = response.json()
    items = data.get("items", [])
    if not items:
        return None
    snippet = items[0]["snippet"]
    details = items[0]["contentDetails"]

    # Duration: convert ISO8601 to "mm:ss"
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

def find_graveyard_row(rows, header_keys):
    """
    Returns the row index (0-based) of the Graveyard header (archive region).
    If not found, returns None.
    """
    for idx, row in enumerate(rows):
        # Test for header repetition (ignore case, spaces)
        row_norm = [str(cell).strip().lower() for cell in row]
        if all(any(key.lower() in cell for cell in row_norm) for key in header_keys):
            # Skip first header; look for a second header row
            if idx > 0:
                return idx
    return None

def validate_row(sheet, row_idx, col_map, all_rows, graveyard_idx, api_key):
    """
    Validates/updates a single row. Only runs if row_idx < graveyard_idx (research row).
    Updates metadata and duplicate status. 
    Returns: dict with keys: updated (bool), duplicate (str), non_youtube (bool)
    """
    row = all_rows[row_idx]
    url = row[col_map.get("URL")]
    duplicate_col = col_map.get("Duplicate", None)
    status_col = col_map.get("Status", None)
    researcher_col = col_map.get("Researcher Name", None)
    title_col = col_map.get("Title", None)
    user_col = col_map.get("User", None)
    date_col = col_map.get("date", None)
    duration_col = col_map.get("duration", None)

    if row_idx >= graveyard_idx:
        # In Graveyard/archive section—do NOT touch
        return {"updated": False, "duplicate": "", "non_youtube": False}

    # --- Check Non-YouTube URL ---
    yt_id = extract_youtube_id(url)
    if not yt_id:
        # Not a YouTube URL: flag as non-YouTube, skip
        if duplicate_col is not None:
            sheet.update_cell(row_idx+1, duplicate_col+1, "Non-YouTube link")
        if status_col is not None:
            sheet.update_cell(row_idx+1, status_col+1, "Non-YouTube link")
        return {"updated": True, "duplicate": "Non-YouTube link", "non_youtube": True}

    # --- Duplicate Checking: scan ALL rows (including Graveyard) ---
    duplicates = []
    for i, other in enumerate(all_rows):
        if i == row_idx:
            continue
        other_url = other[col_map.get("URL", -1)]
        other_yt_id = extract_youtube_id(other_url)
        if yt_id and other_yt_id == yt_id:
            # Check if in Graveyard/archive or research
            if i >= graveyard_idx:
                # Archive/Graveyard
                duplicates.append((i+1, "search PWC Archive tab for further data"))
            else:
                # Research row: get status, researcher
                other_status = other[col_map.get("Status", -1)] if status_col is not None else ""
                other_researcher = other[col_map.get("Researcher Name", -1)] if researcher_col is not None else ""
                duplicates.append((i+1, f"Duplicate of row {i+1} [Status: {other_status}, Researcher: {other_researcher}]"))
    duplicate_str = ""
    if duplicates:
        if any("search PWC Archive tab" in x[1] for x in duplicates):
            # Archive match gets priority
            duplicate_str = "search PWC Archive tab for further data"
        else:
            # Research match—concatenate all found
            duplicate_str = " ; ".join([x[1] for x in duplicates])
    # Update Duplicate col
    if duplicate_col is not None:
        sheet.update_cell(row_idx+1, duplicate_col+1, duplicate_str)
    # Update status if duplicate in research rows (not archive)
    if "Duplicate of row" in duplicate_str:
        if status_col is not None:
            sheet.update_cell(row_idx+1, status_col+1, "DUPLICATE")
        return {"updated": True, "duplicate": duplicate_str, "non_youtube": False}
    # Metadata: only update if missing
    updated = False
    if (title_col is not None and not row[title_col]) and api_key and yt_id:
        meta = fetch_youtube_metadata(yt_id, api_key)
        if meta:
            sheet.update_cell(row_idx+1, title_col+1, meta["title"])
            updated = True
            if user_col is not None: sheet.update_cell(row_idx+1, user_col+1, meta["channel"])
            if date_col is not None: sheet.update_cell(row_idx+1, date_col+1, meta["publishedAt"])
            if duration_col is not None: sheet.update_cell(row_idx+1, duration_col+1, meta["duration"])
    return {"updated": updated, "duplicate": duplicate_str, "non_youtube": False}

def load_user_config():
    if not os.path.exists(USER_CONFIG_PATH):
        logprint(f"❌ No user config at {USER_CONFIG_PATH}", action="user_config_missing", status="error")
        return None
    with open(USER_CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    return cfg

def load_org_secrets():
    if not os.path.exists(ORG_SECRETS_PATH):
        logprint(f"❌ org_secrets.json not found at {ORG_SECRETS_PATH}", action="org_secrets_missing", status="error")
        return None
    with open(ORG_SECRETS_PATH, "r") as f:
        try:
            secrets = json.load(f)
            return secrets
        except Exception as e:
            logprint(f"❌ Could not read org_secrets.json: {e}", action="org_secrets_read_failed", status="error", error_message=str(e))
            return None

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
    # CLI mode: validates all research rows
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
    col_map = {name: idx for idx, name in enumerate(header)}
    header_keys = ["Researcher Name", "URL", "Title", "User"]  # Extend as needed

    graveyard_idx = find_graveyard_row(rows, header_keys)
    if graveyard_idx is None:
        print("⚠️ Graveyard/archive section not found (no repeated header row).")
        cont = input("Proceed with all rows as research? [y/N]: ").strip().lower()
        if cont != "y":
            print("Exiting.")
            return
        graveyard_idx = len(rows)  # treat all as research

    updated_count = 0
    for idx, row in enumerate(rows[1:graveyard_idx], start=1):
        res = validate_row(sheet, idx, col_map, rows, graveyard_idx, api_key)
        if res["updated"]:
            updated_count += 1

    print(f"Done. {updated_count} rows updated.")

if __name__ == "__main__":
    main()
