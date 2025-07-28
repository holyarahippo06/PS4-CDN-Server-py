# backend/hb_formatter.py
import os, math, re
BASE_IMAGE_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
def _format_bytes(size_bytes, decimals=2):
    if size_bytes == 0: return "0 Bytes"
    k = 1024; dm = decimals if decimals >= 0 else 0; sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    i = math.floor(math.log(size_bytes) / math.log(k)); return f"{round(size_bytes / math.pow(k, i), dm)} {sizes[i]}"
def get_apptype_from_path(file_path: str) -> str:
    directory = os.path.dirname(file_path).lower(); categories = { 'themes': 'Theme', 'dlc': 'DLC', 'patches': 'Patch', 'apps': 'App', 'games': 'HB Game', 'other': 'Other' }
    for keyword, label in categories.items():
        if os.path.sep + keyword in directory: return label
    return "Unknown"

# --- NEW: Helper function to intelligently chunk the description text ---
def _chunk_description(text: str, line_length: int = 150) -> list:
    """Splits a long string into a list of lines of a max length without splitting words."""
    if not text:
        return [""]
        
    lines = []
    # Replace existing newlines with spaces to start fresh
    words = text.replace('\n', ' ').split()
    
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 > line_length:
            lines.append(current_line)
            current_line = word
        else:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
    if current_line:
        lines.append(current_line)
        
    return lines

def create_hb_store_item(pkg_data: dict, base_uri: str, pid: int = 1) -> dict:
    title_id = pkg_data.get("TITLE_ID", "N/A"); content_id = pkg_data.get("CONTENT_ID", title_id)
    apptype = pkg_data.get("apptype", "Unknown")
    version = pkg_data.get("APP_VER") if apptype == "Patch" else pkg_data.get("VERSION", "01.00")
    package_url = f"{base_uri}/api/download/{pid}"; icon_url = pkg_data.get("icon_url", ""); file_size = pkg_data.get("SIZE", "N/A")
    
    # --- MODIFIED: Use the new chunking helper ---
    full_description = pkg_data.get("description", "")
    desc_lines = _chunk_description(full_description)
    
    desc_line_1 = desc_lines[0] if len(desc_lines) > 0 else ""
    desc_line_2 = desc_lines[1] if len(desc_lines) > 1 else ""
    desc_line_3 = desc_lines[2] if len(desc_lines) > 2 else ""

    item = {
        "pid": pid, "id": title_id, "name": pkg_data.get("TITLE", "No Title"),
        "desc": desc_line_1, # Line 1
        "image": f"{base_uri}{icon_url}" if icon_url else "",
        "package": package_url, "version": version,
        "picpath": f"/user/app/NPXS39041/storedata/{content_id}.png",
        "desc_1": desc_line_2, # Line 2
        "desc_2": desc_line_3, # Line 3
        "ReviewStars": pkg_data.get("rating", "N/A"),
        "Size": file_size,
        "Author": pkg_data.get("publisher", "HB-Store CDN"),
        "apptype": apptype, "pv": "5.05+",
        "main_icon_path": f"{base_uri}{icon_url}" if icon_url else "",
        "main_menu_pic": f"/user/app/NPXS39041/storedata/{content_id}.png",
        "releaseddate": pkg_data.get("release_date", "2024-01-01"),
    }
    return item
