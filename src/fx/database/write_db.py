# ---------- FILE DESCRIPTION ----------
f"""({__name__}'s file description.) 
This module contains logging functions to keep track of changes within the local repo.
"""

# -------- IMPORTS ----------
import sys

import MetaTrader5 as mt5
import pandas as pd
import pytz
import sqlite3

from datetime import datetime
from pathlib import Path

from fx.connection import mt5_connected
from fx.database.read_db import get_table_names, get_table_content

# -------- CONSTANTS ----------
_DB_PATH = "dataset/MT5_OHLCV.db"
_SYMBOL = "EURUSD"

_TIMEZONE = pytz.timezone("Etc/UTC")
_TIMESTART = datetime(2026, 6, 10, tzinfo = _TIMEZONE)
_TIMEEND = datetime(2026, 7, 11, tzinfo = _TIMEZONE)
_MT5_TIMEFRAME_IN_MINS = {
    "M1": [1, mt5.TIMEFRAME_M1],
    "M2": [2, mt5.TIMEFRAME_M2],
    "M3": [3, mt5.TIMEFRAME_M3],
    "M4": [4, mt5.TIMEFRAME_M4],
    "M5": [5, mt5.TIMEFRAME_M5],
    "M6": [6, mt5.TIMEFRAME_M6],
    "M10": [10, mt5.TIMEFRAME_M10],
    "M12": [12, mt5.TIMEFRAME_M12],
    "M15": [15, mt5.TIMEFRAME_M15],
    "M20": [20, mt5.TIMEFRAME_M20],
    "M30": [30, mt5.TIMEFRAME_M30],
    "H1": [60, mt5.TIMEFRAME_H1],
    "H2": [120, mt5.TIMEFRAME_H2],
    "H3": [180, mt5.TIMEFRAME_H3],
    "H4": [240, mt5.TIMEFRAME_H4],
    "H6": [360, mt5.TIMEFRAME_H6],
    "H8": [480, mt5.TIMEFRAME_H8],
    "H12": [720, mt5.TIMEFRAME_H12],
    "D1": [1440, mt5.TIMEFRAME_D1],
    "W1": [10080, mt5.TIMEFRAME_W1],
    "MN1": [43200, mt5.TIMEFRAME_MN1]
}

# -------- FUNCTIONS ----------
def _get_ohlcv_rates_range(symbol: str,
                          mt5_timeframe: str,
                          date_from: datetime,
                          date_to: datetime) -> pd.DataFrame:
    datacall_func = getattr(mt5, "copy_rates_range")
    timeframe = _MT5_TIMEFRAME_IN_MINS[mt5_timeframe]
    
    rates = datacall_func(symbol, timeframe[1], date_from, date_to)
    df = pd.DataFrame(rates) # Time units is still seconds in UNIX timestamp 
    
    df["timeframe"] = mt5_timeframe
    df["time"] = pd.to_datetime(df["time"], unit = "s") # Convert to yyyy-mm-dd
    
    return df


def _get_ohlcv_rates_from(symbol: str,
                         mt5_timeframe: str,
                         date_from: datetime,
                         count: int) -> pd.DataFrame:
    datacall_func = getattr(mt5, "copy_rates_from")
    timeframe = _MT5_TIMEFRAME_IN_MINS[mt5_timeframe]
    
    rates = datacall_func(symbol, timeframe[1], date_from, count)
    df = pd.DataFrame(rates) # Time units is still seconds in UNIX timestamp 
    
    df["timeframe"] = mt5_timeframe
    df["time"] = pd.to_datetime(df["time"], unit = "s") # Convert to yyyy-mm-dd
    
    return df


def get_ohlcv(symbol: str, 
              mt5_timeframe: str, 
              date_from: datetime,
              date_to: datetime | None = None,
              num_bars: int | None = None) -> pd.DataFrame:
    # Pull data from MetaTrader5 using copy rates.
    if (date_to is None) and (num_bars is None):
        raise ValueError("One of the following variables must be specified: end_date or num_bars.")
    elif (date_to is None) and not (num_bars is None): # No ending date of data. Use bar count instead.
        df = _get_ohlcv_rates_from(symbol, mt5_timeframe, date_from, num_bars)
    elif not (date_to is None): # Prioritize date_to
        df = _get_ohlcv_rates_range(symbol, mt5_timeframe, date_from, date_to)

    return df


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    existing_names = get_table_names(cursor)
    return table_name in existing_names


def _merge_chronologically(existing_table: pd.DataFrame, new_table: pd.DataFrame) -> pd.DataFrame:
    """Union two OHLCV tables, keeping the newest value for any overlapping `time`, sorted ascending."""
    merged = pd.concat([existing_table, new_table], axis=0, join="outer")
    merged = merged.drop_duplicates()
    merged = merged.sort_values(by=["time"]).reset_index(drop=True)
    return merged


def add_table(db_connection: sqlite3.Connection,
              table_name: str,
              input_table: pd.DataFrame,
              cursor:sqlite3.Cursor) -> None:
    # Table doesn't exist. Directly insert input_table.
    if not _table_exists(cursor, table_name):
        input_table.to_sql(table_name, db_connection, index = False)
        return
    
    # If a table with same name already exist, then get existing table and merge with new one.
    existing_table = get_table_content(db_connection, table_name)
    merged_table = _merge_chronologically(existing_table, input_table)
    merged_table.to_sql(table_name, db_connection, if_exists = "replace", index = False)
    return 

# -------- MAIN ----------
def main():
    if not mt5_connected():
        print("<NOTICE> Can't connect to MetaTrader5.")
        sys.exit(1)
    
    # If database (.db file) doesn't exist, it creates a new one automatically.
    with sqlite3.connect(_DB_PATH) as db_connection:
        cursor = db_connection.cursor()
        new_table = get_ohlcv(_SYMBOL, "D1", _TIMESTART, _TIMEEND, 20000)
        add_table(db_connection, _SYMBOL, new_table, cursor)
        
        print(get_table_names(cursor))
        print(get_table_content(db_connection, _SYMBOL))
    
    # with sqlite3.connect(_DB_PATH) as db_connection:
    #     cursor = db_connection.cursor()
        
    #     print(get_table_names)
    #     print(get_table_content(db_connection, _SYMBOL))
    #     pass 

    getattr(mt5, "shutdown")()
    
# -------- SYSTEM CALLING ----------
if __name__ == "__main__":
    main()