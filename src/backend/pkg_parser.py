## pkg_parser lib by n1ghty
## This file is based on
## UnPKG rev 0x00000008 (public edition), (c) flatz
## and
## Python SFO Parser by: Chris Kreager a.k.a LanThief
## Converted and corrected for Python 3

import sys, os, struct, traceback

# text of available values for help texts
AVAILABLE_VALUES = (
    ' Raw values from param.sfo like\n'
    '  - TITLE, TITLE_ID, CONTENT_ID, VERSION, APP_VER, PARENTAL_LEVEL, \n'
    '    SYSTEM_VER, ...\n'
    ' Formatted values, especially for version information:\n'
    '  - LANGUAGES\n'
    '    The list of title name languages, e.g. \'EN,FR,RU\'\n'
    '    This does not always reflect supported languages.'
    '  - VER\n'
    '    Equals VERSION for a game / an application and APP_VER for an update\n'
    '  - SYS_VER\n'
    '    The required system version number in a readable format, e.g. \'2.70\'\n'
    '  - SDK_VER\n'
    '    The used sdk version number in a readable format - if available - e.g. \'2.70\'\n'
    '  - REGION\n'
    '    The region of the pkg (EU, US, JP, ASIA)\n'
    '  - SIZE\n'
    '    The filesize in a readable format, e.g. \'1.1 GB\'\n'
    '  - TITLE_XX\n'
    '    The title name in a specific language XX. If not available, the default\n'
    '    language is used.\n'
    '\n'
    '    Available language codes:\n'
    '      JA, EN, FR, ES, DE, IT, NL, PT, RU, KO, CH, ZH, FI, SV, DA,\n'
    '      NO, PL, BR, GB, TR, LA, AR, CA, CS, HU, EL, RO, TH, VI, IN'
    )

## utility functions
def convert_bytes(num):
    "this function will convert bytes to MB.... GB... etc"
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return '%3.1f %s' % (num, x)
        num /= 1024.0

def read_string(f, length):
    return f.read(length)

def read_uint32_be(f):
    return struct.unpack('>I', f.read(struct.calcsize('>I')))[0]

def le32(bits):
    return struct.unpack('<I', bits)[0]

def le16(bits):
    return struct.unpack('<H', bits)[0]

## classes
class PsfHdr:
    def __init__(self, bits):
        self.size = 20
        self.magic = bits[0:4]
        self.label_ptr = le32(bits[8:12])
        self.data_ptr = le32(bits[12:16])
        self.nsects = le32(bits[16:20])

class PsfSec:
    def __init__(self, bits):
        self.size = 16
        self.label_off = le16(bits[0:2])
        self.data_type = bits[3]  # 0x02 for string, 0x04 for integer
        self.datafield_used = le32(bits[4:8])
        self.data_off = le32(bits[12:16])

class MyError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)

class FileTableEntry:
    entry_fmt = '>IIIIII8x'
    def __init__(self):
        self.type = 0
        self.offset = 0
        self.size = 0

    def read(self, f):
        entry_data = f.read(struct.calcsize(self.entry_fmt))
        if len(entry_data) < struct.calcsize(self.entry_fmt): return False
        self.type, _, _, _, self.offset, self.size = struct.unpack(self.entry_fmt, entry_data)
        return True

## main code
PsfMagic = b'\x00PSF'
PkgMagic = b'\x7FCNT'
TITLE_LANG_MAP = {
            '00': 'JA', '01': 'EN', '02': 'FR', '03': 'ES', '04': 'DE', '05': 'IT',
            '06': 'NL', '07': 'PT', '08': 'RU', '09': 'KO', '10': 'CH', '11': 'ZH',
            '12': 'FI', '13': 'SV', '14': 'DA', '15': 'NO', '16': 'PL', '17': 'BR',
            '18': 'GB', '19': 'TR', '20': 'LA', '21': 'AR', '22': 'CA', '23': 'CS',
            '24': 'HU', '25': 'EL', '26': 'RO', '27': 'TH', '28': 'VI', '29': 'IN',
            }

