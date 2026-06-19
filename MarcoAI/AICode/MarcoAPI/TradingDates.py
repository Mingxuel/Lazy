from ast import Index
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

_TRADING_DATES_CACHE: dict[str, list[str]] = {}

def TRADING_DATES():
    if "data" not in _TRADING_DATES_CACHE:
        with open(PATH_AIDATA_TRADING_DATES(), "r") as file:
            _TRADING_DATES_CACHE["data"] = file.read().splitlines()
    return _TRADING_DATES_CACHE["data"]

def UPDATE_TRADING_DATES():
    tq.initialize(__file__)
    trading_dates = tq.get_trading_dates(market = 'SH', start_time = START_DATE, end_time = '', count = -1)
    with open(PATH_AIDATA_TRADING_DATES(), "w") as file:
        file.write("\n".join(trading_dates))
    _TRADING_DATES_CACHE["data"] = trading_dates
    return trading_dates

def TRADING_DATE_PREVIOUS(date, index):
    trading_dates = TRADING_DATES()
    index = trading_dates.index(date) - index
    if index < 0:
        return None
    return trading_dates[index]

def TRADING_DATE_AFTER(date, index):
    trading_dates = TRADING_DATES()
    index = trading_dates.index(date) + index
    if index > trading_dates.__len__() - 1:
        return None
    return trading_dates[index]

if __name__ == "__main__":
    UPDATE_TRADING_DATES()
