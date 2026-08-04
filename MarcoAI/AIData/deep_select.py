#!/usr/bin/env python3
"""
311策略 三日选股池 + 多维度选股优化
池: D-2/D-1/D-0 三日信号并集
买: D-0尾盘  |  卖: D+1尾盘
测试10+选股方法含深度学习
"""
import os, sys, math, random, json
from collections import defaultdict
from itertools import islice

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

# ===== Step 1: 读取所有信号 =====
all_signals = {}  # date -> [codes]
for fname in os.listdir(SIGNAL_DIR):
    fp = os.path.join(SIGNAL_DIR, fname)
    if not os.path.isfile(fp) or os.path.getsize(fp) <= 3: continue
    with open(fp) as f:
        lines = [l.strip() for l in f if l.strip()]
    if lines:
        all_signals[fname] = [l.split('|')[0] for l in lines if '|' in l]

print(f"信号日数: {len(all_signals)}")

# ===== Step 2: 加载所有需要的K线数据 =====
# 需要每只股票在多个日期的数据
need_kline = defaultdict(set)
pool_info = {}  # (date, code) -> {d0_close, buy_date_for_this_code, etc}

for d_idx in range(4, len(dates)):  # D0 = dates[d_idx]
    d0 = dates[d_idx]
    if d_idx >= len(dates) - 1: continue
    d_next = dates[d_idx+1]  # D+1 卖出日
    
    # 检查 D0/D-1/D-2 三天信号
    pool_codes = set()
    for offset in [0, 1, 2]:
        sd = dates[d_idx - offset]
        if sd in all_signals:
            pool_codes.update(all_signals[sd])
    
    if not pool_codes: continue
    
    for code in pool_codes:
        pool_info[(d0, code)] = d_next
        need_kline[code].add(d0)      # buy price
        need_kline[code].add(d_next)  # sell price
        # 也需要更早的数据计算指标 (往前5天)
        for i in range(1, 21):
            if d_idx - i >= 0:
                need_kline[code].add(dates[d_idx - i])

print(f"池中总(日期,股票)对: {len(pool_info)}, 股票数: {len(need_kline)}")

# 加载K线
print("加载K线数据...")
kline = defaultdict(dict)
for code, tds in need_kline.items():
    kp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(kp): continue
    with open(kp) as kf:
        for line in kf:
            p = line.strip().split('|')
            if len(p) < 6: continue
            if p[0] in tds:
                kline[code][p[0]] = {
                    'open': float(p[1]), 'high': float(p[2]),
                    'low': float(p[3]), 'close': float(p[4]),
                    'volume': float(p[5]), 'amount': float(p[6])
                }

print(f"K线数据就绪")

# ===== Step 3: 为每个候选计算特征 =====
def safe_div(a, b, default=0.0):
    return a/b if b and b!=0 else default

