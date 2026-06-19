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

_SZ200_1D_ALL_CACHE: dict[str, dict[str, DATA_1D]] = {}

def GET_SZ200_1D_PREVIOUS(stock_code: str, date, index) -> DATA_1D | None:
    trading_date = TRADING_DATE_PREVIOUS(date, index)
    if trading_date is None:
        return None

    if stock_code in _SZ200_1D_ALL_CACHE and trading_date in _SZ200_1D_ALL_CACHE[stock_code]:
        return _SZ200_1D_ALL_CACHE[stock_code][trading_date]

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

    if stock_code in _SZ200_1D_ALL_CACHE and trading_date in _SZ200_1D_ALL_CACHE[stock_code]:
        return _SZ200_1D_ALL_CACHE[stock_code][trading_date]

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
    if not _SZ200_1D_ALL_CACHE:
        stock_codes = STOCK_CODES()
        for stock_code in stock_codes:
            _SZ200_1D_ALL_CACHE[stock_code] = {}
            with open(f"{PATH_AIDATA_1D()}/{stock_code}", "r") as file:
                for line in file:
                    parts = line.strip().split('|')
                    _SZ200_1D_ALL_CACHE[stock_code][parts[0]] = DATA_1D(
                        date=parts[0],
                        open=float(parts[1]),
                        high=float(parts[2]),
                        low=float(parts[3]),
                        close=float(parts[4]),
                        volume=float(parts[5]),
                        amount=float(parts[6]))
    return _SZ200_1D_ALL_CACHE

def UPDATE_1D_ALL():
    shutil.rmtree(PATH_AIDATA_1D(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_1D())

    stock_codes = STOCK_CODES()

    tq.initialize(__file__)
    df = tq.get_market_data( field_list=["Open","High", "Low", "Close", "Volume", "Amount"], stock_list=stock_codes, start_time=START_DATE, end_time='', count=-1, dividend_type='front', period='1d', fill_data=True )
    _SZ200_1D_ALL_CACHE.clear()
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for stock_code, stock_cache in zip(stock_codes, pool.map(partial(GENERATE_1D, dataframe=df), stock_codes)):  # pyright: ignore[reportArgumentType]
            _SZ200_1D_ALL_CACHE[stock_code] = stock_cache

def GENERATE_1D(stock_code:str, dataframe:pd.DataFrame) -> dict[str, DATA_1D]:
    stock_cache: dict[str, DATA_1D] = {}
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
            stock_cache[trading_date] = DATA_1D(
                date=_date, open=float(_open), high=float(_high),
                low=float(_low), close=float(_close),
                volume=float(_volume), amount=float(_amount))
    return stock_cache

if __name__ == "__main__":
    UPDATE_1D_ALL()
