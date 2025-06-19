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
    print("🔍 Scanning for completed downloads to rename...")
    packages = device.downloads.query_packages()
    renamed = 0
    for pkg in packages:
        if pkg.get("status") != "Finished":
            continue
        pkg_name = pkg.get("name")
        possible_title = pkg_name  # This is what JD used
        fname = fuzzy_find_file(cfg["download_dir"], possible_title)
        if not fname:
            print(f"⚠️ No file found in {cfg['download_dir']} matching title: {possible_title}")
            continue

        # Get full metadata from Sheet via utility (now centralized)
        rowdata = get_metadata_by_title(cfg, SERVICE_ACCOUNT_PATH, possible_title)
        if not rowdata:
            print(f"⚠️ No Sheet row found for title: {possible_title}")
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
            print(f"ℹ️ File already named: {fname}")
            continue

        try:
            shutil.move(source, target)
            print(f"✅ Renamed: {fname} → {os.path.basename(target)}")
            renamed += 1
            # Centralized status update (via utility)
            update_status_by_title(cfg, SERVICE_ACCOUNT_PATH, possible_title, "Renamed")
        except Exception as e:
            print(f"❌ Failed to rename: {e}")
    print(f"\n✅ Done. {renamed} file(s) renamed.")

def main():
    # Use the centralized config loader (can also import from setup)
    cfg = load_user_config(USER_CONFIG_PATH)
    ok, device = ensure_jd_running_and_connected(cfg, USER_CONFIG_PATH, ORG_SECRETS_PATH)
    if not ok or not device:
        print("❌ Could not connect to MyJDownloader. Exiting.")
        return

    rename_finished_packages(cfg, device)

if __name__ == "__main__":
    main()
