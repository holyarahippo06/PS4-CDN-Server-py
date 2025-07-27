# backend/ps4_pkg_info.py (Literal Port of the Working TypeScript Library)

import os
import base64
import struct
from typing import BinaryIO, Dict, Optional, Union, NamedTuple

# --- Data Structures ---
class Ps4PkgInfo(NamedTuple):
    param_sfo: Optional[Dict[str, Union[str, int]]] = None
    icon0_raw: Optional[bytes] = None
    icon0_base64: Optional[str] = None

class _PkgTableEntry(NamedTuple):
    id: int
    offset: int
    size: int

# --- Internal Core Logic ---
def _parse_param_sfo(sfo_bytes: bytes) -> Dict[str, Union[str, int]]:
    if sfo_bytes[0:4] != b'\x00PSF':
        raise ValueError("Invalid SFO magic")
    label_ptr, data_ptr, section_total = struct.unpack_from('<III', sfo_bytes, 8)
    params = {}
    for i in range(section_total):
        entry_offset = 20 + (i * 16)
        label_offset, _, data_type, used_data_field, _, data_offset = struct.unpack_from(
        '<HBBIII', sfo_bytes, entry_offset  # Changed <HBBII to <HBBIII
    )
        label_start = label_ptr + label_offset
        label_end = sfo_bytes.find(b'\x00', label_start)
        label = sfo_bytes[label_start:label_end].decode('utf-8')
        data_start = data_ptr + data_offset
        if data_type == 2:
            value = sfo_bytes[data_start : data_start + used_data_field - 1].decode('utf-8')
        elif data_type == 4:
            value = struct.unpack_from('<I', sfo_bytes, data_start)[0]
        else:
            continue
        params[label] = value
    return params

def _extract_from_stream(pkg_stream: BinaryIO, generate_base64_icon: bool) -> Ps4PkgInfo:
    pkg_stream.seek(0)
    header = pkg_stream.read(0x20) # Read the first 32 bytes
    if header[0:4] != b'\x7FCNT':
        raise ValueError('Invalid PKG file format')

    # --- THE LITERAL, 1:1 PORT OF THE WORKING TYPESCRIPT CODE ---
    # Reading from the offsets used by the @njzy library: 0x10 and 0x18.
    total_table_entry = struct.unpack('>I', header[0x10:0x14])[0]
    table_offset = struct.unpack('>I', header[0x18:0x1C])[0]
    
    pkg_stream.seek(table_offset)
    
    param_sfo_entry, icon0_entry = None, None
    PARAM_SFO_ID, ICON0_ID = 0x1000, 0x1200
    
    for _ in range(total_table_entry):
        entry_chunk = pkg_stream.read(32)
        if len(entry_chunk) < 32:
            break
        
        values = struct.unpack('>IIIIII8x', entry_chunk)
        entry_id, _, _, _, offset, size = values
        
        if entry_id == PARAM_SFO_ID:
            param_sfo_entry = _PkgTableEntry(id=entry_id, offset=offset, size=size)
        elif entry_id == ICON0_ID:
            icon0_entry = _PkgTableEntry(id=entry_id, offset=offset, size=size)
        
        if param_sfo_entry and icon0_entry:
            break
            
    if not param_sfo_entry:
        raise ValueError("Could not find param.sfo entry (ID 0x1000). The PKG may be corrupt or of an unsupported type.")
            
    sfo_data = None
    if param_sfo_entry:
        pkg_stream.seek(param_sfo_entry.offset)
        sfo_bytes = pkg_stream.read(param_sfo_entry.size)
        sfo_data = _parse_param_sfo(sfo_bytes)
        
    icon_data, b64_icon = None, None
    if icon0_entry:
        pkg_stream.seek(icon0_entry.offset)
        icon_data = pkg_stream.read(icon0_entry.size)
        if icon_data.startswith(b'\x89PNG') and generate_base64_icon:
            b64_icon = f"data:image/png;base64,{base64.b64encode(icon_data).decode('ascii')}"
            
    return Ps4PkgInfo(param_sfo=sfo_data, icon0_raw=icon_data, icon0_base64=b64_icon)

def get_ps4_pkg_info(pkg_file_path: str, generate_base64_icon: bool = False) -> Optional[Ps4PkgInfo]:
    try:
        with open(pkg_file_path, 'rb') as f:
            return _extract_from_stream(f, generate_base64_icon)
    except FileNotFoundError:
        print(f"Error: PKG file not found at {pkg_file_path}")
    except Exception as e:
        print(f"An error occurred processing {os.path.basename(pkg_file_path)}: {e}")
    return None