# GOOGLE SHEETS x JDOWNLOADER VIDEO WORKFLOW — MASTER PLAN

## GENERAL PROJECT SETUP AND DEVELOPMENT FLOW

1. **Set up your development environment:**

   - Install Python 3.x, Git, pip, and optionally VSCode or your favorite editor. Set up a virtual enviroment for the project
   - Install dependencies as needed (PySimpleGUI, requests, myjdapi, etc.).
   - (Mac users: Consider using Homebrew for package management.)

2. **Create a new repository on GitHub:**

   - Initialize a local git repo and connect it to GitHub.
   - Use `main` or `dev` as your default branch (as you prefer).
   - Add a `.gitignore` for Python, OS, and editor/IDE files.

3. **Organize your repo:**

   - Save this master plan as `MASTER_PLAN.md` or `README.md`.
   - Save AI agent instructions as a separate file (`AI_AGENT_INSTRUCTIONS.md`).

4. **Standardize collaboration and version control:**

   - Use feature branches (`feature/gui`, `feature/gdrive`, etc.) for modular development.
   - Commit and push after every meaningful step. Ask the AI for suggested commit messages if desired.

5. **Ask the AI for guidance at every step:**

   - Let the AI suggest when to create branches, commit, push, merge, or document changes.
   - Use the AI for troubleshooting, brainstorming, and workflow suggestions.

---

## 1. APPS SCRIPT WEB APP FOR METADATA REFRESH

- Objective: Allow the Apps Script to be triggered externally by Python, so the Google Sheet is always up to date before downloads/renaming.

### Steps:

1. Prepare your `syncYouTubeMetadata()` function (already written).
2. Wrap it with a web endpoint in Apps Script:
   ```javascript
   function doPost(e) {
     syncYouTubeMetadata();
     return ContentService.createTextOutput('OK');
   }
   ```
3. In the Apps Script editor, deploy as Web App:
   - Set "Anyone with the link" can access (or restrict as needed).
   - Copy the endpoint URL.
4. Test POSTing to the endpoint from Python or curl.

*Tips:* Use an auth token if needed for security. Add logs or return messages for more feedback.

---

## 2. PYTHON SCRIPT TO CALL THE APPS SCRIPT WEB ENDPOINT

- Objective: Trigger the Apps Script metadata refresh from Python (CLI or GUI).

### Steps:

1. Use the `requests` library to POST to the Apps Script endpoint:
   ```python
   import requests

   APPS_SCRIPT_URL = "https://script.google.com/macros/s/XXXXX/exec"

   def trigger_metadata_refresh():
       resp = requests.post(APPS_SCRIPT_URL)
       if resp.ok:
           print("Google Sheet metadata refresh complete.")
       else:
           print("Failed to trigger Apps Script!", resp.status_code, resp.text)
   ```
2. Integrate this call before starting any downloads or renaming steps.

---

## 3. PYTHON SCRIPT TO LIST AND CONTROL DOWNLOADS VIA MYJDOWNLOADER API

- Objective: Use MyJDownloader API to manage downloads, check status, and get filenames/paths.

### Steps:

1. Install the MyJDownloader Python client (`pip install myjdapi`).
2. Authenticate and connect:
   ```python
   import myjdapi

   jd = myjdapi.Myjdapi()
   jd.connect("youremail", "yourpassword")
   jd.update_devices()
   device = jd.get_device("YourJDownloaderDeviceName")
   ```
3. List/download/manage packages and links via API.
4. For finished downloads, get file info from the API.
5. Use Python (`os`, `shutil`) to move/rename files using GSheet data.
6. Clean up extra files and folders as needed.

*Tip:* Start with CLI/test, then move logic into GUI.

---

## 4. GUI PROTOTYPE FOR USER ACTIONS

- Objective: Simple cross-platform interface for all workflow actions.

### Steps:

1. Use PySimpleGUI (or similar) for rapid prototyping.
2. Core interface features:
   - Folder picker for downloads root.
   - Buttons for: Refresh Sheet Metadata, Scan Downloads, Download All, Rename/Organize, Preview Rename Plan.
   - Table or list to show downloads, metadata, proposed new filenames, statuses.
   - Inputs for researcher initials, contact/release status, keywords, description length slider, resolution override.
   - Output panel for logs, warnings, and confirmations.
3. Workflow:
   - User refreshes metadata (triggers Apps Script via Python).
   - Scans downloads, matches files to sheet, shows preview.
   - User reviews/overrides options as needed.
   - Executes move/rename/cleanup, gets summary.
4. Polish as needed (reveal in Finder/Explorer, help, export logs, etc.).

---

**End of Master Plan**

