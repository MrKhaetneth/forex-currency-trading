import h5py
import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent 
sys.path.append(str(parent_dir))

import pandas as pd
from datetime import datetime

import pytz
import MetaTrader5 as mt5

parent_dir = Path(__file__).resolve().parent.parent 
sys.path.append(str(parent_dir))
from check_env import check_status

# HDF5 file path
SCRIPT_DIR  = Path(__file__).resolve().parent 
DATASET_DIR = SCRIPT_DIR.parent.parent.parent / "dataset" 
H5_PATH     = DATASET_DIR / "MetaTrader5CurrencyHistory.h5"

SYMBOL = "EURUSD"
TIMEFRAME = "Y5"
TARGET_KEY = f"{TIMEFRAME}/{SYMBOL}"

TIMEZONE = pytz.timezone("Etc/UTC")
UTC_FROM = datetime(2025, 12, 20, tzinfo = TIMEZONE)
UTC_TO   = datetime(2026, 5, 5, tzinfo = TIMEZONE)

def main():
    # Pull downloaded data
    with h5py.File(H5_PATH, 'r') as mt5_history:
        print(f"Timeframes (Keys) within the file: {list(mt5_history.keys())}")
        
        group_timeframe = mt5_history[TIMEFRAME]
        print(f"Currencies (Keys) within the {group_timeframe} timeframe: {list(group_timeframe.keys())}")
    
    df = pd.read_hdf(str(H5_PATH), key = TARGET_KEY)

    print(f"\n--- Printing Data for: {TARGET_KEY} ---")
    print(df.tail(5))
    
    # New data with overlapping dates
    if not check_status():
        print("Error in checking credentials...")
        quit()
    
    # check if the file already exists
    if not H5_PATH.exists():
        print(f"File not found. This script will create a fresh file at: {H5_PATH.name}")
        with h5py.File(H5_PATH, "a") as f:
            print("File created.")
            pass
    
    # Extract trade history
    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_D1, UTC_FROM, UTC_TO)
    mt5.shutdown()
    
    rates_df = pd.DataFrame(rates)
    rates_df["time"] = pd.to_datetime(rates_df["time"], unit = 's')
    
    print("\n===== COMPARE RESULT! =====")
    print(rates_df.head(5))
    
    print(df.iloc[1563] == rates_df.iloc[2])
    bool_series = (df.iloc[1563] == rates_df.iloc[2])
    print(bool_series.all())

if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")
