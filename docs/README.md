Stalkr App IF — YouTube Metadata + JDownloader Workflow
A workflow and toolkit for managing YouTube video downloads, metadata, and file renaming using Google Sheets, Python, and JDownloader2.

🚦 Project Structure
makefile
Copiar
Editar
stalkr_app_IF/
├── config/           # user and org config (gitignored)
├── docs/             # documentation, setup guides, AI instructions
├── downloader/       # all download and automation scripts
├── private/          # Google API/service account keys (gitignored)
├── sheet/            # all Google Sheets logic, metadata, and tools
├── tests/            # test and utility scripts
├── utils/            # filename generator and other shared utilities
├── requirements.txt  # Python dependencies
└── setup_user_config.py
🚀 Quick Start
Clone the repo and activate your Python environment:

bash
Copiar
Editar
git clone <repo_url>
cd stalkr_app_IF
source stalkr_env/bin/activate   # or your virtualenv
pip install -r requirements.txt
Initial setup
Configure your local user and device:

bash
Copiar
Editar
python setup_user_config.py
This will prompt for initials, JDownloader2 device path, download folder, and Google Sheet URL.
Your settings are saved in config/user_config.json (never tracked by git).

Validate/refresh Sheet metadata:

bash
Copiar
Editar
python sheet/sheet_metadata_validator.py
This ensures your Google Sheet is ready for automation.

Submit YouTube videos to JDownloader2:

bash
Copiar
Editar
python downloader/download_videos.py
Downloads are sent to the configured JDownloader device.

Rename completed downloads and update Sheet:

bash
Copiar
Editar
python downloader/watch_and_rename.py
Renames each file with the correct template, updates download status in your Sheet.

🔐 Configuration & Sensitive Data
User config: config/user_config.json

Org secrets: config/org_secrets.json

Google API/service account keys: private/stalkrorgsheetapi-XXXX.json

These files are protected in .gitignore. Never commit secrets or local configs!

📝 Workflow Overview
Sheet-driven: Google Sheet acts as the source of truth for YouTube links, channel, and metadata.

Automated download: Downloads handled by JDownloader2 via the MyJDownloader API.

Consistent naming: All files renamed using the INDEPENDENT FILMMAKER LABELS template.

Status tracking: Google Sheet is updated with download/rename status automatically.

Filename Template:
DESCRIPTION_yt_{youtubeid}_{channel}_#ncm{jobnumber}_#nr_{resolution}_{researcherinitials}_stalkr

Example:
DESCRIPTION_yt_abTTtyAPeN4_MBrass_#ncm1111_#nr_1080_pm_stalkr

🧩 Developer Notes
All package folders include __init__.py for clean imports.

Use absolute imports (from utils.filename_generator import ...).

Always run scripts from the repo root, or ensure PYTHONPATH includes project root.

🛡️ Security/Privacy
All configs and credentials are gitignored.

Never share or commit real config/user_config.json, config/org_secrets.json, or files in private/.

See .gitignore for details.

📋 Documentation
See docs/MASTER_PLAN_v3.md for master plan, docs/STATUS_REPORT.md for progress,
and docs/SETUP.md for step-by-step onboarding.