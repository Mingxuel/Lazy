import os
import sys
from decimal import Decimal, ROUND_HALF_UP

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *
from AICode.MarcoAPI.SZ2001D import *

def UPDATE_TOP():
    dataframe = GET_SZ200_1D_ALL()
    stock_codes = STOCK_CODES()
    trading_dates = TRADING_DATES()
    for trading_date in trading_dates:
        i = trading_dates.index(trading_date)
        if i == 0:
            continue
        pre_trading_date = trading_dates[i-1]
        top_file = f"{PATH_AIDATA_TOP()}/{trading_date}"
        if os.path.exists(top_file):
            continue
        with open(top_file, "w") as file:
            for stock_code in stock_codes:
                close = dataframe["Close"].loc[trading_date, stock_code]
                pre_close = dataframe["Close"].loc[pre_trading_date, stock_code]
                if _CALCULATE_TOP(close, pre_close):
                    file.write(f"{stock_code}\n")

def _CALCULATE_TOP(close: str, pre_close: str):
    _close: float = float(close)
    _pre_close = float(pre_close)
    decimal = Decimal(float(_pre_close) * 1.1)
    decimal = decimal.quantize(Decimal(f'0.{"0"*3}'), rounding=ROUND_HALF_UP)
    _limit_price = float(decimal.quantize(Decimal(f'0.{"0"*2}'), rounding=ROUND_HALF_UP))

    return abs(_close - _limit_price) < 0.001 or _close >= _limit_price

def IS_TOP(stock_code: str, trading_date: str):
    top_file = f"{PATH_AIDATA_TOP()}/{trading_date}"
    if not os.path.exists(top_file):
        return False
    with open(top_file, "r") as file:
        for line in file:
            if line.strip() == stock_code:
                return True
    return False

if __name__ == "__main__":
    UPDATE_TOP()
