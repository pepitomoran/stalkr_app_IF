import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import requests
import isodate
from utils.logger import logprint, log_event, log_script
from sheet.sheet_tools import (
    get_sheet,
    add_missing_columns,
    find_graveyard_row,
    filter_research_rows,
    ensure_column,
    normalize,
    SHEET_KEYS  # This is loaded from org_secrets.json
)

def extract_youtube_id(url):
    # Temporary until you switch to utils/youtube.py
    import re
    if not url or not isinstance(url, str):
        return None
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

def load_user_config(user_config_path):
    with open(user_config_path, "r") as f:
        return json.load(f)

def load_org_secrets(org_secrets_path):
    with open(org_secrets_path, "r") as f:
        return json.load(f)

@log_script
def main():
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")
    CREDENTIALS_PATH = os.path.join(BASE_DIR, "private", "stalkrorgsheetapi-4feb1ec20bbe.json")
    ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")

    cfg = load_user_config(USER_CONFIG_PATH)
    secrets = load_org_secrets(ORG_SECRETS_PATH)
    api_key = secrets["youtube_api_key"]
    sheet_keys = secrets["sheet_keys"]

    worksheet, header, col_map, rows = get_sheet(cfg, CREDENTIALS_PATH)

    # Ensure required columns exist using sheet_keys
    required_cols = sheet_keys["research_keys"] + [sheet_keys["duplicate_column"]]
    header, col_map = add_missing_columns(worksheet, header, required_cols)

    # Find Graveyard/archive row from config
    graveyard_idx = find_graveyard_row(rows, sheet_keys["archive_keys"])
    if graveyard_idx is None or graveyard_idx == len(rows):
        print("⚠️ Graveyard/archive section not found (no repeated archive header row).")
        cont = input("Proceed with all rows as research? [y/N]: ").strip().lower()
        if cont != "y":
            print("Exiting.")
            return
        graveyard_idx = len(rows)

    # Only process user's research rows
    user_initials = normalize(cfg["initials"])
    research_row_indices = filter_research_rows(rows, col_map, user_initials, graveyard_idx)

    updated_count = 0
    for idx in research_row_indices:
        row = rows[idx]
        url = row[col_map[sheet_keys["research_keys"][1]]]  # "URL"
        duplicate_col = col_map[sheet_keys["duplicate_column"]]
        title_col = col_map[sheet_keys["research_keys"][2]]  # "Title"
        user_col = col_map.get(sheet_keys["research_keys"][3])  # "User"
        date_col = col_map.get("date")
        duration_col = col_map.get("duration")

        yt_id = extract_youtube_id(url)
        if not yt_id:
            worksheet.update_cell(idx+1, duplicate_col+1, "Non-YouTube link")
            continue

        # --- Duplicate detection ---
        duplicates_research = []
        duplicates_archive = []
        for i, other in enumerate(rows):
            if i == idx:
                continue
            other_url = other[col_map[sheet_keys["research_keys"][1]]]  # "URL"
            other_yt_id = extract_youtube_id(other_url)
            if yt_id == other_yt_id:
                if i >= graveyard_idx:
                    duplicates_archive.append(i+1)
                else:
                    other_status = other[col_map.get(sheet_keys["status_column"], -1)] if sheet_keys["status_column"] in col_map else ""
                    other_researcher = other[col_map.get(sheet_keys["researcher_column"], -1)] if sheet_keys["researcher_column"] in col_map else ""
                    duplicates_research.append((i+1, other_status, other_researcher))

        if duplicates_archive:
            duplicate_str = "search PWC Archive tab for further data"
        elif duplicates_research:
            dup_msgs = [f"Duplicate of row {r} [Status: {s}, Researcher: {u}]" for (r,s,u) in duplicates_research]
            duplicate_str = " ; ".join(dup_msgs)
        else:
            duplicate_str = ""

        worksheet.update_cell(idx+1, duplicate_col+1, duplicate_str)

        # Only update metadata if not duplicate in research and title is blank
        if (not duplicate_str or duplicate_str == "search PWC Archive tab for further data") and (not row[title_col]) and api_key and yt_id:
            meta = fetch_youtube_metadata(yt_id, api_key)
            if meta:
                worksheet.update_cell(idx+1, title_col+1, meta["title"])
                if user_col is not None: worksheet.update_cell(idx+1, user_col+1, meta["channel"])
                if date_col is not None: worksheet.update_cell(idx+1, date_col+1, meta["publishedAt"])
                if duration_col is not None: worksheet.update_cell(idx+1, duration_col+1, meta["duration"])
                updated_count += 1

    print(f"Done. {updated_count} rows updated.")

if __name__ == "__main__":
    main()
