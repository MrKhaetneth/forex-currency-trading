print("Hey, this file is for MT5 API!")

import pandas as pd
from pymt5linux import MetaTrader5

# 1. Connect to your Windows MT5 bridge
mt5 = MetaTrader5(host="localhost", port=8001)

if not mt5.initialize():
    print("Failed to initialize MT5 bridge connection.")
    mt5.shutdown()
    exit()

# 2. Grab the last 10 hourly bars for EUR/USD
print("Fetching EURUSD data...")
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 10)

# 3. Clean up the connection right away
mt5.shutdown()

# 4. Process and print the data
if rates is not None and len(rates) > 0:
    df = pd.DataFrame(rates)
    # Convert time from seconds timestamp to readable dates
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    print("\n--- Recent EURUSD Hourly Bars ---")
    print(df[['time', 'open', 'high', 'low', 'close', 'tick_volume']])
else:
    print("No data retrieved. Make sure the symbol is visible in your MT5 Market Watch.")