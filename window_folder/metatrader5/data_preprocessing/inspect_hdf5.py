import h5py
import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent 
sys.path.append(str(parent_dir))

import pandas as pd
from datetime import datetime

# HDF5 file path
SCRIPT_DIR  = Path(__file__).resolve().parent 
DATASET_DIR = SCRIPT_DIR.parent.parent.parent / "dataset" 
H5_PATH     = DATASET_DIR / "MetaTrader5CurrencyHistory.h5"

TIMEFRAME = "Y5"
CURRENCY = "EURUSD"
TARGET_KEY = f"{TIMEFRAME}/{CURRENCY}"

def main():
    with h5py.File(H5_PATH, 'r') as mt5_history:
        print(f"Timeframes (Keys) within the file: {list(mt5_history.keys())}")
        
        group_timeframe = mt5_history[TIMEFRAME]
        print(f"Currencies (Keys) within the {group_timeframe} timeframe: {list(group_timeframe.keys())}")
    
    df = pd.read_hdf(str(H5_PATH), key = TARGET_KEY)

    print(f"\n--- Printing Data for: {TARGET_KEY} ---")
    print(df)
    print(f"Total Rows: {len(df)}\n")
    print(f"Shape: {df.shape}\n")

if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")
