#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
from utils.logger import logprint, log_event
from utils.jd_connection_utils import load_user_config, ensure_jd_running_and_connected
from sheet.sheet_tools import get_sheet, normalize

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")
ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")
SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "private", "stalkrorgsheetapi-4feb1ec20bbe.json")

def fetch_unprocessed_rows(cfg, header, rows, col_map):
    # Define unprocessed as blank status or status == 'TODO'
    researcher_col = col_map.get("Researcher Name")
    status_col = col_map.get("Status")
    user_initials = normalize(cfg["initials"])
    result = []
    for idx, row in enumerate(rows[1:], start=2):
        researcher = normalize(row[researcher_col])
        status = row[status_col].strip() if status_col is not None and row[status_col] else ""
        if researcher == user_initials and (status == "" or status.upper().startswith("TODO")):
            result.append((idx, row))
    return result

def batch_mode(cfg, worksheet, header, rows, col_map):
    unprocessed = fetch_unprocessed_rows(cfg, header, rows, col_map)
    print(f"\nBatch mode: {len(unprocessed)} unprocessed row(s) found for user '{cfg['initials']}'")
    for idx, row in unprocessed[:5]:
        print(f"  Row {idx}: {row[col_map.get('Title')]} | URL: {row[col_map.get('URL')]}")
    if len(unprocessed) > 5:
        print(f"  ...and {len(unprocessed)-5} more.")
    if not unprocessed:
        print("✅ Nothing to process in batch mode.")
        return []
    confirm = input("Proceed to process these rows? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Batch mode cancelled by user.")
        return []
    print("Processing (stub) — rows would be handled here.")
    logprint(
        f"Batch confirmed for {len(unprocessed)} rows.",
        action="batch_start",
        status="info",
        extra_info={"rows": [i for i, _ in unprocessed]}
    )
    # (Stub: actual processing not yet implemented)
    return unprocessed

def watcher_mode(cfg, worksheet, header, col_map, poll_interval=60):
    print("\nEntering watcher mode. Polling for new rows every", poll_interval, "seconds. Ctrl+C to exit.")
    already_seen = set()
    while True:
        rows = worksheet.get_all_values()
        unprocessed = fetch_unprocessed_rows(cfg, header, rows, col_map)
        new_rows = [(i, r) for i, r in unprocessed if i not in already_seen]
        if new_rows:
            print(f"\n[Watcher] {len(new_rows)} new row(s) found for you!")
            for idx, row in new_rows:
                print(f"  Row {idx}: {row[col_map.get('Title')]} | URL: {row[col_map.get('URL')]}")
                already_seen.add(idx)
            # (Stub: actual per-row processing would go here)
            logprint(
                f"Watcher: found {len(new_rows)} new rows.",
                action="watcher_new_rows",
                status="info",
                extra_info={"rows": [i for i, _ in new_rows]}
            )
        else:
            print(".", end="", flush=True)
        time.sleep(poll_interval)

def main():
    # Load user config and check JD2 connection
    cfg = load_user_config(USER_CONFIG_PATH)
    ok, device = ensure_jd_running_and_connected(cfg, USER_CONFIG_PATH, ORG_SECRETS_PATH)
    if not ok:
        print("❌ JDownloader connection failed. Exiting.")
        return
    # Connect to Sheet
    worksheet, header, col_map, rows = get_sheet(cfg, SERVICE_ACCOUNT_PATH)
    # Run batch mode
    batch_mode(cfg, worksheet, header, rows, col_map)
    # Always start watcher mode after batch
    try:
        watcher_mode(cfg, worksheet, header, col_map)
    except KeyboardInterrupt:
        print("\nWatcher stopped by user. Exiting.")

if __name__ == "__main__":
    main()
