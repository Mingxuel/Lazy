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

def GET_SZ200_5M(stock_code:str):
    tq.initialize(__file__)
    df = tq.get_market_data( field_list=["Open","High", "Low", "Close", "Volume", "Amount"], stock_list=[stock_code], start_time=START_DATE, end_time='', count=-1, dividend_type='none', period='5m', fill_data=True )
    return df

def GET_SZ200_5M_ALL():    
    stock_codes = STOCK_CODES()
    df = tq.get_market_data( field_list=["Open","High", "Low", "Close", "Volume", "Amount"], stock_list=stock_codes, start_time=START_DATE, end_time='', count=-1, dividend_type='none', period='5m', fill_data=True )
    return df

def UPDATE_5M_ALL():
    shutil.rmtree(PATH_AIDATA_5M(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_5M())
    tq.initialize(__file__)
    stock_codes = STOCK_CODES()
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
        list(pool.map(partial(GENERATE_5M), stock_codes))  # pyright: ignore[reportArgumentType]

def GENERATE_5M(stock_code:str):
    tq.initialize(__file__)
    dataframe = tq.get_market_data( field_list=["Open","High", "Low", "Close", "Volume", "Amount"], stock_list=[stock_code], start_time=START_DATE, end_time='', count=-1, dividend_type='none', period='5m', fill_data=True )
    with open(f"{PATH_AIDATA_5M()}/{stock_code}", "w") as file:
        trading_times = dataframe["Close"].index.tolist()
        for trading_time in trading_times:
            _date = trading_time
            _open = dataframe["Open"].loc[trading_time, stock_code]
            _high = dataframe["High"].loc[trading_time, stock_code]
            _low = dataframe["Low"].loc[trading_time, stock_code]
            _close = dataframe["Close"].loc[trading_time, stock_code]
            _volume = dataframe["Volume"].loc[trading_time, stock_code]
            _amount = dataframe["Amount"].loc[trading_time, stock_code]
            file.write(f"{_date}|{_open}|{_high}|{_low}|{_close}|{_volume}|{_amount}\n")

if __name__ == "__main__":
    UPDATE_5M_ALL()
