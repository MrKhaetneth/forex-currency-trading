import MetaTrader5 as mt5
print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)

import pandas as pd
pd.set_option('display.max_columns', 500) # number of columns to be displayed
pd.set_option('display.width', 1500)      # max table width to display

import os 
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path = Path("keys.env"))
mt5_init = {"login": os.getenv("login"),
            "password": os.getenv("password"),
            "investor": os.getenv("investor")}

from datetime import datetime
import pytz

SYMBOL = "EURUSD"
date_begin = datetime(2024, 1, 1)
date_end   = datetime(2024, 6, 1)

def main():
    # connects to the running MT5 terminal
    if not mt5.initialize(**mt5_init):
        print("Initialization failed, error code = ", mt5.last_error())
        quit()
        
    # set time zone to UTC
    timezone = pytz.timezone("Etc/UTC")
    # create 'datetime' object in UTC time zone to avoid the implementation of a local time zone offset
    utc_from = datetime(2020, 1, 10, tzinfo = timezone)
    # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
    rates = mt5.copy_rates_from("EURUSD", mt5.TIMEFRAME_H4, utc_from, 10)

    # shutdown connection
    mt5.shutdown()

    print("Display obtained data 'as is'")
    for rate in rates:
        print(rate)
    
    # create DataFrame out of the obtained data
    rates_frame = pd.DataFrame(rates)
    # convert time in seconds into the datetime format
    rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
   
    # display data
    print("\nDisplay dataframe with data")
    print(rates_frame)

# ----- System Calling -----

if __name__ != "__main__":
    print(f"Importing {__name__}...")

if __name__ == "__main__":
    main()