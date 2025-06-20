PROJECT STATUS SUMMARY / HANDOVER (June 2025)
Project:
Google Sheets x JDownloader Org Video Workflow — Multi-user, Python-based, cross-platform automation for video metadata, download, and file management.

What’s been done:
Project approach decided:

All logic (validation, metadata, duplicate checks, status/warnings, renaming) will live in Python, not Apps Script.

Hybrid config: shared org credentials + per-user local config (initials, device, download dir, etc.).

Sheet is updated and monitored by the Python app, including all cell color/status, error handling, and column management.

Modular development, per-stage, with status reports and chat handover at each milestone.

Master plan v3 and org-specific AI agent instructions written, covering:

Org service account & MyJDownloader setup

Modular, testable code for sheet monitoring, metadata fetching, download, renaming, logging, and batch ops

Cross-platform (Mac/Windows) and user-friendly design

All configuration and credentials handled securely (never in repo)

Key UX/Workflow design choices:

Single service account and JDownloader org login for all users

Each user/device visible in MyJDownloader device list

GSheet URL and tab selected per session

“Connect” button to check all connections

Local user preferences (initials, folders) remembered, but editable

Status column and color feedback in the sheet

Full logging in-app with export/history/undo in future scope

Next:
Begin Stage 1:

Set up with org user (no admin), get the service account, enable API, register MyJDownloader device, and connect/test all basic app functions from scratch.

Stage 1 Status Report (for documentation/handover)
STAGE 1: Org Account & Sheet Setup — COMPLETED

Google Cloud project created and configured for the org.

Google Sheets API enabled.

Service account (org-sheets-service@stalkrorgsheetapi.iam.gserviceaccount.com) created and JSON credential stored at:
/Volumes/HENDRIX_SSD/stalkr_app_IF/private/stalkrorgsheetapi-4feb1ec20bbe.json

Target Google Sheet shared with the service account (editor access).

MyJDownloader org account established, with device JDownloader@pepitostalkr registered and visible in the account dashboard.

Project folder structure and Python environment are in place, ready for next development phase.

Key Notes:
No code/scripts run yet—just infrastructure and credential setup.

Local config file and standardized folder structure are recommended as the first Python development steps in Stage 2.

STAGE 2: Sheet Monitoring, Metadata, and Validation — COMPLETED

- CLI sheet validator fills/updates metadata using YouTube Data API
- Duplicates flagged and color-marked, warnings/notes written
- User-config-driven tab selection, secure key management
- All code committed, tested, and merged to main
- Per-user config, secure org secrets, connection validation
- Sheet tab selection, duplicate check, and YouTube metadata fetch/write-back complete
- All code reviewed, tested, merged to main

STAGE 3: Download, Rename, and Sheet Update — IN PROGRESS

- Download script will process valid YouTube links in the selected tab
- Uses MyJDownloader API for remote download control
- Filenames auto-generated using INDEPENDENT FILMMAKER LABELS template:
  `DESCRIPTION_yt_{youtubeid}_{channel}_#ncm{jobnumber}_#nr_{resolution}_{researcherinitials}_stalkr`
- Script updates the Sheet with download status, filename, and timestamp
- Future: expand to batch mode and real-time monitoring

---
Stage: Major Reorganization & Codebase Cleanup
What’s Complete
Project directory restructured:

Scripts are now organized into downloader/, sheet/, utils/, config/, private/, docs/, and tests/.

All pipeline scripts use centralized config and connection utilities.

Removed obsolete Google Apps Script files, junk/, and unnecessary cache/temp files.

All import paths and config references updated:

All scripts use absolute paths from project root for config, secrets, and private keys.

Added __init__.py to each code package directory for clean imports.

.gitignore updated:

Now protects all sensitive config, secrets, private tokens, and Python cache.

Test coverage:

All core scripts (setup_user_config.py, sheet_metadata_validator.py, download_videos.py, watch_and_rename.py) tested and working in new structure.

Utility scripts and test tools moved to tests/.

Current Pipeline
Run setup_user_config.py
Ensures user config, JD2 app path, and Sheet credentials are set.

Run sheet/sheet_metadata_validator.py
Validates and populates Google Sheet metadata.

Run downloader/download_videos.py
Sends new download jobs to JDownloader2.

Run downloader/watch_and_rename.py
Renames finished downloads using standard template and updates Sheet status.

Known Issues / Next Steps
Reorg branch ready for PR or merge.

All scripts tested from repo root and working.

Unit tests and automated test coverage can be expanded.

Consider further documentation update in README.md for onboarding new users.

Potential feature roadmap:

Add logging/error history

Improve Sheet status feedback (e.g., color)

Add batch/loop/watcher modes

Project is stable and ready for further feature development or team onboarding.

# STATUS REPORT / HANDOVER (Batch & Watcher Mode Kickoff — June 2025)

**Logging:**

* Unified `logprint` and summary logging implemented in all key scripts.
* Script start/end, errors, warnings, and summaries now visible in terminal and `/logs/`.

**Sheet Status:**

* Status column enhancements planned for next phase.

**Batch/Catch-up & Watcher Mode (Planned/Next):**

* Activation begins with a “catch-up” pass: finds and processes all new/unprocessed rows assigned to current user, prompts for confirmation, fetches metadata/downloads, updates logs and status columns.
* After catch-up, script enters watcher mode: polls the Sheet at intervals, monitors for new rows for the user, and processes/downloads as they appear.
* Strict per-user logic: each user processes only their rows (by `Researcher Name` or unique ID in config).
* Polling approach for reliability (not webhooks/Apps Script events).

**Git:**

* Next features will be developed in a new branch: `feature/batch-watcher-mode`.

**Ready for:**

* CLI scaffold of batch/catch-up and watcher loop, with full logging and Sheet status support.
