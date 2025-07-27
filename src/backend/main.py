# backend/main.py (Final version with server-side config persistence)

import os
import uvicorn
import hashlib
import anyio
# --- NEW: Import json for handling the config file ---
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from . import pkg_manager, ps4_ftp_client, hb_formatter, db_manager, binary_updater

# --- NEW: Define path for the configuration file ---
CONFIG_PATH = 'config.json'

# --- Application Setup ---
app = FastAPI(title="PS4 CDN Server")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

server_state = {
    "packages": [],
    # --- MODIFIED: Default config structure ---
    "config": {
        "base_path": "Z:\\PS4Games\\pkgs", # Default, will be overridden by config.json
        "ps4_ip": "",
        "ps4_port": 2121
    },
    "db_initialized": False # Use a boolean, not a string
}

# --- Pydantic Models ---
class ScanRequest(BaseModel): base_path: str
class PS4ConnectionInfo(BaseModel): ps4_ip: str; ps4_port: int = 2121
class UpdateCDNRequest(PS4ConnectionInfo): new_cdn_url: str

# --- NEW: Pydantic model for saving the configuration ---
class ConfigUpdateRequest(BaseModel):
    base_path: str
    ps4_ip: str
    ps4_port: int

# --- Core Application Logic ---

@app.on_event("startup")
async def startup_event():
    print("--- Server is starting up! ---")
    
    # --- NEW: Load configuration from file ---
    if os.path.exists(CONFIG_PATH):
        print(f"[*] Found {CONFIG_PATH}, loading settings.")
        with open(CONFIG_PATH, 'r') as f:
            # Use .update() to safely merge saved settings over defaults
            server_state['config'].update(json.load(f))
    else:
        print(f"[*] {CONFIG_PATH} not found, using default settings.")

    binary_updater.update_binaries()

    db_path = db_manager.DB_PATH
    if os.path.exists(db_path):
        print("--- Found existing store.db. Will not rebuild on this run. ---")
        server_state["db_initialized"] = True
    
    base_path = server_state["config"]["base_path"]
    if os.path.isdir(base_path):
        print(f"Pre-scanning directory: {base_path}...")
        server_state["packages"] = pkg_manager.scan_directory(base_path)
        
        if not server_state["db_initialized"]:
            print(f"--- Scan complete. {len(server_state['packages'])} packages found. DB will be built on first visit. ---")
        else:
            print(f"--- Scan complete. {len(server_state['packages'])} packages loaded into memory. ---")
    else:
        print(f"--- WARNING: Configured base path '{base_path}' not found. ---")

def refresh_database(base_uri: str):
    print(f"--- Refreshing database with base URI: {base_uri} ---")
    formatted_packages = [
        hb_formatter.create_hb_store_item(pkg, base_uri, pid=i + 1)
        for i, pkg in enumerate(server_state["packages"])
    ]
    db_manager.create_db_from_packages(formatted_packages)
    server_state["db_initialized"] = True

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if not server_state["db_initialized"] and server_state["packages"]:
        base_url = str(request.base_url).rstrip('/')
        refresh_database(base_url)
    
    # The server_state passed to the template now contains the loaded config
    return templates.TemplateResponse("index.html", {
        "request": request, "server_host": request.client.host,
        "server_port": request.url.port, "server_state": server_state,
    })

