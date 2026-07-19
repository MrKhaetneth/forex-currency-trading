import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent 
sys.path.append(str(parent_dir))

import MetaTrader5 as mt5
import pandas as pd
import pytz
import h5py

from datetime import datetime
from check_env import check_status

SYMBOL = "EURUSD"
TIMEZONE = pytz.timezone("Etc/UTC")
UTC_FROM = datetime(2020, 1, 1, tzinfo = TIMEZONE)
UTC_TO   = datetime(2026, 1, 1, tzinfo = TIMEZONE)

# Save HDF5 file path
SCRIPT_DIR  = Path(__file__).resolve().parent 
DATASET_DIR = SCRIPT_DIR.parent.parent.parent / "dataset" 
H5_PATH     = DATASET_DIR / "MetaTrader5CurrencyHistory.h5"
TARGET_KEY  = f"Y5/{SYMBOL}"

def main():
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
    
    # Check if dataset already exists or not.
    dataset_exists = False
    with h5py.File(H5_PATH, "r") as f:
        if f"Y5/{SYMBOL}" in f:
            dataset_exists = True
    
    if dataset_exists:
        print(f"\n<WARNING> This process is irreversible! THis will overwrite the {TARGET_KEY} dataset! <WARNING>\n")
        overwrite_authorization = input("Do you wish to overwrite the content of this dataset? (Y/N): ")[0].lower()
        overwrite_booldict = {"y": True, "n": False}
        overwrite_authorized = overwrite_booldict[overwrite_authorization]
        if not overwrite_authorized:
            print("\nProgram terminated...")
            quit()
        else:
            print("Removing old dataset...")
            with h5py.File(H5_PATH, "a") as f:
                if TARGET_KEY in f:
                    del f[TARGET_KEY]
                    print("Removed old dataset.")
                    
            print("Appending new dataset...")
            rates_df.to_hdf(
                str(H5_PATH), # File name
                key = TARGET_KEY,         # 5Year is the Group name and SYMBOL is the dataset name
                mode = "a",                      # Use 'a' so you don't overwrite other currency datasets later
                format = "table",                # 'table' format allows for fast querying and appending
            )
    else:
        rates_df.to_hdf(
            str(H5_PATH), # File name
            key = TARGET_KEY,         # 5Year is the Group name and SYMBOL is the dataset name
            mode = "a",                      # Use 'a' so you don't overwrite other currency datasets later
            format = "table",                # 'table' format allows for fast querying and appending
        )
    
    print(f"File updated: Dataset added at {TARGET_KEY}.")

if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")