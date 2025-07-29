# backend/pkg_manager.py

import os
import difflib
from . import ps4_pkg_info, pkg_parser, hb_formatter, pss_scraper

# --- THE NEW, SIMPLER ALIAS SYSTEM ---
# The KEY is the EXACT, RAW title from the SFO as seen in the server logs.
# The VALUE is the precise search term you want to use instead.
# EXAMPLES: "Raw Name" (provided by pkg): "Alias" (Name in Playstation Store)
RAW_TITLE_ALIASES = {
    "HITMAN 3": "HITMAN World of Assassination",
    "Minecraft: PlayStation®4 Edition": "Minecraft",
    "Outlast Trinity: Outlast & Outlast Whistleblower": "Outlast Trinity"
}

def _clean_title(title: str) -> str:
    """
    Helper function to normalize titles for comparison.
    """
    title = title.replace('®', '').replace('™', '').replace(':', ' ').replace('&', ' ')
    title = title.replace('.', ' ').replace('_', ' ')
    # Collapse all whitespace into single spaces for clean comparison
    return ' '.join(title.lower().split())

def process_pkg_file(pkg_path: str, icon_cache_dir: str):
    """Processes a single PKG file, returning its raw metadata."""
    print(f"\n-> Processing: {os.path.basename(pkg_path)}")
    
    info = ps4_pkg_info.get_ps4_pkg_info(pkg_path, generate_base64_icon=False)
    
    if not info or not info.param_sfo:
        print(f"  [!] Failed to process PKG: {os.path.basename(pkg_path)}"); return None
        
    metadata = info.param_sfo
    # ... (icon and metadata setup is the same) ...
    icon_data = info.icon0_raw
    if icon_data:
        base_pkg_filename = os.path.basename(pkg_path); icon_filename = f"{os.path.splitext(base_pkg_filename)[0]}.png"
        icon_save_path = os.path.join(icon_cache_dir, icon_filename); os.makedirs(icon_cache_dir, exist_ok=True)
        with open(icon_save_path, 'wb') as f: f.write(icon_data)
        metadata['icon_url'] = f"/static/icons/{icon_filename}"; print(f"  [+] Icon saved to {icon_filename}")
    else:
        metadata['icon_url'] = None; print("  [-] No icon found for this package.")
    metadata['file_path'] = pkg_path; metadata['SIZE'] = pkg_parser.convert_bytes(os.path.getsize(pkg_path))
    metadata['apptype'] = hb_formatter.get_apptype_from_path(pkg_path)
    if metadata['apptype'] == 'Unknown' and metadata.get('CATEGORY', '').lower() in ('gp', 'gpc'): metadata['apptype'] = 'Patch'

    # --- FINAL: Scraper with the CORRECT Alias System ---
    if metadata.get('apptype') in ['HB Game', 'App'] and 'TITLE_ID' in metadata and 'TITLE' in metadata:
        sfo_title_id = metadata['TITLE_ID']
        sfo_content_id = metadata.get('CONTENT_ID', 'N/A')
        sfo_title_raw = metadata['TITLE'] # The original, uncleaned title
        
        print(f"  [*] Attempting to fetch store data for '{sfo_title_raw}' (Content ID: {sfo_content_id})...")
        
        # --- NEW LOGIC: Check for a RAW alias FIRST ---
        if sfo_title_raw in RAW_TITLE_ALIASES:
            search_title = RAW_TITLE_ALIASES[sfo_title_raw]
            print(f"    [*] Using RAW title alias: '{sfo_title_raw}' -> '{search_title}'")
        else:
            # If no raw alias, fall back to cleaning the title for the search
            search_title = _clean_title(sfo_title_raw)
        
        try:
            search_results = pss_scraper.search_playstation_store(search_title)
            if not search_results:
                print("    [-] No results returned from PlayStation Store.")
                return metadata

            best_match = None; match_type = ""

            # 1. Primary Method: Exact CUSA ID match
            for game in search_results:
                if game.get('cusa_id') == sfo_title_id:
                    best_match = game; match_type = "Exact CUSA ID"; break
            
            # 2. Fallback Method: Fuzzy title match
            if not best_match:
                highest_score = 0.0
                # The search_title is now either a clean alias or a cleaned SFO title
                clean_search_title = _clean_title(search_title)
                
                for game in search_results:
                    store_title_clean = _clean_title(game.get('name', ''))
                    score = difflib.SequenceMatcher(None, clean_search_title, store_title_clean).ratio()
                    if score > highest_score:
                        highest_score = score; best_match = game
                if highest_score > 0.85:
                    match_type = f"Fuzzy Title ({int(highest_score * 100)}%)"
                else:
                    best_match = None

            # 3. Process the result
            if best_match:
                print(f"    [+] Match Found! (Game: '{best_match['name']}', Type: {match_type}). Fetching details...")
                details = pss_scraper.get_game_details(best_match['link'])
                metadata['description'] = details.get('description', 'Description not found.')
                metadata['rating'] = details.get('rating', 'N/A')
                metadata['publisher'] = details.get('publisher', 'N/A')
                metadata['release_date'] = details.get('release_date', '2024-01-01')
                print(f"    [+] Rating: {metadata['rating']}, Author: {metadata['publisher']}, Description/Date: Loaded, Release: {metadata['release_date']}.")
            else:
                print("    [-] Could not find a confident match in search results.")

        except Exception as e:
            print(f"    [!] Scraper failed: {e}")

    return metadata

