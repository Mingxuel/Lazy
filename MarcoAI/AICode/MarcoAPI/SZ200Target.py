from concurrent.futures import ProcessPoolExecutor
from functools import partial
import os
import shutil
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *
from AICode.MarcoAPI.Data import DATA_1D_TARGET
from AICode.MarcoAPI.SZ2001D import GET_SZ200_1D_PREVIOUS
from AICode.MarcoAPI.SZ200Bottom import IS_BOTTOM
from AICode.MarcoAPI.SZ200Top import IS_TOP, INIT_TOP, GET_TOP
from AICode.MarcoAPI.DataAligned import WRITE_ALIGNED_FILE

def UPDATE_TARGET_31():
    shutil.rmtree(PATH_AIDATA_TARGET_31(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_TARGET_31())
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    shared_cache = GET_TOP()
    with ProcessPoolExecutor(max_workers=32, initializer=INIT_TOP, initargs=(shared_cache,)) as pool:
        results = list(pool.map(partial(GENERATE_TARGET_31, stock_codes), trading_dates))
    dates_dict = {d: str(round(v, 4)) for d, v in results}
    WRITE_ALIGNED_FILE(PATH_AIDATA_TARGET_31_RATIO(), dates_dict, "0.0", "{date}|{value}")

def GENERATE_TARGET_31(stock_codes:list[str], trading_date:str):
    print("UPDATE_TARGET_31: " + trading_date)
    data: list[DATA_1D_TARGET] = []
    for stock_code in stock_codes:
        stock = stock_code.split('|')
        record_5 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 5)
        record_4 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 4)
        record_3 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 3)
        record_2 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 2)
        record_1 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 1)
        record_0 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 0)
        if record_5 is None or record_4 is None or record_3 is None or record_2 is None or record_1 is None or record_0 is None:
            continue
        m5 = (record_5.close + record_4.close + record_3.close + record_2.close + record_1.close) / 5.0
        if (record_4.volume < record_3.volume and record_3.volume < record_2.volume and record_2.volume > record_1.volume
                and IS_TOP(stock[0], record_4.date) is False and IS_TOP(stock[0], record_3.date) is True
                and IS_TOP(stock[0], record_2.date) is False and IS_BOTTOM(stock[0], record_2.date) is False
                and IS_TOP(stock[0], record_1.date) is False and IS_BOTTOM(stock[0], record_1.date) is False
                and record_2.close > record_3.close and (record_1.close - record_2.close) / record_2.close < 0.03
                and record_1.close > m5):
            data.append(DATA_1D_TARGET(
                stock_code=stock[0],
                stock_name=stock[1],
                date=record_0.date,
                open=record_0.open,
                high=record_0.high,
                low=record_0.low,
                close=record_0.close,
                volume=record_0.volume,
                amount=record_0.amount,
                pre_close=record_1.close))
    with open(f"{PATH_AIDATA_TARGET_31()}/{trading_date}", "a") as file:
        if len(data) == 0:
            file.write("\n")
        for d in data:
            file.write(f"{d.stock_code}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}|{d.pre_close}\n")
    if len(data) == 0:
        return (trading_date, 0.0)
    total = sum((d.close - d.pre_close) / d.pre_close * 100.0 for d in data)
    return (trading_date, total / len(data))

