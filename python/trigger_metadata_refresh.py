import requests

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw0Qaptp83Pb341P9J8_Aw-JJZNoLMk-ge6ABkKgE_MOm3d2B2PTTSHbx5ze6fWa-iE/exec"

def trigger_metadata_refresh():
    try:
        resp = requests.post(APPS_SCRIPT_URL, allow_redirects=True)
        if resp.ok and resp.text.strip() == "OK":
            print("✅ Google Sheet metadata refresh complete.")
        else:
            print("❌ Failed to trigger Apps Script!")
            print(f"Status code: {resp.status_code}")
            print(f"Response: {resp.text}")
    except Exception as e:
        print("❌ Error during request:", e)

if __name__ == "__main__":
    trigger_metadata_refresh()