def getPkgInfo(pkg_file_path):
    try:
        with open(pkg_file_path, 'rb') as pkg_file:
            magic = read_string(pkg_file, 4)
            if magic != PkgMagic:
                raise MyError('invalid file magic')

            pkg_file.seek(0x18)
            file_table_offset = read_uint32_be(pkg_file)

            pkg_file.seek(file_table_offset)
            # Loop through file table to find param.sfo
            entry = FileTableEntry()
            while entry.read(pkg_file):
                if entry.type == 0x1000: # This is the unencrypted param.sfo
                    original_pos = pkg_file.tell() # Save position
                    pkg_file.seek(entry.offset)
                    sfo_data = pkg_file.read(entry.size)
                    pkg_file.seek(original_pos) # Restore position
                    
                    if not sfo_data.startswith(PsfMagic):
                        raise MyError('param.sfo is not a valid PSF file!')

                    psfheader = PsfHdr(sfo_data)
                    psflabels = sfo_data[psfheader.label_ptr:]
                    psfdata = sfo_data[psfheader.data_ptr:]
                    
                    pkg_info = {}
                    current_section_offset = psfheader.size
                    
                    for _ in range(psfheader.nsects):
                        sect = PsfSec(sfo_data[current_section_offset:])
                        
                        label_bytes = psflabels[sect.label_off:].split(b'\x00')[0]
                        val_label = label_bytes.decode('utf-8', 'ignore')
                        
                        data_chunk = psfdata[sect.data_off : sect.data_off + sect.datafield_used]

                        if sect.data_type == 2: # string
                            val_data = data_chunk.rstrip(b'\x00').decode('utf-8', 'ignore')
                            pkg_info[val_label] = val_data
                        elif sect.data_type == 4: # integer
                            pkg_info[val_label] = str(le32(data_chunk))
                        
                        current_section_offset += sect.size

                    # --- Post-processing after finding and parsing SFO ---
                    pkg_file.seek(0, os.SEEK_END)
                    pkg_info['SIZE'] = convert_bytes(pkg_file.tell())

                    if 'CONTENT_ID' in pkg_info and len(pkg_info['CONTENT_ID']) > 1:
                        region_char = pkg_info['CONTENT_ID'][1] # Region is the 2nd char
                        if region_char == 'P': region = 'EU'
                        elif region_char == 'S': region = 'US'
                        elif region_char == 'A': region = 'Asia'
                        elif region_char == 'I': region = 'JP' # Usually IP for Japan
                        else: region = 'UNKNOWN'
                        pkg_info['REGION'] = region

                    if 'SYSTEM_VER' in pkg_info and pkg_info['SYSTEM_VER'].isdigit():
                        sys_ver_str = str(pkg_info['SYSTEM_VER'])
                        pkg_info['SYS_VER'] = f'{sys_ver_str[0]}.{sys_ver_str[1:3]}'
                    
                    if 'PUBTOOLINFO' in pkg_info:
                        for ptinfo in pkg_info['PUBTOOLINFO'].split(','):
                            if '=' in ptinfo and ptinfo.startswith('sdk_ver'):
                                val = ptinfo.split('=')[1]
                                pkg_info['SDK_VER'] =  f'{val[1]}.{val[2:4]}'

                    for code, lang in TITLE_LANG_MAP.items():
                        var = 'TITLE_' + code
                        var_l = 'TITLE_' + lang
                        pkg_info[var_l] = pkg_info.get(var, pkg_info.get('TITLE', ''))

                    languages = [v for k, v in TITLE_LANG_MAP.items() if f'TITLE_{k}' in pkg_info and pkg_info[f'TITLE_{k}']]
                    pkg_info['LANGUAGES'] = ','.join(languages)

                    if pkg_info.get('CATEGORY') in ('gp', 'gpc'): # Game Patch / Update
                        pkg_info['VER'] = pkg_info.get('APP_VER', '') + ' (Update)'
                    else:
                        pkg_info['VER'] = pkg_info.get('VERSION', '')

                    return pkg_info # Successfully parsed, exit function
            
            # If loop finishes without finding the SFO
            raise MyError("Could not find param.sfo entry (type 0x1000) in the PKG.")

    except OSError:
        print(f'ERROR: i/o error during processing ({pkg_file_path})')
    except MyError as e:
        print(f'ERROR: {e.message} ({pkg_file_path})')
    except Exception:
        print(f'ERROR: unexpected error: {sys.exc_info()[0]} ({pkg_file_path})')
        traceback.print_exc(file=sys.stdout)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        pkg_path = sys.argv[1]
        info = getPkgInfo(pkg_path)
        if info:
            print("\n--- PKG Metadata ---")
            keys_to_print = ['TITLE', 'TITLE_ID', 'CONTENT_ID', 'REGION', 'VER', 'SYS_VER', 'LANGUAGES', 'SIZE']
            for key in keys_to_print:
                if key in info:
                    print(f"{key}: {info[key]}")
            print("--------------------\n")
    else:
        print(f"Usage: python {sys.argv[0]} /path/to/your/file.pkg")