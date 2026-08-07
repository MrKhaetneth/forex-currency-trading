# -------- IMPORTS ----------
from pathlib import Path 

import MetaTrader5 as mt5

from mt5.packages.data_storage_func import load_dataset

# -------- CONSTANTS ----------

# HDF5 file path
FILENAME = "MT5CurrencyHistory.h5"
SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent.parent.parent / "dataset"
HDF5_PATH = DATASET_DIR / FILENAME

# MT5 symbol
SYMBOL = "EURUSD"
MT5_TIMEFRAME = mt5.TIMEFRAME_D1

# -------- MAIN ----------
def main():
    sample_ohlcv = load_dataset(HDF5_PATH, SYMBOL, MT5_TIMEFRAME)
    print(sample_ohlcv)

# -------- SYSTEM CALLING ----------
if __name__ == "__main__":
    main()
else:
    print(f"<IMPORT> Importing {__file__}...")
