import unittest 
import sqlite3 

# Need to create a testing.db

class Calculator():
    def add_num(self, num1, num2):
        return num1 + num2

class TestNumber(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1+2,3)
        self.assertEqual(2+2,4)
    
    def testMultiply(self):
        self.assertEqual(1*1,1)
        self.assertEqual(1*3,3)

class MyTest(unittest.TestCase):
    def test_hello_world(self):
        myCal = Calculator()
        self.assertEqual(myCal.add_num(1, 2), 3)

if __name__ == "__main__":
    # unittest.main()
    
    testcon = sqlite3.connect(":memory:")
    print(testcon == True)