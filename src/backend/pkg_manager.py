# backend/pkg_manager.py

import os
from . import ps4_pkg_info, pkg_parser, hb_formatter

def process_pkg_file(pkg_path: str, icon_cache_dir: str):
    """Processes a single PKG file, returning its raw metadata."""
    print(f"\n-> Processing: {os.path.basename(pkg_path)}")
    
    info = ps4_pkg_info.get_ps4_pkg_info(pkg_path, generate_base64_icon=False)
    
    if not info or not info.param_sfo:
        print(f"  [!] Failed to process PKG: {os.path.basename(pkg_path)}")
        return None
        
    metadata = info.param_sfo
    
    icon_data = info.icon0_raw
    if icon_data:
        # Use CONTENT_ID for the icon filename for uniqueness
        content_id = metadata.get("CONTENT_ID", os.path.basename(pkg_path))
        icon_filename = f"{content_id}.png"
        icon_save_path = os.path.join(icon_cache_dir, icon_filename)
        os.makedirs(icon_cache_dir, exist_ok=True)
        with open(icon_save_path, 'wb') as f: f.write(icon_data)
        metadata['icon_url'] = f"/static/icons/{icon_filename}"
        print(f"  [+] Icon saved to {icon_filename}")
    else:
        metadata['icon_url'] = None
        print("  [-] No icon found for this package.")
        
    metadata['file_path'] = pkg_path
    metadata['SIZE'] = pkg_parser.convert_bytes(os.path.getsize(pkg_path))
    
    # Also determine and add the apptype during the initial scan
    metadata['apptype'] = hb_formatter.get_apptype_from_path(pkg_path)
    if metadata['apptype'] == 'Unknown' and metadata.get('CATEGORY', '').lower() in ('gp', 'gpc'):
        metadata['apptype'] = 'Patch'

    return metadata


def scan_directory(base_path):
    """
    Recursively scans for PKG files, processes them, and then runs 
    post-processing passes for DLC/patches and special theme pairing.
    """
    if not base_path or not os.path.isdir(base_path): return []
    
    print(f"\n[*] Starting recursive scan in directory: {base_path}")
    icon_cache_dir = os.path.abspath(os.path.join('frontend', 'static', 'icons'))
    
    all_packages = []
    for root, _, files in os.walk(base_path):
        for file in sorted(files): # sorted() is crucial for theme pairing
            if file.lower().endswith('.pkg'):
                full_path = os.path.join(root, file)
                package_data = process_pkg_file(full_path, icon_cache_dir)
                if package_data:
                    all_packages.append(package_data)

    print(f"\n[*] Initial scan complete. Found {len(all_packages)} packages.")
    
    # --- PASS 1: Post-processing for DLC/Patches ---
    print("[*] Starting post-processing pass for missing DLC/Patch info...")
    master_info = {}
    placeholder_titles = ['sample', 'test', 'dlc', 'patch', 'update']

    for pkg in all_packages:
        apptype = pkg.get("apptype", "Unknown")
        title_id = pkg.get("TITLE_ID")
        if apptype not in ["Patch", "DLC"] and title_id and pkg.get('icon_url') and pkg.get('TITLE', '').lower() not in placeholder_titles:
            if title_id not in master_info:
                master_info[title_id] = {'TITLE': pkg.get('TITLE'), 'icon_url': pkg.get('icon_url')}

    fixed_count = 0
    for pkg in all_packages:
        apptype = pkg.get("apptype", "Unknown")
        title_id = pkg.get("TITLE_ID")
        if apptype in ["Patch", "DLC"] and title_id in master_info:
            master = master_info[title_id]
            fixed = False

            # --- ICON FALLBACK LOGIC ---
            # First, check if the DLC/Patch is missing an icon. The initial scan sets
            # 'icon_url' to None if no icon was found in the PKG.
            if not pkg.get('icon_url'):
                # If it's missing, check if the parent game has an icon we can use.
                if master.get('icon_url'):
                    # Apply the parent game's icon as a fallback.
                    pkg['icon_url'] = master.get('icon_url')
                    fixed = True

            # --- TITLE FIX LOGIC (Remains the same) ---
            # If the title is a generic placeholder, use the parent's title.
            if pkg.get('TITLE', '').lower() in placeholder_titles:
                pkg['TITLE'] = master.get('TITLE')
                fixed = True
                
            if fixed: fixed_count += 1
    if fixed_count > 0: print(f"[+] Post-processing complete. Fixed info for {fixed_count} packages.")

    # --- PASS 2: Special post-processing for paired Themes ---
    print("[*] Starting post-processing pass for paired Themes...")
    # Create a lookup map for instant access to packages by their file path
    packages_by_path = {pkg['file_path']: pkg for pkg in all_packages}
    themes_fixed_count = 0
    
    # Iterate through all packages to find the "master" themes (_2.pkg)
    for master_theme in all_packages:
        # Check if it's a theme and ends with _2.pkg
        if master_theme.get('apptype') == 'Theme' and master_theme.get('file_path', '').endswith('_2.pkg'):
            
            # Construct the expected partner filename
            partner_path = master_theme['file_path'].replace('_2.pkg', '_1.pkg')
            
            # Find the partner package in our map
            partner_theme = packages_by_path.get(partner_path)
            
            if partner_theme:
                print(f"  [+] Found theme pair: {os.path.basename(partner_path)} & {os.path.basename(master_theme['file_path'])}")
                
                # 1. Clone metadata from master (_2) to partner (_1)
                partner_theme['TITLE'] = master_theme.get('TITLE', 'Untitled Theme')
                partner_theme['icon_url'] = master_theme.get('icon_url')
                partner_theme['TITLE_ID'] = master_theme.get('TITLE_ID')
                partner_theme['CONTENT_ID'] = master_theme.get('CONTENT_ID') # Important for icon cache consistency
                
                # 2. Append identifiers to the titles
                base_title = partner_theme['TITLE']
                partner_theme['TITLE'] = f"{base_title} 1"
                master_theme['TITLE'] = f"{base_title} 2"
                
                print(f"    -> Applied metadata and renamed to '{base_title} 1/2'")
                themes_fixed_count += 1

    if themes_fixed_count > 0: print(f"[+] Theme pairing complete. Processed {themes_fixed_count} pairs.")
        
    return all_packages