# backend/hb_formatter.py (with simplified function signature)

import os
import math
import re

BASE_IMAGE_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def _format_bytes(size_bytes, decimals=2):
    if size_bytes == 0: return "0 Bytes"
    k = 1024
    dm = decimals if decimals >= 0 else 0
    sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    i = math.floor(math.log(size_bytes) / math.log(k))
    return f"{round(size_bytes / math.pow(k, i), dm)} {sizes[i]}"

def get_apptype_from_path(file_path: str) -> str:
    directory = os.path.dirname(file_path).lower()
    categories = {
        'themes': 'Theme',
        'dlc': 'DLC',
        'patches': 'Patch',
        'apps': 'App',
        'games': 'HB Game',
        'other': 'Other'
    }

    for keyword, label in categories.items():
        if os.path.sep + keyword in directory:
            return label

    return "Unknown"

# --- CORRECTED FUNCTION DEFINITION ---
def create_hb_store_item(pkg_data: dict, base_uri: str, pid: int = 1) -> dict:
    """
    Translates a package data dictionary into the HB-Store JSON format.
    """
    title_id = pkg_data.get("TITLE_ID", "N/A")
    content_id = pkg_data.get("CONTENT_ID", title_id)
    apptype = pkg_data.get("apptype", "Unknown")
    version = pkg_data.get("APP_VER") if apptype == "Patch" else pkg_data.get("VERSION", "01.00")
    
    # --- CHANGE HERE: Use the 'pid' (unique index) for the download link ---
    package_url = f"{base_uri}/api/download/{pid}"
    
    icon_url = pkg_data.get("icon_url", "")
    file_size = pkg_data.get("SIZE", "N/A")

    item = {
        "pid": pid,
        "id": title_id,
        "name": pkg_data.get("TITLE", "No Title"),
        "desc": "",
        "image": f"{base_uri}{icon_url}" if icon_url else "",
        "package": package_url, # This will now be unique
        "version": version,
        "picpath": f"/user/app/NPXS39041/storedata/{content_id}.png",
        "desc_1": "",
        "desc_2": "",
        "ReviewStars": "Custom Rating",
        "Size": file_size,
        "Author": "HB-Store CDN",
        "apptype": apptype,
        "pv": "5.05+",
        "main_icon_path": f"{base_uri}{icon_url}" if icon_url else "",
        "main_menu_pic": f"/user/app/NPXS39041/storedata/{content_id}.png",
        "releaseddate": "2024-01-01",
    }
    return item