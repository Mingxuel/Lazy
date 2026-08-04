#!/usr/bin/env python3
"""
策略分析 — 正确版本
  31: D-2(放量日)尾盘买入 → D-0尾盘卖出
  311: D-2(回踩日)尾盘买入 → D-0尾盘卖出
  等权全仓 + 手续费
"""
import os, sys
from collections import defaultdict

STRATEGY = sys.argv[1] if len(sys.argv) > 1 else "311"

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", STRATEGY)
KLINE_DIR = os.path.join(BASE, "1D")
DATES_FILE = os.path.join(BASE, "TRADING_DATES")

# 读取交易日历
dates = []
with open(DATES_FILE) as f:
    for line in f:
        d = line.strip()
        if d: dates.append(d)
date_idx = {d: i for i, d in enumerate(dates)}

# 手续费
COMMISSION_RATE = 0.00025
COMMISSION_MIN = 5.0
STAMP_DUTY = 0.0005
TRANSFER_FEE = 0.00001

# === 收集所有信号，记录需要的 D-2 日期和股票 ===
signal_files = sorted([f for f in os.listdir(SIGNAL_DIR) if os.path.isfile(os.path.join(SIGNAL_DIR, f))])

# signal_days[sig_date] = [(code, sell_close=D-0), ...]
# need_kline[code] = set of D-2 dates
signal_days = {}
need_kline = defaultdict(set)

for fname in signal_files:
    fpath = os.path.join(SIGNAL_DIR, fname)
    if os.path.getsize(fpath) <= 3: continue
    with open(fpath) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines: continue

    sig_date = fname
    idx = date_idx.get(sig_date, -1)
    if idx < 2: continue  # 需要 D-2
    d2_date = dates[idx - 2]  # D-2 交易日

    entries = []
    for line in lines:
        parts = line.split('|')
        if len(parts) < 5: continue
        code = parts[0]
        sell_close = float(parts[4])  # D-0 收盘卖出价
        entries.append((code, sell_close))
        need_kline[code].add(d2_date)

    if entries:
        signal_days[sig_date] = entries

print(f"策略{STRATEGY}: {len(signal_days)} 天有信号, {len(need_kline)} 只股票")

# === 加载 D-2 日的K线数据 ===
print("加载 D-2 K线数据...")
kline = defaultdict(dict)
for code, target_dates in need_kline.items():
    kpath = os.path.join(KLINE_DIR, code)
    if not os.path.exists(kpath): continue
    with open(kpath) as kf:
        for line in kf:
            parts = line.strip().split('|')
            if len(parts) < 5: continue
            if parts[0] in target_dates:
                kline[code][parts[0]] = float(parts[4])

print(f"K线加载: {sum(len(v) for v in kline.values())} 条")

# === 逐日计算 ===
CAPITAL = 1_000_000
daily_results = []

for sig_date in sorted(signal_days.keys()):
    entries = signal_days[sig_date]
    idx = date_idx[sig_date]
    d2_date = dates[idx - 2]  # D-2 买入日

    n = len(entries)
    per_cap = CAPITAL / n
    tr = 0.0
    vc = 0

    for code, sell_close in entries:
        buy_close = kline.get(code, {}).get(d2_date)
        if buy_close is None or buy_close == 0 or sell_close == 0:
            continue

        # 买入
        shares = int(per_cap / buy_close / 100) * 100
        if shares == 0: shares = 100
        cost = shares * buy_close
        buy_fee = max(cost * COMMISSION_RATE, COMMISSION_MIN) + cost * TRANSFER_FEE
        total_buy = cost + buy_fee

        # 卖出
        rev = shares * sell_close
        sell_fee = max(rev * COMMISSION_RATE, COMMISSION_MIN) + rev * TRANSFER_FEE + rev * STAMP_DUTY
        net_sell = rev - sell_fee

        tr += (net_sell - total_buy) / total_buy * 100
        vc += 1

    if vc > 0:
        daily_results.append({'date': sig_date, 'ret': round(tr/vc, 4), 'cnt': vc})

print(f"有效交易日: {len(daily_results)}")

# === 按月汇总 ===
monthly = defaultdict(lambda: {'days': 0, 'sum': 0.0, 'win': 0, 'lose': 0})
for r in daily_results:
    m = r['date'][:6]
    monthly[m]['days'] += 1
    monthly[m]['sum'] += r['ret']
    if r['ret'] > 0: monthly[m]['win'] += 1
    elif r['ret'] < 0: monthly[m]['lose'] += 1

buy_label = "D-2放量日" if STRATEGY == "31" else "D-2回踩日"
print("\n" + "=" * 85)
print(f"  策略{STRATEGY} — {buy_label}尾盘买 / D-0尾盘卖 月度盈亏表（含手续费）")
print(f"  买入: D-2收盘价 | 卖出: D-0收盘价 | 持有2天")
print("  手续费: 佣金万2.5(低消5元) + 印花税万5(卖) + 过户费万0.1")
print("=" * 85)
print(f"  {'月份':<8} {'交易天数':>6} {'累计收益%':>10} {'日均收益%':>10} {'胜率':>8} {'胜/负':>8}")
print("  " + "-" * 78)

all_sum = 0.0; all_days = 0; all_win = 0; all_lose = 0
for month in sorted(monthly.keys()):
    m = monthly[month]
    d = m['days']; s = m['sum']; w = m['win']; l = m['lose']
    all_sum += s; all_days += d; all_win += w; all_lose += l
    wr = w / d * 100 if d else 0
    print(f"  {month:<8} {d:>6} {s:>10.2f}% {s/d:>10.2f}% {wr:>7.1f}% {w:>3}/{l:<3}")
print("  " + "-" * 78)
print(f"  {'合计':<8} {all_days:>6} {all_sum:>10.2f}% {all_sum/all_days:>10.2f}% {all_win/all_days*100:>7.1f}% {all_win:>3}/{all_lose:<3}")

# 净值
print("\n" + "=" * 85)
print("  月度累计净值")
print("=" * 85)
print(f"  {'月份':<8} {'月收益%':>10} {'累计净值':>10} {'最大回撤%':>10}")
cum = 1.0; peak = 1.0; max_dd = 0.0
for month in sorted(monthly.keys()):
    m = monthly[month]
    cum *= (1 + m['sum'] / 100)
    if cum > peak: peak = cum
    dd = (cum - peak) / peak * 100
    if dd < max_dd: max_dd = dd
    print(f"  {month:<8} {m['sum']:>10.2f}% {cum:>10.4f} {dd:>10.2f}%")
print(f"\n  最大回撤: {max_dd:.2f}% | 净值: {cum:.4f} | 总收益: {(cum-1)*100:.2f}%")

# 极端
srt = sorted(daily_results, key=lambda x: x['ret'], reverse=True)
print("\n" + "-"*50)
print("Top5 盈利日:")
for r in srt[:5]:
    print(f"  {r['date']} | {r['ret']:>8.2f}% | {r['cnt']}只")
print("Top5 亏损日:")
for r in srt[-5:]:
    print(f"  {r['date']} | {r['ret']:>8.2f}% | {r['cnt']}只")
