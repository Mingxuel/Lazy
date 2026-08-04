#!/usr/bin/env python3
"""
策略311 隔日尾盘买卖 月度盈亏分析
规则:
  - 信号日尾盘(收盘价)等权全仓买入
  - 次日尾盘(收盘价)全部卖出
  - 手续费: 佣金万2.5(最低5元) + 印花税万5(卖) + 过户费万0.1
"""

import os
from collections import defaultdict

# === 路径配置 ===
BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
KLINE_DIR = os.path.join(BASE, "1D")
TRADING_DATES_FILE = os.path.join(BASE, "TRADING_DATES")

# === 手续费参数 ===
COMMISSION_RATE = 0.00025   # 佣金 万2.5
COMMISSION_MIN = 5.0        # 佣金最低5元
STAMP_DUTY = 0.0005         # 印花税 万5 (仅卖出)
TRANSFER_FEE = 0.00001      # 过户费 万0.1

# === 读取交易日历，构建 next_date 映射 ===
print("加载交易日历...")
trading_dates = []
with open(TRADING_DATES_FILE) as f:
    for line in f:
        d = line.strip()
        if d:
            trading_dates.append(d)

next_date_map = {}
for i in range(len(trading_dates) - 1):
    next_date_map[trading_dates[i]] = trading_dates[i + 1]

# 检查 TARGET/31 文件列表
signal_files = sorted(
    [f for f in os.listdir(SIGNAL_DIR) if os.path.isfile(os.path.join(SIGNAL_DIR, f))]
)
print(f"信号文件数: {len(signal_files)}")

# === 预加载需要的K线数据 ===
# 先收集所有需要的 stock_code 和 date
print("扫描信号文件...")
needed = defaultdict(set)  # stock_code -> set of dates needed
signal_days = {}  # date -> [(stock_code, close), ...]

for fname in signal_files:
    fpath = os.path.join(SIGNAL_DIR, fname)
    size = os.path.getsize(fpath)
    if size <= 3:  # 空文件
        continue
    with open(fpath) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        continue
    sig_date = fname
    entries = []
    for line in lines:
        parts = line.split('|')
        if len(parts) < 5:
            continue
        code = parts[0]
        close = float(parts[4])
        entries.append((code, close))
    if entries:
        signal_days[sig_date] = entries
        next_d = next_date_map.get(sig_date)
        if next_d:
            for code, _ in entries:
                needed[code].add(next_d)

print(f"有信号的交易日: {len(signal_days)}")
print(f"涉及股票数: {len(needed)}")

# 加载K线数据
print("加载K线数据...")
kline_cache = defaultdict(dict)  # stock_code -> {date -> close}
for code in needed:
    kline_path = os.path.join(KLINE_DIR, code)
    if not os.path.exists(kline_path):
        continue
    target_dates = needed[code]
    with open(kline_path) as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 5:
                continue
            d = parts[0]
            if d in target_dates:
                kline_cache[code][d] = float(parts[4])

print(f"K线数据加载完成: {sum(len(v) for v in kline_cache.values())} 条")

# === 逐日计算 ===
CAPITAL = 1_000_000  # 假设本金100万，方便计算绝对金额

daily_results = []  # [(date, daily_return_pct, daily_return_amount, stock_count, detail)]

for sig_date in sorted(signal_days.keys()):
    entries = signal_days[sig_date]
    next_date = next_date_map.get(sig_date)
    if not next_date:
        continue

    n = len(entries)
    per_stock_capital = CAPITAL / n
    total_return = 0.0

    valid_count = 0
    for code, buy_close in entries:
        sell_close = kline_cache.get(code, {}).get(next_date)
        if sell_close is None or buy_close == 0:
            continue

        # 买入股数 = 资金 / 买入价 (按100股取整)
        shares = int(per_stock_capital / buy_close / 100) * 100
        if shares == 0:
            # 最低买100股
            shares = 100
            actual_buy_cost = shares * buy_close
        else:
            actual_buy_cost = shares * buy_close

        # 实际本金消耗
        # 买入手续费
        buy_commission = max(actual_buy_cost * COMMISSION_RATE, COMMISSION_MIN)
        buy_transfer = actual_buy_cost * TRANSFER_FEE
        total_buy_cost = actual_buy_cost + buy_commission + buy_transfer

        # 卖出金额
        sell_amount = shares * sell_close
        sell_commission = max(sell_amount * COMMISSION_RATE, COMMISSION_MIN)
        sell_transfer = sell_amount * TRANSFER_FEE
        sell_stamp = sell_amount * STAMP_DUTY
        total_sell_revenue = sell_amount - sell_commission - sell_transfer - sell_stamp

        # 该股收益
        stock_return = total_sell_revenue - total_buy_cost
        stock_return_pct = (stock_return / total_buy_cost) * 100

        total_return += stock_return_pct
        valid_count += 1

    if valid_count > 0:
        avg_return = total_return / valid_count
        daily_results.append({
            'date': sig_date,
            'next_date': next_date,
            'return_pct': round(avg_return, 4),
            'stock_count': valid_count,
            'total_stocks': n,
        })

