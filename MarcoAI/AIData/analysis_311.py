#!/usr/bin/env python3
"""
策略分析 — D-1尾盘买 / D-0尾盘卖
  - 买入: pre_close (record_1.close) = D-1 收盘价
  - 卖出: close (record_0.close) = D-0 收盘价
  - 等权全仓 + 手续费
"""
import os, sys
from collections import defaultdict

STRATEGY = sys.argv[1] if len(sys.argv) > 1 else "311"

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", STRATEGY)

COMMISSION_RATE = 0.00025
COMMISSION_MIN = 5.0
STAMP_DUTY = 0.0005
TRANSFER_FEE = 0.00001

signal_files = sorted([f for f in os.listdir(SIGNAL_DIR) if os.path.isfile(os.path.join(SIGNAL_DIR, f))])

signal_days = {}
for fname in signal_files:
    fpath = os.path.join(SIGNAL_DIR, fname)
    if os.path.getsize(fpath) <= 3: continue
    with open(fpath) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines: continue
    entries = []
    for line in lines:
        parts = line.split('|')
        if len(parts) < 8: continue
        code = parts[0]
        sell_close = float(parts[4])  # record_0.close → D-0 卖出
        buy_close = float(parts[7])   # pre_close → D-1 买入
        entries.append((code, buy_close, sell_close))
    if entries:
        signal_days[fname] = entries

print(f"策略{STRATEGY}: {len(signal_files)} 文件, {len(signal_days)} 天有信号")

CAPITAL = 1_000_000
daily_results = []

for sig_date in sorted(signal_days.keys()):
    entries = signal_days[sig_date]
    n = len(entries)
    per_cap = CAPITAL / n
    tr = 0.0; vc = 0
    for code, buy, sell in entries:
        if buy == 0 or sell == 0: continue
        shares = int(per_cap / buy / 100) * 100
        if shares == 0: shares = 100
        cost = shares * buy
        buy_fee = max(cost * COMMISSION_RATE, COMMISSION_MIN) + cost * TRANSFER_FEE
        total_buy = cost + buy_fee
        rev = shares * sell
        sell_fee = max(rev * COMMISSION_RATE, COMMISSION_MIN) + rev * TRANSFER_FEE + rev * STAMP_DUTY
        net_sell = rev - sell_fee
        tr += (net_sell - total_buy) / total_buy * 100
        vc += 1
    if vc > 0:
        daily_results.append({'date': sig_date, 'ret': round(tr/vc, 4), 'cnt': vc})

print(f"有效交易日: {len(daily_results)}")

# 按月份汇总
monthly = defaultdict(lambda: {'days': 0, 'sum': 0.0, 'win': 0, 'lose': 0})
for r in daily_results:
    m = r['date'][:6]
    monthly[m]['days'] += 1
    monthly[m]['sum'] += r['ret']
    if r['ret'] > 0: monthly[m]['win'] += 1
    elif r['ret'] < 0: monthly[m]['lose'] += 1

print("\n" + "=" * 85)
print(f"  策略{STRATEGY} — D-1尾盘买 / D-0尾盘卖 月度盈亏表（含手续费）")
print("  买入: D-1收盘价(pre_close) | 卖出: D-0收盘价(close)")
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

# 净值曲线
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
print(f"\n  最大回撤: {max_dd:.2f}%")
print(f"  累计净值: {cum:.4f}")
print(f"  总收益率: {(cum-1)*100:.2f}%")
print(f"  年化收益: {((cum**(12/len(monthly)))-1)*100:.2f}% ({len(monthly)}个月)")

# 极端日
srt = sorted(daily_results, key=lambda x: x['ret'], reverse=True)
print("\n" + "=" * 85)
print("  Top 盈利日")
for r in srt[:5]:
    print(f"  {r['date']}  |  {r['ret']:>8.2f}%  |  {r['cnt']}只")
print("\n  Top 亏损日")
for r in srt[-5:]:
    print(f"  {r['date']}  |  {r['ret']:>8.2f}%  |  {r['cnt']}只")
