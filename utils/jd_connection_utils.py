import os
import subprocess
import json
import time
import platform
import myjdapi

def detect_os():
    plat = platform.system().lower()
    if "darwin" in plat or "mac" in plat:
        return "mac"
    if "windows" in plat:
        return "win"
    if "linux" in plat:
        return "linux"
    return "unknown"

def get_default_jd_path():
    os_type = detect_os()
    if os_type == "mac":
        return "/Applications/JDownloader2.app"
    elif os_type == "win":
        return r"C:\Program Files\JDownloader2\JDownloader2.exe"
    else:
        return "/path/to/JDownloader2"

def load_user_config(user_config_path):
    if not os.path.exists(user_config_path):
        return {}
    with open(user_config_path, "r") as f:
        return json.load(f)

def save_user_config(cfg, user_config_path):
    with open(user_config_path, "w") as f:
        json.dump(cfg, f, indent=2)

def prompt_for_jd_path():
    os_type = detect_os()
    if os_type == "mac":
        hint = "/Applications/JDownloader2.app"
    elif os_type == "win":
        hint = r"C:\Program Files\JDownloader2\JDownloader2.exe"
    else:
        hint = "/path/to/JDownloader2"
    while True:
        path = input(f"Enter full path to JDownloader2 ({hint}): ").strip()
        if path and os.path.exists(path):
            return path
        print("❌ That path does not exist. Please try again.")

def is_jdownloader_running():
    os_type = detect_os()
    if os_type == "mac" or os_type == "linux":
        result = subprocess.run(["pgrep", "-f", "JDownloader"], capture_output=True)
        return result.returncode == 0
    elif os_type == "win":
        # Try 'tasklist' (not super robust, but works for default JD2 install)
        result = subprocess.run('tasklist', capture_output=True, text=True)
        return "JDownloader2.exe" in result.stdout
    else:
        return False

def launch_jdownloader(jd_app_path):
    os_type = detect_os()
    try:
        if os_type == "mac":
            subprocess.Popen(["open", jd_app_path])
        elif os_type == "win":
            subprocess.Popen([jd_app_path], shell=True)
        elif os_type == "linux":
            subprocess.Popen(["xdg-open", jd_app_path])
        else:
            print("❌ Unknown OS, cannot launch JDownloader automatically.")
            return False
        print("🚀 JDownloader2 launch command sent.")
        return True
    except Exception as e:
        print(f"❌ Could not launch JDownloader2: {e}")
        return False

def check_jd_api_connection(cfg, org_secrets_path):
    if not os.path.exists(org_secrets_path):
        print(f"❌ org_secrets.json not found at {org_secrets_path}")
        return False, None
    with open(org_secrets_path, "r") as f:
        secrets = json.load(f)
    try:
        jd = myjdapi.Myjdapi()
        jd.connect(secrets["myjd_email"], secrets["myjd_password"])
        jd.update_devices()
        device = jd.get_device(cfg["device"])
        if device:
            print(f"✅ Connected to MyJDownloader device: {cfg['device']}")
            return True, device
        else:
            print(f"❌ Device '{cfg['device']}' not found in your MyJDownloader account.")
            return False, None
    except Exception as e:
        print(f"❌ MyJDownloader connection failed: {e}")
        return False, None

def ensure_jd_running_and_connected(cfg, user_config_path, org_secrets_path):
    # Check JD app path in config or prompt
    if not cfg.get("jd_app_path"):
        print("No JDownloader2 app path found in user config.")
        jd_app_path = prompt_for_jd_path()
        cfg["jd_app_path"] = jd_app_path
        save_user_config(cfg, user_config_path)
    else:
        jd_app_path = cfg["jd_app_path"]

    # Check if JD is running
    if is_jdownloader_running():
        print("✅ JDownloader2 is already running.")
    else:
        print("JDownloader2 is not running. Attempting to launch...")
        launched = launch_jdownloader(jd_app_path)
        if not launched:
            print("\n⚠️  Please open JDownloader2 manually from:")
            print(f"   {jd_app_path}")
            print("If not installed, download from: https://jdownloader.org/download/index")
            input("Press ENTER after JDownloader2 is running and logged in with the org account...")
        else:
            # Give JD a few seconds to finish launching
            time.sleep(10)

    # Try connecting to JD API (repeat if needed)
    for attempt in range(3):
        ok, device = check_jd_api_connection(cfg, org_secrets_path)
        if ok:
            return True, device
        print("Waiting 10 seconds before retrying...")
        time.sleep(10)

    print("\n❌ Could not connect to JDownloader2. Please ensure it is running and logged in with the org account, then try again.")
    return False, None

# Example usage
if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    user_config_path = os.path.join(BASE_DIR, "python", "config", "user_config.json")
    org_secrets_path = os.path.join(BASE_DIR, "private", "org_secrets.json")
    cfg = load_user_config(user_config_path)
    ensure_jd_running_and_connected(cfg, user_config_path, org_secrets_path)
