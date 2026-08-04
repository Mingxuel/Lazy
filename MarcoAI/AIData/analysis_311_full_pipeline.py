#!/usr/bin/env python3
"""
策略311 完整流水线 (买+卖 情绪自适应)
D-2: 按情绪选1只最优 → D-2尾盘买入
D-1: 按情绪选卖点策略 → D-1盘中卖出
输出: 每笔明细 + 月度盈亏
"""
import os, sys
import numpy as np
from collections import defaultdict

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
FIVEM_DIR = os.path.join(BASE, "5M")
KLINE_DIR = os.path.join(BASE, "1D")

CR = 0.00025; CM = 5.0; SD = 0.0005; TF = 0.00001; CAPITAL = 1_000_000

def load_td():
    ds = []
    with open(os.path.join(BASE, "TRADING_DATES")) as f:
        for l in f: 
            l = l.strip()
            if l: ds.append(l)
    return sorted(ds)

def load_stock_info():
    info = {}
    with open(os.path.join(BASE, "STOCK_CODES_ALL"), encoding='utf-8') as f:
        for i, l in enumerate(f):
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 2: info[p[0]] = {'rank': i, 'name': p[1]}
    return info

def load_kline_range(code, dates):
    fp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fp): return {}
    result = {}
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) < 7: continue
            if p[0] in dates:
                result[p[0]] = (float(p[1]), float(p[2]), float(p[3]),
                                float(p[4]), float(p[5]), float(p[6]))
    return result

def load_5m(code, dt):
    fp = os.path.join(FIVEM_DIR, code)
    if not os.path.exists(fp): return None
    df = f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}"
    bars = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) < 6: continue
            if p[0].startswith(df):
                bars.append((p[0], float(p[4]), float(p[2]), float(p[3]), float(p[1]), float(p[5])))
    return bars if bars else None

def load_sigs():
    sd = {}
    for fn in sorted(os.listdir(SIGNAL_DIR)):
        fp = os.path.join(SIGNAL_DIR, fn)
        if os.path.getsize(fp) <= 3: continue
        with open(fp, encoding='utf-8') as f:
            ls = [l.strip() for l in f if l.strip()]
        if not ls: continue
        es = [(l.split('|')[0], float(l.split('|')[7])) for l in ls if len(l.split('|'))>=8]
        if es: sd[fn] = es
    return sd

def load_sentiment():
    sent = defaultdict(dict)
    for fname, keys in [("1D_PANIC_INDEX", [('panic', float)]),
                         ("1D_AVG_CHANGE", [('avg_chg', float)]),
                         ("1D_MOTION_COUNT", [('net_motion', int)]),
                         ("1D_TOTAL_AMOUNT", [('amount', lambda x: float(x) if x!='nan' else None),
                                             ('amount_ma5', lambda x: float(x) if x!='nan' else None)])]:
        with open(os.path.join(BASE, fname)) as f:
            for l in f:
                l = l.strip()
                if not l: continue
                p = l.split('|')
                for i, (k, conv) in enumerate(keys):
                    if len(p) > i+1:
                        try: sent[p[0]][k] = conv(p[i+1])
                        except: pass
    return sent

def classify_sentiment(s):
    panic = s.get('panic', 20); avg_chg = s.get('avg_chg', 0)
    net = s.get('net_motion', 0); amt = s.get('amount')
    amt_ma5 = s.get('amount_ma5')
    score = 0
    if panic > 70: score -= 3
    elif panic > 50: score -= 2
    elif panic > 30: score -= 1
    elif panic < 5: score += 1
    if avg_chg < -2.0: score -= 3
    elif avg_chg < -1.0: score -= 2
    elif avg_chg < -0.3: score -= 1
    elif avg_chg > 2.0: score += 2
    elif avg_chg > 1.0: score += 1
    mp = net/677*100
    if mp < -30: score -= 2
    elif mp < -10: score -= 1
    elif mp > 30: score += 2
    elif mp > 10: score += 1
    if amt and amt_ma5 and amt_ma5 > 0:
        if amt/amt_ma5 > 1.3: score += 1
        elif amt/amt_ma5 < 0.7: score -= 1
    if score <= -4: return 0, '恐慌'
    elif score <= -1: return 1, '偏空'
    elif score <= 1: return 2, '震荡'
    elif score <= 4: return 3, '偏多'
    else: return 4, '过热'

