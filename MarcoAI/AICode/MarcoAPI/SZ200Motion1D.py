import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *
from AICode.MarcoAPI.SZ2001D import *
from AICode.MarcoAPI.DataAligned import WRITE_ALIGNED_FILE, READ_ALIGNED_LINES
from AICode.MarcoAPI.Data import DATA_1D

def UPDATE_1D_WIN_COUNT():
    dataframe: dict[str, dict[str, DATA_1D]] = GET_SZ200_1D_ALL()
    trading_dates = TRADING_DATES()
    stock_codes = STOCK_CODES()
    data = {}
    for i, trading_date in enumerate(trading_dates):
        print("UPDATE_1D_WIN_COUNT: " + trading_date)
        if i == 0:
            continue
        up = 0
        flat = 0
        down = 0
        total = 0
        total_amount = 0.0
        pre_trading_date = trading_dates[i - 1]
        for stock_code in stock_codes:
            pre_close = dataframe[stock_code][pre_trading_date].close
            _close = dataframe[stock_code][trading_date].close
            if pre_close > 0.0 and _close > 0.0:
                total += 1
                total_amount += float(dataframe[stock_code][trading_date].amount)
                if float(_close) > float(pre_close):
                    up += 1
                elif float(_close) < float(pre_close):
                    down += 1
                else:
                    flat += 1
        # 无数据也写入全零行，保证对齐
        data[trading_date] = f"{up}|{flat}|{down}|{total}|{total_amount:.0f}"

    WRITE_ALIGNED_FILE(PATH_AIDATA_1D_WIN_COUNT(), data, "0|0|0|0|0", "{date}|{value}")

def UPDATE_1D_MOTION_COUNT():
    """计算收盘时上涨数-开盘时上涨数 和 收盘时成交额-开盘时成交额"""
    dataframe: dict[str, dict[str, DATA_1D]] = GET_SZ200_1D_ALL()
    trading_dates = TRADING_DATES()
    stock_codes = STOCK_CODES()
    data = {}
    for i, trading_date in enumerate(trading_dates):
        print("UPDATE_1D_MOTION_COUNT: " + trading_date)
        if i == 0:
            continue
        open_up = 0
        close_up = 0
        total_amount = 0.0
        pre_trading_date = trading_dates[i - 1]
        for stock_code in stock_codes:
            sd = dataframe[stock_code][trading_date]
            pre_close = dataframe[stock_code][pre_trading_date].close
            if pre_close > 0.0 and sd.close > 0.0:
                total_amount += float(sd.amount)
                if float(sd.close) > float(pre_close):
                    close_up += 1
                if float(sd.open) > float(pre_close):
                    open_up += 1
        up_motion = close_up - open_up
        data[trading_date] = f"{up_motion}|{total_amount:.0f}"
    WRITE_ALIGNED_FILE(PATH_AIDATA_1D_MOTION_COUNT(), data, "0|0", "{date}|{value}")
    print(f"UPDATE_1D_MOTION_COUNT DONE → {PATH_AIDATA_1D_MOTION_COUNT()}")

def UPDATE_1D_PANIC_INDEX():
    """根据涨跌家数计算恐慌指数（0~100，越高越恐慌）"""
    data = {}
    for date, line in READ_ALIGNED_LINES(PATH_AIDATA_1D_WIN_COUNT()):
        if not line:
            data[date] = "0.0"
            continue
        parts = line.split('|')
        up = int(parts[1])
        down = int(parts[3])
        total = int(parts[4])
        if total == 0:
            data[date] = "0.0"
            continue
        up_r = up / total
        dn_r = down / total
        # 上涨占比 < 40% → 越少越恐慌
        up_score = max(0, min(100, (0.4 - up_r) / 0.4 * 100)) if up_r < 0.4 else 0
        # 下跌占比 > 30% → 越多越恐慌
        dn_score = max(0, min(100, (dn_r - 0.3) / 0.4 * 100)) if dn_r > 0.3 else 0
        # 等权合成恐慌指数
        panic_index = round(0.50 * up_score + 0.50 * dn_score, 1)
        data[date] = str(panic_index)
    WRITE_ALIGNED_FILE(PATH_AIDATA_1D_PANIC_INDEX(), data, "0.0", "{date}|{value}")
    print(f"UPDATE_1D_PANIC_INDEX DONE → {PATH_AIDATA_1D_PANIC_INDEX()}")

def UPDATE_1D_PRICE():
    """计算两种均价：当日收盘价简单均价 和 量加权均价(VWAP)，写入AIData/1D_PRICE。"""
    import math
    dataframe: dict[str, dict[str, DATA_1D]] = GET_SZ200_1D_ALL()
    trading_dates = TRADING_DATES()
    stock_codes = STOCK_CODES()
    data = {}
    for i, trading_date in enumerate(trading_dates):
        print("UPDATE_1D_PRICE: " + trading_date)
        sum_close = 0.0
        sum_close_volume = 0.0
        sum_volume = 0.0
        count = 0
        for stock_code in stock_codes:
            sd = dataframe[stock_code].get(trading_date)
            if sd is None or sd.close <= 0 or math.isnan(sd.close):
                continue
            close = sd.close
            volume = sd.volume
            sum_close += close
            sum_close_volume += close * volume
            sum_volume += volume
            count += 1
        if count == 0:
            data[trading_date] = "0.0|0.0"
        else:
            avg_close = round(sum_close / count, 2)
            vwap = round(sum_close_volume / sum_volume, 2) if sum_volume > 0 else 0.0
            data[trading_date] = f"{avg_close}|{vwap}"
    WRITE_ALIGNED_FILE(PATH_AIDATA_1D_PRICE(), data, "0.0|0.0", "{date}|{value}")
    print(f"UPDATE_1D_PRICE DONE → {PATH_AIDATA_1D_PRICE()}")

if __name__ == "__main__":
    UPDATE_1D_MOTION_COUNT()
    #UPDATE_1D_PANIC_INDEX()
