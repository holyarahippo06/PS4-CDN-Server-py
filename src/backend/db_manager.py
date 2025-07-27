# backend/db_manager.py
import sqlite3
import os
import shutil

DB_TEMPLATE = os.path.join(os.path.dirname(__file__), 'store.clean.db')
DB_PATH = os.path.join(os.path.dirname(__file__), 'store.db')

def create_db_from_packages(packages: list):
    """
    Creates a new store.db by copying a template and inserting package data.
    """
    # 1. Renew the DB by copying the clean template
    try:
        shutil.copyfile(DB_TEMPLATE, DB_PATH)
        print("Renewed store.db from template.")
    except Exception as e:
        print(f"ERROR renewing database: {e}")
        return False

    # 2. Connect to the new DB and insert all items
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()

        # The INSERT statement must match the table structure exactly
        sql = """
        INSERT INTO homebrews (
            pid, id, name, desc, image, package, version, picpath, 
            desc_1, desc_2, ReviewStars, Size, Author, apptype, 
            pv, main_icon_path, main_menu_pic, releaseddate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Create a list of tuples for executemany
        data_to_insert = []
        for item in packages:
            data_to_insert.append(tuple(item.get(key) for key in [
                "pid", "id", "name", "desc", "image", "package", "version", "picpath",
                "desc_1", "desc_2", "ReviewStars", "Size", "Author", "apptype",
                "pv", "main_icon_path", "main_menu_pic", "releaseddate"
            ]))
        
        cur.executemany(sql, data_to_insert)
        con.commit()
        con.close()
        print(f"Successfully inserted {len(packages)} items into store.db.")
        return True
    except Exception as e:
        print(f"ERROR inserting items into database: {e}")
        return False