def compute_features(code, d0, d_idx):
    """计算D0时刻已知的所有特征"""
    k0 = kline.get(code, {}).get(d0, {})
    if not k0 or k0.get('close',0) == 0: return None
    
    f = {}
    f['code'] = code
    f['d0'] = d0
    f['close'] = k0['close']
    f['open'] = k0['open']
    f['high'] = k0['high']
    f['low'] = k0['low']
    f['volume'] = k0['volume']
    f['amount'] = k0['amount']
    
    # ---- VWAP 估算 ----
    k0_prev = kline.get(code, {}).get(dates[d_idx-1] if d_idx>0 else '', {})
    if k0 and k0_prev and k0['volume'] > 0:
        typical_price = (k0['high'] + k0['low'] + k0['close']) / 3
        prev_typical = (k0_prev.get('high',0) + k0_prev.get('low',0) + k0_prev.get('close',0)) / 3
        vwap_daily = (typical_price * k0['volume'] + prev_typical * k0_prev.get('volume',1)) / (k0['volume'] + k0_prev.get('volume',1))
        f['vwap_deviation'] = safe_div(k0['close'] - vwap_daily, vwap_daily) * 100
    else:
        f['vwap_deviation'] = 0.0
    
    # ---- 最近N日数据 ----
    closes_20 = []; volumes_20 = []; highs_20 = []; lows_20 = []
    for i in range(20):
        dd = dates[d_idx - i] if d_idx - i >= 0 else None
        if dd:
            k = kline.get(code, {}).get(dd, {})
            c = k.get('close', 0)
            if c > 0:
                closes_20.append(c)
                volumes_20.append(k.get('volume', 0))
                highs_20.append(k.get('high', 0))
                lows_20.append(k.get('low', 0))
    
    if len(closes_20) < 5: return None
    
    # 均线
    for n in [3, 5, 10, 20]:
        if len(closes_20) >= n:
            ma = sum(closes_20[:n]) / n
            f[f'ma{n}_dev'] = safe_div(k0['close'] - ma, ma) * 100
    
    # 波动率
    if len(closes_20) >= 10:
        rets = [safe_div(closes_20[i] - closes_20[i+1], closes_20[i+1]) for i in range(9)]
        f['volatility_10d'] = (sum(r*r for r in rets) / 9) ** 0.5 * 100
    
    # 量比
    if len(volumes_20) >= 5:
        avg_vol_5 = sum(volumes_20[1:6]) / 5  # D-1到D-5
        f['vol_ratio_5'] = safe_div(k0['volume'], avg_vol_5)
        avg_vol_20 = sum(volumes_20[1:]) / min(19, len(volumes_20)-1)
        f['vol_ratio_20'] = safe_div(k0['volume'], avg_vol_20)
    
    # 日内强度
    f['intraday_strength'] = safe_div(k0['close'] - k0['low'], k0['high'] - k0['low'])
    f['upper_shadow'] = safe_div(k0['high'] - max(k0['close'], k0['open']), k0['high'] - k0['low'])
    f['daily_return'] = safe_div(k0['close'] - k0['open'], k0['open']) * 100
    
    # 近期动量
    if len(closes_20) >= 5:
        f['mom_1d'] = safe_div(closes_20[0] - closes_20[1], closes_20[1]) * 100
        f['mom_3d'] = safe_div(closes_20[0] - closes_20[3], closes_20[3]) * 100
        f['mom_5d'] = safe_div(closes_20[0] - closes_20[5], closes_20[5]) * 100 if len(closes_20)>=6 else 0
    
    # RSI 14
    if len(closes_20) >= 15:
        gains = [max(closes_20[i] - closes_20[i+1], 0) for i in range(14)]
        losses = [max(closes_20[i+1] - closes_20[i], 0) for i in range(14)]
        avg_gain = sum(gains)/14
        avg_loss = sum(losses)/14
        f['rsi_14'] = safe_div(avg_gain, avg_gain+avg_loss) * 100 if (avg_gain+avg_loss)>0 else 50
    
    # 高低点位置
    if len(highs_20) >= 20 and len(lows_20) >= 20:
        hh = max(highs_20); ll = min(lows_20)
        f['price_position'] = safe_div(k0['close'] - ll, hh - ll) * 100
    
    # D-0 涨跌幅 (relative to D-1)
    if len(closes_20) >= 2:
        f['ret_d0'] = safe_div(closes_20[0] - closes_20[1], closes_20[1]) * 100
    
    # 成交额排名（当日）
    f['amount_log'] = math.log(f['amount'] + 1)
    
    return f

# ===== Step 4: 构建数据集 =====
print("构建特征数据集...")
CAPITAL = 1_000_000

def calc_ret_1d(buy_price, sell_price, n_stocks=2):
    shares = int(CAPITAL / n_stocks / buy_price / 100) * 100
    if shares == 0: shares = 100
    cost = shares * buy_price
    bf = max(cost * COMM, COMM_MIN) + cost * TRANS
    total_buy = cost + bf
    rev = shares * sell_price
    sf = max(rev * COMM, COMM_MIN) + rev * TRANS + rev * STAMP
    net_sell = rev - sf
    return (net_sell - total_buy) / total_buy * 100

all_samples = []  # 每条: (d0, features_dict, actual_ret, size_rank_for_day)
day_pools = {}     # d0 -> [features_dict...]

for d_idx in range(4, len(dates)):
    d0 = dates[d_idx]
    if d_idx >= len(dates) - 1: continue
    d_next = dates[d_idx + 1]
    
    day_stocks = []
    for code in need_kline:
        if (d0, code) not in pool_info: continue
        features = compute_features(code, d0, d_idx)
        if features is None: continue
        
        sell_data = kline.get(code, {}).get(d_next, {})
        sell_close = sell_data.get('close', 0)
        if sell_close == 0: continue
        
        actual_ret = calc_ret_1d(features['close'], sell_close)
        features['actual_ret'] = actual_ret
        features['d_next'] = d_next
        features['sell_close'] = sell_close
        
        day_stocks.append(features)
        all_samples.append(features)
    
    if day_stocks:
        day_pools[d0] = day_stocks

print(f"样本数: {len(all_samples)}, 有效交易日: {len(day_pools)}")

