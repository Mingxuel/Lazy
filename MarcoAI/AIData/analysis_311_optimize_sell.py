#!/usr/bin/env python3
"""
策略311 卖点优化 — 基于5分钟数据（正确版 v2）

311策略:
  涨停(D-4) → 放量(D-3) → 回踩(D-2)→尾盘买入 → 空(D-1)→尾盘卖出 → D-0信号日
  
  买入: D-2收盘价 (从1D K线获取)
  卖出: D-1收盘价 = signal[7] = pre_close (baseline)
  
  5M优化: 在D-1(卖出日)用5分钟数据找更好的卖点
"""
import os, sys
from collections import defaultdict

STRATEGY = "311"
BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", STRATEGY)
FIVEM_DIR = os.path.join(BASE, "5M")
KLINE_DIR = os.path.join(BASE, "1D")

COMMISSION_RATE = 0.00025
COMMISSION_MIN = 5.0
STAMP_DUTY = 0.0005
TRANSFER_FEE = 0.00001
CAPITAL = 1_000_000

# ============================================================
# 卖出策略定义 (在 D-1 日执行)
# ============================================================

STRATEGIES = {}

# --- 固定时间卖点 ---
FIXED_TIMES = [
    ("09:35", "09:35"), ("10:00", "10:00"), ("10:30", "10:30"),
    ("11:00", "11:00"), ("11:30", "11:30"), ("13:05", "13:05"),
    ("14:00", "14:00"), ("14:30", "14:30"), ("14:50", "14:50"),
]
for label, target_time in FIXED_TIMES:
    def make_fixed(t=target_time):
        def f(bars, pre_close):
            key = bars[0]['date'] + ' ' + t + ':00'
            for b in bars:
                if b['dt'] == key:
                    return b['close'], key
            return bars[-1]['close'], bars[-1]['dt']
        return f
    STRATEGIES[f"固定时间_{label}"] = make_fixed()

# --- baseline: D-1收盘卖出（用signal[7]=pre_close）---
STRATEGIES["收盘(D-1)_baseline"] = None

# --- 日内最高价 ---
def exit_max_close(bars, pre_close):
    best = max(bars, key=lambda b: b['close'])
    return best['close'], best['dt']
STRATEGIES["日内最高价"] = exit_max_close

# --- 上午最高价 ---
def exit_morning_max(bars, pre_close):
    morning = [b for b in bars if b['dt'] <= bars[0]['date'] + ' 11:30:00']
    if not morning:
        return bars[0]['close'], bars[0]['dt']
    best = max(morning, key=lambda b: b['close'])
    return best['close'], best['dt']
STRATEGIES["上午最高价"] = exit_morning_max

# --- 日内最低价 ---
def exit_min_close(bars, pre_close):
    worst = min(bars, key=lambda b: b['close'])
    return worst['close'], worst['dt']
STRATEGIES["日内最低价"] = exit_min_close

# --- 移动止盈: 从日内最高回落X% ---
for pct in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
    def make_trailing(threshold=pct):
        def f(bars, pre_close):
            peak = bars[0]['close']
            for b in bars:
                if b['close'] > peak:
                    peak = b['close']
                elif (peak - b['close']) / peak * 100 >= threshold:
                    return b['close'], b['dt']
            return bars[-1]['close'], bars[-1]['dt']
        return f
    STRATEGIES[f"移动止盈_-{pct}%"] = make_trailing()

# --- 新高后回落1%卖 ---
def exit_exhaustion(bars, pre_close):
    peak = bars[0]['close']
    peak_idx = 0
    for i, b in enumerate(bars):
        if b['close'] > peak:
            peak = b['close']
            peak_idx = i
    for i in range(peak_idx + 1, len(bars)):
        if bars[i]['close'] < peak * 0.99:
            return bars[i]['close'], bars[i]['dt']
    return bars[-1]['close'], bars[-1]['dt']
STRATEGIES["新高后回落1%卖"] = exit_exhaustion

# --- 接近涨停(9%+)即卖 ---
def exit_near_limit(bars, pre_close):
    limit_price = pre_close * 1.095
    for b in bars:
        if b['close'] >= limit_price:
            return b['close'], b['dt']
        if b['close'] >= pre_close * 1.09:
            return b['close'], b['dt']
    return bars[-1]['close'], bars[-1]['dt']
