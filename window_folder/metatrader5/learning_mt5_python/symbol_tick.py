import MetaTrader5 as mt5
import pandas as pd
import sys

from pathlib import Path

# make python looks inside other folders (to get check_status function from check_env)
parent_dir = Path(__file__).resolve().parent.parent 
sys.path.append(str(parent_dir))

from check_env import check_status

def main():
    if not check_status():
        print("Error in checking credentials...")
    
    # attempt to enable the display of the GBPUSD in MarketWatch
    selected=mt5.symbol_select("GBPUSD",True)
    if not selected:
        print("Failed to select GBPUSD")
        mt5.shutdown()
        quit()
    
    # display the last GBPUSD tick
    lasttick=mt5.symbol_info_tick("GBPUSD")
    print(lasttick)
    # display tick field values in the form of a list
    print("Show symbol_info_tick(\"GBPUSD\")._asdict():")
    symbol_info_tick_dict = mt5.symbol_info_tick("GBPUSD")._asdict()
    for prop in symbol_info_tick_dict:
        print("  {}={}".format(prop, symbol_info_tick_dict[prop]))

    mt5.shutdown()

if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")