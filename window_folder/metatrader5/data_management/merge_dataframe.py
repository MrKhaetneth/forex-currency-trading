# -------- IMPORTS ----------
import MetaTrader5 as mt5
import pandas as pd
import pytz
import sys

import matplotlib.pyplot as plt

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

# MetaTrader5
SYMBOL = "EURUSD"
START1 = datetime(2022, 1, 1, tzinfo = TIMEZONE)
START2 = datetime(2021, 1, 1, tzinfo = TIMEZONE)
END1 = datetime(2024, 1, 1, tzinfo = TIMEZONE)
END2 = datetime(2023, 1, 1, tzinfo = TIMEZONE)

# -------- FUNCTIONS ----------

# -------- MAIN ----------
def main():
    # Testing connection and authorization with MetaTrader5
    if not check_status():
        quit()
    
    rate1 = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_D1, START1, END1)
    rate2 = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_D1, START2, END2)
    rate1 = pd.DataFrame(rate1)
    rate2 = pd.DataFrame(rate2)
    rate1['time'] = pd.to_datetime(rate1["time"], unit = 's')
    rate2['time'] = pd.to_datetime(rate2["time"], unit = 's')
    
    print(START1 > START2)
    print(START2 > START1)
    
    print("===== TABLE 1 =====")
    print(rate1.head(5))
    print(rate1.tail(5))
    
    print("\n===== TABLE 2 =====")
    print(rate2.head(5))
    print(rate2.tail(5))
    
    # UNION
    rate3 = pd.concat([rate1, rate2], axis = 0, join = "outer")
    rate3 = rate3.drop_duplicates()
    rate3 = rate3.sort_values(by = ["time"])
    
    print("\n===== UNION =====")
    print(rate3.head(5))
    print(rate3.tail(5))
    
    
    plt.figure(figsize = (10, 6))
    plt.step(rate1['time'], rate1['open'], color = 'red', alpha = 0.3)
    plt.step(rate2['time'], rate2['open'], color = 'blue', alpha = 0.3)
    plt.step(rate3['time'], rate3['open'], color = 'black', alpha = 0.3)
    
    plt.show()
        
    mt5.shutdown()

# -------- SYSTEM CALLING ----------
if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")