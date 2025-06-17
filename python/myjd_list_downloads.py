import myjdapi
import getpass

# Credentials (for real projects, use env variables or a config file)
MYJD_EMAIL = "pepitomoran@gmail.com"
MYJD_DEVICE = "JDownloader@pepitomoran"

# Prompt for password at runtime for security
MYJD_PASSWORD = getpass.getpass("Enter MyJDownloader password: ")

jd = myjdapi.Myjdapi()
print("Connecting to MyJDownloader...")
jd.connect(MYJD_EMAIL, MYJD_PASSWORD)
jd.update_devices()
device = jd.get_device(MYJD_DEVICE)
if not device:
    print("Device not found! Check device name.")
    exit(1)

print(f"Connected to device: {MYJD_DEVICE}")

# List all packages in Downloadlist
dl_packages = device.downloads.query_packages()
print("\nCurrent Download Packages:")
for pkg in dl_packages:
    print(f" - {pkg['name']} | Status: {pkg['status']} | Files: {pkg['childCount']}")