def fee(buy, sell, pc):
    if buy == 0 or sell == 0: return 0.0
    sh = int(pc / buy / 100) * 100
    if sh == 0: sh = 100
    c = sh * buy; bf = max(c*CR, CM) + c*TF; tb = c + bf
    r = sh * sell; sf = max(r*CR, CM) + r*TF + r*SD
    return (r - sf - tb) / tb * 100

# ============================================================
# 选股因子
# ============================================================
def compute_factors(code, kd2, kd3, kd4, stock_info):
    if not kd2 or not kd3: return None
    o2, h2, l2, c2, v2, a2 = kd2
    o3, h3, l3, c3, v3, a3 = kd3
    f = {}
    f['pullback_depth'] = (c3 - c2) / c3 * 100 if c3 else 0
    f['lower_shadow'] = (c2 - l2) / (h2 - l2) * 100 if h2 > l2 else 50
    f['close_position'] = (c2 - l2) / (h2 - l2) * 100 if h2 > l2 else 50
    f['vol_ratio_d3_d2'] = v3 / v2 if v2 else 1
    f['cap_rank'] = stock_info.get(code, {}).get('rank', 338)
    f['cap_rank_norm'] = f['cap_rank'] / 677.0
    f['is_mega_cap'] = 1 if f['cap_rank'] < 100 else 0
    f['vol_contract'] = 1 if v2 < v3 * 0.8 else 0
    f['shadow_support'] = 1 if (f['lower_shadow'] > 50 and f['pullback_depth'] > 1) else 0
    if kd4:
        f['vol_ratio_d3_d4'] = v3 / kd4[4] if kd4[4] else 1
    else:
        f['vol_ratio_d3_d4'] = 1
    score = 0
    if 0 < f['pullback_depth'] < 8: score += 2
    elif f['pullback_depth'] > 15: score -= 1
    if f['lower_shadow'] > 60: score += 2
    if f['vol_contract']: score += 2
    if f['vol_ratio_d3_d2'] > 1.5: score += 1
    if f['shadow_support']: score += 1
    f['quality_score'] = score
    return f

# ============================================================
# 选股 (按情绪)
# ============================================================
def select_stock(candidates, env_name):
    """candidates: [(code, d2_close, bars, factors), ...]"""
    if env_name == '过热':
        return None  # 不开仓
    
    if env_name in ('恐慌', '偏空'):
        # 防御: 大市值 + 有支撑
        scored = []
        for code, d2c, bars, f in candidates:
            if f is None: continue
            s = f.get('is_mega_cap', 0) * 5 + f.get('shadow_support', 0) * 3 + f.get('vol_contract', 0) * 2
            scored.append((s, code, d2c, bars, f))
        scored.sort(key=lambda x: -x[0])
        return scored[0] if scored else None
    
    elif env_name == '震荡':
        # 小市值 + 动量
        scored = []
        for code, d2c, bars, f in candidates:
            if f is None: continue
            s = (1 - f.get('cap_rank_norm', 0.5)) * 5
            if f.get('vol_ratio_d3_d2', 1) > 1.2: s += 2
            if 0 < f.get('pullback_depth', 0) < 10: s += 1
            scored.append((s, code, d2c, bars, f))
        scored.sort(key=lambda x: -x[0])
        return scored[0] if scored else None
    
    elif env_name == '偏多':
        # 回踩适中 + 质量
        scored = []
        for code, d2c, bars, f in candidates:
            if f is None: continue
            s = f.get('quality_score', 0)
            if 2 < f.get('pullback_depth', 0) < 8: s += 2
            scored.append((s, code, d2c, bars, f))
        scored.sort(key=lambda x: -x[0])
        return scored[0] if scored else None
    
    return None

