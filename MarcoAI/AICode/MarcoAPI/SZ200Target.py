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
from AICode.MarcoAPI.SZ200Top import IS_TOP
from AICode.MarcoAPI.UI.UITarget import SHOW_TARGET_1D
from AICode.MarcoAPI.DataAligned import WRITE_ALIGNED_FILE

def UPDATE_TARGET_31():
    datas: dict[str, list[DATA_1D_TARGET]] = {}
    for trading_date in TRADING_DATES():
        datas[trading_date] = []
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    for trading_date in trading_dates:
        for stock in stock_codes:
            record_5 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 5)
            record_4 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 4)
            record_3 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 3)
            record_2 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 2)
            record_1 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 1)
            record_0 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 0)
            if record_5 is None or record_4 is None or record_3 is None or record_2 is None or record_1 is None or record_0 is None:
                continue
            m5 = (record_5.close + record_4.close + record_3.close + record_2.close + record_1.close) / 5.0
            if (record_4.volume < record_3.volume and record_3.volume < record_2.volume and record_2.volume > record_1.volume
                and IS_TOP(stock["Code"], record_4.date) is False and IS_TOP(stock["Code"], record_3.date) is True
                and IS_TOP(stock["Code"], record_2.date) is False and IS_BOTTOM(stock["Code"], record_2.date) is False
                and IS_TOP(stock["Code"], record_1.date) is False and IS_BOTTOM(stock["Code"], record_1.date) is False
                and record_2.close > record_3.close and (record_1.close - record_2.close) / record_2.close < 0.03
                and record_1.close > m5):
                datas[record_0.date].append(DATA_1D_TARGET(
                    stock_code=stock["Code"],
                    stock_name=stock["Name"],
                    date=record_0.date,
                    open=record_0.open,
                    high=record_0.high,
                    low=record_0.low,
                    close=record_0.close,
                    volume=record_0.volume,
                    amount=record_0.amount,
                    pre_close=record_1.close
                ))

    shutil.rmtree(PATH_AIDATA_TARGET_31(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_TARGET_31())

    for date, data in datas.items():
        with open(f"{PATH_AIDATA_TARGET_31()}/{date}", "a") as file:
            for d in data:
                file.write(f"{d.stock_code}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}|{d.pre_close}\n")

def UPDATE_TARGET_31_RATIO():
    data: dict[str, float] = {}
    trading_dates = TRADING_DATES()
    for trading_date in trading_dates:
        ratio = 0.0
        count = 0
        for line in open(f"{PATH_AIDATA_TARGET_31()}/{trading_date}", "r"):
            parts = line.strip().split('|')
            close = float(parts[4])
            pre_close = float(parts[7])
            ratio += (close - pre_close) / pre_close * 100.0
            count += 1
        if count == 0:
            data[trading_date] = ratio
            continue
        ratio = ratio / count
        data[trading_date] = ratio
    
    # 使用 WRITE_ALIGNED_FILE 全宽对齐写入，自动跳过第一个交易日
    dates_dict = {d: str(round(v, 4)) for d, v in data.items()}
    WRITE_ALIGNED_FILE(PATH_AIDATA_TARGET_31_RATIO(), dates_dict, "0.0", "{date}|{value}")

def UPDATE_TARGET_311():
    datas: dict[str, list[DATA_1D_TARGET]] = {}
    for trading_date in TRADING_DATES():
        datas[trading_date] = []
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    for trading_date in trading_dates:
        for stock in stock_codes:
            record_6 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 6)
            record_5 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 5)
            record_4 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 4)
            record_3 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 3)
            record_2 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 2)
            record_1 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 1)
            record_0 = GET_SZ200_1D_PREVIOUS(stock["Code"], trading_date, 0)
            if record_6 is None or record_5 is None or record_4 is None or record_3 is None or record_2 is None or record_1 is None or record_0 is None:
                continue
            m5 = (record_6.close + record_5.close + record_4.close + record_3.close + record_2.close) / 5.0
            if (record_5.volume < record_4.volume and record_4.volume < record_3.volume and record_3.volume > record_2.volume
                and IS_TOP(stock["Code"], record_5.date) is False and IS_TOP(stock["Code"], record_4.date) is True
                and IS_TOP(stock["Code"], record_3.date) is False and IS_BOTTOM(stock["Code"], record_3.date) is False
                and IS_TOP(stock["Code"], record_2.date) is False and IS_BOTTOM(stock["Code"], record_2.date) is False
                and record_3.close > record_4.close and (record_2.close - record_3.close) / record_3.close < 0.03
                and record_2.close > m5):
                datas[record_0.date].append(DATA_1D_TARGET(
                    stock_code=stock["Code"],
                    stock_name=stock["Name"],
                    date=record_0.date,
                    open=record_0.open,
                    high=record_0.high,
                    low=record_0.low,
                    close=record_0.close,
                    volume=record_0.volume,
                    amount=record_0.amount,
                    pre_close=record_1.close
                ))

    shutil.rmtree(PATH_AIDATA_TARGET_311(), ignore_errors=True)
    os.mkdir(PATH_AIDATA_TARGET_311())

    for date, data in datas.items():
        with open(f"{PATH_AIDATA_TARGET_311()}/{date}", "a") as file:
            for d in data:
                file.write(f"{d.stock_code}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}|{d.pre_close}\n")

def UPDATE_TARGET_311_RATIO():
    data: dict[str, float] = {}
    trading_dates = TRADING_DATES()
    for trading_date in trading_dates:
        ratio = 0.0
        count = 0
        for line in open(f"{PATH_AIDATA_TARGET_311()}/{trading_date}", "r"):
            parts = line.strip().split('|')
            close = float(parts[4])
            pre_close = float(parts[7])
            ratio += (close - pre_close) / pre_close * 100.0
            count += 1
        if count == 0:
            data[trading_date] = ratio
            continue
        ratio = ratio / count
        data[trading_date] = ratio
    
    # 使用 WRITE_ALIGNED_FILE 全宽对齐写入，自动跳过第一个交易日
    dates_dict = {d: str(round(v, 4)) for d, v in data.items()}
    WRITE_ALIGNED_FILE(PATH_AIDATA_TARGET_311_RATIO(), dates_dict, "0.0", "{date}|{value}")

if __name__ == "__main__":
    #UPDATE_TARGET_31()
    #UPDATE_TARGET_311()
    #SHOW_TARGET_1D()
    #UPDATE_TARGET_31_RATIO()
    #UPDATE_TARGET_311_RATIO()
    SHOW_TARGET_1D()
