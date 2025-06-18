# Stalkr App IF — YouTube Metadata + JDownloader Workflow

A workflow and toolkit for managing YouTube video downloads, metadata, and renaming using Google Sheets, Apps Script, Python, and JDownloader2.

## Structure

- `google_apps_script/`: All Google Apps Script code and config.
- `python/`: Python scripts for automation and integration.
- `docs/`: Project documentation, setup guides, AI instructions.
- `image_refs/`: Reference images/screenshots.

See `docs/master_plan.md` for the master plan.


## Quick Start

- Clone the repo and see `docs/SETUP.md` for setup instructions.
- Requires Python 3.8+, Google account, and JDownloader2 with MyJDownloader API access.

## Configuration & Sensitive Data

- Per-user config: `python/config/user_config.json` (not tracked in git)
- Org credentials/secrets: `private/org_secrets.json`, plus Google service account file(s)
- Logs: `logs/`

> Never commit secrets or user configs! Always keep your `private/` and `python/config/` folders in your `.gitignore`.


## Setup & First Use

1. **Configure your local user settings**  
   Run:
python python/setup_user_config.py

markdown
Copiar
Editar
This will prompt for initials, JDownloader device name, download folder, and Google Sheet URL. Your settings are saved in `python/config/user_config.json` (never tracked by git).

2. **Check all connections**  
Run:
python python/connection_check.py

sql
Copiar
Editar
This script verifies Google Sheet and MyJDownloader connections using your local config and org credentials from `private/org_secrets.json`.

> Make sure your service account credentials and org_secrets.json are present in the `private/` folder.  
> Never commit real credentials or user configs—these files are listed in `.gitignore`.