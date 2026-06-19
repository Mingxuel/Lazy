import os
import sys
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal, ROUND_HALF_UP
from functools import partial
from multiprocessing import Manager
from typing import Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *
from AICode.MarcoAPI.SZ2001D import *

_TOP_CACHE: dict[str, set[str]] = {}
_WORKER_TOP_CACHE: Optional[dict[str, set[str]]] = None  # worker 进程中由 initializer 注入

def INIT_TOP(proxy: dict[str, set[str]]):
    """ProcessPoolExecutor initializer: 将 Manager.dict 代理注入 worker 全局变量"""
    global _WORKER_TOP_CACHE
    _WORKER_TOP_CACHE = proxy  # pyright: ignore[reportConstantRedefinition]

_MANAGER: Optional[Manager] = None

def GET_TOP() -> dict[str, set[str]]:
    """创建并返回跨进程共享的 Manager.dict 代理（从已填充的 _TOP_CACHE 构建）"""
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = Manager()  # pyright: ignore[reportConstantRedefinition]
    proxy: dict[str, set[str]] = _MANAGER.dict()  # pyright: ignore[reportOptionalMemberAccess]
    proxy.update(_TOP_CACHE)
    return proxy

def UPDATE_TOP():
    stock_codes = STOCK_CODES()
    trading_dates = TRADING_DATES()
    with ProcessPoolExecutor(max_workers=32) as pool:
        list(pool.map(partial(GENERATE_TOP, stock_codes), trading_dates))
    _TOP_CACHE.clear()
    for trading_date in trading_dates:
        top_file = f"{PATH_AIDATA_TOP()}/{trading_date}"
        if os.path.exists(top_file):
            with open(top_file, "r") as file:
                _TOP_CACHE[trading_date] = {line.strip() for line in file}
        else:
            _TOP_CACHE[trading_date] = set()

def GENERATE_TOP(stock_codes: list[str], trading_date: str):
    print("UPDATE_TOP: " + trading_date)
    pre_trading_date = TRADING_DATE_PREVIOUS(trading_date, 1)
    if pre_trading_date is None:
        return
    top_file = f"{PATH_AIDATA_TOP()}/{trading_date}"
    if os.path.exists(top_file):
        return
    with open(top_file, "w") as file:
        for stock_code in stock_codes:
            record = GET_SZ200_1D_PREVIOUS(stock_code, trading_date, 0)
            pre_record = GET_SZ200_1D_PREVIOUS(stock_code, pre_trading_date, 0)
            if record is None or pre_record is None:
                continue
            if _CALCULATE_TOP(record.close, pre_record.close):
                file.write(f"{stock_code}\n")

def _CALCULATE_TOP(close: float, pre_close: float):
    decimal = Decimal(float(pre_close) * 1.1)
    decimal = decimal.quantize(Decimal(f'0.{"0"*3}'), rounding=ROUND_HALF_UP)
    _limit_price = float(decimal.quantize(Decimal(f'0.{"0"*2}'), rounding=ROUND_HALF_UP))

    return abs(close - _limit_price) < 0.001 or close >= _limit_price

def UPDATE_TOPPED():
    stock_codes = STOCK_CODES()
    trading_dates = TRADING_DATES()
    with ProcessPoolExecutor(max_workers=32) as pool:
        list(pool.map(partial(GENERATE_TOPPED, stock_codes), trading_dates))

def GENERATE_TOPPED(stock_codes: list[str], trading_date: str):
    print("UPDATE_TOPPED: " + trading_date)
    pre_trading_date = TRADING_DATE_PREVIOUS(trading_date, 1)
    if pre_trading_date is None:
        return
    top_file = f"{PATH_AIDATA_TOPPED()}/{trading_date}"
    if os.path.exists(top_file):
        return
    with open(top_file, "w") as file:
        for stock_code in stock_codes:
            record = GET_SZ200_1D_PREVIOUS(stock_code, trading_date, 0)
            pre_record = GET_SZ200_1D_PREVIOUS(stock_code, pre_trading_date, 0)
            if record is None or pre_record is None:
                continue
            if _CALCULATE_TOP(record.high, pre_record.close) and _CALCULATE_TOP(record.close, pre_record.close) is False:
                file.write(f"{stock_code}\n")

def IS_TOP(stock_code: str, trading_date: str):
    # 主进程：使用模块级普通 dict
    stock_set = _TOP_CACHE.get(trading_date)
    if stock_set is not None:
        return stock_code in stock_set
    # worker 进程：使用 Manager.dict 代理（通过 initializer 注入）
    if _WORKER_TOP_CACHE is not None:
        stock_set = _WORKER_TOP_CACHE.get(trading_date)
        if stock_set is not None:
            return stock_code in stock_set
    # 缓存未填充时，回退到文件读取（兜底）
    top_file = f"{PATH_AIDATA_TOP()}/{trading_date}"
    if not os.path.exists(top_file):
        return False
    with open(top_file, "r") as file:
        for line in file:
            if line.strip() == stock_code:
                return True
    return False

if __name__ == "__main__":
    UPDATE_TOPPED()
