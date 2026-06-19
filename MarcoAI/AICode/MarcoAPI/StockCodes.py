import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.Path import *

sys.path.append(PATH_TDX())
from tqcenter import tq

_STOCK_CODES_CACHE: dict[str, list[str]] = {}
_STOCK_CODES_ALL_CACHE: dict[str, list[str]] = {}

def STOCK_CODES():
    if "data" not in _STOCK_CODES_CACHE:
        if os.path.exists(PATH_AIDATA_STOCK_CODES()):
            with open(PATH_AIDATA_STOCK_CODES(), "r") as file:
                _STOCK_CODES_CACHE["data"] = file.read().splitlines()
        else:
            tq.initialize(__file__)
            stock_codes = tq.get_stock_list_in_sector(block_code = 'SZ200', block_type = 1, list_type = 0)
            with open(PATH_AIDATA_STOCK_CODES(), "w") as file:
                file.write("\n".join(stock_codes))
            _STOCK_CODES_CACHE["data"] = stock_codes
    return _STOCK_CODES_CACHE["data"]

def STOCK_CODES_ALL():
    if "data" not in _STOCK_CODES_ALL_CACHE:
        if os.path.exists(PATH_AIDATA_STOCK_CODES_ALL()):
            with open(PATH_AIDATA_STOCK_CODES_ALL(), "r", encoding="utf-8") as file:
                _STOCK_CODES_ALL_CACHE["data"] = file.read().splitlines()
        else:
            tq.initialize(__file__)
            data: list[str] = []
            with open(PATH_AIDATA_STOCK_CODES_ALL(), "w", encoding="utf-8") as file:
                stock_codes = tq.get_stock_list_in_sector(block_code = 'SZ200', block_type = 1, list_type = 1)
                for stock_code in stock_codes:
                    content = stock_code["Code"]+ "|" + stock_code["Name"]
                    data.append(content)
                    file.write(content + "\n")
            _STOCK_CODES_ALL_CACHE["data"] = data
    return _STOCK_CODES_ALL_CACHE["data"]

if __name__ == "__main__":
    print(STOCK_CODES_ALL())
