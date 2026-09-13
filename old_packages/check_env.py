# -------- IMPORTS ----------
import os 
import MetaTrader5 as mt5

from dotenv import load_dotenv, find_dotenv

# -------- CONSTANTS ----------
ENV_PATH = find_dotenv(filename="keys.env", raise_error_if_not_found=True)
load_dotenv(dotenv_path = ENV_PATH)

MT5_CRED = {"account": int(os.getenv("mt5_account")),
            "password": os.getenv("mt5_password"),
            "investor": os.getenv("mt5_investor"),
            "server": os.getenv("mt5_server")}

# -------- FUNCTIONS ----------
def check_status():
    print("<NOTICE> Attempting to connect to MetaTrader5...")
    if not mt5.initialize():
        print("<NOTICE> Initialization failed. Error code = ", mt5.last_error())
        print("\n<TERM> Session terminated.")
        mt5.shutdown()
        return False
    
    print("<NOTICE> Checking credentials...")
    authorized = mt5.login(MT5_CRED["account"], password = MT5_CRED["password"], server = MT5_CRED["server"])
    if authorized:
        print("<NOTICE> Connected to account #{} on server {}".format(MT5_CRED["account"], MT5_CRED["server"]))
    else:
        print("<NOTICE> Failed to connect to account #{}. Error code: {}".format(MT5_CRED["account"], mt5.last_error()))
        print("\n<TERM> Session terminated.")
        mt5.shutdown()
        return False 
    
    return True

# -------- SYSTEM CALLING ----------
if __name__ != "__main__":
    print(f"<IMPORT> Importing {__file__}...")

else:
    print("Why are you running this file?")