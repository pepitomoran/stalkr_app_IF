#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import argparse
import time
from utils.logger import logprint, log_event
from utils.jd_connection_utils import load_user_config, ensure_jd_running_and_connected
from sheet.sheet_tools import get_sheet, update_status_by_title, normalize

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")
ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")
SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "private", "stalkrorgsheetapi-4feb1ec20bbe.json")

def fetch_unprocessed_rows(cfg, header, rows, col_map):
    """Find rows for user with blank or TODO status."""
    researcher_col = col_map.get("Researcher Name")
    status_col = col_map.get("Status")
    url_col = col_map.get("URL")
    user_initials = normalize(cfg["initials"])
    result = []
    for idx, row in enumerate(rows[1:], start=2):
        # Robust: skip if URL missing, status not blank or TODO
        url = row[url_col] if url_col is not None else ""
        if not url or not url.startswith("http"):
            continue
        researcher = normalize(row[researcher_col]) if researcher_col is not None else ""
        status = row[status_col].strip() if status_col is not None and row[status_col] else ""
        if researcher == user_initials and (status == "" or status.upper().startswith("TODO")):
            result.append((idx, row))
    return result

def process_row(cfg, device, worksheet, header, col_map, row_idx, row, hold=False):
    title = row[col_map.get("Title")]
    url = row[col_map.get("URL")]
    user_initials = cfg["initials"]
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
        # Mark in Sheet as "Hold" for visibility, or skip Sheet update if preferred
        update_status_by_title(cfg, SERVICE_ACCOUNT_PATH, title, "Hold")
        return "hold"
    # Try to send to JD2
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
        # Update status in Sheet
        update_status_by_title(cfg, SERVICE_ACCOUNT_PATH, title, "Sent to JD2")
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
        update_status_by_title(cfg, SERVICE_ACCOUNT_PATH, title, "ERROR: " + str(e))
        logprint(
            f"❌ Error sending row {row_idx} to JD2: {title} | {e}",
            action="status_error",
            status="error",
            sheet_row=row_idx,
            error_message=str(e)
        )
        return "error"

def batch_mode(cfg, device, worksheet, header, rows, col_map, hold=False):
    unprocessed = fetch_unprocessed_rows(cfg, header, rows, col_map)
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
    processed, errors, holds = 0, 0, 0
    for idx, row in unprocessed:
        result = process_row(cfg, device, worksheet, header, col_map, idx, row, hold=hold)
        if result == "sent":
            processed += 1
        elif result == "hold":
            holds += 1
        else:
            errors += 1
    log_event(
        script="batch_watcher_cli.py",
        action="batch_complete",
        status="success" if errors == 0 else "partial",
        extra_info={"rows_processed": processed, "errors": errors, "holds": holds}
    )
    print(f"\nBatch summary: {processed} sent, {holds} held, {errors} errors.")
    return unprocessed

def watcher_mode(cfg, device, worksheet, header, col_map, poll_interval=60, hold=False):
    print("\nEntering watcher mode. Polling for new rows every", poll_interval, "seconds. Ctrl+C to exit.")
    already_seen = set()
    try:
        while True:
            rows = worksheet.get_all_values()
            unprocessed = fetch_unprocessed_rows(cfg, header, rows, col_map)
            new_rows = [(i, r) for i, r in unprocessed if i not in already_seen]
            if new_rows:
                print(f"\n[Watcher] {len(new_rows)} new row(s) found for you!")
                processed, errors, holds = 0, 0, 0
                for idx, row in new_rows:
                    print(f"  Row {idx}: {row[col_map.get('Title')]} | URL: {row[col_map.get('URL')]}")
                    result = process_row(cfg, device, worksheet, header, col_map, idx, row, hold=hold)
                    already_seen.add(idx)
                    if result == "sent":
                        processed += 1
                    elif result == "hold":
                        holds += 1
                    else:
                        errors += 1
                log_event(
                    script="batch_watcher_cli.py",
                    action="watcher_found",
                    status="success" if errors == 0 else "partial",
                    extra_info={"rows_processed": processed, "errors": errors, "holds": holds}
                )
                print(f"[Watcher] Summary: {processed} sent, {holds} held, {errors} errors.")
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
    parser = argparse.ArgumentParser(description="Batch & Watcher CLI for Stalkr Sheet+JD2 Workflow")
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

    # Connect to Sheet
    worksheet, header, col_map, rows = get_sheet(cfg, SERVICE_ACCOUNT_PATH)

    # Run batch mode
    batch_mode(cfg, device, worksheet, header, rows, col_map, hold=args.hold)

    # Always start watcher mode after batch
    watcher_mode(cfg, device, worksheet, header, col_map, poll_interval=args.interval, hold=args.hold)

if __name__ == "__main__":
    main()
