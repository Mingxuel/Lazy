#!/usr/bin/env python3
"""
311策略 Top-2 选股优化
测试多种排名指标，每天最多选2只
"""
import os, sys
from collections import defaultdict

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
KLINE_DIR = os.path.join(BASE, "1D")
DATES_FILE = os.path.join(BASE, "TRADING_DATES")

dates = []
with open(DATES_FILE) as f:
    for line in f:
        d = line.strip()
        if d: dates.append(d)
date_idx = {d: i for i, d in enumerate(dates)}

COMM = 0.00025; COMM_MIN = 5.0; STAMP = 0.0005; TRANS = 0.00001
CAPITAL = 1_000_000

# 收集所有信号 + 需要的K线数据
signal_days = {}
need_kline = defaultdict(set)  # code -> {(date, field), ...}

for fname in sorted(os.listdir(SIGNAL_DIR)):
    fpath = os.path.join(SIGNAL_DIR, fname)
    if os.path.getsize(fpath) <= 3: continue
    with open(fpath) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines: continue

    sig_date = fname
    idx = date_idx.get(sig_date, -1)
    if idx < 2: continue
    d2_date = dates[idx - 2]
    d3_date = dates[idx - 3]

    entries = []
    for line in lines:
        p = line.split('|')
        if len(p) < 8: continue
        code = p[0]
        # D-0 数据
        d0_close = float(p[4])
        d0_volume = float(p[5])
        d0_amount = float(p[6])
        d1_close = float(p[7])  # pre_close = D-1

        entries.append({
            'code': code,
            'd0_close': d0_close, 'd0_volume': d0_volume, 'd0_amount': d0_amount,
            'd1_close': d1_close,
        })
        need_kline[code].add((d2_date, 'close'))
        need_kline[code].add((d3_date, 'close'))
        need_kline[code].add((d3_date, 'volume'))

    if entries:
        signal_days[sig_date] = (entries, d2_date, d3_date)

# 加载K线
kline = defaultdict(dict)
for code, queries in need_kline.items():
    kp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(kp): continue
    dates_needed = {q[0] for q in queries}
    with open(kp) as kf:
        for line in kf:
            p = line.strip().split('|')
            if len(p) < 6: continue
            if p[0] in dates_needed:
                kline[code][p[0]] = {'close': float(p[4]), 'volume': float(p[5])}

# 计算每笔交易的收益
def calc_return(buy_price, sell_price):
    shares = int(CAPITAL / 2 / buy_price / 100) * 100  # 2只平分
    if shares == 0: shares = 100
    cost = shares * buy_price
    buy_fee = max(cost * COMM, COMM_MIN) + cost * TRANS
    total_buy = cost + buy_fee
    rev = shares * sell_price
    sell_fee = max(rev * COMM, COMM_MIN) + rev * TRANS + rev * STAMP
    net_sell = rev - sell_fee
    return (net_sell - total_buy) / total_buy * 100

# 为每天每只股票补充K线数据
for sig_date, (entries, d2_date, d3_date) in signal_days.items():
    for e in entries:
        code = e['code']
        d2 = kline.get(code, {}).get(d2_date, {})
        d3 = kline.get(code, {}).get(d3_date, {})
        d2_close = d2.get('close')
        d3_close = d3.get('close')
        d3_volume = d3.get('volume')

        e['d2_close'] = d2_close
        e['d3_close'] = d3_close
        e['d3_volume'] = d3_volume

        # 计算排名指标
        if d2_close and d3_close and d2_close > 0 and d3_close > 0:
            e['pullback_pct'] = (d3_close - d2_close) / d3_close * 100  # 回踩幅度(越小越好)
        else:
            e['pullback_pct'] = None

        if d3_volume and d3_volume > 0:
            e['vol_ratio'] = e['d0_volume'] / d3_volume  # 量比(越大越好)
        else:
            e['vol_ratio'] = None

        if d2_close and d2_close > 0:
            e['d0_vs_d2'] = (e['d0_close'] - d2_close) / d2_close * 100  # D-0相对D-2涨幅
        else:
            e['d0_vs_d2'] = None