def UPDATE_TARGET_TOP_31():
    shutil.rmtree(PATH_AIDATA_TARGET_TOP_31(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_TARGET_TOP_31())
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    shared_cache = GET_TOP()
    with ProcessPoolExecutor(max_workers=32, initializer=INIT_TOP, initargs=(shared_cache,)) as pool:
        results = list(pool.map(partial(GENERATE_TARGET_TOP_31, stock_codes), trading_dates))
    dates_dict = {d: str(round(v, 4)) for d, v in results}
    WRITE_ALIGNED_FILE(PATH_AIDATA_TARGET_TOP_31_RATIO(), dates_dict, "0.0", "{date}|{value}")

def GENERATE_TARGET_TOP_31(stock_codes:list[str], trading_date:str):
    print("UPDATE_TARGET_TOP_31: " + trading_date)
    data: list[DATA_1D_TARGET] = []
    for stock_code in stock_codes:
        stock = stock_code.split('|')
        record_5 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 5)
        record_4 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 4)
        record_3 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 3)
        record_2 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 2)
        record_1 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 1)
        record_0 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 0)
        if record_5 is None or record_4 is None or record_3 is None or record_2 is None or record_1 is None or record_0 is None:
            continue
        if (record_4.volume < record_3.volume and record_3.volume < record_2.volume
                and IS_TOP(stock[0], record_4.date) is False and IS_TOP(stock[0], record_3.date) is True
                and IS_TOP(stock[0], record_2.date) is False and IS_BOTTOM(stock[0], record_2.date) is False
                and record_2.close > record_3.close):
            data.append(DATA_1D_TARGET(
                stock_code=stock[0],
                stock_name=stock[1],
                date=record_0.date,
                open=record_0.open,
                high=record_0.high,
                low=record_0.low,
                close=record_0.close,
                volume=record_0.volume,
                amount=record_0.amount,
                pre_close=record_1.close))
    with open(f"{PATH_AIDATA_TARGET_TOP_31()}/{trading_date}", "a") as file:
        if len(data) == 0:
            file.write("\n")
        for d in data:
            file.write(f"{d.stock_code}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}|{d.pre_close}\n")
    if len(data) == 0:
        return (trading_date, 0.0)
    total = sum((d.close - d.pre_close) / d.pre_close * 100.0 for d in data)
    return (trading_date, total / len(data))

def UPDATE_TARGET_311():
    shutil.rmtree(PATH_AIDATA_TARGET_311(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_TARGET_311())
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    shared_cache = GET_TOP()
    with ProcessPoolExecutor(max_workers=32, initializer=INIT_TOP, initargs=(shared_cache,)) as pool:
        results = list(pool.map(partial(GENERATE_TARGET_311, stock_codes), trading_dates))
    dates_dict = {d: str(round(v, 4)) for d, v in results}
    WRITE_ALIGNED_FILE(PATH_AIDATA_TARGET_311_RATIO(), dates_dict, "0.0", "{date}|{value}")

def GENERATE_TARGET_311(stock_codes: list[str], trading_date: str):
    print("UPDATE_TARGET_311: " + trading_date)
    data: list[DATA_1D_TARGET] = []
    for stock_code in stock_codes:
        stock = stock_code.split('|')
        record_6 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 6)
        record_5 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 5)
        record_4 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 4)
        record_3 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 3)
        record_2 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 2)
        record_1 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 1)
        record_0 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 0)
        if record_6 is None or record_5 is None or record_4 is None or record_3 is None or record_2 is None or record_1 is None or record_0 is None:
            continue
        m5 = (record_6.close + record_5.close + record_4.close + record_3.close + record_2.close) / 5.0
        if (record_5.volume < record_4.volume and record_4.volume < record_3.volume and record_3.volume > record_2.volume
                and IS_TOP(stock[0], record_5.date) is False and IS_TOP(stock[0], record_4.date) is True
                and IS_TOP(stock[0], record_3.date) is False and IS_BOTTOM(stock[0], record_3.date) is False
                and IS_TOP(stock[0], record_2.date) is False and IS_BOTTOM(stock[0], record_2.date) is False
                and record_3.close > record_4.close and (record_2.close - record_3.close) / record_3.close < 0.03
                and record_2.close > m5):
            data.append(DATA_1D_TARGET(
                stock_code=stock[0],
                stock_name=stock[1],
                date=record_0.date,
                open=record_0.open,
                high=record_0.high,
                low=record_0.low,
                close=record_0.close,
                volume=record_0.volume,
                amount=record_0.amount,
                pre_close=record_1.close))
    with open(f"{PATH_AIDATA_TARGET_311()}/{trading_date}", "a") as file:
        if len(data) == 0:
            file.write("\n")
        for d in data:
            file.write(f"{d.stock_code}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}|{d.pre_close}\n")
    if len(data) == 0:
        return (trading_date, 0.0)
    total = sum((d.close - d.pre_close) / d.pre_close * 100.0 for d in data)
    return (trading_date, total / len(data))