print(f"\n有效交易日: {len(daily_results)}")

# === 按月汇总 ===
monthly = defaultdict(lambda: {
    'days': 0,
    'total_return_pct': 0.0,
    'win_days': 0,
    'lose_days': 0,
    'detail_days': [],
})
for r in daily_results:
    month = r['date'][:6]
    monthly[month]['days'] += 1
    monthly[month]['total_return_pct'] += r['return_pct']
    if r['return_pct'] > 0:
        monthly[month]['win_days'] += 1
    elif r['return_pct'] < 0:
        monthly[month]['lose_days'] += 1
    monthly[month]['detail_days'].append(r)

# === 输出 ===
print("\n" + "=" * 85)
print("  策略311 — 隔日尾盘买卖 月度盈亏表（含手续费）")
print("  买入: 信号日收盘价 | 卖出: 次日收盘价")
print("  手续费: 佣金万2.5(低消5元) + 印花税万5(卖) + 过户费万0.1")
print("=" * 85)
print(f"  {'月份':<8} {'交易天数':>6} {'累计收益%':>10} {'日均收益%':>10} {'胜率':>8} {'胜/负':>8}")
print("  " + "-" * 78)

all_total_return = 0.0
all_days = 0
all_win = 0
all_lose = 0

for month in sorted(monthly.keys()):
    m = monthly[month]
    avg = m['total_return_pct'] / m['days']
    wr = m['win_days'] / m['days'] * 100 if m['days'] > 0 else 0
    all_total_return += m['total_return_pct']
    all_days += m['days']
    all_win += m['win_days']
    all_lose += m['lose_days']
    print(f"  {month:<8} {m['days']:>6} {m['total_return_pct']:>10.2f}% {avg:>10.2f}% {wr:>7.1f}% {m['win_days']:>3}/{m['lose_days']:<3}")

print("  " + "-" * 78)
all_avg = all_total_return / all_days if all_days > 0 else 0
all_wr = all_win / all_days * 100 if all_days > 0 else 0
print(f"  {'合计':<8} {all_days:>6} {all_total_return:>10.2f}% {all_avg:>10.2f}% {all_wr:>7.1f}% {all_win:>3}/{all_lose:<3}")

# === 最大回撤月 ===
cum = 0.0
max_dd_month = None
max_dd_val = 0.0
peak = 0.0

print("\n" + "=" * 85)
print("  月度累计净值曲线")
print("=" * 85)
print(f"  {'月份':<8} {'月收益%':>10} {'累计净值':>10} {'最大回撤%':>10}")

peak = 0.0
cum = 1.0
max_dd = 0.0
for month in sorted(monthly.keys()):
    m = monthly[month]
    cum *= (1 + m['total_return_pct'] / 100)
    if cum > peak:
        peak = cum
    dd = (cum - peak) / peak * 100
    if dd < max_dd:
        max_dd = dd
    print(f"  {month:<8} {m['total_return_pct']:>10.2f}% {cum:>10.4f} {dd:>10.2f}%")

print(f"\n  最大回撤: {max_dd:.2f}%")
print(f"  累计净值: {cum:.4f}")
print(f"  总收益率: {(cum - 1) * 100:.2f}%")
print(f"  年化收益: {((cum ** (12 / len(monthly))) - 1) * 100:.2f}% (按{len(monthly)}个月计算)")

# === 最大单日收益/亏损 ===
print("\n" + "=" * 85)
print("  极端交易日 Top 5")
print("=" * 85)
sorted_by_return = sorted(daily_results, key=lambda x: x['return_pct'], reverse=True)
print("\n  【最大盈利日】")
for r in sorted_by_return[:5]:
    print(f"  {r['date']} -> {r['next_date']}  |  {r['return_pct']:>8.2f}%  |  {r['stock_count']}只票")
print("\n  【最大亏损日】")
for r in sorted_by_return[-5:]:
    print(f"  {r['date']} -> {r['next_date']}  |  {r['return_pct']:>8.2f}%  |  {r['stock_count']}只票")
