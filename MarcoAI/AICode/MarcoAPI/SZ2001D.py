from concurrent.futures import ProcessPoolExecutor
import os
import shutil
import sys
import pandas as pd
from functools import partial

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *
from AICode.MarcoAPI.Data import DATA_1D

sys.path.append(PATH_TDX())
from tqcenter import tq

def GET_SZ200_1D_PREVIOUS(stock_code: str, date, index) -> DATA_1D | None:
    trading_date = TRADING_DATE_PREVIOUS(date, index)
    if trading_date is None:
        return None

    with open(f"{PATH_AIDATA_1D()}/{stock_code}", "r") as file:
        for line in file:
            if line.startswith(trading_date):
                parts = line.strip().split('|')
                return DATA_1D(
                    date=parts[0],
                    open=float(parts[1]),
                    high=float(parts[2]),
                    low=float(parts[3]),
                    close=float(parts[4]),
                    volume=float(parts[5]),
                    amount=float(parts[6]),
                )

def GET_SZ200_1D_AFTER(stock_code: str, date, index) -> DATA_1D | None:
    trading_date = TRADING_DATE_AFTER(date, index)
    if trading_date is None:
        return None
        
    with open(f"{PATH_AIDATA_1D()}/{stock_code}", "r") as file:
        for line in file:
            if line.startswith(trading_date):
                parts = line.strip().split('|')
                return DATA_1D(
                    date=parts[0],
                    open=float(parts[1]),
                    high=float(parts[2]),
                    low=float(parts[3]),
                    close=float(parts[4]),
                    volume=float(parts[5]),
                    amount=float(parts[6]),
                )

def GET_SZ200_1D_ALL():
    tq.initialize(__file__)
    
    stock_codes = STOCK_CODES()
    df = tq.get_market_data( field_list=["Open","High", "Low", "Close", "Volume", "Amount"], stock_list=stock_codes, start_time=START_DATE, end_time='', count=-1, dividend_type='front', period='1d', fill_data=True )
    return df

def UPDATE_1D_ALL():
    shutil.rmtree(PATH_AIDATA_1D(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_1D())

    stock_codes = STOCK_CODES()

    tq.initialize(__file__)
    df = tq.get_market_data( field_list=["Open","High", "Low", "Close", "Volume", "Amount"], stock_list=stock_codes, start_time=START_DATE, end_time='', count=-1, dividend_type='front', period='1d', fill_data=True )
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
        list(pool.map(partial(GENERATE_1D, dataframe=df), stock_codes))  # pyright: ignore[reportArgumentType]

def GENERATE_1D(stock_code:str, dataframe:pd.DataFrame):
    with open(f"{PATH_AIDATA_1D()}/{stock_code}", "w") as file:
        trading_dates = TRADING_DATES()
        for trading_date in trading_dates:
            _date = trading_date
            _open = dataframe["Open"].loc[trading_date, stock_code]
            _high = dataframe["High"].loc[trading_date, stock_code]
            _low = dataframe["Low"].loc[trading_date, stock_code]
            _close = dataframe["Close"].loc[trading_date, stock_code]
            _volume = dataframe["Volume"].loc[trading_date, stock_code]
            _amount = dataframe["Amount"].loc[trading_date, stock_code]
            file.write(f"{_date}|{_open}|{_high}|{_low}|{_close}|{_volume}|{_amount}\n")

if __name__ == "__main__":
    UPDATE_1D_ALL()