# ============================================================
# 卖出策略 (按情绪)
# ============================================================
def sell_strategy(bars, bp, env_name):
    """情绪自适应卖出"""
    if env_name == '震荡':
        # 震荡用紧止损: 新高回落0.5%
        peak = bars[0][1]
        for b in bars:
            if b[1] > peak: peak = b[1]
            elif (peak - b[1]) / peak * 100 >= 0.5:
                return b[1], b[0], 'trail_0.5'
        return bars[-1][1], bars[-1][0], 'close'
    else:
        # 恐慌/偏空/偏多: 上午强卖高否则1430
        am_bars = [b for b in bars if int(b[0][11:13]) <= 11]
        if am_bars:
            am_ret = (am_bars[-1][1] - bars[0][1]) / bars[0][1] * 100
            if am_ret > 1.5:
                sell_p = max(b[2] for b in am_bars)
                # find time
                for b in am_bars:
                    if b[2] == sell_p:
                        return sell_p, b[0], 'am_high'
                return sell_p, am_bars[-1][0], 'am_high'
        for b in bars:
            if '14:30' in b[0]:
                return b[1], b[0], '1430'
        return bars[-1][1], bars[-1][0], 'close'


# ============================================================
# 主流程
# ============================================================
print("="*100)
print("  策略311 完整流水线 (情绪自适应 买+卖)")
print("  D-2: 情绪选股 → D-2尾盘买 → D-1: 情绪卖点 → D-1盘中卖")
print("="*100)

sigs = load_sigs(); tds = load_td(); di = {d:i for i,d in enumerate(tds)}
stock_info = load_stock_info(); sentiment = load_sentiment()

# 构建完整交易流水线
trades = []  # [(d1_date, env, code, name, buy_price, sell_price, ret%, sell_time, sell_method, factors)]

for d0 in sorted(sigs.keys()):
    es = sigs[d0]; d0i = di.get(d0)
    if d0i is None or d0i < 3: continue
    d1, d2, d3 = tds[d0i-1], tds[d0i-2], tds[d0i-3]
    d4 = tds[d0i-4] if d0i >= 4 else None
    
    sent_d2 = sentiment.get(d2, {})
    if not sent_d2: continue
    env_code, env_name = classify_sentiment(sent_d2)
    
    # 过热跳过
    if env_name == '过热': continue
    
    # 构建候选池
    candidates = []
    for code, d1_close in es:
        klines = load_kline_range(code, set(filter(None, [d2, d3, d4])))
        kd2 = klines.get(d2); kd3 = klines.get(d3); kd4 = klines.get(d4) if d4 else None
        if not kd2 or not kd3: continue
        d2_close = kd2[3]
        factors = compute_factors(code, kd2, kd3, kd4, stock_info)
        if not factors: continue
        bars = load_5m(code, d1)
        if not bars or len(bars) < 10: continue
        candidates.append((code, d2_close, bars, factors))
    
    if not candidates: continue
    
    # 选股
    pick = select_stock(candidates, env_name)
    if pick is None: continue
    _, code, buy_price, bars, factors = pick
    
    # 卖出
    sell_price, sell_time, sell_method = sell_strategy(bars, buy_price, env_name)
    
    # 计算收益
    ret = fee(buy_price, sell_price, CAPITAL)
    
    name = stock_info.get(code, {}).get('name', code)
    trades.append((d1, env_name, code, name, buy_price, sell_price, ret, sell_time, sell_method, factors))

print(f"\n总计: {len(trades)}笔交易, {len(set(t[0] for t in trades))}个卖出日")

# ============================================================
# 逐笔明细
# ============================================================
print("\n"+"="*120)
print("  逐笔交易明细")
print("="*120)
print(f"  {'日期':<10} {'环境':<6} {'代码':<12} {'名称':<8} {'买入价':>8} {'卖出价':>8} {'收益%':>8} {'卖出时间':<20} {'卖出方式':<12} {'因子':<20}")
print(f"  {'-'*115}")

monthly = defaultdict(lambda: {'trades': [], 'sum_ret': 0.0, 'wins': 0, 'losses': 0})
cum_ret = 1.0; peak = 1.0; max_dd = 0.0

for t in trades:
    d1, env, code, name, bp, sp, ret, st, sm, factors = t
    
    # 因子摘要
    if factors:
        fac_str = f"QS={factors.get('quality_score',0)} LS={factors.get('lower_shadow',0):.0f}% PB={factors.get('pullback_depth',0):.1f}%"
    else:
        fac_str = ""
    
    print(f"  {d1:<10} {env:<6} {code:<12} {name:<8} {bp:>8.2f} {sp:>8.2f} {ret:>8.2f} {st:<20} {sm:<12} {fac_str:<20}")
    
    month = d1[:6]
    monthly[month]['trades'].append(t)
    monthly[month]['sum_ret'] += ret
    if ret > 0: monthly[month]['wins'] += 1
    else: monthly[month]['losses'] += 1
    
    cum_ret *= (1 + ret/100)
    if cum_ret > peak: peak = cum_ret
    dd = (cum_ret - peak) / peak * 100
    if dd < max_dd: max_dd = dd

