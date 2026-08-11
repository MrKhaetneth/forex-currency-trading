# -------- IMPORTS ----------
from pathlib import Path 

import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import seaborn as sns
import pandas as pd
import numpy as np

from project_packages.data_storage_func import load_dataset
from scipy.stats import kurtosis

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
    sample_ohlcv: pd.DataFrame = load_dataset(HDF5_PATH, SYMBOL, MT5_TIMEFRAME)
    sample_ohlcv["log_return"] = np.log( sample_ohlcv["close"] / sample_ohlcv["close"].shift(1) )
    df = sample_ohlcv.dropna()
    
    log_return = df["log_return"].to_numpy()
    
    sns.set_style("darkgrid")
    print(f"<NOTICE> Kurtosis (Fisher definition: normal dist = 0.0): {kurtosis(log_return, fisher = True)}.")
    sns.histplot(log_return, kde = True)
    plt.show()
    

# -------- SYSTEM CALLING ----------
if __name__ == "__main__":
    main()
else:
    print(f"<IMPORT> Importing {__file__}...")
