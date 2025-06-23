import gspread
import os
import json
from google.oauth2.service_account import Credentials

# --- Config Loader for Sheet Keys ---

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")

def load_sheet_keys():
    with open(ORG_SECRETS_PATH, "r") as f:
        secrets = json.load(f)
    return secrets["sheet_keys"]

SHEET_KEYS = load_sheet_keys()  # Loaded once per script execution

def normalize(text):
    if not isinstance(text, str):
        return ""
    return text.strip().lower()

def get_column_map(header, config_keys=None):
    """
    Returns {colname: idx} map for all header fields, normalized.
    If config_keys (list) given, only maps canonical names.
    """
    header_norm = [normalize(col) for col in header]
    col_map = {}
    if config_keys:
        for key in config_keys:
            idx = next((i for i, h in enumerate(header_norm) if h == normalize(key)), None)
            if idx is not None:
                col_map[key] = idx
    else:
        for idx, col in enumerate(header):
            col_map[col] = idx
    return col_map

def ensure_column(worksheet, header, colname):
    """
    Ensure colname exists at right end; returns index in header.
    Expands the sheet if needed.
    """
    if colname in header:
        return header.index(colname)
    if len(header) >= worksheet.col_count:
        worksheet.add_cols(1)
    worksheet.update_cell(1, len(header) + 1, colname)
    header.append(colname)
    return len(header) - 1  # 0-based

def add_missing_columns(worksheet, header, required_cols):
    """
    Ensure all required_cols are present as columns; add at right if not.
    Returns updated header and col_map.
    """
    for col in required_cols:
        if col not in header:
            ensure_column(worksheet, header, col)
    col_map = get_column_map(header)
    return header, col_map

def get_sheet(cfg, service_account_path):
    """
    Returns worksheet, header (list), col_map, rows (list of lists).
    Uses config-driven sheet keys.
    """
    creds = Credentials.from_service_account_file(service_account_path, scopes=[
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    sheet = client.open_by_url(cfg["sheet_url"])
    worksheet = sheet.worksheet(cfg["last_tab"])
    rows = worksheet.get_all_values()
    header = rows[0]
    # Use research_keys and any additional ones needed
    all_required = SHEET_KEYS["research_keys"] + [SHEET_KEYS["duplicate_column"], SHEET_KEYS["status_column"]]
    header, col_map = add_missing_columns(worksheet, header, all_required)
    return worksheet, header, col_map, rows

def find_graveyard_row(rows, archive_keys=None):
    """
    Returns the row index (0-based) of the Graveyard header (archive region).
    Uses config-driven archive_keys (default), matches at least 3.
    """
    if archive_keys is None:
        archive_keys = SHEET_KEYS["archive_keys"]
    min_matches = 3
    found = 0
    for idx, row in enumerate(rows):
        row_norm = [normalize(cell) for cell in row]
        matches = sum(1 for key in archive_keys if any(key in cell for cell in row_norm))
        if matches >= min_matches:
            found += 1
            if found == 2:
                return idx
    return len(rows)

def filter_research_rows(rows, col_map, user_initials, graveyard_idx):
    """
    Returns indices of rows above graveyard assigned to user_initials.
    Comparison is case-insensitive/stripped. Uses config-driven researcher_column.
    """
    researcher_col = col_map.get(SHEET_KEYS["researcher_column"])
    result = []
    if researcher_col is None:
        return result
    for idx, row in enumerate(rows[1:graveyard_idx], start=1):
        researcher = normalize(row[researcher_col])
        if researcher == normalize(user_initials):
            result.append(idx)
    return result

def update_status_by_title(cfg, service_account_path, title, status, status_colname=None):
    """
    Update the status of the row with given title (case-insensitive, stripped).
    Uses config-driven status_column if not given.
    """
    if status_colname is None:
        status_colname = SHEET_KEYS["status_column"]
    worksheet, header, col_map, rows = get_sheet(cfg, service_account_path)
    status_col = ensure_column(worksheet, header, status_colname)
    title_col = col_map.get("Title")
    if title_col is None:
        raise Exception("No 'Title' column found in sheet.")
    for idx, row in enumerate(rows[1:], start=2):
        sheet_title = row[title_col]
        if normalize(sheet_title) == normalize(title):
            worksheet.update_cell(idx, status_col + 1, status)
            print(f"📝 Updated status for row {idx}: {status}")
            return True
    print(f"⚠️ Could not find row for title '{title}' to update status.")
    return False

def get_metadata_by_title(cfg, service_account_path, title):
    worksheet, header, col_map, rows = get_sheet(cfg, service_account_path)
    title_col = col_map.get("Title")
    if title_col is None:
        raise Exception("No 'Title' column found in sheet.")
    for row in rows[1:]:
        sheet_title = row[title_col]
        if normalize(sheet_title) == normalize(title):
            return {
                "youtube_id": row[col_map.get("URL", -1)].split("v=")[-1][:11],
                "channel": row[col_map.get("User", -1)],
                "job_number": row[col_map.get("Job Number", -1)],
                "resolution": row[col_map.get("resolution", -1)] if "resolution" in col_map else "1080",
                "researcher_initials": row[col_map.get(SHEET_KEYS["researcher_column"], -1)] if SHEET_KEYS["researcher_column"] in col_map else "",
                "description": "DESCRIPTION"
            }
    return None
