#!/usr/bin/env python3
"""
311策略 多种卖出方式对比
买入: D-2回踩日收盘  |  卖出: D-1日 各种策略
"""
import os, math, random
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

# 收集信号
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
    d2 = dates[idx - 2]  # 买入日
    d1 = dates[idx - 1]  # 卖出日
    entries = [(l.split('|')[0], d2, d1) for l in lines if '|' in l]
    if entries:
        signal_days[sd] = entries
        for code, d2, d1 in entries:
            need_kline[code].add(d2)
            need_kline[code].add(d1)
            need_kline[code].add(dates[idx])  # D-0 for MA calc
            for i in range(1, 21):
                if idx - i >= 0:
                    need_kline[code].add(dates[idx - i])

# 加载K线
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
                    'l': float(p[3]), 'c': float(p[4]), 'v': float(p[5]), 'a': float(p[6])}

CAPITAL = 1_000_000

def calc(buy_price, sell_price, n_stocks=None):
    """计算含手续费的收益率，n_stocks用于分配资金"""
    shares_per_stock = CAPITAL / (n_stocks or 1) if n_stocks else CAPITAL
    shares = int(shares_per_stock / buy_price / 100) * 100
    if shares == 0: shares = 100
    cost = shares * buy_price
    bf = max(cost * COMM, COMM_MIN) + cost * TRANS
    tb = cost + bf
    rev = shares * sell_price
    sf = max(rev * COMM, COMM_MIN) + rev * TRANS + rev * STAMP
    return (rev - sf - tb) / tb * 100

# 构建交易数据集
trades = []
for sd, entries in sorted(signal_days.items()):
    idx = date_idx[sd]
    for code, d2, d1 in entries:
        k2 = kline.get(code, {}).get(d2, {})
        k1 = kline.get(code, {}).get(d1, {})
        buy_p = k2.get('c', 0)
        if not buy_p or not k1: continue
        
        # 卖出入场前5日的均线数据
        closes_prev = []
        for i in range(1, 21):
            dd = dates[idx - i] if idx - i >= 0 else None
            k = kline.get(code, {}).get(dd, {}) if dd else {}
            c = k.get('c', 0)
            if c > 0: closes_prev.append(c)
        
        ma5 = sum(closes_prev[:5])/5 if len(closes_prev) >= 5 else buy_p
        ma10 = sum(closes_prev[:10])/10 if len(closes_prev) >= 10 else buy_p
        
        # ATR (14日)
        atr = 0
        if len(closes_prev) >= 15:
            trs = []
            for i in range(14):
                k_i = kline.get(code, {}).get(dates[idx - i - 1], {}) if idx-i-1 >= 0 else {}
                k_prev = kline.get(code, {}).get(dates[idx - i - 2], {}) if idx-i-2 >= 0 else {}
                h, l, pc = k_i.get('h',0), k_i.get('l',0), k_prev.get('c',0)
                if h and l and pc:
                    trs.append(max(h-l, abs(h-pc), abs(l-pc)))
            atr = sum(trs)/14 if trs else 0
        
        trades.append({
            'sd': sd, 'code': code, 'buy': buy_p,
            'd1_open': k1['o'], 'd1_high': k1['h'],
            'd1_low': k1['l'], 'd1_close': k1['c'],
            'd1_vol': k1['v'], 'ma5': ma5, 'ma10': ma10, 'atr': atr
        })

print(f"交易笔数: {len(trades)}")

# ===== 卖出策略 =====
def backtest_sell(name, sell_func):
    """sell_func(trade) -> sell_price"""
    monthly = defaultdict(lambda: {'sum':0.0, 'days':0, 'win':0, 'lose':0})
    day_groups = defaultdict(list)
    for t in trades:
        day_groups[t['sd']].append(t)
    
    for sd, group in sorted(day_groups.items()):
        rets = []
        for t in group:
            sp = sell_func(t)
            if sp is None or sp <= 0: continue
            rets.append(calc(t['buy'], sp))
        if len(group) > 0 and len(rets) > 0:
            # 取Top2按成交额
            sorted_grp = sorted(zip(rets, group), key=lambda x: x[1]['d1_vol'] * x[1]['buy'], reverse=True)
            top = sorted_grp[:2] if len(sorted_grp) >= 2 else sorted_grp
            rets2 = [r for r, _ in top]
            
            avg = sum(rets2) / len(rets2)
        else:
            avg = 0
            rets2 = []
        
        m = sd[:6]
        monthly[m]['sum'] += avg
        monthly[m]['days'] += 1
        if avg > 0: monthly[m]['win'] += 1
        elif avg < 0: monthly[m]['lose'] += 1
    
    cum = 1.0; peak = 1.0; dd = 0.0; w = 0; d = 0
    for m in sorted(monthly):
        d += monthly[m]['days']; w += monthly[m]['win']
        cum *= (1 + monthly[m]['sum'] / 100)
        if cum > peak: peak = cum
        _dd = (cum - peak) / peak * 100
        if _dd < dd: dd = _dd
    wr = w/d*100 if d else 0
    return {'name': name, 'nav': cum, 'total': (cum-1)*100, 'dd': dd, 'wr': wr}

