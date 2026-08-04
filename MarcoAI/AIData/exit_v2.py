#!/usr/bin/env python3
"""
真正正确的跟踪止损实现
止损基准=买入价, 处理低开场景
"""
import os, sys
from collections import defaultdict

BASE = r"C:\Lazy\MarcoAI\AIData"
KLINE_DIR = os.path.join(BASE, "1D")
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
DATES_FILE = os.path.join(BASE, "TRADING_DATES")

dates = []
with open(DATES_FILE) as f:
    for l in f:
        d = l.strip()
        if d: dates.append(d)
date_idx = {d: i for i, d in enumerate(dates)}

COMM = 0.00025; COMM_MIN = 5.0; STAMP = 0.0005; TRANS = 0.00001
CAPITAL = 1_000_000

signal_days = {}
need_kline = defaultdict(set)
for fname in sorted(os.listdir(SIGNAL_DIR)):
    fp = os.path.join(SIGNAL_DIR, fname)
    if os.path.getsize(fp) <= 3: continue
    with open(fp) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines: continue
    sd = fname; idx = date_idx.get(sd, -1)
    if idx < 2: continue
    d2 = dates[idx-2]; d1 = dates[idx-1]
    entries = [(l.split('|')[0], d2, d1) for l in lines if '|' in l]
    if entries:
        signal_days[sd] = entries
        for code, d2, d1 in entries:
            need_kline[code].add(d2); need_kline[code].add(d1)

kline = defaultdict(dict)
for code, tds in need_kline.items():
    kp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(kp): continue
    with open(kp) as kf:
        for line in kf:
            p = line.strip().split('|')
            if len(p) < 6: continue
            if p[0] in tds:
                kline[code][p[0]] = {'o': float(p[1]), 'h': float(p[2]),
                    'l': float(p[3]), 'c': float(p[4]), 'v': float(p[5])}

def calc(buy, sell, n=2):
    shares = int((CAPITAL/n)/buy/100)*100
    if shares == 0: shares = 100
    cost = shares*buy
    bf = max(cost*COMM, COMM_MIN) + cost*TRANS
    tb = cost+bf
    rev = shares*sell
    sf = max(rev*COMM, COMM_MIN) + rev*TRANS + rev*STAMP
    return (rev-sf-tb)/tb*100

# 构建交易
trades = []
for sd, entries in sorted(signal_days.items()):
    for code, d2, d1 in entries:
        k2 = kline.get(code,{}).get(d2,{})
        k1 = kline.get(code,{}).get(d1,{})
        buy_p = k2.get('c',0)
        if not buy_p or not k1 or buy_p==0: continue
        trades.append({
            'sd': sd, 'code': code, 'buy': buy_p,
            'open': k1['o'], 'high': k1['h'], 'low': k1['l'], 'close': k1['c'], 'vol': k1['v']
        })

print(f"交易: {len(trades)} 笔\n")

def backtest(name, sell_func):
    monthly = defaultdict(lambda: {'sum':0.0, 'days':0, 'win':0, 'lose':0})
    day_grp = defaultdict(list)
    for t in trades: day_grp[t['sd']].append(t)
    
    for sd, group in sorted(day_grp.items()):
        scored = [(t['vol']*t['buy'], t) for t in group]
        scored.sort(reverse=True)
        top = [s[1] for s in scored[:2]]
        rets = []
        for t in top:
            sp = sell_func(t)
            if sp and sp > 0:
                rets.append(calc(t['buy'], sp))
        if rets:
            avg = sum(rets)/len(rets)
        else:
            avg = 0
        m = sd[:6]
        monthly[m]['sum'] += avg; monthly[m]['days'] += 1
        if avg > 0: monthly[m]['win'] += 1
        elif avg < 0: monthly[m]['lose'] += 1
    
    cum = 1.0; peak = 1.0; dd = 0.0; w = 0; d = 0
    for m in sorted(monthly):
        d += monthly[m]['days']; w += monthly[m]['win']
        cum *= (1 + monthly[m]['sum']/100)
        if cum > peak: peak = cum
        _dd = (cum-peak)/peak*100
        if _dd < dd: dd = _dd
    return {'name': name, 'nav': cum, 'total': (cum-1)*100, 'dd': dd, 'wr': w/d*100 if d else 0}

