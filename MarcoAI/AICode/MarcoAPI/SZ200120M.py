from concurrent.futures import ProcessPoolExecutor
import os
import shutil
import sys
from functools import partial

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *

sys.path.append(PATH_TDX())
from tqcenter import tq

def UPDATE_120M_ALL():
    

if __name__ == "__main__":
    UPDATE_120M_ALL()
