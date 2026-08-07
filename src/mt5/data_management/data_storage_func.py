# -------- IMPORTS ----------
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import h5py
import pytz
import sys

from datetime import datetime
from pathlib import Path

import utility_func as uf

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

# Sample download spec used by this test
SYMBOL = "EURUSD"
MT5_TIMEFRAME = mt5.TIMEFRAME_D1
TIME_START = datetime(2024, 1, 1, tzinfo=TIMEZONE)
TIME_END = datetime(2024, 2, 1, tzinfo=TIMEZONE)

# Reverse lookup: mt5.TIMEFRAME_* value -> its suffix string, e.g. mt5.TIMEFRAME_D1 -> "D1"
_TIMEFRAME_NAMES = {
    value: name.replace("TIMEFRAME_", "")
    for name, value in vars(mt5).items()
    if name.startswith("TIMEFRAME_")
}

_ROW_DTYPE = np.dtype([
    ("time", "i8"),
    ("open", "f8"),
    ("high", "f8"),
    ("low", "f8"),
    ("close", "f8"),
    ("tick_volume", "i8"),
    ("spread", "i4"),
    ("real_volume", "i8"),
])


# -------- FUNCTIONS ----------
def resolve_timeframe_name(mt5_timeframe: int) -> str:
    """Convert an mt5.TIMEFRAME_* constant into its string suffix, e.g. mt5.TIMEFRAME_D1 -> "D1".

    Args:
        mt5_timeframe (int): One of the mt5.TIMEFRAME_* constants.

    Returns:
        str: The timeframe's suffix, used as the HDF5 group name under "TIMEFRAME/".
    """
    timeframe_name = _TIMEFRAME_NAMES.get(mt5_timeframe)
    if timeframe_name is None:
        raise ValueError(f"<ERROR> Unrecognized MetaTrader5 timeframe constant: {mt5_timeframe}.")
    return timeframe_name


def download_ohlcv(symbol: str, mt5_timeframe: int, time_start: datetime, time_end: datetime) -> pd.DataFrame:
    """Download OHLCV price history from MetaTrader5 for a single symbol/timeframe.

    Args:
        symbol (str): MetaTrader5 symbol name, e.g. "EURUSD".
        mt5_timeframe (int): One of the mt5.TIMEFRAME_* constants.
        time_start (datetime): Start of the requested time range (UTC).
        time_end (datetime): End of the requested time range (UTC).

    Returns:
        pd.DataFrame: Columns [time, open, high, low, close, tick_volume, spread, real_volume].
    """
    print(f"\n<NOTICE> Downloading {symbol} ({resolve_timeframe_name(mt5_timeframe)}) from {time_start} to {time_end}...")
    rates = mt5.copy_rates_range(symbol, mt5_timeframe, time_start, time_end)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"<ERROR> No data returned for {symbol}. MT5 error: {mt5.last_error()}.")

    df = pd.DataFrame(rates)
    print(f"<NOTICE> Downloaded {len(df)} rows.")
    return df


def _time_to_datetime(time_values) -> pd.Series:
    """Coerce a `time` column (either unix-second integers or already-datetime) to datetime64."""
    series = pd.Series(time_values)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_datetime(series, unit="s")
    return pd.to_datetime(series)


def _df_to_structured(df: pd.DataFrame) -> np.ndarray:
    """Convert an OHLCV DataFrame into the compound numpy array stored in HDF5."""
    arr = np.empty(len(df), dtype=_ROW_DTYPE)
    for name in _ROW_DTYPE.names:
        if name == "time":
            arr["time"] = _time_to_datetime(df["time"]).values.astype("datetime64[s]").astype("int64")
        else:
            arr[name] = df[name].values
    return arr


def _structured_to_df(arr: np.ndarray) -> pd.DataFrame:
    """Reverse of _df_to_structured. `time` stays as unix-second integers (internal representation)."""
    return pd.DataFrame({name: arr[name] for name in arr.dtype.names})


