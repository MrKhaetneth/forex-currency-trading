import MetaTrader5 as mt5
import pandas as pd

SYMBOL = "EURUSD"
PRICE_DELTA = 0.00005

def main():
    
    if not mt5.initialize():
        print("===== Error Log =====")
        print("MetaTrader5 initialization failed.")
        mt5.shutdown()
        return 0
    
    if not mt5.symbol_select(SYMBOL, True):
        print("===== Error Log =====")
        print("Failed to get the ticker/symbol.")
        mt5.shutdown()
        return 0
    
    price_info = mt5.symbol_info_tick(SYMBOL)
    if price_info is None:
        print("===== Error Log =====")
        print(f"Failed to get price information for {SYMBOL}.")
        mt5.shutdown()
        return 0         

    # Display price_info object
    print(type(price_info))
    print(price_info)
    
    starting_price = price_info.bid
    price_level_high = starting_price + PRICE_DELTA 
    price_level_low = starting_price - PRICE_DELTA
    
    print(f"The starting price is {starting_price}.")
    print(f"The high price is {price_level_high}.")
    print(f"The low price is {price_level_low}.")
    
    mt5.shutdown()


if __name__ != "__main__":
    print(f"Importing {__name__}...")

if __name__ == "__main__":
    main() 