Project Setup
1. Python Environment
Create and activate the virtual environment:

bash
Copiar
Editar
python3 -m venv stalkr_env
source stalkr_env/bin/activate
Install required packages:

bash
Copiar
Editar
pip install -r requirements.txt
2. Configuration & Credentials
User config:
Path: config/user_config.json
How to generate:
Run:

bash
Copiar
Editar
python setup_user_config.py
and follow the prompts.
This stores your initials, JD2 device, download folder, and Sheet URL.

Org credentials:
Path:

config/org_secrets.json (MyJDownloader/org login)

private/stalkrorgsheetapi-<xxxx>.json (Google service account)
These are never committed—keep them safe.

3. Initial Connection Test (Optional)
You can test your config and device by running:

bash
Copiar
Editar
python setup_user_config.py
If all is set up, it will confirm paths and credentials.

4. Core Workflow
Run each stage from the project root in order:

Validate Sheet metadata

bash
Copiar
Editar
python sheet/sheet_metadata_validator.py
Updates/validates all YouTube links, fills in title/channel/duration, flags duplicates, and updates status columns in the Sheet.

Send new downloads to JDownloader2

bash
Copiar
Editar
python downloader/download_videos.py
Queues eligible videos from Sheet for download (best video, template name, etc).

Rename finished downloads and update status

bash
Copiar
Editar
python downloader/watch_and_rename.py
Renames each finished file with template, updates status column in Sheet.

5. Additional Notes
Always run scripts from the repo root (not from inside /downloader or /sheet) for clean imports.

Add new user/config/secrets only via setup scripts—never edit by hand.

If you see import errors, confirm you have __init__.py in all code folders and that you are running scripts with the root in PYTHONPATH.

6. Test & Utility Scripts
Run test and debug scripts from /tests as needed.

bash
Copiar
Editar
python tests/myjd_list_downloads.py
7. Privacy & Security
All sensitive config and keys are gitignored.

Never commit config/user_config.json, config/org_secrets.json, private/*.json, or any real tokens/keys.

8. For Org Admins/Devs
For service account setup, JD org login, and Sheet sharing, see docs/MASTER_PLAN_v3.md.

For onboarding and AI agent instructions, see docs/AI_AGENT_INSTRUCTIONS_ORG.md.