strategies = []

# 1. 收盘卖 (基准)
strategies.append(("1.收盘卖(基准)", lambda t: t['d1_close']))

# 2. 开盘卖
strategies.append(("2.开盘卖", lambda t: t['d1_open']))

# 3. 开盘/收盘孰高
strategies.append(("3.开盘收盘取高", lambda t: max(t['d1_open'], t['d1_close'])))

# 4. 高开就卖，低开守到收盘
strategies.append(("4.高开卖低开等", lambda t: t['d1_open'] if t['d1_open'] > t['buy'] else t['d1_close']))

# 5. 开盘止盈2%，否则收盘
strategies.append(("5.开盘涨2%止盈", lambda t: t['d1_open'] if t['d1_open'] > t['buy']*1.02 else t['d1_close']))

# 6. 开盘止盈3%，否则收盘
strategies.append(("6.开盘涨3%止盈", lambda t: t['d1_open'] if t['d1_open'] > t['buy']*1.03 else t['d1_close']))

# 7. 移动止损: 从开盘跟踪，跌破日内最高价2%
strategies.append(("7.跟踪止损2%", 
    lambda t: (t['d1_high']*0.98 if t['d1_low'] <= t['d1_high']*0.98 else t['d1_close'])))

# 8. 移动止损3%
strategies.append(("8.跟踪止损3%",
    lambda t: (t['d1_high']*0.97 if t['d1_low'] <= t['d1_high']*0.97 else t['d1_close'])))

# 9. 跌破买入价止损
strategies.append(("9.跌破买入价止损",
    lambda t: (t['buy']*0.995 if t['d1_low'] <= t['buy'] else t['d1_close'])))

# 10. ATR止损: 跌破high-2*ATR
strategies.append(("10.ATR 2倍止损",
    lambda t: (max(t['d1_high'] - 2*t['atr'], t['d1_low']) 
               if t['atr'] > 0 and t['d1_low'] <= t['d1_high'] - 2*t['atr'] 
               else t['d1_close'])))

# 11. 跌破MA5卖
strategies.append(("11.跌破MA5止损",
    lambda t: t['d1_close'] if t['d1_close'] >= t['ma5'] else t['d1_close']))

# 12. 高开2%卖一半(收盘)，低开3%全卖(开盘)
strategies.append(("12.高开2%卖一半",
    lambda t: (t['d1_open'] + t['d1_close'])/2 if t['d1_open'] > t['buy']*1.02 
              else (t['d1_open'] if t['d1_open'] < t['buy']*0.97 else t['d1_close'])))

# 13. 开盘破MA5就开盘出，否则守到收盘
strategies.append(("13.开盘破MA5出",
    lambda t: t['d1_open'] if t['d1_open'] < t['ma5'] else t['d1_close']))

# 14. 最高价2%回撤止盈 (理想化，用最高价附近卖出)
strategies.append(("14.日内最高2%回撤",
    lambda t: t['d1_high']*0.98 if t['d1_low'] <= t['d1_high']*0.98 and t['d1_high'] > t['buy']*1.01 
              else t['d1_close']))

# 15. 组合: 开盘涨1.5%卖，否则跟踪止损2.5%
strategies.append(("15.开涨1.5%出+跟踪2.5%",
    lambda t: t['d1_open'] if t['d1_open'] > t['buy']*1.015 
              else (t['d1_high']*0.975 if t['d1_low'] <= t['d1_high']*0.975 else t['d1_close'])))

print(f"\n{'='*70}")
print(f"  311策略 — {len(strategies)}种卖出方式对比")
print(f"  买入: D-2回踩日收盘 | Top2按成交额")
print(f"{'='*70}")
print(f"  {'卖出策略':<28} {'收益%':>9} {'净值':>7} {'回撤%':>7} {'胜率%':>6}")
print(f"  {'-'*58}")
results = []
for name, func in strategies:
    r = backtest_sell(name, func)
    results.append(r)
    print(f"  {r['name']:<28} {r['total']:>9.1f} {r['nav']:>7.2f} {r['dd']:>7.1f} {r['wr']:>6.1f}")

best = max(results, key=lambda x: x['total'])
print(f"\n  最佳: {best['name']} — 净值{best['nav']:.1f}倍 回撤{abs(best['dd']):.1f}%")
print(f"  原始(收盘卖): {results[0]['total']:.1f}% 净值{results[0]['nav']:.2f}")