strategies = []

# 0. 基准: 收盘卖
strategies.append(("0.收盘卖(基准)", lambda t: t['close']))

# === 固定止损(基于买入价) ===
for pct in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]:
    stop_level = 1 - pct/100
    strategies.append((
        f"A.固定止损{pct}%",
        lambda t, sl=stop_level: (
            # 低开直接穿止损 → 开盘出
            t['open'] if t['open'] <= t['buy']*sl
            # 盘中跌破止损 → 止损价出(止损价=max(low, buy*sl)偏保守估计)
            else t['buy']*sl if t['low'] <= t['buy']*sl
            # 没触发 → 收盘出
            else t['close']
        )
    ))

# === 跟踪止损(基于买入价→日内最高价) ===
# 逻辑: 
#   初始止损 = buy * (1-pct%)
#   开盘如果低开穿止损 → 立即出
#   如果高开, 止损上移 = max(初始止损, high*(1-pct%))
#   最终: 低点是否跌破止损
for pct in [1.0, 1.5, 2.0, 2.5, 3.0]:
    stop_pct = 1 - pct/100
    strategies.append((
        f"B.跟踪止损{pct}%(正确版)",
        lambda t, sp=stop_pct: (
            # 低开穿止损 → 开盘出
            t['open'] if t['open'] <= t['buy']*sp
            # 高开, 跟踪止损上移
            else (max(t['buy']*sp, t['high']*sp) if t['low'] <= max(t['buy']*sp, t['high']*sp) and t['high'] > t['buy']
            # 设被穿 → 以止损价出
            else t['close'])
        )
    ))

# === 改进跟踪止损: 止损价更保守(用low估计实际成交) ===
for pct in [1.0, 1.5, 2.0, 2.5, 3.0]:
    sp = 1 - pct/100
    strategies.append((
        f"C.跟踪止损{pct}%(保守成交)",
        lambda t, sp=sp: (
            t['open'] if t['open'] <= t['buy']*sp else
            (t['low'] if t['low'] <= max(t['buy']*sp, t['high']*sp) and t['high'] > t['buy'] else t['close'])
        )
    ))

# === 组合: 开盘1.5%止盈 + 跟踪2%止损 ===
strategies.append((
    "D.开盘1.5%止盈+跟踪2%止损",
    lambda t: (
        t['open'] if t['open'] > t['buy']*1.015
        else (t['open'] if t['open'] <= t['buy']*0.98
        else (max(t['buy']*0.98, t['high']*0.98) if t['low'] <= max(t['buy']*0.98, t['high']*0.98) and t['high'] > t['buy']
        else t['close']))
    )
))

print(f"{'策略':<32} {'收益%':>9} {'净值':>7} {'回撤%':>7} {'胜率%':>6} {'止损触发率':>8}")
print("-" * 72)
results = []

# 计算止损触发率
def calc_stop_rate(sell_func):
    triggered = 0
    for t in trades:
        sp = sell_func(t)
        if sp and sp > 0 and sp != t['close']:
            triggered += 1
    return triggered / len(trades) * 100 if trades else 0

for name, func in strategies:
    r = backtest(name, func)
    r['stop_rate'] = calc_stop_rate(func)
    results.append(r)
    print(f"  {r['name']:<32} {r['total']:>9.1f} {r['nav']:>7.2f} {r['dd']:>7.1f} {r['wr']:>6.1f} {r['stop_rate']:>7.1f}%")

# 最佳 vs 基准
best = max(results, key=lambda x: x['total'])
print(f"\n  基准(收盘卖): {results[0]['total']:.1f}%  净值{results[0]['nav']:.2f}")
print(f"  最佳: {best['name']}")
print(f"  收益: {best['total']:.1f}%  净值: {best['nav']:.1f}  回撤: {best['dd']:.1f}%  胜率: {best['wr']:.1f}%")
