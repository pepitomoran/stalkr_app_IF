from utils.youtube import extract_youtube_id

def find_duplicates(all_rows, col_map, target_url, target_row_idx, graveyard_idx):
    """
    Returns a dict:
      {
        'archive': [row_numbers],
        'research': [(row_number, researcher, status)]
      }
    """
    yt_id = extract_youtube_id(target_url)
    if not yt_id:
        return {'archive': [], 'research': []}
    duplicates_archive = []
    duplicates_research = []
    for i, other in enumerate(all_rows):
        if i == target_row_idx:
            continue
        other_url = other[col_map.get("URL", -1)]
        other_yt_id = extract_youtube_id(other_url)
        if yt_id == other_yt_id:
            if i >= graveyard_idx:
                duplicates_archive.append(i+1)
            else:
                other_status = other[col_map.get("Status", -1)] if "Status" in col_map else ""
                other_researcher = other[col_map.get("Researcher Name", -1)] if "Researcher Name" in col_map else ""
                duplicates_research.append((i+1, other_researcher, other_status))
    return {'archive': duplicates_archive, 'research': duplicates_research}
