# -------- IMPORTS ----------
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import subprocess
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
# For HDF5 input
STRING_DATATYPE = h5py.string_dtype(encoding = "utf-8")
TIMEZONE = pytz.timezone("Etc/UTC")

# -------- FUNCTIONS ----------
def get_local_git_username() -> str:
    """Get the user's local git username for logging.

    Returns:
        str: User's local git username or Unknown.
    """
    try:
        # Runs 'git config user.name' in the shell
        result = subprocess.run(["git", "config", "user.name"], stdout=subprocess.PIPE, text=True, check=True)
        return result.stdout.strip()
    
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Unknown"

def change_log(FILENAME: str, HDF5_PATH: Path, log_mode: str, log_description: dict = {}):
    """Add change log into HDF5 file. There will be 6 colums: ["LOG_TIME", "ACTION", "BY", "AT", "SYMBOL_TCST", "SYMBOL_TCET"].
        - LOG_TIME: The time at which the log was recorded.
        - ACTION: What you did.
        - BY: Who you are.
        - AT: Where did the action took place? (If you update the table of a symbol, this column will also record which symbol you updated.)
        - SYMBOL_TCST: The starting time of the downloaded table of a symbol's pricing history (before merging). (Table Change Starting Time)
        - SYMBOL_TCET: The ending time of the downloaded table of a symbol's pricing history (before merging). (Table Change Ending Time)

    Args:
        FILENAME (str): The name of the HDF5 file.
        HDF5_PATH (Path): Location (as a Path object) of the HDF5 file.
        log_mode (str): Mode of writing the change log.
        log_description (dict): Additional description about this change log.
    """
    log_mode = log_mode.strip().lower()
    writer = get_local_git_username()
    match log_mode:
        case "create":
            with h5py.File(HDF5_PATH, mode = "a") as logfile:
                if "change_log" in logfile:
                    del logfile["change_log"]
                dummy_header = np.zeros((0, 6), dtype = object)
                log_data = logfile.create_dataset(
                    "change_log",
                    data = dummy_header,
                    maxshape = (None, 6),
                    chunks = True,
                    dtype = STRING_DATATYPE
                )
                log_time = datetime.now().replace(microsecond = 0).strftime("%Y-%m-%d %H:%M:%S")
                action = "Create File"
                by = writer
                at = f"dataset/{FILENAME}"
                symbol_tcst = ""
                symbol_tcet = ""
                
                initial_row = np.array([[log_time, action, by, at, symbol_tcst, symbol_tcet]], dtype = object)
                log_data.resize(log_data.shape[0] + initial_row.shape[0], axis = 0) # Add another row to the table for substitution
                log_data[-1:] = initial_row
            
            print(f"\n<{FILENAME}-LOG> Log file initialized. You may view change logs at dataset \"change_log\" within {FILENAME}.")

        case "append":
            pass
        
        case "delete" | "remove":
            pass 

def parse_datetime(time_input: str) -> datetime:
    """Check the format of the input time.

    Args:
        time_input (str): User's input of time.

    Raises:
        ValueError: The user's input format does not match the valid/required format of datetime.

    Returns:
        datetime: A valid datetime object in UTC.
    """
    # Strip whitespace from the edges of the input
    clean_input = time_input.strip()
    
    # Define acceptable format patterns from most specific to least specific
    formats = [
        "%Y-%m-%d %H:%M:%S",  # 2026-07-26 19:45:30
        "%Y-%m-%d %H:%M",     # 2026-07-26 19:45
        "%Y-%m-%d"           # 2026-07-26
    ]
    
    # Try parsing the string against each format
    for fmt in formats:
        try:
            return_date = datetime.strptime(clean_input, fmt)
            return return_date.replace(tzinfo = TIMEZONE)
        except ValueError:
            continue
            
    # Raise an error if none of the formats matched
    raise ValueError(f"<ERROR> Could not parse '{time_input}'. Format not recognized.")

