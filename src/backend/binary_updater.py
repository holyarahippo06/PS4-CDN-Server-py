# backend/binary_updater.py

import os
import requests

# The official GitHub API endpoint for the HB-Store releases
GITHUB_API_URL = "https://api.github.com/repos/LightningMods/PS4-Store/releases"

# The specific files the PS4 app checks for, as seen in server.js
ASSET_NAMES = [
    'homebrew.elf',
    'homebrew.elf.sig',
    'remote.md5',
    'store.prx',
    'store.prx.sig',
]

# The local directory where we will store these downloaded binaries
BIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'bin'))

def get_latest_release_assets() -> dict:
    """
    Fetches the latest release from the GitHub API and returns a dictionary
    of required asset names and their download URLs.
    """
    print("Checking GitHub for the latest HB-Store release...")
    try:
        response = requests.get(GITHUB_API_URL, timeout=15)
        response.raise_for_status()
        releases = response.json()
        
        if not releases:
            raise ValueError("No releases found on GitHub.")
            
        latest_release = releases[0] # The first one is the latest
        assets = latest_release.get("assets", [])
        
        asset_urls = {
            asset['name']: asset['browser_download_url']
            for asset in assets if asset['name'] in ASSET_NAMES
        }
        
        print(f"Found latest release: {latest_release['tag_name']}")
        return asset_urls

    except Exception as e:
        print(f"Error fetching from GitHub API: {e}")
        return {}

def update_binaries():
    """
    Downloads the required binaries from the latest GitHub release
    into the local '/backend/bin' directory.
    """
    asset_urls = get_latest_release_assets()
    if not asset_urls:
        print("Could not retrieve asset URLs. Aborting binary update.")
        return {"success": False, "message": "Could not retrieve asset URLs from GitHub."}

    # Ensure the 'bin' directory exists
    os.makedirs(BIN_DIR, exist_ok=True)
    
    print("--- Starting HB-Store binary download ---")
    try:
        for name, url in asset_urls.items():
            destination_path = os.path.join(BIN_DIR, name)
            print(f"Downloading {name}...")
            
            # Download the file
            download_response = requests.get(url, timeout=30)
            download_response.raise_for_status()
            
            # Save the file
            with open(destination_path, 'wb') as f:
                f.write(download_response.content)
            print(f" -> Saved to {destination_path}")

        print("--- HB-Store binary update complete! ---")
        return {"success": True, "message": "HB-Store binaries updated successfully!"}
    except Exception as e:
        print(f"An error occurred during download: {e}")
        return {"success": False, "message": f"An error occurred: {e}"}