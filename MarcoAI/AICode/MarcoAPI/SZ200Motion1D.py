from concurrent.futures import ProcessPoolExecutor
from math import nan
import os
import sys
from functools import partial

import pandas as pd

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Constants import *
from AICode.MarcoAPI.StockCodes import *
from AICode.MarcoAPI.TradingDates import *
from AICode.MarcoAPI.Path import *
from AICode.MarcoAPI.SZ2001D import *
from AICode.MarcoAPI.KLine import SHOW_K_LINE, SHOW_WIN_COUNT

def CALCULATE_SZ200_MOTION_1D_PRICE():
    dataframe = GET_SZ200_1D_ALL()
    trading_dates = TRADING_DATES()
    stock_codes = STOCK_CODES()
    pre_close_price = 100.0
    with open(f"{PATH_AIDATA_1D_MOTION_PRICE()}", "w") as file:
        for trading_date in trading_dates:
            last_trading_date = LAST_1D_MOTION_TRADING_DATE(PATH_AIDATA_1D_MOTION_PRICE())
            if last_trading_date != "" and trading_date <= last_trading_date:
                continue
            i = trading_dates.index(trading_date)
            if i == 0:
                continue
            open_ratio = 0.0
            high_ratio = 0.0
            low_ratio = 0.0
            close_ratio = 0.0
            volume = 0.0
            amount = 0.0
            count = 0
            pre_trading_date = trading_dates[i-1]
            for stock_code in stock_codes:
                pre_close = dataframe["Close"].loc[pre_trading_date, stock_code]
                _open = dataframe["Open"].loc[trading_date, stock_code]
                _high = dataframe["High"].loc[trading_date, stock_code]
                _low = dataframe["Low"].loc[trading_date, stock_code]
                _close = dataframe["Close"].loc[trading_date, stock_code]
                _volume = dataframe["Volume"].loc[trading_date, stock_code]
                _amount = dataframe["Amount"].loc[trading_date, stock_code]
                
                if pre_close != "" and _close != "":
                    count += 1
                    open_ratio += float(_open) / float(pre_close)
                    high_ratio += float(_high) / float(pre_close)
                    low_ratio += float(_low) / float(pre_close)
                    close_ratio += float(_close) / float(pre_close)
                    volume += float(_volume)
                    amount += float(_amount)
            if pd.isna(open_ratio) or pd.isna(high_ratio) or pd.isna(low_ratio) or pd.isna(close_ratio):
                continue
            open_price = round(open_ratio / count * pre_close_price,2)
            high_price = round(high_ratio / count * pre_close_price,2)
            low_price = round(low_ratio / count * pre_close_price,2)
            close_price = round(close_ratio / count * pre_close_price,2)
            pre_close_price = close_price
            volume = round(volume / count,2)
            amount = round(amount / count,2)
            file.write(f"{trading_date}|{open_price}|{high_price}|{low_price}|{close_price}|{volume}|{amount}\n")

def CALCULATE_SZ200_MOTION_1D_PRICE_VOLUME():
    dataframe = GET_SZ200_1D_ALL()
    trading_dates = TRADING_DATES()
    stock_codes = STOCK_CODES()
    pre_close_price = 100.0
    with open(f"{PATH_AIDATA_1D_MOTION_PRICE_VOLUME()}", "w") as file:
        for trading_date in trading_dates:
            last_trading_date = LAST_1D_MOTION_TRADING_DATE(PATH_AIDATA_1D_MOTION_PRICE_VOLUME())
            if last_trading_date != "" and trading_date <= last_trading_date:
                continue
            i = trading_dates.index(trading_date)
            if i == 0:
                continue
            open_volume = 0.0
            high_volume = 0.0
            low_volume = 0.0
            close_volume = 0.0
            volume = 0.0
            amount = 0.0
            count = 0
            pre_trading_date = trading_dates[i-1]
            for stock_code in stock_codes:
                pre_close = dataframe["Close"].loc[pre_trading_date, stock_code]
                _open = dataframe["Open"].loc[trading_date, stock_code]
                _high = dataframe["High"].loc[trading_date, stock_code]
                _low = dataframe["Low"].loc[trading_date, stock_code]
                _close = dataframe["Close"].loc[trading_date, stock_code]
                _volume = dataframe["Volume"].loc[trading_date, stock_code]
                _amount = dataframe["Amount"].loc[trading_date, stock_code]
                
                if pre_close != "" and _close != "":
                    count += 1
                    open_volume += float(_open) / float(pre_close) * _volume
                    high_volume += float(_high) / float(pre_close) * _volume
                    low_volume += float(_low) / float(pre_close) * _volume
                    close_volume += float(_close) / float(pre_close) * _volume
                    volume += float(_volume)
                    amount += float(_amount)
            if pd.isna(open_volume) or pd.isna(high_volume) or pd.isna(low_volume) or pd.isna(close_volume):
                continue
            open_price = round(open_volume / volume * pre_close_price,2)
            high_price = round(high_volume / volume * pre_close_price,2)
            low_price = round(low_volume / volume * pre_close_price,2)
            close_price = round(close_volume / volume * pre_close_price,2)
            pre_close_price = close_price
            volume = round(volume / count,2)
            amount = round(amount / count,2)
            file.write(f"{trading_date}|{open_price}|{high_price}|{low_price}|{close_price}|{volume}|{amount}\n")

