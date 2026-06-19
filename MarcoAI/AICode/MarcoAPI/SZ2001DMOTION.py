import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Data import DATA_1D
from AICode.MarcoAPI.StockCodes import STOCK_CODES
from AICode.MarcoAPI.TradingDates import TRADING_DATES
from AICode.MarcoAPI.Path import PATH_AIDATA_5M, PATH_AIDATA_MOTION
from AICode.MarcoAPI.SZ2001D import GET_SZ200_1D_ALL
from AICode.MarcoAPI.DataAligned import WRITE_ALIGNED_FILE


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
    UPDATE_5M_MOTION_COUNT()
