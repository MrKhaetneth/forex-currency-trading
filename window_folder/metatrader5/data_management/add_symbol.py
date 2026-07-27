# -------- IMPORTS ----------
import utility_func as uf

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import h5py
import pytz
import sys

from datetime import datetime
from pathlib import Path 

parent_dir = Path(__file__).resolve().parent.parent 
sys.path.append(str(parent_dir))
from check_env import check_status
del parent_dir 

# -------- CONSTANTS ----------

# HDF5 file path
FILENAME = "MT5CurrencyHistory.h5"
SCRIPT_DIR = Path(__file__).resolve().parent 
DATASET_DIR = SCRIPT_DIR.parent.parent.parent / "dataset"
HDF5_PATH = DATASET_DIR / FILENAME
TIMEZONE = pytz.timezone("Etc/UTC")

# -------- FUNCTIONS ----------
def merge_tables(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """_summary_

    Args:
        df1 (pd.DataFrame): _description_
        df2 (pd.DataFrame): _description_

    Returns:
        pd.DataFrame: _description_
    """
    return_table = pd.concat([df1, df2], axis = 0, join = "outer") # Just put two DataFrames on top of one-another
    return_table = return_table.drop_duplicates().sort_values(by = ["time"]) # Any intersection will be duplicated. So, remove them.
    return return_table

# -------- MAIN ----------
def main():
    # -------- OUTPUT ----------
    print("===========================")
    print("|      USER INTERFACE     |")
    print("===========================\n")

    print(f"Script Purpose: To add the price history of a currency pair of interest within a designated time frame to {FILENAME}.")
    
    # Testing connection and authorization with MetaTrader5
    if not check_status():
        quit()
    
    # Will be good to allow the user to include many symbols at once, or search for a symbol!
    # -------- USER INPUT ----------
    user_spec = uf.get_input(FILENAME)
    symbol = user_spec["SYMBOL"]
    mt5_timeframe = user_spec["MT5_TIMEFRAME"]
    hdf5_timeframe = user_spec["HDF5_TIMEFRAME"]
    time_start = user_spec["TIME_START"]
    time_end = user_spec["TIME_END"]

    # -------- DOWNLOAD DATA FROM MT5 ----------
    mt5_rates = uf.mt5_download_rates(**user_spec)
    print(mt5_rates)
    ncol = mt5_rates.shape[1]
    dset_dt = [
        ('time', 'i8'),
        ('open', 'f8'),
        ('time', 'i8'),
        ('open', 'f8'),
        ('high', 'f8'),
        ('low', 'f8'),
        ('close', 'f8'),
        ('tick_volume', 'i8'),
        ('spread', 'i8'),
        ('real_volume', 'i8')
    ]
    hdf5_dataset_datatype = np.dtype(dset_dt)
    if ncol != len(dset_dt):
        raise Exception("<ERROR> Number of columns of downloaded data is not equal to the length of data type specification list! Contact @MrKhaetneth.")
    
    # -------- HDF5 SECTION ----------
    # Check HDF5 file existence
    print(f"\n<NOTICE> Locating {FILENAME}...")
    if not HDF5_PATH.exists():
        print(f"<NOTICE> {FILENAME} does not exist in the \'/dataset\' directory.")
        print(f"<NOTICE> Creating {FILENAME} at {HDF5_PATH}...")
        uf.make_file(FILENAME, HDF5_PATH)
    else:
        print(f"<NOTICE> {FILENAME} located at {HDF5_PATH}. Proceeding to the next step...")
    
    # Check group
    # Check 3 cases: 
    # (1) Timeframe/group never exist; 
    # (2) Timeframe exist but symbol never got recorded; 
    # (3) table already exist. Then check for overlap.
    with h5py.File(HDF5_PATH, mode = "a") as hdf5_file:
        group_exists = (hdf5_timeframe in hdf5_file)
        if group_exists:
            dataset_exists = (symbol in hdf5_file[hdf5_timeframe])
        
        if not group_exists:
            print(f"\n<NOTICE> {hdf5_timeframe} group does not exist in the root layer of {FILENAME}.")
            print(f"\n<NOTICE> Creating the {hdf5_timeframe} group...")
            timeframe_group = hdf5_file.create_group(hdf5_timeframe)
            print(f"<NOTICE> {hdf5_timeframe} group created.")
            group_exists = True 
        
        timeframe_group = hdf5_file[hdf5_timeframe]
        if not dataset_exists:
            print(f"\n<NOTICE> {symbol} dataset does not exist in {hdf5_timeframe} group of {FILENAME}.")
            print(f"<NOTICE> Creating the {symbol} dataset within {hdf5_timeframe} group...")
            # symbol_dataset = timeframe_group.create_dataset((None, ncol), )
            
            
    
    
    
    # merge tables with the function merge_tables
    
    # # Check target group existence
    # target_groupname = mt5_timeframe[1]
    
        
    
    # append
    # Make log history inside HDF5 too. 
    print("TEST")

    mt5.shutdown()
    
    print("\n<TERM> Session terminated.")

# -------- SYSTEM CALLING ----------
if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")