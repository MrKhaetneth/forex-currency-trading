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
    
    # number of financial instruments available in MT5
    num_sym = mt5.symbols_total()
    if num_sym > 0:
        print("Total symbols = ", num_sym)
    else:
        print("Symbols not found.")
    
    # Get all symbols
    symbols = mt5.symbols_get()
    print("Symbols: ", len(symbols))
    
    count = 0
    for s in symbols:
        count += 1
        print("{}. {}".format(count, s.name))
        if count == 5: 
            break
    print()
    
    # get symbols containing RU in their names (like regex?)
    sym_ru = mt5.symbols_get("*RU*")
    print("Number of those with RU: ", len(sym_ru))
    for s in sym_ru:
        print(s.name)
    print()
    
    # get symbols whose name does not contain USD, EUR, JPY, and GBP
    sym_group = mt5.symbols_get(group = "*,!*USD*,!*EUR*,!*JPY*,!*GBP*")
    print("Number of symbols without USD, EUR, JPY, and GBP: ", len(sym_group))
    print(sym_group[0].name, ":", sym_group[0])
    print()
    
    # attempt to enable the display of the EURCAD in MarketWatch
    selected = mt5.symbol_select("EURCAD",True)
    if not selected:
        print("Failed to select EURCAD, error code =",mt5.last_error())
    else:
        # get info from specified financial instrument (EURCAD in this case)
        symbol_info = mt5.symbol_info("EURCAD")
        print("EURCAD: currency_base =",symbol_info.currency_base,"  currency_profit =",symbol_info.currency_profit,"  currency_margin =",symbol_info.currency_margin)
        print()
    
        # get symbol properties in the form of a dictionary
        print("Show symbol_info()._asdict():")
        symbol_info_dict = symbol_info._asdict()
        for prop in symbol_info_dict:
            print("  {} = {}".format(prop, symbol_info_dict[prop]))
        print()
    
        # convert the dictionary into DataFrame and print
        df=pd.DataFrame(list(symbol_info_dict.items()), columns = ['property','value'])
        print("symbol_info_dict() as dataframe:")
        print(df)    

    mt5.shutdown()

if __name__ == "__main__":
    main()
else:
    print(f"Importing {__name__}...")