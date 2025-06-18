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
