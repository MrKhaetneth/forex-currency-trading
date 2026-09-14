import unittest
import sqlite3
import sys 
import MetaTrader5 as mt5
import pytz 
import pandas as pd

from datetime import datetime 
from fx.connection import mt5_connected
from fx.database import read_db, write_db 

def check_db_connection(db_path: str) -> bool:
    try: 
        db_connection = sqlite3.connect(db_path)
        db_connection.cursor()
        db_connection.close()
        return True 
    except Exception as ex:
        db_connection.close()
        return False 

# Test MetaTrader5 and in-memory database connection
class testConnection(unittest.TestCase):
    def testMetaTrader5Connection(self):
        self.assertTrue(mt5_connected(), msg = "Could not initialize connection with MetaTrader5. Check internet connection or check whether MetaTrader5 is installed or not.")
        getattr(mt5, "shutdown")()
        
        print("<NOTICE> MetaTrader5 connection test passed.")
    
    def testDatabaseConnectionInMemory(self):
        # Use in-RAM to create and test database
        db_path = ":memory:"
        self.assertTrue(
            check_db_connection(db_path), 
            msg = "Can't connect to in-memory database via sqlite3."
        )
        
        print("<NOTICE> In-memory database connection test passed.")
    
    def testDatabaseConnectionExistingDatabase(self):
        # Connection with real testing.db
        db_path = "tests/data/test.db"
        self.assertTrue(
            check_db_connection(db_path),
            msg = "Can't connect to exisitng testing database which is supposed to be at tests/data/test.db."
        )
        
        print("<NOTICE> Existing database connection teset passed.")
        

# Test writing and reading on an existing database 
class testDatabaseIO(unittest.TestCase):
    # Should also include testing with num_bars get_ohlcv feature 
    def testIO(self):
        db_path = "tests/data/test.db"
        symbol = "EURUSD"
        table_name = f"test{symbol}"
        
        timezone = pytz.timezone("Etc/UTC")
        date_from = datetime(2026, 6, 10, tzinfo = timezone)
        date_to = datetime(2026, 7, 11, tzinfo = timezone)
        
        if not mt5_connected():
            sys.exit(1)
        
        test_table = write_db.get_ohlcv(symbol, "D1", date_from, date_to)
        
        with sqlite3.connect(db_path) as db_connection:
            existing_table = read_db.get_table_content(db_connection, symbol)
            
            cursor = db_connection.cursor()
            write_db.add_table(db_connection, cursor, table_name, test_table)
            
            pd.testing.assert_frame_equal(test_table, existing_table)
            cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
            db_connection.commit()
        
        print("<NOTICE> Writing table into and reading a table on a sample database ran without failure.")
        
        getattr(mt5, "shutdown")()
    

if __name__ == "__main__":
    unittest.main()