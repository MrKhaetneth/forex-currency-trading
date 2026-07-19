import MetaTrader5 as mt5
import pandas as pd
import sys

from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent 
sys.path.append(str(parent_dir))

from check_env import check_status

from datetime import datetime
import pytz

SYMBOL = "EURUSD"
TIMEZONE = pytz.timezone("Etc/UTC")
UTC_FROM = datetime(2020, 1, 1, tzinfo = TIMEZONE)
UTC_TO   = datetime(2020, 1, 10, tzinfo = TIMEZONE)

def main():
    if not check_status():
        print("Error in checking credentials...")
        quit()
    
    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_D1, UTC_FROM, UTC_TO)
    
    mt5.shutdown()
    
    rates_df = pd.DataFrame(rates)
    rates_df["time"] = pd.to_datetime(rates_df["time"], unit = 's')
    
    print(rates_df.head(10))
    
if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")