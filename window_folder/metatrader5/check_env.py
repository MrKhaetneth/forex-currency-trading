import MetaTrader5 as mt5
import os 

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path = Path("keys.env"))
mt5_cred = {"account": int(os.getenv("mt5_account")),
            "password": os.getenv("mt5_password"),
            "investor": os.getenv("mt5_investor"),
            "server": os.getenv("mt5_server")}

def check_status():
    print("Checking credentials...\n")
    if not mt5.initialize():
        print("Initialization failed, error code = ", mt5.last_error(), "\n")
        mt5.shutdown()
        return False
    
    authorized = mt5.login(mt5_cred["account"], password = mt5_cred["password"], server = mt5_cred["server"])
    if authorized:
        print("connected to account #{} on server {}\n".format(mt5_cred["account"], mt5_cred["server"]))
    else:
        print("failed to connect at account #{}, error code: {}\n".format(mt5_cred["account"], mt5.last_error()))
        mt5.shutdown()
        return False 
    
    return True
    
if __name__ != "__main__":
    print(f"Importing {__file__}...")
else:
    print("Why are you running this file?")