def UPDATE_TARGET_TOP_311():
    shutil.rmtree(PATH_AIDATA_TARGET_TOP_311(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_TARGET_TOP_311())
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    shared_cache = GET_TOP()
    with ProcessPoolExecutor(max_workers=32, initializer=INIT_TOP, initargs=(shared_cache,)) as pool:
        results = list(pool.map(partial(GENERATE_TARGET_TOP_311, stock_codes), trading_dates))
    dates_dict = {d: str(round(v, 4)) for d, v in results}
    WRITE_ALIGNED_FILE(PATH_AIDATA_TARGET_TOP_311_RATIO(), dates_dict, "0.0", "{date}|{value}")

def GENERATE_TARGET_TOP_311(stock_codes: list[str], trading_date: str):
    print("UPDATE_TARGET_TOP_311: " + trading_date)
    data: list[DATA_1D_TARGET] = []
    for stock_code in stock_codes:
        stock = stock_code.split('|')
        record_6 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 6)
        record_5 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 5)
        record_4 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 4)
        record_3 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 3)
        record_2 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 2)
        record_1 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 1)
        record_0 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 0)
        if record_6 is None or record_5 is None or record_4 is None or record_3 is None or record_2 is None or record_1 is None or record_0 is None:
            continue
        if (record_5.volume < record_4.volume and record_4.volume < record_3.volume
                and IS_TOP(stock[0], record_5.date) is False and IS_TOP(stock[0], record_4.date) is True
                and IS_TOP(stock[0], record_3.date) is False and IS_BOTTOM(stock[0], record_3.date) is False
                and record_3.close > record_4.close):
            data.append(DATA_1D_TARGET(
                stock_code=stock[0],
                stock_name=stock[1],
                date=record_0.date,
                open=record_0.open,
                high=record_0.high,
                low=record_0.low,
                close=record_0.close,
                volume=record_0.volume,
                amount=record_0.amount,
                pre_close=record_1.close))
    with open(f"{PATH_AIDATA_TARGET_TOP_311()}/{trading_date}", "a") as file:
        if len(data) == 0:
            file.write("\n")
        for d in data:
            file.write(f"{d.stock_code}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}|{d.pre_close}\n")
    if len(data) == 0:
        return (trading_date, 0.0)
    total = sum((d.close - d.pre_close) / d.pre_close * 100.0 for d in data)
    return (trading_date, total / len(data))

def UPDATE_TARGET_TOP_11():
    shutil.rmtree(PATH_AIDATA_TARGET_TOP_11(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_TARGET_TOP_11())
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    shared_cache = GET_TOP()
    with ProcessPoolExecutor(max_workers=32, initializer=INIT_TOP, initargs=(shared_cache,)) as pool:
        results = list(pool.map(partial(GENERATE_TARGET_TOP_11, stock_codes), trading_dates))
    dates_dict = {d: str(round(v, 4)) for d, v in results}
    WRITE_ALIGNED_FILE(PATH_AIDATA_TARGET_TOP_11_RATIO(), dates_dict, "0.0", "{date}|{value}")

def GENERATE_TARGET_TOP_11(stock_codes:list[str], trading_date:str):
    print("UPDATE_TARGET_TOP_11: " + trading_date)
    data: list[DATA_1D_TARGET] = []
    for stock_code in stock_codes:
        stock = stock_code.split('|')
        record_2 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 2)
        record_1 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 1)
        record_0 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 0)
        if record_2 is None or record_1 is None or record_0 is None:
            continue
        if (IS_TOP(stock[0], record_2.date) is False and IS_TOP(stock[0], record_1.date) is True):
            data.append(DATA_1D_TARGET(
                stock_code=stock[0],
                stock_name=stock[1],
                date=record_0.date,
                open=record_0.open,
                high=record_0.high,
                low=record_0.low,
                close=record_0.close,
                volume=record_0.volume,
                amount=record_0.amount,
                pre_close=record_1.close))
    with open(f"{PATH_AIDATA_TARGET_TOP_11()}/{trading_date}", "a") as file:
        if len(data) == 0:
            file.write("\n")
        for d in data:
            file.write(f"{d.stock_code}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}|{d.pre_close}\n")
    if len(data) == 0:
        return (trading_date, 0.0)
    total = sum((d.close - d.pre_close) / d.pre_close * 100.0 for d in data)
    return (trading_date, total / len(data))

