import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *

sys.path.append(PATH_TDX())
from tqcenter import tq

def STOCK_CODES():
    tq.initialize(__file__)
    stock_codes = tq.get_stock_list_in_sector(block_code = 'SZ200', block_type = 1, list_type = 0)
    return stock_codes

def STOCK_CODES_ALL():
    tq.initialize(__file__)
    stock_codes = tq.get_stock_list_in_sector(block_code = 'SZ200', block_type = 1, list_type = 1)
    return stock_codes

if __name__ == "__main__":
    print(STOCK_CODES())
