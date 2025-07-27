# backend/ps4_ftp_client.py (Final version with correct INI parsing)

import ftplib
import configparser # <-- The correct library for .ini files
from io import StringIO, BytesIO

# --- The correct path you found ---
HBS_SETTINGS_PATH = "/user/app/NPXS39041/settings.ini"

def _connect_to_ps4(host: str, port: int):
    """Establishes an FTP connection to the PS4."""
    try:
        ftp = ftplib.FTP()
        print(f"Connecting to PS4 FTP at {host}:{port}...")
        ftp.connect(host, port, timeout=10)
        ftp.login()
        print("FTP connection successful.")
        return ftp
    except Exception as e:
        raise ConnectionError(f"Could not connect to PS4 FTP at {host}:{port}. Ensure FTP is running.")

def _get_settings_config(ftp: ftplib.FTP) -> configparser.ConfigParser:
    """Finds and downloads the settings.ini into a configparser object."""
    memory_file = BytesIO()
    try:
        print(f"Attempting to download settings from: {HBS_SETTINGS_PATH}...")
        ftp.retrbinary(f"RETR {HBS_SETTINGS_PATH}", memory_file.write)
        memory_file.seek(0)
        
        # Decode the bytes from FTP into a string for the parser
        ini_string = memory_file.read().decode('utf-8')
        
        config = configparser.ConfigParser()
        config.read_string(ini_string)
        
        print(f"Success! Found and parsed settings file.")
        return config
        
    except ftplib.error_perm as e:
        if "550" in str(e):
            raise FileNotFoundError(f"Could not find {HBS_SETTINGS_PATH} on the PS4. Is HB-Store installed and has it been run at least once?")
        else:
            raise
            
def update_cdn(host: str, port: int, new_cdn_url: str) -> bool:
    """
    Connects to the PS4, downloads settings.ini, updates the CDN URL,
    and uploads the modified file back.
    """
    ftp = _connect_to_ps4(host, port)
    
    try:
        # 1. Download and parse the INI file
        config = _get_settings_config(ftp)
        
        # 2. Modify the CDN URL under the [Settings] section
        print(f"Changing CDN from '{config['Settings']['CDN']}' to '{new_cdn_url}'")
        config['Settings']['CDN'] = new_cdn_url
        
        # 3. Prepare the new file for upload
        # We write the changes to an in-memory string buffer
        string_buffer = StringIO()
        config.write(string_buffer)
        
        # Get the string content and encode it back to bytes for FTP
        upload_bytes = string_buffer.getvalue().encode('utf-8')
        upload_buffer = BytesIO(upload_bytes)
        
        # 4. Upload the modified file back to the PS4
        print(f"Uploading modified settings back to {HBS_SETTINGS_PATH}...")
        ftp.storbinary(f"STOR {HBS_SETTINGS_PATH}", upload_buffer)
        
        print("CDN update successful!")
        return True

    finally:
        ftp.quit()