# Project Setup

## Python Environment

1. Create and activate the virtual environment:
    ```bash
    python3 -m venv stalkr_env
    source stalkr_env/bin/activate
    ```

2. Install required packages:
    ```bash
    pip install -r requirements.txt
    ```

## Local User Config

- **Config path:** `python/config/user_config.json`
- **How to generate:** Run `python python/setup_user_config.py` and follow prompts.
- **What it stores:** Your initials, device name, download folder, and default Sheet URL.

## Org Credentials

- **Path:** `private/org_secrets.json` and service account json.
- **How to use:** These are automatically loaded by `connection_check.py` and other scripts. Do not commit these files.

## Connection Test

- **How to test:** Run `python python/connection_check.py`
- This will check both Google Sheets and MyJDownloader access, reporting status for both.

## Stage 3: Download & Rename Script Setup

**Requirements:**
- All prior config steps completed (user_config, org_secrets, credentials, MyJDownloader setup)
- Install/confirm the following Python packages:

pip install myjdapi

- Download destination folder must be set in `user_config.json`
- Ensure JDownloader is running and logged in to org account on your device

**How to Use:**
- Run the Stage 3 script (`python/download_and_rename.py`) from the project root
- The script will download, rename, and update the Sheet for each eligible video, using the current naming convention

**To update the filename template or logic:**  
Edit the filename generator function in the Stage 3 script (`download_and_rename.py`)