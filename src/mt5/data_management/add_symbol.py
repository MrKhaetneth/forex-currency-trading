# -------- IMPORTS ----------
import sys

import MetaTrader5 as mt5
import pandas as pd
import pytz

from pathlib import Path 

from old_packages.data_storage_func import download_ohlcv, save_dataset, load_dataset
from old_packages.utility_func import get_input
from old_packages.check_env import check_status

# -------- CONSTANTS ----------

# HDF5 file path
FILENAME = "MT5CurrencyHistory.h5"
SCRIPT_DIR = Path(__file__).resolve().parent 
DATASET_DIR = SCRIPT_DIR.parent.parent.parent / "dataset"
HDF5_PATH = DATASET_DIR / FILENAME
TIMEZONE = pytz.timezone("Etc/UTC")

# -------- FUNCTIONS ----------


# -------- MAIN ----------
def main():
    # -------- OUTPUT ----------
    print("===========================")
    print("|   TEST: DATA STORAGE    |")
    print("===========================\n")
    print(f"Script Purpose: Manage data in {FILENAME}.")
    
    # Testing connection and authorization with MetaTrader5
    if not check_status():
        quit()
    
    # Get user input
    user_spec = get_input(FILENAME)
    SYMBOL = user_spec["SYMBOL"]
    MT5_TIMEFRAME = user_spec["MT5_TIMEFRAME"]
    TIME_START = user_spec["TIME_START"]
    TIME_END = user_spec["TIME_END"]
    
    # -------- DOWNLOAD DATA ----------
    df = download_ohlcv(SYMBOL, MT5_TIMEFRAME, TIME_START, TIME_END)
    print(df.head())

    # -------- SAVE / MERGE INTO HDF5 ----------
    dataset_path = save_dataset(HDF5_PATH, SYMBOL, MT5_TIMEFRAME, df)
    print(f"\n<NOTICE> Data saved at '{dataset_path}' inside {HDF5_PATH}.")

    # -------- VERIFY ----------
    reloaded = load_dataset(HDF5_PATH, SYMBOL, MT5_TIMEFRAME)
    print(f"<NOTICE> Reloaded {len(reloaded)} rows from '{dataset_path}'.")
    print(f"<CHECK> Rows are chronologically ascending: {pd.Series(reloaded['time']).is_monotonic_increasing}")

    print(reloaded)
    
    mt5.shutdown()
    print("\n<TERM> Session terminated.")
    

# -------- SYSTEM CALLING ----------
if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")