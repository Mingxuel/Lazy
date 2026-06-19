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
from AICode.MarcoAPI.SZ2005M import *
from AICode.MarcoAPI.KLine import SHOW_K_LINE, SHOW_WIN_COUNT
from AICode.MarcoAPI.SZ2001D import GET_SZ200_1D_ALL
from AICode.MarcoAPI.DataAligned import WRITE_ALIGNED_FILE
from AICode.MarcoAPI.Data import DATA_1D

def CALCULATE_SZ200_MOTION_5M_PRICE():
    dataframe = GET_SZ200_5M_ALL()
    trading_times = dataframe["Close"].index.tolist()
    stock_codes = STOCK_CODES()
    pre_close_price = 100.0
    with open(f"{PATH_AIDATA_5M_MOTION_PRICE()}", "w") as file:
        for trading_time in trading_times:
            last_trading_time = LAST_5M_MOTION_TRADING_DATE(PATH_AIDATA_5M_MOTION_PRICE())
            if last_trading_time != "" and trading_time <= pd.Timestamp(last_trading_time):
                continue
            i = trading_times.index(trading_time)
            if i == 0:
                continue
            open_ratio = 0.0
            high_ratio = 0.0
            low_ratio = 0.0
            close_ratio = 0.0
            volume = 0.0
            amount = 0.0
            count = 0
            pre_trading_times = trading_times[i-1]
            for stock_code in stock_codes:
                pre_close = dataframe["Close"].loc[pre_trading_times, stock_code]
                _open = dataframe["Open"].loc[trading_time, stock_code]
                _high = dataframe["High"].loc[trading_time, stock_code]
                _low = dataframe["Low"].loc[trading_time, stock_code]
                _close = dataframe["Close"].loc[trading_time, stock_code]
                _volume = dataframe["Volume"].loc[trading_time, stock_code]
                _amount = dataframe["Amount"].loc[trading_time, stock_code]
                
                if pre_close != "" and _close != "":
                    count += 1
                    open_ratio += float(_open) / float(pre_close)
                    high_ratio += float(_high) / float(pre_close)
                    low_ratio += float(_low) / float(pre_close)
                    close_ratio += float(_close) / float(pre_close)
                    volume += float(_volume)
                    amount += float(_amount)
            if pd.isna(open_ratio) or pd.isna(high_ratio) or pd.isna(low_ratio) or pd.isna(close_ratio) or count == 0:
                continue
            open_price = round(open_ratio / count * pre_close_price,2)
            high_price = round(high_ratio / count * pre_close_price,2)
            low_price = round(low_ratio / count * pre_close_price,2)
            close_price = round(close_ratio / count * pre_close_price,2)
            pre_close_price = close_price
            volume = round(volume / count,2)
            amount = round(amount / count,2)
            file.write(f"{trading_time}|{open_price}|{high_price}|{low_price}|{close_price}|{volume}|{amount}\n")

def CALCULATE_SZ200_MOTION_5M_PRICE_VOLUME():
    dataframe = GET_SZ200_5M_ALL()
    trading_times = dataframe["Close"].index.tolist()
    stock_codes = STOCK_CODES()
    pre_close_price = 100.0
    with open(f"{PATH_AIDATA_5M_MOTION_PRICE_VOLUME()}", "w") as file:
        for trading_time in trading_times:
            i = trading_times.index(trading_time)
            if i == 0:
                continue
            open_volume = 0.0
            high_volume = 0.0
            low_volume = 0.0
            close_volume = 0.0
            volume = 0.0
            amount = 0.0
            count = 0
            pre_trading_time = trading_times[i-1]
            for stock_code in stock_codes:
                pre_close = dataframe["Close"].loc[pre_trading_time, stock_code]
                _open = dataframe["Open"].loc[trading_time, stock_code]
                _high = dataframe["High"].loc[trading_time, stock_code]
                _low = dataframe["Low"].loc[trading_time, stock_code]
                _close = dataframe["Close"].loc[trading_time, stock_code]
                _volume = dataframe["Volume"].loc[trading_time, stock_code]
                _amount = dataframe["Amount"].loc[trading_time, stock_code]
                
                if pre_close != "" and _close != "":
                    count += 1
                    open_volume += float(_open) / float(pre_close) * _volume
                    high_volume += float(_high) / float(pre_close) * _volume
                    low_volume += float(_low) / float(pre_close) * _volume
                    close_volume += float(_close) / float(pre_close) * _volume
                    volume += float(_volume)
                    amount += float(_amount)
            if pd.isna(open_volume) or pd.isna(high_volume) or pd.isna(low_volume) or pd.isna(close_volume) or count == 0:
                continue
            open_price = round(open_volume / volume * pre_close_price,2)
            high_price = round(high_volume / volume * pre_close_price,2)
            low_price = round(low_volume / volume * pre_close_price,2)
            close_price = round(close_volume / volume * pre_close_price,2)
            if str(trading_time)[-8:] == "15:00:00":
                 pre_close_price = close_price
            volume = round(volume / count,2)
            amount = round(amount / count,2)
            file.write(f"{trading_time}|{open_price}|{high_price}|{low_price}|{close_price}|{volume}|{amount}\n")

