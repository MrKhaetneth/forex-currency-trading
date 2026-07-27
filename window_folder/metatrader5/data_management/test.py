# -------- IMPORTS ----------
import MetaTrader5 as mt5
import pandas as pd
import subprocess
import h5py
import pytz

from utility_func import change_log
from datetime import datetime
from pathlib import Path

# parent_dir = Path(__file__).resolve().parent.parent 
# sys.path.append(str(parent_dir))
# from check_env import check_status
# del parent_dir 

# -------- CONSTANTS ----------

# HDF5 file path
FILENAME = "hdf5_test.h5"
SCRIPT_DIR = Path(__file__).resolve().parent 
DATASET_DIR = SCRIPT_DIR.parent.parent.parent / "dataset"
HDF5_PATH = DATASET_DIR / FILENAME
TIMEZONE = pytz.timezone("Etc/UTC")

# -------- FUNCTIONS ----------
def make_file(FILENAME: str, HDF5_PATH: Path):
    """
    Description: 
        Create/initialize the HDF5 file of interest

    Args:
        FILENAME (str): Name of the HDF5 file we will create.
        HDF5_PATH (Path): Absolute path (as a Path object) of the HDF5 file (that we will create).
    """
    with h5py.File(HDF5_PATH, mode = "w") as hdf5_file:
        print(f"\n<NOTICE> File created:")
        print(f"File name: {FILENAME}")
        print(f"File location: {HDF5_PATH}")
        
        print(f"\n<NOTICE> The file has been created successfully.")
        
    change_log(FILENAME, HDF5_PATH, log_mode = "create")
    print(f"<LOG {FILENAME}> Log group initialized.")

def get_local_git_username():
    try:
        # Runs 'git config user.name' in the shell
        result = subprocess.run(["git", "config", "user.name"], stdout=subprocess.PIPE, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Unknown"
    
# -------- MAIN ----------
def main():
    # Checking HDF5 file
    print(f"\n<NOTICE> Locating {FILENAME}...")
    if not HDF5_PATH.exists():
        print(f"<NOTICE> {FILENAME} does not exist in the \'/dataset\' directory.")
        print(f"<NOTICE> Creating {FILENAME} at {HDF5_PATH}...")
        make_file(FILENAME, HDF5_PATH)
    else:
        print(f"<NOTICE> {FILENAME} located at {HDF5_PATH}.")
        print("<NOTICE> Proceeding to the next step...")

    TIMEFRAME_TARGET = "D1"
    
    with h5py.File(HDF5_PATH, mode = "a") as hdf5_file:
        # Get or create the group
        if "TIMEFRAME" in hdf5_file:
            hdf5_timeframe = hdf5_file["TIMEFRAME"]
        else:
            hdf5_timeframe = hdf5_file.create_group("TIMEFRAME")
            print("GROUP CREATED: TIMEFRAME")
        
        # Get or create the target timeframe group
        if TIMEFRAME_TARGET in hdf5_timeframe:
            hdf5_timeframe_target = hdf5_timeframe[TIMEFRAME_TARGET]
        else:
            hdf5_timeframe_target = hdf5_timeframe.create_group(TIMEFRAME_TARGET)
            print(f"TARGET TIMEFRAME CREATED: {TIMEFRAME_TARGET}")
        
        print(list(hdf5_timeframe_target.keys()))
    
    print(datetime.now())
        
        
            
            
            
            
    
    # with h5py.File(HDF5_PATH, mode = "a") as hdf5_file:
    #     pass


# -------- SYSTEM CALLING ----------
if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")