#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import argparse
import time
from utils.logger import logprint, log_event
from utils.jd_connection_utils import load_user_config, ensure_jd_running_and_connected
from sheet.sheet_metadata_validator import get_sheet, find_graveyard_row, validate_row, load_user_config as v_load_user_config, load_org_secrets
from sheet.sheet_tools import normalize

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")
ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")
SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "private", "stalkrorgsheetapi-4feb1ec20bbe.json")

def fetch_unprocessed_rows(cfg, header, rows, col_map, graveyard_idx):
    """Find research rows for user with blank or TODO status, before graveyard."""
    researcher_col = col_map.get("Researcher Name")
    status_col = col_map.get("Status")
    url_col = col_map.get("URL")
    user_initials = normalize(cfg["initials"])
    result = []
    for idx, row in enumerate(rows[1:graveyard_idx], start=1):  # Only up to graveyard
        url = row[url_col] if url_col is not None else ""
        if not url or not url.startswith("http"):
            continue
        researcher = normalize(row[researcher_col]) if researcher_col is not None else ""
        status = row[status_col].strip() if status_col is not None and row[status_col] else ""
        if researcher == user_initials and (status == "" or status.upper().startswith("TODO")):
            result.append((idx, row))
    return result

def process_row(cfg, device, worksheet, header, col_map, row_idx, row, graveyard_idx, api_key, hold=False):
    # --- Run per-row validator (flags duplicate/non-yt, updates metadata) ---
    res = validate_row(worksheet, row_idx, col_map, worksheet.get_all_values(), graveyard_idx, api_key)
    duplicate_info = res.get("duplicate", "")
    non_youtube = res.get("non_youtube", False)

    title = row[col_map.get("Title")]
    url = row[col_map.get("URL")]
    user_initials = cfg["initials"]

    # Decision logic
    if non_youtube:
        logprint(
            f"Skipped row {row_idx}: Non-YouTube link.",
            action="skip_non_youtube",
            status="info",
            sheet_row=row_idx,
            extra_info={"title": title, "url": url}
        )
        return "skipped"

    if "search PWC Archive" in duplicate_info:
        logprint(
            f"Row {row_idx}: Duplicate found in Graveyard/archive, proceeding with download.",
            action="duplicate_in_graveyard",
            status="warning",
            sheet_row=row_idx,
            extra_info={"title": title, "url": url}
        )
        # Proceed, but mark duplicate in sheet already handled by validator

    elif "Duplicate of row" in duplicate_info:
        logprint(
            f"Skipped row {row_idx}: Duplicate found in research. Info: {duplicate_info}",
            action="skip_duplicate_research",
            status="warning",
            sheet_row=row_idx,
            extra_info={"title": title, "url": url, "duplicate_info": duplicate_info}
        )
        return "skipped"

    # If here, row is assigned to user, has no critical duplicate, and is YouTube
    log_event(
        script="batch_watcher_cli.py",
        action="row_processing_started",
        status="info",
        sheet_row=row_idx,
        extra_info={"title": title, "url": url, "user": user_initials}
    )
    if hold:
        logprint(
            f"[HOLD] Would send row {row_idx} to JD2: {title} | {url}",
            action="hold_no_download",
            status="info",
            sheet_row=row_idx,
            extra_info={"title": title, "url": url}
        )
        return "hold"
    try:
        device.linkgrabber.add_links([{
            "autostart": True,
            "links": url,
            "packageName": title,
            "destinationFolder": cfg["download_dir"]
        }])
        log_event(
            script="batch_watcher_cli.py",
            action="sent_to_jd2",
            status="success",
            sheet_row=row_idx,
            extra_info={"title": title, "url": url, "user": user_initials}
        )
        worksheet.update_cell(row_idx+1, col_map["Status"]+1, "Sent to JD2")
        logprint(
            f"✅ Sent to JD2: {title} (row {row_idx})",
            action="status_updated",
            status="success",
            sheet_row=row_idx,
            extra_info={"title": title, "status": "Sent to JD2"}
        )
        return "sent"
    except Exception as e:
        log_event(
            script="batch_watcher_cli.py",
            action="send_to_jd2_failed",
            status="error",
            sheet_row=row_idx,
            error_message=str(e),
            extra_info={"title": title, "url": url}
        )
        worksheet.update_cell(row_idx+1, col_map["Status"]+1, "ERROR: " + str(e))
        logprint(
            f"❌ Error sending row {row_idx} to JD2: {title} | {e}",
            action="status_error",
            status="error",
            sheet_row=row_idx,
            error_message=str(e)
        )
        return "error"