STRATEGIES["接近涨停(9%+)即卖"] = exit_near_limit

# --- 半仓D-1收盘+半仓D-1上午最高 ---
def exit_half_amhigh_close(bars, pre_close):
    morning = [b for b in bars if b['dt'] <= bars[0]['date'] + ' 11:30:00']
    am_high = max(b['close'] for b in morning) if morning else bars[0]['close']
    ret_am = (am_high - pre_close) / pre_close if pre_close else 0
    ret_close = (bars[-1]['close'] - pre_close) / pre_close if pre_close else 0
    return pre_close * (1 + (ret_am + ret_close) / 2), bars[0]['date'] + ' 上午高/收盘'
STRATEGIES["5050_上午最高+收盘"] = exit_half_amhigh_close

# --- 连3阴卖出 ---
def exit_3red(bars, pre_close):
    red_count = 0
    for i in range(1, len(bars)):
        if bars[i]['close'] < bars[i-1]['close']:
            red_count += 1
            if red_count >= 3:
                return bars[i]['close'], bars[i]['dt']
        else:
            red_count = 0
    return bars[-1]['close'], bars[-1]['dt']
STRATEGIES["连3阴卖出"] = exit_3red

# --- 开盘价卖出 ---
def exit_open(bars, pre_close):
    return bars[0]['close'], bars[0]['dt']
STRATEGIES["开盘价卖出"] = exit_open


# ============================================================
# 数据加载
# ============================================================

def load_trading_dates():
    """加载交易日历"""
    fpath = os.path.join(BASE, "TRADING_DATES")
    dates = []
    with open(fpath) as f:
        for line in f:
            line = line.strip()
            if line:
                dates.append(line)
    return sorted(dates)


def load_1d_close(code, date_str):
    """获取某只股票某日的收盘价"""
    fpath = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fpath):
        return None
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line.startswith(date_str):
                parts = line.split('|')
                if len(parts) >= 5:
                    return float(parts[4])
    return None


def load_5m_bars(code, date_str):
    """加载某只股票某日的5分钟K线。date_str: YYYYMMDD"""
    fpath = os.path.join(FIVEM_DIR, code)
    if not os.path.exists(fpath):
        return None
    date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    bars = []
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('|')
            if len(parts) < 6: continue
            dt = parts[0]
            if not dt.startswith(date_formatted): continue
            bars.append({
                'dt': dt,
                'date': dt[:10],
                'time': dt[11:],
                'open':  float(parts[1]),
                'high':  float(parts[2]),
                'low':   float(parts[3]),
                'close': float(parts[4]),
            })
    return bars if bars else None