def UPDATE_TARGET_TOP_1():
    shutil.rmtree(PATH_AIDATA_TARGET_TOP_1(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_TARGET_TOP_1())
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    shared_cache = GET_TOP()
    with ProcessPoolExecutor(max_workers=32, initializer=INIT_TOP, initargs=(shared_cache,)) as pool:
        results = list(pool.map(partial(GENERATE_TARGET_TOP_1, stock_codes), trading_dates))
    dates_dict = {d: str(round(v, 4)) for d, v in results}
    WRITE_ALIGNED_FILE(PATH_AIDATA_TARGET_TOP_1_RATIO(), dates_dict, "0.0", "{date}|{value}")

def GENERATE_TARGET_TOP_1(stock_codes:list[str], trading_date:str):
    print("UPDATE_TARGET_TOP_1: " + trading_date)
    data: list[DATA_1D_TARGET] = []
    for stock_code in stock_codes:
        stock = stock_code.split('|')
        record_1 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 1)
        record_0 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 0)
        if record_1 is None or record_0 is None:
            continue
        if (IS_TOP(stock[0], record_1.date) is True):
            data.append(DATA_1D_TARGET(
                stock_code=stock[0],
                stock_name=stock[1],
                date=record_0.date,
                open=record_0.open,
                high=record_0.high,
                low=record_0.low,
                close=record_0.close,
                volume=record_0.volume,
                amount=record_0.amount,
                pre_close=record_1.close))
    with open(f"{PATH_AIDATA_TARGET_TOP_1()}/{trading_date}", "a") as file:
        if len(data) == 0:
            file.write("\n")
        for d in data:
            file.write(f"{d.stock_code}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}|{d.pre_close}\n")
    if len(data) == 0:
        return (trading_date, 0.0)
    total = sum((d.close - d.pre_close) / d.pre_close * 100.0 for d in data)
    return (trading_date, total / len(data))

def UPDATE_TARGET_HISTORY():
    shutil.rmtree(PATH_AIDATA_TARGET_HISTORY(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_TARGET_HISTORY())
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    shared_cache = GET_TOP()
    with ProcessPoolExecutor(max_workers=32, initializer=INIT_TOP, initargs=(shared_cache,)) as pool:
        results = list(pool.map(partial(GENERATE_TARGET_HISTORY, stock_codes), trading_dates))
    dates_dict = {d: str(round(v, 4)) for d, v in results}
    WRITE_ALIGNED_FILE(PATH_AIDATA_TARGET_HISTORY_RATIO(), dates_dict, "0.0", "{date}|{value}")

def GENERATE_TARGET_HISTORY(stock_codes: list[str], trading_date: str):
    print("UPDATE_TARGET_HISTORY: " + trading_date)
    data: list[DATA_1D_TARGET] = []
    for stock_code in stock_codes:
        stock = stock_code.split('|')
        # 检查 D-1 到 D-5 作为模式检测日期 X
        for offset in range(1, 6):
            # X = trading_date 往前 offset 天
            record_x_3 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, offset + 2)
            record_x_2 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, offset + 1)
            record_x_1 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, offset)
            if record_x_3 is None or record_x_2 is None or record_x_1 is None:
                continue
            # 条件：vol 递增、high 递增、涨停模式
            if (record_x_3.volume < record_x_2.volume < record_x_1.volume
                    and record_x_2.high < record_x_1.high
                    and IS_TOP(stock[0], record_x_3.date) is False
                    and IS_TOP(stock[0], record_x_2.date) is True
                    and IS_TOP(stock[0], record_x_1.date) is False):
                # 匹配成功，记录该股票在 D 日的数据
                record_0 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 0)
                record_1 = GET_SZ200_1D_PREVIOUS(stock[0], trading_date, 1)
                if record_0 is None or record_1 is None:
                    continue
                data.append(DATA_1D_TARGET(
                    stock_code=stock[0],
                    stock_name=stock[1],
                    date=record_0.date,
                    open=record_0.open,
                    high=record_0.high,
                    low=record_0.low,
                    close=record_0.close,
                    volume=record_0.volume,
                    amount=record_0.amount,
                    pre_close=record_1.close))
                break  # 已匹配，不再检查后续 offset
    with open(f"{PATH_AIDATA_TARGET_HISTORY()}/{trading_date}", "a") as file:
        if len(data) == 0:
            file.write("\n")
        for d in data:
            file.write(f"{d.stock_code}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}|{d.pre_close}\n")
    if len(data) == 0:
        return (trading_date, 0.0)
    total = sum((d.close - d.pre_close) / d.pre_close * 100.0 for d in data)
    return (trading_date, total / len(data))

if __name__ == "__main__":
    #UPDATE_TARGET_31()
    #UPDATE_TARGET_311()
    #SHOW_TARGET_1D()
    #UPDATE_TARGET_TOP_311()
    #UPDATE_TARGET_HISTORY()
    UPDATE_TARGET_31()
    #SHOW_TARGET_1D()