# The scan_directory function and all post-processing loops remain completely unchanged.
def scan_directory(base_path):
    # ... (no changes here) ...
    if not base_path or not os.path.isdir(base_path): return []
    print(f"\n[*] Starting recursive scan in directory: {base_path}"); icon_cache_dir = os.path.abspath(os.path.join('frontend', 'static', 'icons')); all_packages = []
    for root, _, files in os.walk(base_path):
        for file in sorted(files):
            if file.lower().endswith('.pkg'):
                full_path = os.path.join(root, file); package_data = process_pkg_file(full_path, icon_cache_dir)
                if package_data: all_packages.append(package_data)
    print(f"\n[*] Initial scan complete. Found {len(all_packages)} packages."); print("[*] Starting post-processing pass for missing DLC/Patch info.")
    master_info = {}
    placeholder_titles = ['sample', 'test', 'dlc', 'patch', 'update']
    for pkg in all_packages:
        apptype = pkg.get("apptype", "Unknown"); title_id = pkg.get("TITLE_ID")
        if apptype not in ["Patch", "DLC"] and title_id and pkg.get('TITLE', '').lower() not in placeholder_titles:
            if title_id not in master_info: master_info[title_id] = { 'TITLE': pkg.get('TITLE'), 'icon_url': pkg.get('icon_url'), 'publisher': pkg.get('publisher'), 'release_date': pkg.get('release_date'), 'rating': pkg.get('rating') }
    fixed_count = 0
    for pkg in all_packages:
        apptype = pkg.get("apptype", "Unknown"); title_id = pkg.get("TITLE_ID")
        if apptype in ["Patch", "DLC"] and title_id in master_info:
            master = master_info[title_id]; fixed = False
            if not pkg.get('icon_url') and master.get('icon_url'): pkg['icon_url'] = master.get('icon_url'); fixed = True
            if pkg.get('TITLE', '').lower() in placeholder_titles: pkg['TITLE'] = master.get('TITLE'); fixed = True
            if not pkg.get('publisher') and master.get('publisher'): pkg['publisher'] = master.get('publisher'); fixed = True
            if not pkg.get('release_date') and master.get('release_date'): pkg['release_date'] = master.get('release_date'); fixed = True
            if not pkg.get('rating') and master.get('rating'): pkg['rating'] = master.get('rating'); fixed = True
            if fixed: fixed_count += 1
    if fixed_count > 0: print(f"[+] Post-processing complete. Fixed info for {fixed_count} packages.")
    print("[*] Starting post-processing pass for paired Themes..."); packages_by_path = {pkg['file_path']: pkg for pkg in all_packages}; themes_fixed_count = 0
    for master_theme in all_packages:
        if master_theme.get('apptype') == 'Theme' and master_theme.get('file_path', '').endswith('_2.pkg'):
            partner_path = master_theme['file_path'].replace('_2.pkg', '_1.pkg'); partner_theme = packages_by_path.get(partner_path)
            if partner_theme:
                print(f"  [+] Found theme pair: {os.path.basename(partner_path)} & {os.path.basename(master_theme['file_path'])}"); partner_theme['TITLE'] = master_theme.get('TITLE', 'Untitled Theme'); partner_theme['icon_url'] = master_theme.get('icon_url'); partner_theme['TITLE_ID'] = master_theme.get('TITLE_ID'); partner_theme['CONTENT_ID'] = master_theme.get('CONTENT_ID')
                base_title = partner_theme['TITLE']; partner_theme['TITLE'] = f"{base_title} 1"; master_theme['TITLE'] = f"{base_title} 2"
                print(f"    -> Applied metadata and renamed to '{base_title} 1/2'"); themes_fixed_count += 1
    if themes_fixed_count > 0: print(f"[+] Theme pairing complete. Processed {themes_fixed_count} pairs.")
    return all_packages
