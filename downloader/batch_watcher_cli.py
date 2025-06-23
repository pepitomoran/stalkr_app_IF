import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import argparse
import time
from utils.logger import logprint, log_event
from utils.jd_connection_utils import load_user_config, ensure_jd_running_and_connected
from sheet.sheet_tools import (
    get_sheet,
    add_missing_columns,
    find_graveyard_row,
    filter_research_rows,
    ensure_column,
    normalize
)
# Temporary YouTube util, swap for utils/youtube.py when ready
import re
def extract_youtube_id(url):
    if not url or not isinstance(url, str):
        return None
    match = re.search(r'(?:v=|youtu\.be/|/embed/|/shorts/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

def per_row_validator(worksheet, rows, idx, col_map, graveyard_idx):
    """Calls duplicate logic, writes to 'Duplicate' column, returns duplicate flag."""
    url = rows[idx][col_map["URL"]]
    duplicate_col = col_map["Duplicate"]

    yt_id = extract_youtube_id(url)
    if not yt_id:
        worksheet.update_cell(idx+1, duplicate_col+1, "Non-YouTube link")
        return "Non-YouTube link"

    duplicates_research = []
    duplicates_archive = []
    for i, other in enumerate(rows):
        if i == idx:
            continue
        other_url = other[col_map["URL"]]
        other_yt_id = extract_youtube_id(other_url)
        if yt_id == other_yt_id:
            if i >= graveyard_idx:
                duplicates_archive.append(i+1)
            else:
                other_status = other[col_map.get("Status", -1)] if "Status" in col_map else ""
                other_researcher = other[col_map.get("Researcher Name", -1)] if "Researcher Name" in col_map else ""
                duplicates_research.append((i+1, other_status, other_researcher))

    if duplicates_archive:
        duplicate_str = "search PWC Archive tab for further data"
    elif duplicates_research:
        dup_msgs = [f"Duplicate of row {r} [Status: {s}, Researcher: {u}]" for (r,s,u) in duplicates_research]
        duplicate_str = " ; ".join(dup_msgs)
    else:
        duplicate_str = ""

    worksheet.update_cell(idx+1, duplicate_col+1, duplicate_str)
    return duplicate_str

def main():
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")
    ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")
    SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "private", "stalkrorgsheetapi-4feb1ec20bbe.json")
    REQUIRED_COLS = ["Researcher Name", "URL", "Title", "User", "Duplicate", "Status"]
    ARCHIVE_KEYS = [
        "clip id", "clip title", "vimeo author's name", "source (vimeo, yt, flickr, etc)"
    ]

    parser = argparse.ArgumentParser(description="Batch & Watcher CLI for Stalkr Sheet+JD2 Workflow (modular)")
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

    # Sheet setup
    worksheet, header, col_map, rows = get_sheet(cfg, SERVICE_ACCOUNT_PATH)
    header, col_map = add_missing_columns(worksheet, header, REQUIRED_COLS)
    graveyard_idx = find_graveyard_row(rows, ARCHIVE_KEYS)
    if graveyard_idx is None or graveyard_idx == len(rows):
        print("⚠️ Graveyard/archive section not found (no repeated archive-style header row).")
        cont = input("Proceed with all rows as research? [y/N]: ").strip().lower()
        if cont != "y":
            print("Exiting.")
            return
        graveyard_idx = len(rows)

    user_initials = normalize(cfg["initials"])
    research_row_indices = filter_research_rows(rows, col_map, user_initials, graveyard_idx)

    def fetch_unprocessed_rows():
        # Refresh after any changes
        rows = worksheet.get_all_values()
        col_map = {col: idx for idx, col in enumerate(rows[0])}
        unprocessed = []
        for idx in research_row_indices:
            row = rows[idx]
            status = row[col_map["Status"]].strip().lower() if "Status" in col_map and row[col_map["Status"]] else ""
            if status == "" or status.startswith("todo"):
                unprocessed.append((idx, row))
        return unprocessed

    def process_row(idx, row, hold=False):
        # Run validator logic for this row and get duplicate string
        duplicate_str = per_row_validator(worksheet, rows, idx, col_map, graveyard_idx)
        title = row[col_map["Title"]]
        url = row[col_map["URL"]]

        if "Non-YouTube" in duplicate_str:
            logprint(
                f"Skipped row {idx}: Non-YouTube link.",
                action="skip_non_youtube",
                status="info",
                sheet_row=idx,
                extra_info={"title": title, "url": url}
            )
            return "skipped"

        if "search PWC Archive" in duplicate_str:
            logprint(
                f"Row {idx}: Duplicate found in Graveyard/archive, proceeding with download.",
                action="duplicate_in_graveyard",
                status="warning",
                sheet_row=idx,
                extra_info={"title": title, "url": url}
            )
            # Proceed

        elif "Duplicate of row" in duplicate_str:
            logprint(
                f"Skipped row {idx}: Duplicate found in research. Info: {duplicate_str}",
                action="skip_duplicate_research",
                status="warning",
                sheet_row=idx,
                extra_info={"title": title, "url": url, "duplicate_info": duplicate_str}
            )
            return "skipped"

        # If here, ready to send to JD2 (unless --hold)
        log_event(
            script="batch_watcher_cli.py",
            action="row_processing_started",
            status="info",
            sheet_row=idx,
            extra_info={"title": title, "url": url, "user": user_initials}
        )
        if hold:
            logprint(
                f"[HOLD] Would send row {idx} to JD2: {title} | {url}",
                action="hold_no_download",
                status="info",
                sheet_row=idx,
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
                sheet_row=idx,
                extra_info={"title": title, "url": url, "user": user_initials}
            )
            worksheet.update_cell(idx+1, col_map["Status"]+1, "Sent to JD2")
            logprint(
                f"✅ Sent to JD2: {title} (row {idx})",
                action="status_updated",
                status="success",
                sheet_row=idx,
                extra_info={"title": title, "status": "Sent to JD2"}
            )
            return "sent"
        except Exception as e:
            log_event(
                script="batch_watcher_cli.py",
                action="send_to_jd2_failed",
                status="error",
                sheet_row=idx,
                error_message=str(e),
                extra_info={"title": title, "url": url}
            )
            worksheet.update_cell(idx+1, col_map["Status"]+1, "ERROR: " + str(e))
            logprint(
                f"❌ Error sending row {idx} to JD2: {title} | {e}",
                action="status_error",
                status="error",
                sheet_row=idx,
                error_message=str(e)
            )
            return "error"

    # BATCH MODE
    unprocessed = fetch_unprocessed_rows()
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
    else:
        confirm = input("Proceed to process these rows? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Batch mode cancelled by user.")
            log_event(
                script="batch_watcher_cli.py",
                action="batch_cancelled",
                status="info"
            )
            return
        processed, errors, holds, skipped = 0, 0, 0, 0
        for idx, row in unprocessed:
            result = process_row(idx, row, hold=args.hold)
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

    # WATCHER MODE
    print("\nEntering watcher mode. Polling for new rows every", args.interval, "seconds. Ctrl+C to exit.")
    already_seen = set()
    try:
        while True:
            worksheet, header, col_map, rows = get_sheet(cfg, SERVICE_ACCOUNT_PATH)
            research_row_indices = filter_research_rows(rows, col_map, user_initials, graveyard_idx)
            unprocessed = []
            for idx in research_row_indices:
                row = rows[idx]
                status = row[col_map["Status"]].strip().lower() if "Status" in col_map and row[col_map["Status"]] else ""
                if status == "" or status.startswith("todo"):
                    unprocessed.append((idx, row))
            new_rows = [(idx, row) for idx, row in unprocessed if idx not in already_seen]
            if new_rows:
                print(f"\n[Watcher] {len(new_rows)} new row(s) found for you!")
                processed, errors, holds, skipped = 0, 0, 0, 0
                for idx, row in new_rows:
                    print(f"  Row {idx}: {row[col_map.get('Title')]} | URL: {row[col_map.get('URL')]}")
                    result = process_row(idx, row, hold=args.hold)
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
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nWatcher stopped by user. Exiting.")
        log_event(
            script="batch_watcher_cli.py",
            action="watcher_stopped",
            status="info"
        )

if __name__ == "__main__":
    main()
