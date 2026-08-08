import os
from re import T
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *
from AICode.MarcoAPI.SZ2001D import UPDATE_1D_ALL
from AICode.MarcoAPI.SZ200Bottom import UPDATE_BOTTOM
from AICode.MarcoAPI.SZ200Top import UPDATE_TOP, UPDATE_TOPPED
from AICode.MarcoAPI.SZ200Target import UPDATE_TARGET_31, UPDATE_TARGET_311, UPDATE_TARGET_HISTORY, UPDATE_TARGET_TOP_1, UPDATE_TARGET_TOP_11, UPDATE_TARGET_TOP_31, UPDATE_TARGET_TOP_311
from AICode.MarcoAPI.SZ200Motion1D import UPDATE_1D_WIN_COUNT, UPDATE_1D_PANIC_INDEX, UPDATE_1D_MOTION_COUNT, UPDATE_1D_PRICE
from AICode.MarcoAPI.UI.UITarget import SHOW_TARGET_1D
from AICode.MarcoAPI.SZ2005M import UPDATE_5M_ALL

if __name__ == "__main__":
    SHOW_ONLY = False
    #SHOW_ONLY = True
    if SHOW_ONLY:
        SHOW_TARGET_1D()
        exit(0)
    print("UPDATE_TRADING_DATES BEGIN")
    UPDATE_TRADING_DATES()
    print("UPDATE_TRADING_DATES END")
    print("UPDATE_1D_ALL BEGIN")
    UPDATE_1D_ALL()
    print("UPDATE_1D_ALL END")
    UPDATE_5M_ALL()
    print("UPDATE_TOP BEGIN")
    UPDATE_TOP()
    print("UPDATE_TOP END")
    print("UPDATE_TOPPED BEGIN")
    UPDATE_TOPPED()
    print("UPDATE_TOPPED END")
    print("UPDATE_BOTTOM BEGIN")
    UPDATE_BOTTOM()
    print("UPDATE_BOTTOM END")
    print("UPDATE_1D_WIN_COUNT BEGIN")
    UPDATE_1D_WIN_COUNT()
    print("UPDATE_1D_WIN_COUNT END")
    print("UPDATE_1D_PANIC_INDEX BEGIN")
    UPDATE_1D_PANIC_INDEX()
    print("UPDATE_1D_PANIC_INDEX END")
    print("UPDATE_1D_MOTION_COUNT BEGIN")
    UPDATE_1D_MOTION_COUNT()
    print("UPDATE_1D_MOTION_COUNT END")
    print("UPDATE_1D_PRICE BEGIN")
    UPDATE_1D_PRICE()
    print("UPDATE_1D_PRICE END")
    print("UPDATE_TARGET_31 BEGIN")
    UPDATE_TARGET_31()
    print("UPDATE_TARGET_31 END")
    print("UPDATE_TARGET_311 BEGIN")
    UPDATE_TARGET_311()
    print("UPDATE_TARGET_311 END")
    print("UPDATE_TARGET_HISTORY BEGIN")
    UPDATE_TARGET_HISTORY()
    print("UPDATE_TARGET_HISTORY END")
    print("UPDATE_TARGET_TOP_1 BEGIN")
    UPDATE_TARGET_TOP_1()
    print("UPDATE_TARGET_TOP_1 END")
    print("UPDATE_TARGET_TOP_11 BEGIN")
    UPDATE_TARGET_TOP_11()
    print("UPDATE_TARGET_TOP_11 END")
    print("SHOW_TARGET_1D BEGIN")
    SHOW_TARGET_1D()
    print("SHOW_TARGET_1D END")