def CALCULATE_SZ200_MOTION_1D_WIN_COUNT():
    dataframe = GET_SZ200_1D_ALL()
    trading_dates = TRADING_DATES()
    stock_codes = STOCK_CODES()
    with open(f"{PATH_AIDATA_1D_WIN_COUNT()}", "w") as file:
        for i, trading_date in enumerate(trading_dates):
            last_trading_date = LAST_1D_MOTION_TRADING_DATE(PATH_AIDATA_1D_WIN_COUNT())
            if last_trading_date != "" and trading_date <= last_trading_date:
                continue
            if i == 0:
                continue
            up = 0
            flat = 0
            down = 0
            total = 0
            pre_trading_date = trading_dates[i - 1]
            for stock_code in stock_codes:
                pre_close = dataframe["Close"].loc[pre_trading_date, stock_code]
                _close = dataframe["Close"].loc[trading_date, stock_code]
                if pre_close != "" and _close != "":
                    total += 1
                    if float(_close) > float(pre_close):
                        up += 1
                    elif float(_close) < float(pre_close):
                        down += 1
                    else:
                        flat += 1
            if total == 0:
                continue
            file.write(f"{trading_date}|{up}|{flat}|{down}|{total}\n")

def LAST_1D_MOTION_TRADING_DATE(file_path):
    last_trading_date = ""
    with open(f"{file_path}", "r") as file:
        for line in file:
            if line.strip() == "":
                continue
            last_trading_date = line.split("|")[0]
    return last_trading_date

def CALCULATE_SZ200_MOTION_1D_SIGNALS():
    """计算日线入场信号（恐慌底/广度拐点/MA金叉/广度背离）并写入文件。"""
    # ── 读取涨跌家数 ──
    dates, ups, downs, ratios = [], [], [], []
    with open(PATH_AIDATA_1D_WIN_COUNT(), 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) != 5:
                continue
            d, u, _, dn = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
            total = u + dn
            if total == 0:
                continue
            dates.append(d)
            ups.append(u)
            downs.append(dn)
            ratios.append(u / total)

    # ── 读取收盘价 ──
    closes = {}
    with open(PATH_AIDATA_1D_MOTION_PRICE(), 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 5:
                closes[parts[0]] = float(parts[4])

    def sma(arr, period):
        out = []
        for i in range(len(arr)):
            out.append(None if i < period - 1 else sum(arr[i - period + 1:i + 1]) / period)
        return out

    close_arr = [closes.get(d, 0) for d in dates]
    ratio_ma5 = sma(ratios, 5)
    close_ma5 = sma(close_arr, 5)
    close_ma20 = sma(close_arr, 20)

    signals = []
    n = len(dates)

    for i in range(n):
        date = dates[i]
        ratio = ratios[i]
        close = close_arr[i]

        # 跳过无价格数据的日期
        if close == 0:
            continue

        # 1. 恐慌底: 上涨占比 < 20%
        if ratio < 0.20:
            signals.append(f"{date}|panic_bottom|BUY|{close}|恐慌底: 上涨{ups[i]}下跌{downs[i]}, 下跌占比{(1-ratio)*100:.0f}%")
            continue

        # 2. 广度拐点: 涨跌比上穿MA5, 且前值<0.5
        if i >= 1 and ratio_ma5[i] is not None and ratio_ma5[i-1] is not None:
            prev_ratio = ratios[i-1]
            if prev_ratio < 0.5 and ratios[i-1] <= ratio_ma5[i-1] and ratio > ratio_ma5[i]:
                signals.append(f"{date}|breadth_thrust|BUY|{close}|广度拐点: 涨跌比({ratio:.2f})上穿MA5({ratio_ma5[i]:.2f})")
                continue

        # 3. MA金叉: MA5 上穿 MA20
        if close_ma5[i] is not None and close_ma20[i] is not None:
            if i >= 1 and close_ma5[i-1] is not None and close_ma20[i-1] is not None:
                if close_ma5[i-1] <= close_ma20[i-1] and close_ma5[i] > close_ma20[i]:
                    signals.append(f"{date}|ma_golden_cross|BUY|{close}|MA金叉: MA5({close_ma5[i]:.2f})上穿MA20({close_ma20[i]:.2f})")
                    continue

        # 4. 广度背离: 价格新低但上涨家数未创新低
        if i >= 9:
            close_10d = close_arr[i-9:i+1]
            up_10d = ups[i-9:i+1]
            if min(close_10d) > 0 and close == min(close_10d) and ups[i] != min(up_10d):
                signals.append(f"{date}|breadth_divergence|BUY|{close}|广度背离: 价新低({close})但上涨家数({ups[i]})未创新低({min(up_10d)})")

    with open(PATH_AIDATA_1D_SIGNALS(), 'w') as f:
        for s in signals:
            f.write(s + '\n')
    print(f"[信号] 共生成 {len(signals)} 个信号 → {PATH_AIDATA_1D_SIGNALS()}")
    for s in signals:
        print(f"  {s}")


if __name__ == "__main__":
    # CALCULATE_SZ200_MOTION_1D_PRICE()
    # SHOW_K_LINE(PATH_AIDATA_1D_MOTION_PRICE(), title='SZ200 Motion 1D K-Line', intraday=False)
    #CALCULATE_SZ200_MOTION_1D_PRICE_VOLUME()
    #SHOW_K_LINE(PATH_AIDATA_1D_MOTION_PRICE_VOLUME(), title='SZ200 Motion 1D Price-Volume K-Line', intraday=False)
    #CALCULATE_SZ200_MOTION_1D_WIN_COUNT()
    SHOW_WIN_COUNT(PATH_AIDATA_1D_WIN_COUNT(), title='SZ200 Motion 1D Win Count', top_dir=PATH_AIDATA_TOP())