def _merge_chronologically(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """Union two OHLCV tables, keeping the newest value for any overlapping `time`, sorted ascending."""
    merged = pd.concat([existing_df, new_df], axis=0, join="outer")
    merged = merged.drop_duplicates(subset=["time"], keep="last")
    merged = merged.sort_values(by=["time"]).reset_index(drop=True)
    return merged


def save_dataset(hdf5_path: Path, symbol: str, mt5_timeframe: int, df: pd.DataFrame) -> str:
    """Save/merge an OHLCV DataFrame into the HDF5 file under "TIMEFRAME/<suffix>/<symbol>".

    Never truncates the file (opened in append mode "a"). If a dataset already exists at
    that path, its rows are merged with the newly downloaded ones and re-sorted so `time`
    is ascending; otherwise a new dataset/group is created.

    Args:
        hdf5_path (Path): Path to the HDF5 file (created if it doesn't exist).
        symbol (str): MetaTrader5 symbol name, used as the dataset name.
        mt5_timeframe (int): One of the mt5.TIMEFRAME_* constants, used to derive the group name.
        df (pd.DataFrame): Newly downloaded OHLCV rows to save.

    Returns:
        str: The internal HDF5 dataset path the data was written to.
    """
    timeframe_name = resolve_timeframe_name(mt5_timeframe)
    group_path = f"TIMEFRAME/{timeframe_name}"
    dataset_path = f"{group_path}/{symbol}"
    new_arr = _df_to_structured(df)

    hdf5_path.parent.mkdir(parents=True, exist_ok=True)
    is_new_file = not hdf5_path.exists()
    if is_new_file:
        with h5py.File(hdf5_path, "w") as f:  # only truncates because the file doesn't exist yet
            pass
        uf.change_log(hdf5_path.name, hdf5_path, log_mode="create")

    with h5py.File(hdf5_path, "a") as f:  # "a" never overwrites/truncates the whole file
        group = f.require_group(group_path)

        if symbol in group:
            print(f"<NOTICE> Existing dataset found at '{dataset_path}'. Merging with newly downloaded data...")
            existing_arr = group[symbol][:]
            merged_df = _merge_chronologically(_structured_to_df(existing_arr), _structured_to_df(new_arr))
            merged_arr = _df_to_structured(merged_df)
            del group[symbol]  # replacing this dataset's content only, not the file
        else:
            print(f"<NOTICE> No existing dataset at '{dataset_path}'. Creating a new one...")
            merged_arr = new_arr

        chunk_rows = min(len(merged_arr), 8192) or 1
        dset = group.create_dataset(
            symbol,
            data=merged_arr,
            chunks=(chunk_rows,),
            maxshape=(None,),
            compression="gzip",
            compression_opts=4,
        )
        dset.attrs["columns"] = list(merged_arr.dtype.names)
        dset.attrs["time_unit"] = "unix_seconds"
        dset.attrs["source"] = "MetaTrader5"
        dset.attrs["n_rows"] = len(merged_arr)

    new_time = _time_to_datetime(df["time"])
    uf.change_log(hdf5_path.name, hdf5_path, log_mode="append", log_description={
        "SYMBOL": symbol,
        "TIMEFRAME": timeframe_name,
        "TIME_START": new_time.min(),
        "TIME_END": new_time.max(),
    })

    return dataset_path


def load_dataset(hdf5_path: Path, symbol: str, mt5_timeframe: int) -> pd.DataFrame:
    """Load a previously saved dataset back into a DataFrame.

    Args:
        hdf5_path (Path): Path to the HDF5 file.
        symbol (str): MetaTrader5 symbol name.
        mt5_timeframe (int): One of the mt5.TIMEFRAME_* constants.

    Returns:
        pd.DataFrame: Columns [time, open, high, low, close, tick_volume, spread, real_volume],
            with `time` as a datetime64 column.
    """
    dataset_path = f"TIMEFRAME/{resolve_timeframe_name(mt5_timeframe)}/{symbol}"
    with h5py.File(hdf5_path, "r") as f:
        if dataset_path not in f:
            raise KeyError(f"<ERROR> '{dataset_path}' not found in {hdf5_path}.")
        arr = f[dataset_path][:]

    df = _structured_to_df(arr)
    df["time"] = _time_to_datetime(df["time"])
    return df


def remove_dataset(hdf5_path: Path, symbol: str, mt5_timeframe: int) -> str:
    """Delete a previously saved dataset from the HDF5 file and record the removal in the change log.

    Args:
        hdf5_path (Path): Path to the HDF5 file.
        symbol (str): MetaTrader5 symbol name.
        mt5_timeframe (int): One of the mt5.TIMEFRAME_* constants.

    Returns:
        str: The internal HDF5 dataset path that was removed.
    """
    timeframe_name = resolve_timeframe_name(mt5_timeframe)
    dataset_path = f"TIMEFRAME/{timeframe_name}/{symbol}"

    with h5py.File(hdf5_path, "a") as f:
        if dataset_path not in f:
            raise KeyError(f"<ERROR> '{dataset_path}' not found in {hdf5_path}.")
        del f[dataset_path]

    print(f"<NOTICE> Removed dataset '{dataset_path}' from {hdf5_path}.")
    uf.change_log(hdf5_path.name, hdf5_path, log_mode="remove", log_description={
        "SYMBOL": symbol,
        "TIMEFRAME": timeframe_name,
    })

    return dataset_path


# -------- MAIN ----------
# Example
def main():
    # -------- OUTPUT ----------
    print("===========================")
    print("|   TEST: DATA STORAGE    |")
    print("===========================\n")
    print("Script Purpose: Download a sample OHLCV dataset from MetaTrader5 and verify the HDF5 save/merge behavior.")

    # Testing connection and authorization with MetaTrader5
    if not check_status():
        quit()

    # -------- DOWNLOAD SAMPLE DATA ----------
    df = download_ohlcv(SYMBOL, MT5_TIMEFRAME, TIME_START, TIME_END)
    print(df.head())

    # -------- SAVE / MERGE INTO HDF5 ----------
    dataset_path = save_dataset(HDF5_PATH, SYMBOL, MT5_TIMEFRAME, df)
    print(f"\n<NOTICE> Data saved at '{dataset_path}' inside {HDF5_PATH}.")

    # -------- VERIFY ----------
    reloaded = load_dataset(HDF5_PATH, SYMBOL, MT5_TIMEFRAME)
    print(f"<NOTICE> Reloaded {len(reloaded)} rows from '{dataset_path}'.")
    print(f"<CHECK> Rows are chronologically ascending: {pd.Series(reloaded['time']).is_monotonic_increasing}")

    mt5.shutdown()
    print("\n<TERM> Session terminated.")


# -------- SYSTEM CALLING ----------
if __name__ == "__main__":
    main()
else:
    print(f"<IMPORT> Importing {__file__}...")
