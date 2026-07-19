import MetaTrader5 as mt5
print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)

import pandas as pd
pd.set_option('display.max_columns', 500) # number of columns to be displayed
pd.set_option('display.width', 1500)      # max table width to display

import sys
from pathlib import Path
# make python looks inside other folders (to get check_status function from check_env)
parent_dir = Path(__file__).resolve().parent.parent 
sys.path.append(str(parent_dir))

from check_env import check_status

from datetime import datetime
import pytz

# Set timezone
TIMEZONE = pytz.timezone("Etc/UTC")
UTC_FROM = datetime(2025, 6, 1, tzinfo = TIMEZONE)

def main():
    if not check_status():
        print("Error in checking credentials...")
        return 

    # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
    rates = mt5.copy_rates_from("EURUSD", mt5.TIMEFRAME_M1, UTC_FROM, 100)
    
    # shut down connection to the MetaTrader 5 terminal
    mt5.shutdown()
    
    # create DataFrame out of the obtained data
    rates_frame = pd.DataFrame(rates)
    # convert time in seconds into the datetime format
    rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
                            
    # display data
    print("\nDisplay dataframe with data")
    print(rates_frame)
    print(mt5.last_error()) 
   
if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")