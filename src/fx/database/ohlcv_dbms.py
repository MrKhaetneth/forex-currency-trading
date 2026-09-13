# ---------- FILE DESCRIPTION ----------
f"""({__name__}'s file description.) 
This module contains logging functions to keep track of changes within the local repo.
"""

# -------- IMPORTS ----------
import sys

import MetaTrader5 as mt5
import pandas as pd
import subprocess
import pytz
import sqlite3

from datetime import datetime
from pathlib import Path

from fx.connection import mt5_connected

# -------- FUNCTIONS ----------
def get_table_names(db_connection: sqlite3.Connection, 
                    cursor: sqlite3.Cursor | None = None) -> list[str]:
    if cursor is None:
        cursor = db_connection.cursor()
    
    table_names = []
    fetched_table_names = cursor.execute("SELECT name FROM sqlite_master").fetchall()
    if fetched_table_names is None:
        return [""]
    
    for table in fetched_table_names:
        table_names.append(table[0])
        
    return table_names


def get_column_names(db_connection: sqlite3.Connection, 
                     table_name: str, 
                     cursor: sqlite3.Cursor | None = None) -> list[str]:
    if cursor is None:
        cursor = db_connection.cursor()
    
    # Run a quick query on table
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
    except sqlite3.OperationalError as err:
        print(f"<ERROR> {err}")
        sys.exit(1)
    
    column_names = [desc[0] for desc in cursor.description]
    if len(column_names) == 0:
        return [""]
    return column_names
    

def main():
    _DB_PATH = "dataset/MT5_OHLCV.db"
    _DB_PATH = "testing_area/mt5_ohlcv.db"
    con = sqlite3.connect(_DB_PATH)
    cursor = con.cursor()
    print(get_table_names(con))
    print(get_table_names(con, cursor))
    print(get_column_names(con, "EURUSD"))
    print(get_column_names(con, "EURUSD", cursor))
    
    con.close()

# -------- SYSTEM CALLING ----------
if __name__ != "__main__":
    pass # Run import notice
else:
    main() # run test