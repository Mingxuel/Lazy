#!/usr/bin/env python3
"""
31: D-2(放量日)尾盘买 → D-1(回踩日)尾盘卖  持有1天
311: D-2(回踩日)尾盘买 → D-1(次日)尾盘卖    持有1天
含手续费，列出每日详细清单
"""
import os, sys
from collections import defaultdict

STRATEGY = sys.argv[1] if len(sys.argv) > 1 else "311"

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", STRATEGY)
KLINE_DIR = os.path.join(BASE, "1D")
DATES_FILE = os.path.join(BASE, "TRADING_DATES")

dates = []
with open(DATES_FILE) as f:
    for line in f:
        d = line.strip()
        if d: dates.append(d)
date_idx = {d: i for i, d in enumerate(dates)}

COMM = 0.00025; COMM_MIN = 5.0; STAMP = 0.0005; TRANS = 0.00001

signal_files = sorted([f for f in os.listdir(SIGNAL_DIR) if os.path.isfile(os.path.join(SIGNAL_DIR, f))])

# 收集信号
signal_days = {}   # sig_date -> [(code, sell_close, buy_date)]
need_kline = defaultdict(set)

for fname in signal_files:
    fpath = os.path.join(SIGNAL_DIR, fname)
    if os.path.getsize(fpath) <= 3: continue
    with open(fpath) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines: continue

    sig_date = fname
    idx = date_idx.get(sig_date, -1)
    if idx < 2: continue
    d2_date = dates[idx - 2]  # D-2 买入日

    entries = []
    for line in lines:
        parts = line.split('|')
        if len(parts) < 8: continue
        code = parts[0]
        sell_price = float(parts[7])  # pre_close = D-1 卖出（1天持仓）
        entries.append((code, sell_price))
        need_kline[code].add(d2_date)

    if entries:
        signal_days[sig_date] = (entries, d2_date)

print(f"策略{STRATEGY}: {len(signal_days)} 天有信号")

# 加载 D-2 K线
kline = defaultdict(dict)
for code, tds in need_kline.items():
    kp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(kp): continue
    with open(kp) as kf:
        for line in kf:
            p = line.strip().split('|')
            if len(p) < 5: continue
            if p[0] in tds:
                kline[code][p[0]] = float(p[4])

# 逐日计算
CAPITAL = 1_000_000
daily_results = []
detail_rows = []

for sig_date in sorted(signal_days.keys()):
    entries, d2_date = signal_days[sig_date]
    n = len(entries)
    per_cap = CAPITAL / n
    tr = 0.0; vc = 0
    day_detail = []

    for code, sell_price in entries:
        buy_price = kline.get(code, {}).get(d2_date)
        if buy_price is None or buy_price == 0 or sell_price == 0:
            continue

        shares = int(per_cap / buy_price / 100) * 100
        if shares == 0: shares = 100
        cost = shares * buy_price
        buy_fee = max(cost * COMM, COMM_MIN) + cost * TRANS
        total_buy = cost + buy_fee

        rev = shares * sell_price
        sell_fee = max(rev * COMM, COMM_MIN) + rev * TRANS + rev * STAMP
        net_sell = rev - sell_fee

        ret_amt = net_sell - total_buy
        ret_pct = ret_amt / total_buy * 100
        tr += ret_pct
        vc += 1

        day_detail.append({
            'code': code, 'buy': buy_price, 'sell': sell_price,
            'shares': shares, 'ret': round(ret_pct, 2)
        })
        detail_rows.append({
            'sig_date': sig_date, 'code': code,
            'buy_date': d2_date, 'sell_date': dates[date_idx[sig_date]-1],
            'buy': buy_price, 'sell': sell_price,
            'ret': round(ret_pct, 2)
        })

    if vc > 0:
        daily_results.append({'date': sig_date, 'ret': round(tr/vc, 4), 'cnt': vc, 'detail': day_detail})

print(f"有效交易日: {len(daily_results)}")

# === 明细表（前20天 + 后10天） ===
sell_label = "D-1回踩日" if STRATEGY == "31" else "D-1次日"
print(f"\n{'='*100}")
print(f"  策略{STRATEGY} — D-2尾盘买 / {sell_label}尾盘卖  逐笔明细（含手续费）")
print(f"{'='*100}")
print(f"  {'信号日':<12} {'股票':<12} {'买入日':<12} {'买入价':>8} {'卖出日':<12} {'卖出价':>8} {'收益率':>10}")
print(f"  {'-'*92}")

shown = 0
for r in detail_rows:
    if shown < 40 or shown >= len(detail_rows) - 10:
        print(f"  {r['sig_date']:<12} {r['code']:<12} {r['buy_date']:<12} {r['buy']:>8.2f} {r['sell_date']:<12} {r['sell']:>8.2f} {r['ret']:>9.2f}%")
    elif shown == 40:
        print(f"  {'...':<12} {'(中间省略)':<12}")
    shown += 1

print(f"\n  共 {shown} 笔交易")

# === 月度汇总 ===
monthly = defaultdict(lambda: {'days': 0, 'sum': 0.0, 'win': 0, 'lose': 0})
for r in daily_results:
    m = r['date'][:6]
    monthly[m]['days'] += 1
    monthly[m]['sum'] += r['ret']
    if r['ret'] > 0: monthly[m]['win'] += 1
    elif r['ret'] < 0: monthly[m]['lose'] += 1

print(f"\n{'='*100}")
print(f"  策略{STRATEGY} 月度盈亏汇总（含手续费）")
print(f"{'='*100}")
print(f"  {'月份':<8} {'交易天数':>6} {'月收益率':>10} {'日均':>8} {'胜率':>8} {'胜/负':>8}")
print(f"  {'-'*68}")

all_sum = 0.0; all_days = 0; all_win = 0; all_lose = 0
for month in sorted(monthly.keys()):
    m = monthly[month]
    d = m['days']; s = m['sum']; w = m['win']; l = m['lose']
    all_sum += s; all_days += d; all_win += w; all_lose += l
    print(f"  {month:<8} {d:>6} {s:>10.2f}% {s/d:>8.2f}% {w/d*100:>7.1f}% {w:>3}/{l:<3}")
print(f"  {'-'*68}")
print(f"  {'合计':<8} {all_days:>6} {all_sum:>10.2f}% {all_sum/all_days:>8.2f}% {all_win/all_days*100:>7.1f}% {all_win:>3}/{all_lose:<3}")

# 净值
cum = 1.0; peak = 1.0; max_dd = 0.0
print(f"\n  月度净值:")
for month in sorted(monthly.keys()):
    s = monthly[month]['sum']
    cum *= (1 + s / 100)
    if cum > peak: peak = cum
    dd = (cum - peak) / peak * 100
    if dd < max_dd: max_dd = dd
    print(f"  {month}: {s:>8.2f}%  →  净值 {cum:.4f}  回撤 {dd:.1f}%")
print(f"\n  最终净值: {cum:.4f}  |  最大回撤: {max_dd:.2f}%  |  总收益: {(cum-1)*100:.2f}%")
