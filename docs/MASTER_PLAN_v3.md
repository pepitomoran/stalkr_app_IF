# GOOGLE SHEETS x JDOWNLOADER ORGANIZATION VIDEO WORKFLOW — MASTER PLAN v3

---

## 0. OVERVIEW

A modular, Python-based, cross-platform workflow for a multi-user organization. All core logic (validation, metadata fetching, duplicate checking, Sheet updating, download/rename) is handled in Python, not Apps Script. The only Google-side setup is sharing the target Sheet with the service account.

* One Google Service Account & MyJDownloader login shared across org (not in code).
* Each user launches the Python app, sets their initials, device, and working folder (all remembered locally).
* All sheet validation, status, logging, and renaming is managed from Python.
* The system is robust, maintainable, and easy to update.

---

## 1. INITIAL ORG ACCOUNT SETUP (ONE-TIME)

### 1.1. Google Service Account

* Create a service account in org Google Cloud (no admin needed)
* Enable Sheets API
* Download JSON credentials and place in a safe, org-shared location
* Share the working GSheet (and any future ones) with the service account email

### 1.2. MyJDownloader Org Account

* Create one MyJDownloader org account (if not already)
* Each user logs in and adds their device to the org account
* All devices appear in the central account’s device list

### 1.3. Git & Repo Setup

* New repo: include `.gitignore` for credentials, `.env`, etc
* Save this master plan and AI agent instructions in the repo root
* Structure code for modularity

---

## 2. APP STAGES & WORKFLOW

### **Stage 1: First Launch & Connection**

* User launches app
* App checks for local user config (initials, last-used folder, device name)

  * If missing, prompts user and saves
* User pastes GSheet URL (required each launch)
* User selects tab to monitor (optional at launch, default to first tab)
* User picks download directory (remember across sessions)
* App checks Google credentials, MyJDownloader login, Sheet access, and device presence
* **Connect** button tests all above and gives feedback

---

### **Stage 2: Sheet Monitoring, Metadata Fetch, and Validation**

* App monitors (polls or manual “scan” button) for new YouTube links in the Sheet (target column)
* On new link:

  * Fetches metadata via YouTube API or `yt-dlp` (title, channel, duration, etc)
  * Checks for duplicate YouTube IDs in the Sheet (via Python, not Apps Script)
  * Updates Sheet: fills metadata, colors duplicate/invalid rows, logs status
  * Adds new columns as needed to right end (never overwrites)
  * If researcher initials differ from user, merges them (e.g., pm\_ms)
  * Status column: latest action, error/warning if any
* **All logic is Python-side for easy maintenance and cross-platform use**

---

### **Stage 3: Download and Rename**

* App (auto or on user click) sends URL to MyJDownloader device selected for this session

  * Default: download best video at 1080p (user can override per session)
  * User can choose to download audio/subs if desired; multi-file packages are put in a folder
  * Only video by default; if only one file, goes straight to target dir
* App monitors download status via API
* On completion:

  * Renames file using template ({date}*{youtubeid}*{user}\_{title}, all safe chars)
  * Removes or replaces weird chars, underscores for spaces
  * Moves file/folder to final directory if needed
  * Updates Sheet (status, filename, completion time)

---

### **Stage 4: Status, Logging, and Error Handling**

* App maintains in-app log/history of last N actions (renames, warnings, errors)
* Log is exportable (CSV, JSON, text)
* Each rename/download action is recorded (timestamp, old/new name, user, GDoc row, etc)
* Undo/restore is in future scope
* Sheet status column and color marks errors/duplicates/invalids
* User can view last action history and filter/search log

---

### **Stage 5: Batch Mode and Advanced Features**

* App can process all new links in batch or one-by-one
* Supports additional temporary columns (added to right, can be removed/hidden later)
* User can trigger “refresh” (manual Sheet re-sync) or set auto-poll interval
* App supports "show history" and (future) "undo last action"

---

## 3. CONFIG & DEPLOYMENT

* Hybrid config: org credentials + per-user local settings
* Credentials in safe path, never in repo
* Local config stores initials, last dir, device, etc
* All major actions, errors, and status in app and (where relevant) in Sheet

---

## 4. DEVELOPMENT PRACTICES

* Modular code: one script/module per function (Sheet access, downloader, GUI, validation, etc)
* Inline comments and docstrings throughout
* Each stage or major function gets a clear, testable script
* After each development stage: status report, update to README and master plan
* Encourage modular, maintainable, cross-platform Python codebase

---

## 5. USER/ORG STAGING

* Start with user/dev account, then migrate to org credentials
* Test with non-admin org account to find any privilege gaps
* Document any admin actions required for deployment

---

## 6. NEXT STEPS

1. Stage 1: Org service account & JDownloader setup, test Sheet/devices
2. Stage 2: Python app—connect, config, monitor Sheet, test fetch/validation
3. Stage 3: Download/rename pipeline, Sheet update
4. Stage 4: Logging, error handling, export
5. Stage 5: Batch ops, temp columns, admin scripts

---

**End of Master Plan v3**