def CALCULATE_SZ200_MOTION_5M_WIN_COUNT():
    dataframe = GET_SZ200_5M_ALL()
    trading_times = dataframe["Close"].index.tolist()
    stock_codes = STOCK_CODES()
    close_df = dataframe["Close"]

    # 预计算：每个交易日最后一根 5M 的收盘价
    daily_last = close_df.groupby(close_df.index.date).last()
    trading_dates = sorted(daily_last.index)

    with open(f"{PATH_AIDATA_5M_WIN_COUNT()}", "w") as file:
        for trading_time in trading_times:
            last_trading_time = LAST_5M_MOTION_TRADING_DATE(PATH_AIDATA_5M_WIN_COUNT())
            if last_trading_time != "" and trading_time <= pd.Timestamp(last_trading_time):
                continue
            current_date = trading_time.date()
            try:
                date_idx = trading_dates.index(current_date)
            except ValueError:
                continue
            if date_idx == 0:
                continue
            prev_date = trading_dates[date_idx - 1]
            prev_day_close = daily_last.loc[prev_date]

            up = 0
            flat = 0
            down = 0
            total = 0
            for stock_code in stock_codes:
                pre_close = prev_day_close[stock_code]
                _close = close_df.loc[trading_time, stock_code]
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
            file.write(f"{trading_time}|{up}|{flat}|{down}|{total}\n")

def LAST_5M_MOTION_TRADING_DATE(file_path):
    last_trading_time = ""
    with open(f"{file_path}", "r") as file:
        for line in file:
            if line.strip() == "":
                continue
            last_trading_time = line.split("|")[0]
    return last_trading_time


