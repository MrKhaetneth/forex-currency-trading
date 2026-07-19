import MetaTrader5 as mt5
import os 

from dotenv import load_dotenv 
from pathlib import Path

load_dotenv(dotenv_path = Path("keys.env"))
mt5_acc = {"account": int(os.getenv("mt5_account")),
            "password": os.getenv("mt5_password"),
            "investor": os.getenv("mt5_investor"),
            "server": os.getenv("mt5_server")}

def main():
    if not mt5.initialize():
        print("Initialization failed, error code = ", mt5.last_error())
        quit()
    
    authorized = mt5.login(mt5_acc["account"], password = mt5_acc["password"], server = "HantecMarketsMU-MT5")
    if authorized:
        print("connected to account #{}".format(mt5_acc["account"]))
        
        print("===== MetaTrader5 Account Details =====")
        # display trading account info as is 
        print(mt5.account_info())
        # display trading account data in the form of a list
        account_info_dict = mt5.account_info()._asdict()
        for prop in account_info_dict:
            print("  {}={}".format(prop, account_info_dict[prop]))
    else:
        print("failed to connect at account #{}, error code: {}".format(mt5_acc["account"], mt5.last_error()))
        quit()
    
    # display data on connection status, server name and trading account
    print(f"Terminal Info: {mt5.terminal_info()}")
    # display data on MetaTrader 5 version
    print(f"MetaTrader5 Version: {mt5.version()}")
    
    mt5.shutdown()

if __name__ != "__main__":
    print(f"Importing {__name__}...")

if __name__ == "__main__":
    main()