# 测试各种排名策略
def test_strategy(name, rank_key, reverse=True):
    """rank_key: lambda e -> score, reverse=True means higher=better"""
    monthly = defaultdict(lambda: {'days': 0, 'sum': 0.0, 'win': 0, 'lose': 0})
    total_trades = 0
    
    for sig_date, (entries, d2_date, d3_date) in sorted(signal_days.items()):
        # 过滤有完整数据的
        valid = [e for e in entries if e.get('d2_close') and e.get('d1_close') and e['d2_close'] > 0 and e['d1_close'] > 0]
        if not valid: continue
        
        # 排序
        scored = []
        for e in valid:
            score = rank_key(e)
            if score is not None:
                scored.append((score, e))
        
        if not scored: continue
        
        scored.sort(key=lambda x: x[0], reverse=reverse)
        top2 = [s[1] for s in scored[:2]]
        
        tr = 0.0
        for e in top2:
            ret = calc_return(e['d2_close'], e['d1_close'])
            tr += ret
            total_trades += 1
        
        avg = tr / len(top2)
        m = sig_date[:6]
        monthly[m]['days'] += 1
        monthly[m]['sum'] += avg
        if avg > 0: monthly[m]['win'] += 1
        elif avg < 0: monthly[m]['lose'] += 1

    # 汇总
    all_sum = 0.0; all_days = 0; all_win = 0; all_lose = 0
    cum = 1.0; peak = 1.0; max_dd = 0.0
    for month in sorted(monthly.keys()):
        m = monthly[month]
        all_sum += m['sum']; all_days += m['days']
        all_win += m['win']; all_lose += m['lose']
        cum *= (1 + m['sum'] / 100)
        if cum > peak: peak = cum
        dd = (cum - peak) / peak * 100
        if dd < max_dd: max_dd = dd

    wr = all_win / all_days * 100 if all_days else 0
    return {
        'name': name, 'total': (cum-1)*100, 'nav': cum,
        'dd': max_dd, 'wr': wr, 'days': all_days,
        'trades': total_trades, 'months': len(monthly)
    }

# 基准：全部等权（之前的622笔）
all_results = []
print("测试排名策略...\n")

# 1. 回踩幅度最小（最强势）
r = test_strategy("1.回踩最小(越强越好)", lambda e: -e.get('pullback_pct', 999) if e.get('pullback_pct') is not None else None, reverse=True)
all_results.append(r)

# 2. D-0对D-2涨幅最大（动量最强）
r = test_strategy("2.D0vsD2涨幅(动量最强)", lambda e: e.get('d0_vs_d2'), reverse=True)
all_results.append(r)

# 3. 量比最大（放量最猛）
r = test_strategy("3.量比最大(放量最猛)", lambda e: e.get('vol_ratio'), reverse=True)
all_results.append(r)

# 4. 成交额最大（流动性最好）
r = test_strategy("4.成交额最大(流动性)", lambda e: e['d0_amount'], reverse=True)
all_results.append(r)

# 5. 回踩最小 + 量比组合
r = test_strategy("5.回踩最小×量比", lambda e: (-e.get('pullback_pct', 999) * (e.get('vol_ratio') or 1)) if e.get('pullback_pct') is not None else None, reverse=True)
all_results.append(r)

# 6. D-0收盘价距离D-2最近（最稳）
r = test_strategy("6.D0距D2最近(最稳)", lambda e: -abs(e.get('d0_vs_d2', 999)), reverse=True)
all_results.append(r)

# 7. 每日D-0涨幅最大
r = test_strategy("7.D-0日涨幅最大", lambda e: (e['d0_close'] - e['d1_close']) / e['d1_close'] * 100, reverse=True)
all_results.append(r)

# 8. 先按回踩排序，取前4，再按量比取前2
r = test_strategy("8.回踩Top4→量比Top2", 
    lambda e: None, reverse=True)  # 需要特殊处理, skip for now

# 8替代：回踩<2% + 量比>1 筛选后按成交额
# Skip complex composite for now

# 打印结果
print(f"{'策略':<30} {'总收益%':>10} {'净值':>8} {'回撤%':>8} {'胜率%':>7} {'天数':>6}")
print("-" * 80)
for r in sorted(all_results, key=lambda x: x['total'], reverse=True):
    print(f"{r['name']:<30} {r['total']:>10.2f} {r['nav']:>8.2f} {r['dd']:>8.1f} {r['wr']:>7.1f} {r['days']:>6}")