# ============================================================
# 月度汇总
# ============================================================
print("\n"+"="*120)
print("  月度盈亏汇总")
print("="*120)
print(f"  {'月份':<8} {'交易笔数':>8} {'月收益%':>10} {'累计净值':>10} {'回撤%':>10} {'胜率':>8} {'胜/负':>8}")
print(f"  {'-'*70}")

cum = 1.0; peak_m = 1.0; max_dd_m = 0.0

for month in sorted(monthly.keys()):
    m = monthly[month]
    n = len(m['trades'])
    if n == 0: continue
    # 月复利
    month_ret = 1.0
    for t in m['trades']:
        month_ret *= (1 + t[6]/100)
    month_ret_pct = (month_ret - 1) * 100
    
    cum *= month_ret
    if cum > peak_m: peak_m = cum
    dd = (cum - peak_m) / peak_m * 100
    if dd < max_dd_m: max_dd_m = dd
    
    wr = m['wins'] / n * 100
    print(f"  {month:<8} {n:>8} {month_ret_pct:>10.2f}% {cum:>10.4f} {dd:>10.2f}% {wr:>7.1f}% {m['wins']:>3}/{m['losses']:<3}")

total_ret = (cum - 1) * 100
print(f"  {'-'*70}")
print(f"  {'合计':<8} {len(trades):>8} {total_ret:>10.2f}% {cum:>10.4f} {max_dd_m:>10.2f}% "
      f"{sum(m['wins'] for m in monthly.values())/len(trades)*100:>7.1f}% "
      f"{sum(m['wins'] for m in monthly.values()):>3}/{sum(m['losses'] for m in monthly.values()):<3}")

# ============================================================
# 汇总统计
# ============================================================
print("\n"+"="*120)
print("  最终汇总")
print("="*120)
all_rets = [t[6] for t in trades]
wr = sum(1 for r in all_rets if r > 0) / len(all_rets) * 100
dly = np.array(all_rets)
sh = np.mean(dly) / np.std(dly) * np.sqrt(252) if np.std(dly) > 0 else 0

print(f"  总交易日: {len(monthly)}个月, {len(trades)}笔")
print(f"  累计净值: {cum:.4f}")
print(f"  总收益率: {total_ret:.2f}%")
print(f"  胜率: {wr:.1f}%")
print(f"  最大回撤: {max_dd_m:.2f}%")
print(f"  夏普比率: {sh:.2f}")
print(f"  日均收益: {np.mean(all_rets):.2f}%")
print(f"  单笔最大盈利: {max(all_rets):.2f}%")
print(f"  单笔最大亏损: {min(all_rets):.2f}%")

# 环境统计
print(f"\n  分环境统计:")
for env in ['恐慌', '偏空', '震荡', '偏多']:
    env_trades = [t for t in trades if t[1] == env]
    if not env_trades: continue
    env_rets = [t[6] for t in env_trades]
    env_wr = sum(1 for r in env_rets if r > 0) / len(env_rets) * 100
    env_cum = 1.0
    for r in env_rets: env_cum *= (1 + r/100)
    print(f"    {env}: {len(env_trades)}笔, 净值{env_cum:.4f}, "
          f"收益{(env_cum-1)*100:.1f}%, 胜率{env_wr:.1f}%, 均值{np.mean(env_rets):.2f}%")

# 卖出方式统计
print(f"\n  卖出方式统计:")
sell_counts = defaultdict(lambda: {'count': 0, 'sum_ret': 0.0})
for t in trades:
    sm = t[8]
    sell_counts[sm]['count'] += 1
    sell_counts[sm]['sum_ret'] += t[6]
for sm, sc in sorted(sell_counts.items(), key=lambda x: -x[1]['count']):
    print(f"    {sm}: {sc['count']}笔, 总收益{sc['sum_ret']:.1f}%, 均值{sc['sum_ret']/sc['count']:.2f}%")

print("\n"+"="*120)
print("  流水线分析完成!")
print("="*120)