# ===== Step 5: 定义选股方法 =====
def backtest_method(name, rank_func, reverse=True, top_n=2):
    """rank_func: features -> score"""
    monthly = defaultdict(lambda: {'sum':0.0,'days':0,'win':0,'lose':0})
    
    for d0, pool in sorted(day_pools.items()):
        scored = [(rank_func(f), f) for f in pool if rank_func(f) is not None]
        if not scored: continue
        scored.sort(key=lambda x: x[0], reverse=reverse)
        selected = [s[1] for s in scored[:top_n]]
        
        avg_ret = sum(f['actual_ret'] for f in selected) / len(selected)
        m = d0[:6]
        monthly[m]['sum'] += avg_ret
        monthly[m]['days'] += 1
        if avg_ret > 0: monthly[m]['win'] += 1
        elif avg_ret < 0: monthly[m]['lose'] += 1
    
    cum = 1.0; peak = 1.0; dd = 0.0; w = 0; d = 0
    for m in sorted(monthly):
        d += monthly[m]['days']; w += monthly[m]['win']
        cum *= (1 + monthly[m]['sum'] / 100)
        if cum > peak: peak = cum
        _dd = (cum - peak) / peak * 100
        if _dd < dd: dd = _dd
    
    return {'name': name, 'nav': cum, 'total': (cum-1)*100, 'dd': dd, 'wr': w/d*100 if d else 0}

# ---- 方法定义 ----
methods = []

# 1. VWAP偏离最小 (收盘价接近VWAP = 真实价值附近)
methods.append(("1.VWAP偏离最小(价值)", lambda f: -abs(f['vwap_deviation']), True))

# 2. VWAP上方幅度适中 (站在VWAP上方但不太远)
methods.append(("2.VWAP上方2%内", lambda f: f['vwap_deviation'] if 0 < f['vwap_deviation'] < 2 else None, True))

# 3. 量比最大 (当天放量明显)
methods.append(("3.量比5日最大", lambda f: f.get('vol_ratio_5', 0), True))

# 4. 日内强度 (收盘在日内高位 = 强势)
methods.append(("4.日内强度最高", lambda f: f['intraday_strength'], True))

# 5. 均线多头排列 (股价在MA3/5/10/20之上)
methods.append(("5.均线多头排列", 
    lambda f: sum(1 for n in [3,5,10,20] if f.get(f'ma{n}_dev', -999) > 0), True))

# 6. 低波动+均线支撑 (防守型)
methods.append(("6.低波+MA5支撑", 
    lambda f: -f.get('volatility_10d', 99) * 10 + (f.get('ma5_dev', -999) if f.get('ma5_dev', -999) > -2 else -999), True))

# 7. RSI适中 (50-70区间，趋势中不强不弱)
methods.append(("7.RSI 50-70区间", 
    lambda f: f.get('rsi_14', 50) if 50 <= f.get('rsi_14', 50) <= 70 else None, True))

# 8. 高位+高量 (价格在20日高位且有量配合)
methods.append(("8.高位放量", 
    lambda f: f.get('price_position', 50) * 0.5 + f.get('vol_ratio_20', 1) * 0.5, True))

# 9. 动量最强 (近3日涨幅最大)
methods.append(("9.近3日动量最强", lambda f: f.get('mom_3d', 0), True))

# 10. 回撤最小 (相对20日高点回撤最小)
methods.append(("10.距20日高点最近", 
    lambda f: -abs(f.get('price_position', 50) - 100), True))

# 11. 组合评分: 量比+日内强度+均线偏离
methods.append(("11.综合评分(量比+强度+均线)", 
    lambda f: f.get('vol_ratio_5', 1) * 0.3 + f['intraday_strength'] * 0.3 + max(0, f.get('ma5_dev', -10)) * 0.2 + f.get('mom_3d', 0) * 0.2, True))

# 12. 成交额最大 (流动性)
methods.append(("12.成交额最大", lambda f: f['amount'], True))

# 13. 上影线最小 (抛压小)
methods.append(("13.上影线最小(抛压小)", lambda f: -f.get('upper_shadow', 0.5), True))

# 14. 随机对照
random.seed(42)
methods.append(("14.随机选择(基准)", lambda f: random.random(), True))

print(f"\n{'='*68}")
print(f"  测试 {len(methods)} 种选股方法")
print(f"{'='*68}")

print(f"  {'方法':<30} {'收益%':>9} {'净值':>7} {'回撤%':>7} {'胜率%':>6}")
print(f"  {'-'*60}")
results = []
for name, func, rev in methods:
    r = backtest_method(name, func, rev)
    results.append(r)
    print(f"  {r['name']:<30} {r['total']:>9.1f} {r['nav']:>7.2f} {r['dd']:>7.1f} {r['wr']:>6.1f}")

best = max(results, key=lambda x: x['total'])
print(f"\n  最佳: {best['name']} — 净值{best['nav']:.1f}倍 回撤{abs(best['dd']):.1f}%")
