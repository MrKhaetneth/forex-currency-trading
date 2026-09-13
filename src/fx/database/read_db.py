f"""({__name__}'s file description)
This module contains function pertinent to reading or extracting information from a database (.db files).
"""
# -------- IMPORTS ----------
import sqlite3 
import sys

import pandas as pd

# -------- CONSTANTS ----------
_DB_DIR = "dataset/"
_DB_PATH = _DB_DIR + "MT5_OHLCV.db"

# -------- FUNCTIONS ----------
def get_table_names(cursor: sqlite3.Cursor) -> list[str]:
    table_names = []
    fetched_table_names = cursor.execute("SELECT name FROM sqlite_master").fetchall()
    if fetched_table_names is None:
        return [""]
    
    for table in fetched_table_names:
        table_names.append(table[0])
        
    return table_names


def get_column_names(cursor: sqlite3.Cursor, table_name: str) -> list[str]:
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


def get_table_content(db_connection: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table_name}", db_connection)

# -------- SYSTEM CALLING ----------
if __name__ == "__main__":
    print(sys.argv)
    # uv run src/fx/database/read_db.py makes the first argv being the file path.
    # Make a test for these functions, including the expected errors.