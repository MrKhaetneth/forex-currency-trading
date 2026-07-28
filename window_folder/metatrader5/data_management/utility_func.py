# -------- IMPORTS ----------
import MetaTrader5 as mt5
import pandas as pd
import subprocess
import pytz
import csv
import sys

from datetime import datetime
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
from check_env import check_status
del parent_dir

# -------- CONSTANTS ----------
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

_LOG_COLUMNS = ["LOG_TIME", "ACTION", "BY", "SYMBOL", "TIMEFRAME", "TCST", "TCET"]

def log_csv_path(HDF5_PATH: Path) -> Path:
    """Return the change-log CSV path that sits alongside a given HDF5 file (same folder, "<stem>_change_log.csv").

    Args:
        HDF5_PATH (Path): Location (as a Path object) of the HDF5 file.

    Returns:
        Path: Location of that file's change-log CSV.
    """
    return HDF5_PATH.with_name(f"{HDF5_PATH.stem}_change_log.csv")

def _append_log_row(HDF5_PATH: Path, row: list):
    """Append a single row to the change-log CSV, writing the header first if the file is new.

    Args:
        HDF5_PATH (Path): Location (as a Path object) of the HDF5 file the log belongs to.
        row (list): Values matching the order of _LOG_COLUMNS.
    """
    csv_path = log_csv_path(HDF5_PATH)
    csv_path.parent.mkdir(parents = True, exist_ok = True)
    is_new_file = not csv_path.exists()

    with open(csv_path, mode = "a", newline = "", encoding = "utf-8") as f:
        csv_writer = csv.writer(f)
        if is_new_file:
            csv_writer.writerow(_LOG_COLUMNS)
        csv_writer.writerow(row)

def change_log(FILENAME: str, HDF5_PATH: Path, log_mode: str, log_description: dict = {}):
    """Record an entry into the CSV change log kept alongside the HDF5 file (see log_csv_path).

    Kept as a plain CSV (rather than inside the HDF5 file) so non-technical collaborators can
    open it directly in Excel/Notepad without needing h5py/pandas, and so it diffs cleanly in git.

    There are 7 columns (see _LOG_COLUMNS): ["LOG_TIME", "ACTION", "BY", "SYMBOL", "TIMEFRAME", "TCST", "TCET"].
        - LOG_TIME: The time at which the log was recorded.
        - ACTION: What was done ("File Creation", "Add Data", "Remove Dataset").
        - BY: The local git username of whoever performed the action.
        - SYMBOL: The symbol affected by the action (blank for "File Creation").
        - TIMEFRAME: The HDF5 timeframe group affected, e.g. "D1" (blank for "File Creation").
        - TCST: For "Add Data", the starting time of the newly downloaded table (before merging). (Table Change Starting Time)
        - TCET: For "Add Data", the ending time of the newly downloaded table (before merging). (Table Change Ending Time)

    Args:
        FILENAME (str): The name of the HDF5 file.
        HDF5_PATH (Path): Location (as a Path object) of the HDF5 file.
        log_mode (str): One of "create", "append", "delete"/"remove".
        log_description (dict): For "append": {"SYMBOL", "TIMEFRAME", "TIME_START", "TIME_END"}.
            For "delete"/"remove": {"SYMBOL", "TIMEFRAME"}. Unused for "create".
    """
    log_mode = log_mode.strip().lower()
    writer_name = get_local_git_username()
    log_time = datetime.now().replace(microsecond = 0).strftime("%Y-%m-%d %H:%M:%S")

    match log_mode:
        case "create":
            _append_log_row(HDF5_PATH, [log_time, "File Creation", writer_name, "", "", "", ""])
            print(f"\n<{FILENAME}-LOG> Log initialized at {log_csv_path(HDF5_PATH).name}.")

        case "append":
            symbol = log_description.get("SYMBOL", "")
            timeframe = log_description.get("TIMEFRAME", "")
            tcst = str(log_description.get("TIME_START", ""))
            tcet = str(log_description.get("TIME_END", ""))

            _append_log_row(HDF5_PATH, [log_time, "Add Data", writer_name, symbol, timeframe, tcst, tcet])
            print(f"<{FILENAME}-LOG> Logged data addition for {symbol} ({timeframe}).")

        case "delete" | "remove":
            symbol = log_description.get("SYMBOL", "")
            timeframe = log_description.get("TIMEFRAME", "")

            _append_log_row(HDF5_PATH, [log_time, "Remove Dataset", writer_name, symbol, timeframe, "", ""])
            print(f"<{FILENAME}-LOG> Logged dataset removal for {symbol} ({timeframe}).")

        case _:
            raise ValueError(f"<ERROR> Unrecognized log_mode: '{log_mode}'.")

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