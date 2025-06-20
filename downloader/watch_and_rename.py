import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import shutil
from utils.filename_generator import generate_ifl_filename
from sheet.sheet_tools import (
    get_metadata_by_title,
    update_status_by_title,
    normalize
)
from utils.jd_connection_utils import (
    ensure_jd_running_and_connected,
    load_user_config
)
from utils.logger import logprint, log_script

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
USER_CONFIG_PATH = os.path.join(BASE_DIR, "config", "user_config.json")
ORG_SECRETS_PATH = os.path.join(BASE_DIR, "config", "org_secrets.json")
SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "private", "stalkrorgsheetapi-4feb1ec20bbe.json")

def fuzzy_find_file(directory, title):
    n_title = normalize(title)
    for fname in os.listdir(directory):
        base, ext = os.path.splitext(fname)
        if n_title and n_title in normalize(base):
            return fname
    return None

def rename_finished_packages(cfg, device):
    logprint("🔍 Scanning for completed downloads to rename...", action="start_scan", status="info")
    packages = device.downloads.query_packages()
    renamed = 0
    errors = 0
    not_found = 0
    sheet_not_found = 0

    for pkg in packages:
        if pkg.get("status") != "Finished":
            continue
        pkg_name = pkg.get("name")
        possible_title = pkg_name
        fname = fuzzy_find_file(cfg["download_dir"], possible_title)
        if not fname:
            logprint(
                f"⚠️ No file found in {cfg['download_dir']} matching title: {possible_title}",
                action="file_not_found",
                status="warning",
                extra_info={"pkg_name": pkg_name}
            )
            not_found += 1
            continue

        rowdata = get_metadata_by_title(cfg, SERVICE_ACCOUNT_PATH, possible_title)
        if not rowdata:
            logprint(
                f"⚠️ No Sheet row found for title: {possible_title}",
                action="sheet_row_not_found",
                status="warning",
                extra_info={"title": possible_title}
            )
            sheet_not_found += 1
            continue

        template_filename = generate_ifl_filename(
            youtube_id=rowdata["youtube_id"],
            channel=rowdata["channel"],
            job_number=rowdata["job_number"],
            resolution=rowdata["resolution"],
            researcher_initials=rowdata["researcher_initials"],
            description=rowdata["description"]
        )

        ext = os.path.splitext(fname)[1]
        source = os.path.join(cfg["download_dir"], fname)
        target = os.path.join(cfg["download_dir"], f"{template_filename}{ext}")

        if source == target:
            logprint(
                f"ℹ️ File already named: {fname}",
                action="already_renamed",
                status="info",
                extra_info={"filename": fname}
            )
            continue

        try:
            shutil.move(source, target)
            logprint(
                f"✅ Renamed: {fname} → {os.path.basename(target)}",
                action="renamed",
                status="success",
                extra_info={"old": fname, "new": os.path.basename(target)}
            )
            renamed += 1
            update_status_by_title(cfg, SERVICE_ACCOUNT_PATH, possible_title, "Renamed")
        except Exception as e:
            logprint(
                f"❌ Failed to rename {fname}: {e}",
                action="rename_failed",
                status="error",
                error_message=str(e),
                extra_info={"filename": fname}
            )
            errors += 1

    # Summary log
    logprint(
        f"\nSummary: {renamed} files renamed, {not_found} not found, {sheet_not_found} sheet rows not found, {errors} errors.",
        action="summary",
        status="info",
        extra_info={
            "renamed": renamed,
            "not_found": not_found,
            "sheet_not_found": sheet_not_found,
            "errors": errors
        }
    )

@log_script
def main():
    cfg = load_user_config(USER_CONFIG_PATH)
    ok, device = ensure_jd_running_and_connected(cfg, USER_CONFIG_PATH, ORG_SECRETS_PATH)
    if not ok or not device:
        logprint("❌ Could not connect to MyJDownloader. Exiting.", action="jd_connect_fail", status="error")
        return

    rename_finished_packages(cfg, device)

if __name__ == "__main__":
    main()