def CALCULATE_SZ200_MOTION_5M_SIGNALS():
    """计算5分钟入场信号并写入文件。"""
    # ── 读取5M价格数据，建立时间集合 ──
    price_times = set()
    closes = {}
    with open(PATH_AIDATA_5M_MOTION_PRICE(), 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 5:
                t = parts[0]
                price_times.add(t)
                closes[t] = float(parts[4])

    # ── 读取涨跌家数，只取有价格数据的K线 ──
    dates, ups, downs, ratios = [], [], [], []
    with open(PATH_AIDATA_5M_WIN_COUNT(), 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) != 5:
                continue
            d, u, _, dn = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
            if d not in price_times:
                continue
            total = u + dn
            if total == 0:
                continue
            dates.append(d)
            ups.append(u)
            downs.append(dn)
            ratios.append(u / total)

    close_arr = [closes[d] for d in dates]

    def sma(arr, period):
        out = []
        for i in range(len(arr)):
            out.append(None if i < period - 1 else sum(arr[i - period + 1:i + 1]) / period)
        return out

    ratio_ma5 = sma(ratios, 5)
    close_ma5 = sma(close_arr, 5)
    close_ma20 = sma(close_arr, 20)

    signals = []
    n = len(dates)

    for i in range(n):
        date = dates[i]
        ratio = ratios[i]
        close = close_arr[i]

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

        # 4. 广度背离: 价格新低(48根内)但上涨家数未创新低
        if i >= 47:
            close_48 = close_arr[i-47:i+1]
            up_48 = ups[i-47:i+1]
            if close == min(close_48) and ups[i] != min(up_48):
                signals.append(f"{date}|breadth_divergence|BUY|{close}|广度背离: 价新低({close})但上涨家数({ups[i]})未创新低({min(up_48)})")

    with open(PATH_AIDATA_5M_SIGNALS(), 'w') as f:
        for s in signals:
            f.write(s + '\n')
    print(f"[信号] 共生成 {len(signals)} 个信号 → {PATH_AIDATA_5M_SIGNALS()}")
    for s in signals[-20:]:
        print(f"  {s}")


def UPDATE_5M_MOTION_COUNT():
    """从本地5M数据文件生成开盘/中午/收盘时段的涨跌家数和成交额。

    输出文件: AIData/MOTION/5M_MOTION_COUNT
    格式: {date}|open_up|open_dn|noon_up|noon_dn|noon_amount|close_up|close_dn|close_amount
      - open_up/open_dn: 开盘(第1根5M bar的open价 vs 前日收盘)
      - noon_up/noon_dn: 中午11:30收盘价 vs 前日收盘
      - noon_amount: 9:30~11:30区间总成交额
      - close_up/close_dn: 下午15:00收盘价 vs 前日收盘
      - close_amount: 13:00~15:00区间总成交额
    """
    # 加载1D数据（用于获取前收盘价）
    dataframe_1d: dict[str, dict[str, DATA_1D]] = GET_SZ200_1D_ALL()
    trading_dates = TRADING_DATES()
    stock_codes = STOCK_CODES()
    print(f"[UPDATE_5M_MOTION_COUNT] 共 {len(stock_codes)} 只股票, {len(trading_dates)} 个交易日")

    # 初始化累加器 {date: {fields}}
    acc = {d: {
        'open_up': 0, 'open_dn': 0,
        'noon_up': 0, 'noon_dn': 0, 'noon_amt': 0.0,
        'close_up': 0, 'close_dn': 0, 'close_amt': 0.0,
    } for d in trading_dates}

    for idx, stock_code in enumerate(stock_codes):
        if (idx + 1) % 50 == 0:
            print(f"  [{idx+1}/{len(stock_codes)}] {stock_code}")

        filepath = os.path.join(PATH_AIDATA_5M(), stock_code)
        if not os.path.isfile(filepath):
            continue

        # 按日期分组5M bars
        stock_5m: dict[str, list[dict]] = {}
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) < 7:
                    continue
                ts = parts[0]  # "2025-01-02 09:35:00"
                date_str = ts[:10].replace('-', '')  # "20250102"
                time_str = ts[11:16]  # "09:35"
                stock_5m.setdefault(date_str, []).append({
                    'time': time_str,
                    'open': float(parts[1]),
                    'close': float(parts[4]),
                    'amount': float(parts[6]),
                })

        # 逐日分析
        for i, trading_date in enumerate(trading_dates):
            if i == 0:
                continue
            if trading_date not in stock_5m:
                continue
            bars = stock_5m[trading_date]
            if not bars:
                continue

            pre_trading_date = trading_dates[i - 1]
            sd = dataframe_1d.get(stock_code, {}).get(trading_date)
            pre_sd = dataframe_1d.get(stock_code, {}).get(pre_trading_date)
            if not sd or not pre_sd or pre_sd.close <= 0 or sd.close <= 0:
                continue
            pre_close = pre_sd.close

            # --- 开盘：第一个bar的open vs 前收盘 ---
            first_bar = bars[0]
            if first_bar['open'] > pre_close:
                acc[trading_date]['open_up'] += 1
            elif first_bar['open'] < pre_close:
                acc[trading_date]['open_dn'] += 1

            # --- 上午时段 (09:35 ~ 11:30) ---
            morning_bars = [b for b in bars if b['time'] <= '11:30']
            if morning_bars:
                noon_bar = morning_bars[-1]  # 11:30 的 bar
                if noon_bar['close'] > pre_close:
                    acc[trading_date]['noon_up'] += 1
                elif noon_bar['close'] < pre_close:
                    acc[trading_date]['noon_dn'] += 1
                acc[trading_date]['noon_amt'] += sum(b['amount'] for b in morning_bars)

            # --- 下午时段 (13:05 ~ 15:00) ---
            afternoon_bars = [b for b in bars if b['time'] > '11:30']
            if afternoon_bars:
                last_bar = afternoon_bars[-1]  # 15:00 的 bar
                if last_bar['close'] > pre_close:
                    acc[trading_date]['close_up'] += 1
                elif last_bar['close'] < pre_close:
                    acc[trading_date]['close_dn'] += 1
                acc[trading_date]['close_amt'] += sum(b['amount'] for b in afternoon_bars)

    # 构建输出字典
    output = {}
    for d in trading_dates:
        a = acc[d]
        output[d] = f"{a['open_up']}|{a['open_dn']}|{a['noon_up']}|{a['noon_dn']}|{a['noon_amt']:.0f}|{a['close_up']}|{a['close_dn']}|{a['close_amt']:.0f}"

    # 写入对齐文件
    os.makedirs(PATH_AIDATA_MOTION(), exist_ok=True)
    output_path = os.path.join(PATH_AIDATA_MOTION(), "5M_MOTION_COUNT")
    WRITE_ALIGNED_FILE(output_path, output, "0|0|0|0|0|0|0|0", "{date}|{value}")
    print(f"[UPDATE_5M_MOTION_COUNT] DONE → {output_path}")


if __name__ == "__main__":
    #CALCULATE_SZ200_MOTION_5M_PRICE()
    #SHOW_K_LINE(PATH_AIDATA_5M_MOTION_PRICE(), title='SZ200 Motion 5M K-Line', intraday=True)
    # CALCULATE_SZ200_MOTION_5M_PRICE_VOLUME()
    #SHOW_K_LINE(PATH_AIDATA_5M_MOTION_PRICE_VOLUME(), title='SZ200 Motion 5M Price-Volume K-Line', intraday=True)
    #CALCULATE_SZ200_MOTION_5M_WIN_COUNT()
    SHOW_WIN_COUNT(PATH_AIDATA_5M_WIN_COUNT(), title='SZ200 Motion 5M Win Count', intraday=True, top_dir=PATH_AIDATA_TOP())
    #CALCULATE_SZ200_MOTION_5M_SIGNALS()
    #from AICode.MarcoAPI.KLine import SHOW_K_LINE_WITH_SIGNALS
    #SHOW_K_LINE_WITH_SIGNALS(PATH_AIDATA_5M_MOTION_PRICE(), PATH_AIDATA_5M_SIGNALS(),
    #                          title='SZ200 Motion 5M K-Line + 信号', intraday=True)
