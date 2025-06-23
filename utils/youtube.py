import re

YOUTUBE_PATTERNS = [
    r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com|m\.youtube\.com)/",
    r"(?:v=|youtu\.be/|/embed/|/shorts/)([0-9A-Za-z_-]{11})"
]

def is_youtube_url(url):
    if not url or not isinstance(url, str):
        return False
    return bool(re.search(YOUTUBE_PATTERNS[0], url))

def extract_youtube_id(url):
    if not url or not isinstance(url, str):
        return None
    # Extract 11-char ID from any known pattern
    match = re.search(YOUTUBE_PATTERNS[1], url)
    return match.group(1) if match else None

def detect_source(url):
    if is_youtube_url(url):
        return "YouTube"
    # Future: add detection for Vimeo, Flickr, etc.
    # Example:
    # if "vimeo.com" in url: return "Vimeo"
    return "Unknown"
