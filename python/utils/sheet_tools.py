import gspread
from google.oauth2.service_account import Credentials

def get_sheet(cfg, service_account_path):
    """Return (worksheet, header, col_map, all_rows)."""
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
    col_map = {key: idx for idx, key in enumerate(header)}
    return worksheet, header, col_map, rows

def ensure_column(worksheet, header, colname):
    """Add a column to the sheet if not present. Return column index."""
    if colname in header:
        return header.index(colname)
    worksheet.update_cell(1, len(header) + 1, colname)
    return len(header)  # 0-based index

def normalize(s):
    return ''.join(c.lower() for c in str(s) if c.isalnum())

def update_status_by_title(cfg, service_account_path, title, status, status_colname="Status"):
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
    """Return metadata dict for the row matching the title."""
    worksheet, header, col_map, rows = get_sheet(cfg, service_account_path)
    title_col = col_map.get("Title")
    if title_col is None:
        raise Exception("No 'Title' column found in sheet.")

    for row in rows[1:]:
        sheet_title = row[title_col]
        if normalize(sheet_title) == normalize(title):
            # Adapt field names as needed for your sheet:
            return {
                "youtube_id": row[col_map.get("URL", -1)].split("v=")[-1][:11],
                "channel": row[col_map.get("User", -1)],
                "job_number": row[col_map.get("Job Number", -1)],
                "resolution": row[col_map.get("resolution", -1)] if "resolution" in col_map else "1080",
                "researcher_initials": row[col_map.get("Researcher Name", -1)] if "Researcher Name" in col_map else cfg["initials"],
                "description": "DESCRIPTION"
            }
    return None