def batch_mode(cfg, device, worksheet, header, rows, col_map, graveyard_idx, api_key, hold=False):
    unprocessed = fetch_unprocessed_rows(cfg, header, rows, col_map, graveyard_idx)
    print(f"\nBatch mode: {len(unprocessed)} unprocessed row(s) found for user '{cfg['initials']}'")
    for idx, row in unprocessed[:5]:
        print(f"  Row {idx}: {row[col_map.get('Title')]} | URL: {row[col_map.get('URL')]}")
    if len(unprocessed) > 5:
        print(f"  ...and {len(unprocessed)-5} more.")
    if not unprocessed:
        print("✅ Nothing to process in batch mode.")
        log_event(
            script="batch_watcher_cli.py",
            action="batch_complete",
            status="info",
            extra_info={"rows_processed": 0}
        )
        return []
    confirm = input("Proceed to process these rows? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Batch mode cancelled by user.")
        log_event(
            script="batch_watcher_cli.py",
            action="batch_cancelled",
            status="info"
        )
        return []
    processed, errors, holds, skipped = 0, 0, 0, 0
    for idx, row in unprocessed:
        result = process_row(cfg, device, worksheet, header, col_map, idx, row, graveyard_idx, api_key, hold=hold)
        if result == "sent":
            processed += 1
        elif result == "hold":
            holds += 1
        elif result == "skipped":
            skipped += 1
        else:
            errors += 1
    log_event(
        script="batch_watcher_cli.py",
        action="batch_complete",
        status="success" if errors == 0 else "partial",
        extra_info={"rows_processed": processed, "errors": errors, "holds": holds, "skipped": skipped}
    )
    print(f"\nBatch summary: {processed} sent, {holds} held, {skipped} skipped, {errors} errors.")
    return unprocessed

def watcher_mode(cfg, device, worksheet, header, col_map, graveyard_idx, api_key, poll_interval=60, hold=False):
    print("\nEntering watcher mode. Polling for new rows every", poll_interval, "seconds. Ctrl+C to exit.")
    already_seen = set()
    try:
        while True:
            rows = worksheet.get_all_values()
            unprocessed = fetch_unprocessed_rows(cfg, header, rows, col_map, graveyard_idx)
            new_rows = [(i, r) for i, r in unprocessed if i not in already_seen]
            if new_rows:
                print(f"\n[Watcher] {len(new_rows)} new row(s) found for you!")
                processed, errors, holds, skipped = 0, 0, 0, 0
                for idx, row in new_rows:
                    print(f"  Row {idx}: {row[col_map.get('Title')]} | URL: {row[col_map.get('URL')]}")
                    result = process_row(cfg, device, worksheet, header, col_map, idx, row, graveyard_idx, api_key, hold=hold)
                    already_seen.add(idx)
                    if result == "sent":
                        processed += 1
                    elif result == "hold":
                        holds += 1
                    elif result == "skipped":
                        skipped += 1
                    else:
                        errors += 1
                log_event(
                    script="batch_watcher_cli.py",
                    action="watcher_found",
                    status="success" if errors == 0 else "partial",
                    extra_info={"rows_processed": processed, "errors": errors, "holds": holds, "skipped": skipped}
                )
                print(f"[Watcher] Summary: {processed} sent, {holds} held, {skipped} skipped, {errors} errors.")
            else:
                print(".", end="", flush=True)
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\nWatcher stopped by user. Exiting.")
        log_event(
            script="batch_watcher_cli.py",
            action="watcher_stopped",
            status="info"
        )

def main():
    parser = argparse.ArgumentParser(description="Batch & Watcher CLI for Stalkr Sheet+JD2 Workflow (with Graveyard & duplicates logic)")
    parser.add_argument("--hold", action="store_true", help="Dry-run: do NOT send downloads, just log (default: off)")
    parser.add_argument("--interval", type=int, default=60, help="Watcher poll interval in seconds (default: 60)")
    args = parser.parse_args()

    # Load config and check JD2 connection
    cfg = load_user_config(USER_CONFIG_PATH)
    ok, device = ensure_jd_running_and_connected(cfg, USER_CONFIG_PATH, ORG_SECRETS_PATH)
    if not ok or not device:
        print("❌ JDownloader connection failed. Exiting.")
        log_event(
            script="batch_watcher_cli.py",
            action="jd_connect_fail",
            status="error"
        )
        return

    # Connect to Sheet and find Graveyard
    worksheet = get_sheet(cfg)
    rows = worksheet.get_all_values()
    header = rows[0]
    col_map = {name: idx for idx, name in enumerate(header)}
    header_keys = ["Researcher Name", "URL", "Title", "User"]
    graveyard_idx = find_graveyard_row(rows, header_keys)
    if graveyard_idx is None:
        print("⚠️ Graveyard/archive section not found (no repeated header row).")
        cont = input("Proceed with all rows as research? [y/N]: ").strip().lower()
        if cont != "y":
            print("Exiting.")
            return
        graveyard_idx = len(rows)

    secrets = load_org_secrets()
    if not secrets or not secrets.get("youtube_api_key"):
        print("❌ YouTube API key missing.")
        return
    api_key = secrets["youtube_api_key"]

    # Run batch mode
    batch_mode(cfg, device, worksheet, header, rows, col_map, graveyard_idx, api_key, hold=args.hold)

    # Always start watcher mode after batch
    watcher_mode(cfg, device, worksheet, header, col_map, graveyard_idx, api_key, poll_interval=args.interval, hold=args.hold)

if __name__ == "__main__":
    main()
