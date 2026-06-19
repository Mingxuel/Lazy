import os
import sys
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal, ROUND_HALF_UP
from functools import partial

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *
from AICode.MarcoAPI.SZ2001D import *

def UPDATE_BOTTOM():
    stock_codes = STOCK_CODES()
    trading_dates = TRADING_DATES()
    with ProcessPoolExecutor(max_workers=32) as pool:
        list(pool.map(partial(GENERATE_BOTTOM, stock_codes), trading_dates))

def GENERATE_BOTTOM(stock_codes: list[str], trading_date: str):
    print("UPDATE_BOTTOM: " + trading_date)
    pre_trading_date = TRADING_DATE_PREVIOUS(trading_date, 1)
    if pre_trading_date is None:
        return
    bottom_file = f"{PATH_AIDATA_BOTTOM()}/{trading_date}"
    if os.path.exists(bottom_file):
        return
    with open(bottom_file, "w") as file:
        for stock_code in stock_codes:
            record = GET_SZ200_1D_PREVIOUS(stock_code, trading_date, 0)
            pre_record = GET_SZ200_1D_PREVIOUS(stock_code, pre_trading_date, 0)
            if record is None or pre_record is None:
                continue
            if _CALCULATE_BOTTOM(record.close, pre_record.close):
                file.write(f"{stock_code}\n")

def _CALCULATE_BOTTOM(close: float, pre_close: float):
    decimal = Decimal(float(pre_close) * 0.9)
    decimal = decimal.quantize(Decimal(f'0.{"0"*3}'), rounding=ROUND_HALF_UP)
    _limit_price = float(decimal.quantize(Decimal(f'0.{"0"*2}'), rounding=ROUND_HALF_UP))

    return abs(close - _limit_price) < 0.001

def IS_BOTTOM(stock_code: str, trading_date: str):
    bottom_file = f"{PATH_AIDATA_BOTTOM()}/{trading_date}"
    if not os.path.exists(bottom_file):
        return False
    with open(bottom_file, "r") as file:
        for line in file:
            if line.strip() == stock_code:
                return True
    return False

if __name__ == "__main__":
    UPDATE_BOTTOM()