def verify_timeframe(mt5_timeframe: str):
    """Check whether the user's input MetaTrader5 timeframe is valid or not.

    Args:
        mt5_timeframe (str): User's input timeframe.

    Returns:
        list: MetaTrader5.TIMEFRAME_X object and the string of validated timeframe which will be use in the future.
        None: None if the user's input is invalid/unrecognized.
    """
    mt5_timeframe = mt5_timeframe.strip().lower()
    correct_timeframe = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M10', 'M12', 'M15', 'M20', 'M30',
                         'H1', 'H2', 'H3', 'H4', 'H6', 'H8', 'H12', 'D1', 'W1', 'MN1']
    mt5_timeref = {
        "M1": mt5.TIMEFRAME_M1,
        "M2": mt5.TIMEFRAME_M2,
        "M3": mt5.TIMEFRAME_M3,
        "M4": mt5.TIMEFRAME_M4,
        "M5": mt5.TIMEFRAME_M5,
        "M6": mt5.TIMEFRAME_M6,
        "M10": mt5.TIMEFRAME_M10,
        "M12": mt5.TIMEFRAME_M12,
        "M15": mt5.TIMEFRAME_M15,
        "M20": mt5.TIMEFRAME_M20,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H2": mt5.TIMEFRAME_H2,
        "H3": mt5.TIMEFRAME_H3,
        "H4": mt5.TIMEFRAME_H4,
        "H6": mt5.TIMEFRAME_H6,
        "H8": mt5.TIMEFRAME_H8,
        "H12": mt5.TIMEFRAME_H12,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    for timeframe in correct_timeframe:
        if mt5_timeframe == timeframe.lower():
            return [mt5_timeref[timeframe], timeframe]
        
    print("<ERROR> Invalid input. Please retry.")
    return None

def verify_symbol(user_input: str, symbols_name: list[str]) -> str | None:
    """_summary_

    Args:
        user_input (str): _description_
        symbols_name (list[str]): _description_

    Returns:
        str | None: _description_
    """
    # If user's input is an valid symbol in the first place
    user_input = user_input.strip().lower()
    symbols_name_lower = [name.lower() for name in symbols_name]
    
    # Return the symbol name if the user's input 
    if user_input in symbols_name_lower:
        sym_index = symbols_name_lower.index(user_input)
        return symbols_name[sym_index]

    # If user's input is not a valid symbol
    match user_input:
        case "help":
            print()
            print("<NOTICE> The following are available inputs/commands:")
            print("help          -> List all the available commands.")
            print("dump          -> Prints out all the downloadable symbols from MetaTrader5.")
            print("terminate     -> Abruptly terminates the program")
            print("search        -> Search for symbols with a part of it containing user's input.")

        case "dump":
            print("<NOTICE> The script is dumping out all the downloadable symbols from MetaTrader5, sorted alphanumerically...")
            for symbol_name in symbols_name:
                print(symbol_name)
        
        case "terminate":
            print("\n<TERM> Session terminated.")
            quit()
        
        case "search":
            print("<NOTICE> Input part of the symbols you are looking for. For example, if you look for symbols with \"EUR\", just type in \"EUR\".")
    
    return None

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

def get_input(FILENAME: str) -> dict:
    """_summary_

    Args:
        FILENAME (str): _description_

    Returns:
        dict: _description_
    """
    return_dict = {}
    
    # Get symbols
    print(f"\n<NOTICE> You may now input a symbol within MetaTrader5 that you wanted to add to {FILENAME}.")
    print("<HINT> Write \"help\" to list all the available commands/inputs.")
    
    symbols = mt5.symbols_get()
    symbols_name = sorted([symbol.name for symbol in symbols])
    
    continue_loop = True
    while continue_loop: # Loop until user terminate the program or input a valid symbol
        user_input = input("\n<INPUT> Your input (case-insensitive): ")
        continue_loop = (verify_symbol(user_input, symbols_name) is None)
    
    symbol = verify_symbol(user_input, symbols_name)
    print(f"\n<NOTICE> The requested symbol is {symbol}.")
    print("<NOTICE> The user may now input the starting time of interest.")
    
    return_dict.update({"SYMBOL": symbol})
    
    # Get start and end time
    continue_loop = True
    while continue_loop:
        time_start = input("\n<INPUT> Starting time stamp (the formats are \"YYYY-MM-DD\" or \"YYYY-MM-DD hh:mm:ss\"): ")
        time_start = parse_datetime(time_start)
        continue_loop = not isinstance(time_start, datetime)
    continue_loop = True
    while continue_loop:
        time_end = input("\n<INPUT> End time stamp (the formats are \"YYYY-MM-DD\" or \"YYYY-MM-DD hh:mm:ss\"): ")
        time_end = parse_datetime(time_end)
        continue_loop = not isinstance(time_end, datetime)
    
    return_dict.update({"TIME_START": time_start, "TIME_END": time_end})
    
    # Specify timeframe
    print("\n<NOTICE> You are required to specify the time frame of each bar in the pricing history.")
    print("<NOTICE> The following list enumerates the available timeframes:")
    print("Minutes: M1, M2, M3, M4, M5, M6, M10, M12, M15, M20, M30.")
    print("Hours: H1, H2, H3, H4, H6, H8, H12.")
    print("Miscellaneous: D1, W1, MN1.")
    print(f"<HINT> For example, W1 refers to the 1 week long timeframe for each bar data point in the downloaded pricing history of {symbol}.")
    continue_loop = True
    while continue_loop:
        mt5_timeframe = input("\n<INPUT> Your input (has to be one of the valid timeframe above, e.g. \"M5\" or \"MN1\", etc.): ")
        mt5_timeframe = verify_timeframe(mt5_timeframe)
        continue_loop = (mt5_timeframe is None)
    
    return_dict.update({"MT5_TIMEFRAME": mt5_timeframe[0], "HDF5_TIMEFRAME": mt5_timeframe[1]})
    
    return return_dict

def mt5_download_rates(SYMBOL: str, MT5_TIMEFRAME, HDF5_TIMEFRAME: str, TIME_START: datetime, TIME_END: datetime) -> pd.DataFrame:
    """_summary_

    Args:
        SYMBOL (str): _description_
        MT5_TIMEFRAME (_type_): _description_
        HDF5_TIMEFRAME (str): _description_
        TIME_START (datetime): _description_
        TIME_END (datetime): _description_

    Returns:
        pd.DataFrame: _description_
    """
    print(f"\n<NOTICE> Attempting to download {SYMBOL} with timeframe {HDF5_TIMEFRAME} during {TIME_START} until {TIME_END}...")
    try: 
        mt5_rates = mt5.copy_rates_range(SYMBOL, MT5_TIMEFRAME, TIME_START, TIME_END)
        print("<NOTICE> Data downloaded.")
    except Exception as err:
        print(f"<ERROR> Something went wrong during the download. Error code: {mt5.last_error()}.")
        raise Exception(f"\n<ERROR> Python diagnostic: {err}.")
    
    mt5_rates = pd.DataFrame(mt5_rates)
    mt5_rates['time'] = pd.to_datetime(mt5_rates["time"], unit = 's')
    
    return mt5_rates

# -------- SYSTEM CALLING ----------
if __name__ != "__main__":
    print(f"Importing {__file__}...")

else:
    print("Why are you running this file?")