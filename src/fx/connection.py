# ---------- FILE DESCRIPTION ----------
f"""({__name__}'s file description.) 
This module tests the connection between the client and MT5 server through MT5 API.
"""

# -------- IMPORTS ----------
import os 
import MetaTrader5 as mt5

from dotenv import load_dotenv, find_dotenv

# -------- CONSTANTS ----------
_ENV_PATH = find_dotenv(filename="keys.env", 
                        raise_error_if_not_found=True)
load_dotenv(dotenv_path = _ENV_PATH)

_MT5_CRED = {"account": int(os.environ["mt5_account"]),
            "password": os.environ["mt5_password"],
            "investor": os.environ["mt5_investor"],
            "server": os.environ["mt5_server"]}

# -------- FUNCTIONS ----------
def mt5_connected():
    print("<NOTICE> Attempting to connect to MetaTrader5...")

    if not getattr(mt5, "initialize")():
        print("<NOTICE> Initialization failed. Error code = ", getattr(mt5, "last_error")())
        print("\n<TERM> Session terminated.")
        
        getattr(mt5, "shutdown")()
        return False
    
    print("<NOTICE> Checking credentials...")
    
    login = getattr(mt5, "login")
    authorized = login(login    = _MT5_CRED["account"], 
                       password = _MT5_CRED["password"], 
                       server   = _MT5_CRED["server"])
    
    if authorized:
        print("<NOTICE> Connected to account #{} on server {}".format(_MT5_CRED["account"], 
                                                                      _MT5_CRED["server"]))
    else:
        print("<NOTICE> Failed to connect to account #{}. Error code: {}".format(_MT5_CRED["account"], 
                                                                                 getattr(mt5, "last_error")()))
        print("\n<TERM> Session terminated.")
        getattr(mt5, "shutdown")()
        return False 
    
    return True

# -------- SYSTEM CALLING ----------
if __name__ != "__main__":
    print(f"<IMPORT> Importing {__file__}...")

if __name__ == "__main__":
    mt5_connected()