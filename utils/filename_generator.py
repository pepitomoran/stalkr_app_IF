# filename_generator.py
import re

def sanitize_for_filename(text):
    if not text:
        return ''
    safe = re.sub(r'[^\w\-]+', '_', text)
    safe = re.sub(r'_+', '_', safe)
    return safe.strip('_')

def generate_ifl_filename(
    youtube_id,
    channel,
    job_number,
    resolution,
    researcher_initials,
    description='DESCRIPTION'
):
    description = sanitize_for_filename(description)
    channel = sanitize_for_filename(channel)
    researcher_initials = sanitize_for_filename(researcher_initials)
    job_number = str(job_number)
    resolution = sanitize_for_filename(str(resolution))

    return (
        f"{description}_yt_{youtube_id}_{channel}_"
        f"#ncm{job_number}_#nr_{resolution}_{researcher_initials}_stalkr"
    )