# --- NEW: Endpoint to save the configuration ---
@app.post("/api/actions/save_config", summary="Saves the server configuration to config.json")
async def save_config_endpoint(config_data: ConfigUpdateRequest):
    try:
        # Update the config in memory
        server_state['config']['base_path'] = config_data.base_path
        server_state['config']['ps4_ip'] = config_data.ps4_ip
        server_state['config']['ps4_port'] = config_data.ps4_port
        
        # Write the updated config to the file
        with open(CONFIG_PATH, 'w') as f:
            json.dump(server_state['config'], f, indent=4)
            
        print(f"[*] Configuration saved to {CONFIG_PATH}")
        return JSONResponse(content={"message": "Configuration saved successfully."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {e}")

# ... (The rest of your endpoints: get_all_packages, get_hb_store_db, etc. remain unchanged) ...
@app.get("/api/packages")
async def get_all_packages():
    return JSONResponse(content=server_state["packages"])

@app.api_route("/store.db", methods=["GET", "HEAD"])
async def get_hb_store_db(request: Request):
    db_path = db_manager.DB_PATH
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="store.db not found.")
    print("--- PS4 is requesting store.db ---")
    return FileResponse(path=db_path, media_type='application/octet-stream', filename='store.db')

@app.get("/api.php", summary="Handle DB hash check from PS4")
async def get_api_php(db_check_hash: bool = False):
    if db_check_hash:
        db_path = db_manager.DB_PATH
        if not os.path.exists(db_path):
            raise HTTPException(status_code=404, detail="store.db not found for hashing.")
        print("--- PS4 is requesting store.db hash ---")
        with open(db_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return JSONResponse(content={"hash": file_hash})
    return JSONResponse(content={"status": "ok"})

@app.get("/download.php", summary="Handle pre-download check from PS4")
async def handle_download_check(tid: str = "", check: bool = False):
    if check and tid:
        print(f"--- PS4 is performing a pre-download check for TID: {tid} ---")
        return JSONResponse(content={"status": "ok"})
    raise HTTPException(status_code=400, detail="Invalid request to download.php")

@app.api_route("/api/download/{pkg_index}", methods=["GET", "HEAD"], summary="Download a PKG file")
async def download_pkg(pkg_index: int, request: Request):
    try:
        pkg = server_state["packages"][pkg_index - 1]
    except (IndexError, TypeError):
        raise HTTPException(status_code=404, detail=f"Package with index {pkg_index} not found.")
    if not pkg or not os.path.exists(pkg.get("file_path")):
        raise HTTPException(status_code=404, detail="Package file path not found or invalid.")
    file_path = pkg["file_path"]
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    headers = {'Content-Disposition': f'attachment; filename="{filename}"', 'Content-Length': str(file_size)}
    if request.method == "HEAD":
        print(f"--- PS4 is requesting headers for package: {filename} ---")
        return Response(headers=headers, media_type='application/octet-stream')
    async def file_iterator(path: str):
        try:
            async with await anyio.open_file(path, "rb") as f:
                while chunk := await f.read(1024 * 1024): yield chunk
        except anyio.get_cancelled_exc_class():
            print(f"--- Download cancelled by client for: {filename} ---")
        except Exception as e:
            print(f"An error occurred during file streaming for {filename}: {e}")
    print(f"--- PS4 is starting download for package: {filename} ---")
    return StreamingResponse(file_iterator(file_path), media_type='application/octet-stream', headers=headers)

@app.get("/update/{filename:path}")
async def get_update_file(filename: str):
    file_path = os.path.join(binary_updater.BIN_DIR, filename)
    if not file_path.startswith(binary_updater.BIN_DIR):
        raise HTTPException(status_code=403, detail="Forbidden")
    if os.path.exists(file_path):
        print(f"--- PS4 is requesting update file: {filename} ---")
        return FileResponse(path=file_path, media_type='application/octet-stream')
    else:
        raise HTTPException(status_code=404, detail=f"Update file '{filename}' not found.")

@app.post("/api/actions/full_rescan", summary="Deletes the DB and rescans everything")
async def trigger_full_rescan(request: Request):
    print("--- Full database rebuild requested! ---")
    db_path = db_manager.DB_PATH
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f" -> Successfully deleted old database: {db_path}")
            server_state["db_initialized"] = False
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Error deleting database file: {e}")
    base_path = server_state["config"]["base_path"]
    if not os.path.isdir(base_path):
        raise HTTPException(status_code=404, detail="Package directory not found.")
    print(" -> Rescanning package directory...")
    server_state["packages"] = pkg_manager.scan_directory(base_path)
    print(" -> Rebuilding database from scan results...")
    refresh_database(str(request.base_url).rstrip('/'))
    message = f"Database rebuild complete. Found {len(server_state['packages'])} packages."
    print(f"--- {message} ---")
    return {"message": message}

@app.post("/api/actions/scan")
async def trigger_scan(scan_request: ScanRequest, request: Request):
    base_path = scan_request.base_path
    if not os.path.isdir(base_path):
        raise HTTPException(status_code=404, detail="Directory not found.")
    # --- MODIFIED: Update config in memory, but don't save to file here ---
    # The user should explicitly click "Save Settings" for that.
    server_state["config"]["base_path"] = base_path
    server_state["packages"] = pkg_manager.scan_directory(base_path)
    refresh_database(str(request.base_url).rstrip('/'))
    return {"message": f"Scan complete. Found {len(server_state['packages'])} packages."}

@app.post("/api/actions/update_binaries")
async def trigger_binary_update():
    result = binary_updater.update_binaries()
    return JSONResponse(content=result)

@app.post("/api/ps4/update_cdn")
async def update_ps4_cdn(request: UpdateCDNRequest):
    try:
        if ps4_ftp_client.update_cdn(request.ps4_ip, request.ps4_port, request.new_cdn_url):
            return {"message": f"Successfully updated PS4 CDN to {request.new_cdn_url}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)