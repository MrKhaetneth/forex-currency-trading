import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import pytz

print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)

pd.set_option('display.max_columns', 500) # number of columns to be displayed
pd.set_option('display.width', 1500)      # max table width to display

SYMBOL = "EURUSD"
date_begin = datetime(2024, 1, 1)
date_end   = datetime(2024, 6, 1)

# connects to the running MT5 terminal
if not mt5.initialize():
    print("Initialization failed, error code = ", mt5.last_error())
    quit()
    
# set time zone to UTC
timezone = pytz.timezone("Etc/UTC")
# create 'datetime' object in UTC time zone to avoid the implementation of a local time zone offset
utc_from = datetime(2020, 1, 10, tzinfo=timezone)
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
rates_frame['time']=pd.to_datetime(rates_frame['time'], unit='s')
                           
# display data
print("\nDisplay dataframe with data")
print(rates_frame)

# --------- OUTPUT -----------
# MetaTrader5 package author:  MetaQuotes Ltd.
# MetaTrader5 package version:  5.0.5735
# Display obtained data 'as is'
# (1577822400, 1.12281, 1.12282, 1.12157, 1.12162, 1823, 18, 0)
# (1577836800, 1.12088, 1.12215, 1.12081, 1.12188, 996, 50, 0)
# (1577923200, 1.12187, 1.12245, 1.11636, 1.11708, 24787, 50, 0)
# (1578009600, 1.11709, 1.1179999999999999, 1.1125099999999999, 1.1155599999999999
# , 27368, 50, 0)
# (1578182400, 1.1165, 1.11675, 1.11585, 1.11604, 1590, 50, 0)
# (1578268800, 1.11601, 1.12055, 1.1157, 1.11954, 25240, 50, 0)
# (1578355200, 1.11954, 1.1197, 1.11335, 1.1154, 27883, 50, 0)
# (1578441600, 1.11538, 1.11682, 1.11021, 1.11129, 32942, 50, 0)
# (1578528000, 1.11141, 1.11204, 1.10931, 1.11092, 26140, 50, 0)
# (1578614400, 1.11093, 1.11291, 1.10852, 1.11209, 23287, 50, 0)

# Display dataframe with data
#                  time     open     high      low    close  tick_volume  spread
# real_volume
# 0 2019-12-31 20:00:00  1.12281  1.12282  1.12157  1.12162         1823      180
# 1 2020-01-01 00:00:00  1.12088  1.12215  1.12081  1.12188          996      500
# 2 2020-01-02 00:00:00  1.12187  1.12245  1.11636  1.11708        24787      500
# 3 2020-01-03 00:00:00  1.11709  1.11800  1.11251  1.11556        27368      500
# 4 2020-01-05 00:00:00  1.11650  1.11675  1.11585  1.11604         1590      500
# 5 2020-01-06 00:00:00  1.11601  1.12055  1.11570  1.11954        25240      500
# 6 2020-01-07 00:00:00  1.11954  1.11970  1.11335  1.11540        27883      500
# 7 2020-01-08 00:00:00  1.11538  1.11682  1.11021  1.11129        32942      500
# 8 2020-01-09 00:00:00  1.11141  1.11204  1.10931  1.11092        26140      500
# 9 2020-01-10 00:00:00  1.11093  1.11291  1.10852  1.11209        23287      500