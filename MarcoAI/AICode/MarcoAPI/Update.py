import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *
from AICode.MarcoAPI.SZ2001D import UPDATE_1D_ALL
from AICode.MarcoAPI.SZ2005M import UPDATE_5M_ALL
from AICode.MarcoAPI.SZ200Bottom import UPDATE_BOTTOM
from AICode.MarcoAPI.SZ200Top import UPDATE_TOP
from AICode.MarcoAPI.SZ200Target import UPDATE_TARGET_31, UPDATE_TARGET_311

sys.path.append(PATH_TDX())
from tqcenter import tq

if __name__ == "__main__":
    UPDATE_TRADING_DATES()
    UPDATE_1D_ALL()
    UPDATE_5M_ALL()
    UPDATE_TOP()
    UPDATE_BOTTOM()
    UPDATE_TARGET_31()
    UPDATE_TARGET_311()