def load_signals():
    """加载所有311信号，返回 {D0_date: [(code, D1_close)]}"""
    signal_days = {}
    signal_files = sorted([f for f in os.listdir(SIGNAL_DIR)
                           if os.path.isfile(os.path.join(SIGNAL_DIR, f))])
    for fname in signal_files:
        fpath = os.path.join(SIGNAL_DIR, fname)
        if os.path.getsize(fpath) <= 3: continue
        with open(fpath, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines: continue
        entries = []
        for line in lines:
            parts = line.split('|')
            if len(parts) < 8: continue
            code = parts[0]
            d1_close = float(parts[7])  # pre_close = D-1 close = 卖出价
            entries.append((code, d1_close))
        if entries:
            signal_days[fname] = entries
    return signal_days


def calc_return(buy_price, sell_price, per_cap):
    """计算单笔收益率(含手续费)"""
    if buy_price == 0 or sell_price == 0:
        return 0.0
    shares = int(per_cap / buy_price / 100) * 100
    if shares == 0:
        shares = 100
    cost = shares * buy_price
    buy_fee = max(cost * COMMISSION_RATE, COMMISSION_MIN) + cost * TRANSFER_FEE
    total_buy = cost + buy_fee
    rev = shares * sell_price
    sell_fee = max(rev * COMMISSION_RATE, COMMISSION_MIN) + rev * TRANSFER_FEE + rev * STAMP_DUTY
    net_sell = rev - sell_fee
    return (net_sell - total_buy) / total_buy * 100


# ============================================================
# 主分析
# ============================================================

print("=" * 95)
print("  策略311 卖点优化 v2 — 正确版")
print("  D-2尾盘买 / D-1尾盘卖(或优化卖点) / D-0信号日")
print("=" * 95)

signal_days = load_signals()
trading_dates = load_trading_dates()
date_index = {d: i for i, d in enumerate(trading_dates)}

print(f"\n信号范围: D0日期 {min(signal_days.keys())} ~ {max(signal_days.keys())}, "
      f"{len(signal_days)}天有信号")

# 为每个信号查找D-1(卖出日)和D-2(买入日)日期
# signal file date = D0
# 需要: D-1 = trading day before D0, D-2 = trading day before D-1
processed = []  # [(code, d2_date, d1_date, d2_close, d1_close)]
missing_d2 = 0
missing_5m = 0

for d0_date in sorted(signal_days.keys()):
    entries = signal_days[d0_date]
    
    # Find D-1 and D-2
    d0_idx = date_index.get(d0_date)
    if d0_idx is None or d0_idx < 2:
        continue
    d1_date = trading_dates[d0_idx - 1]
    d2_date = trading_dates[d0_idx - 2]
    
    for code, d1_close in entries:
        # Get D-2 close (buy price) from 1D K-line
        d2_close = load_1d_close(code, d2_date)
        if d2_close is None:
            missing_d2 += 1
            continue
        processed.append((code, d2_date, d1_date, d2_close, d1_close, d0_date))

print(f"有效交易: {len(processed)} (D2数据缺失: {missing_d2})")

# 预加载D-1日的5M数据（卖出日的5分钟K线）
print("预加载D-1日5M数据...")
fivem_cache = {}
hit = 0
for code, d2_date, d1_date, d2_close, d1_close, d0_date in processed:
    key = (code, d1_date)
    if key not in fivem_cache:
        bars = load_5m_bars(code, d1_date)
        if bars:
            fivem_cache[key] = bars
            hit += 1
        else:
            missing_5m += 1

print(f"5M数据命中: {hit}, 缺失: {missing_5m}")

# 按D0日期分组（保持跟之前分析一样的日期维度）
# 实际上应该按D1(卖出日)分组，因为一天内可能有多只股票同时卖出
strategy_names = list(STRATEGIES.keys())
results = {name: [] for name in strategy_names}

for d0_date in sorted(signal_days.keys()):
    # 找出所有D1=某日的交易
    day_trades = [p for p in processed if p[2] in 
                  [trading_dates[date_index[d0_date]-1] if date_index.get(d0_date) and date_index[d0_date] >= 1 else None]]
    
    # 按D1日期分组更合理
    pass

# 按D1日期（实际卖出日）分组
by_d1 = defaultdict(list)
for p in processed:
    by_d1[p[2]].append(p)  # p[2] = d1_date

print(f"\n实际卖出日: {len(by_d1)}天")

strategy_names = list(STRATEGIES.keys())
results = {name: [] for name in strategy_names}

for d1_date in sorted(by_d1.keys()):
    trades = by_d1[d1_date]
    n = len(trades)
    per_cap = CAPITAL / n

    day_results = {name: [] for name in strategy_names}

    # Baseline: 所有股票用D-1收盘价卖出
    for code, d2_date, d1_date, d2_close, d1_close, d0_date in trades:
        day_results["收盘(D-1)_baseline"].append(
            calc_return(d2_close, d1_close, per_cap))

    # 5M策略
    valid_trades = []
    for code, d2_date, d1_date, d2_close, d1_close, d0_date in trades:
        bars = fivem_cache.get((code, d1_date))
        if bars is not None:
            valid_trades.append((code, d2_close, d1_close, bars))

    if not valid_trades:
        # 没有任何5M数据，但baseline已记录，仍需聚合
        for sname in strategy_names:
            rets = day_results[sname]
            if rets:
                avg_ret = sum(rets) / len(rets)
                results[sname].append({
                    'date': d1_date,
                    'ret': round(avg_ret, 4),
                    'cnt': len(rets)
                })
        continue

    valid_n = len(valid_trades)
    per_cap_5m = CAPITAL / valid_n
    for code, d2_close, d1_close, bars in valid_trades:
        for sname, sfunc in STRATEGIES.items():
            if sname == "收盘(D-1)_baseline":
                continue
            sell_price, _ = sfunc(bars, d2_close)  # pre_close for the 5M day = D-2 close
            day_results[sname].append(calc_return(d2_close, sell_price, per_cap_5m))

    # Aggregate
    for sname in strategy_names:
        rets = day_results[sname]
        if rets:
            avg_ret = sum(rets) / len(rets)
            results[sname].append({
                'date': d1_date,
                'ret': round(avg_ret, 4),
                'cnt': len(rets)
            })


# ============================================================
# 输出对比报告
# ============================================================

print("\n" + "=" * 95)
print("  策略对比总览 (按累计净值降序) — 每日复利计算")
print(f"  D-2尾盘买 / D-1盘中卖出 / 等权均分资金 / 含手续费")
print("=" * 95)
print(f"  {'策略':<22} {'累计净值':>8} {'总收益%':>10} {'胜率%':>8} {'年化%':>8} {'最大回撤%':>10} {'交易日':>6}")
print("  " + "-" * 90)

rankings = []
for sname in strategy_names:
    data = results[sname]
    if not data:
        continue
    total_days = len(data)
    win_days = sum(1 for r in data if r['ret'] > 0)
    win_rate = win_days / total_days * 100 if total_days else 0

    cum = 1.0; peak = 1.0; max_dd = 0.0
    for r in data:
        cum *= (1 + r['ret'] / 100)
        if cum > peak: peak = cum
        dd = (cum - peak) / peak * 100
        if dd < max_dd: max_dd = dd

    total_months = len(set(r['date'][:6] for r in data))
    ann_ret = ((cum ** (12 / total_months)) - 1) * 100 if total_months else 0
    total_ret_pct = (cum - 1) * 100

    rankings.append((cum, sname, total_days, ann_ret, win_rate, total_ret_pct, max_dd))

rankings.sort(key=lambda x: x[0], reverse=True)

for cum, sname, td, ann, wr, total_ret_pct, dd in rankings:
    print(f"  {sname:<22} {cum:>8.4f} {total_ret_pct:>10.2f} {wr:>7.1f} {ann:>8.2f} {dd:>10.2f} {td:>6}")

# 月度对比
print("\n" + "=" * 95)
print("  前5策略 月度收益对比（简单求和）")
print("=" * 95)

top5 = rankings[:5]
months = sorted(set(r['date'][:6] for _, sname, _, _, _, _, _ in top5 for r in results[sname]))

header = f"  {'月份':<8}"
for _, sname, _, _, _, _, _ in top5:
    header += f" {sname[:12]:>12}"
print(header)
print("  " + "-" * (8 + 13 * len(top5)))

for month in months:
    row = f"  {month:<8}"
    for _, sname, _, _, _, _, _ in top5:
        m_sum = sum(r['ret'] for r in results[sname] if r['date'].startswith(month))
        row += f" {m_sum:>12.2f}%"
    print(row)

# 盈亏分布
print("\n" + "=" * 95)
print("  各策略盈亏分布详情（日收益分布）")
print("=" * 95)
print(f"  {'策略':<22} {'<-5%':>8} {'-5~-2%':>8} {'-2~0%':>8} {'0~2%':>8} {'2~5%':>8} {'>5%':>8} {'均值%':>8}")
print("  " + "-" * 84)

for _, sname, _, _, _, _, _ in rankings:
    data = results[sname]
    buckets = {'lt_m5':0, 'm5_m2':0, 'm2_0':0, 'p0_2':0, 'p2_5':0, 'gt5':0}
    for r in data:
        ret = r['ret']
        if ret < -5: buckets['lt_m5'] += 1
        elif ret < -2: buckets['m5_m2'] += 1
        elif ret < 0: buckets['m2_0'] += 1
        elif ret < 2: buckets['p0_2'] += 1
        elif ret < 5: buckets['p2_5'] += 1
        else: buckets['gt5'] += 1
    avg_ret = sum(r['ret'] for r in data) / len(data)
    print(f"  {sname:<22} {buckets['lt_m5']:>8} {buckets['m5_m2']:>8} {buckets['m2_0']:>8} "
          f"{buckets['p0_2']:>8} {buckets['p2_5']:>8} {buckets['gt5']:>8} {avg_ret:>8.2f}")

print("\n" + "=" * 95)
print("  分析完成")
print("=" * 95)
