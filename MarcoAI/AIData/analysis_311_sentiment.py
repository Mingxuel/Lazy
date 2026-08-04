#!/usr/bin/env python3
"""
策略311 按市场情绪环境分档分析 v2
★ 关键修正: 用D-2收盘情绪(D-1开盘前已知)来预判D-1环境
原则: 情绪定环境 → 环境定仓位 → 技术面执行
"""
import os
import numpy as np
from collections import defaultdict

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
FIVEM_DIR = os.path.join(BASE, "5M")
KLINE_DIR = os.path.join(BASE, "1D")

CR = 0.00025; CM = 5.0; SD = 0.0005; TF = 0.00001; CAPITAL = 1_000_000

# ============================================================
# 数据加载
# ============================================================
def load_td():
    ds = []
    with open(os.path.join(BASE, "TRADING_DATES")) as f:
        for l in f:
            l = l.strip()
            if l: ds.append(l)
    return sorted(ds)

def load_1d(code, dt):
    fp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fp): return None
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l: continue
            if l.startswith(dt):
                p = l.split('|')
                if len(p) >= 5: return float(p[4])

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
        es = []
        for l in ls:
            p = l.split('|')
            if len(p) < 8: continue
            es.append((p[0], float(p[7])))
        if es: sd[fn] = es
    return sd

# ============================================================
# 情绪指标加载
# ============================================================
def load_sentiment():
    """加载并返回 {date: {指标...}}"""
    sent = defaultdict(dict)
    
    # 恐慌指数
    with open(os.path.join(BASE, "1D_PANIC_INDEX")) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 2:
                try: sent[p[0]]['panic'] = float(p[1])
                except: pass
    
    # 成交额
    with open(os.path.join(BASE, "1D_TOTAL_AMOUNT")) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 4:
                try:
                    sent[p[0]]['amount'] = float(p[1]) if p[1] != 'nan' else None
                    sent[p[0]]['amount_ma5'] = float(p[2]) if p[2] != 'nan' else None
                except: pass
    
    # 平均涨跌幅
    with open(os.path.join(BASE, "1D_AVG_CHANGE")) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 4:
                try:
                    sent[p[0]]['avg_chg'] = float(p[1])
                    sent[p[0]]['avg_chg_ma5'] = float(p[2])
                except: pass
    
    # 涨跌家数
    with open(os.path.join(BASE, "1D_MOTION_COUNT")) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 2:
                try: sent[p[0]]['net_motion'] = int(p[1])
                except: pass
    
    # MA交叉情绪标签
    with open(os.path.join(BASE, "1D_MA_CROSS")) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 7:
                sent[p[0]]['ma_label'] = p[-1].strip()
    
    return sent


def classify_sentiment(s):
    """
    综合情绪分类: 0=恐慌 1=偏空 2=震荡 3=偏多 4=过热
    """
    panic = s.get('panic', 20)
    avg_chg = s.get('avg_chg', 0)
    net_motion = s.get('net_motion', 0)
    amount = s.get('amount')
    amount_ma5 = s.get('amount_ma5')
    ma_label = s.get('ma_label', '')
    
    score = 0
    
    # 恐慌指数
    if panic > 70: score -= 3
    elif panic > 50: score -= 2
    elif panic > 30: score -= 1
    elif panic < 5: score += 1
    
    # 平均涨跌幅
    if avg_chg < -2.0: score -= 3
    elif avg_chg < -1.0: score -= 2
    elif avg_chg < -0.3: score -= 1
    elif avg_chg > 2.0: score += 2
    elif avg_chg > 1.0: score += 1
    
    # 涨跌家数
    total_stocks = 677
    motion_pct = net_motion / total_stocks * 100
    if motion_pct < -30: score -= 2
    elif motion_pct < -10: score -= 1
    elif motion_pct > 30: score += 2
    elif motion_pct > 10: score += 1
    
    # 成交额 vs MA5 (放量/缩量)
    if amount and amount_ma5 and amount_ma5 > 0:
        amt_ratio = amount / amount_ma5
        if amt_ratio > 1.3: score += 1  # 放量
        elif amt_ratio < 0.7: score -= 1  # 缩量
    
    # MA交叉标签
    if '强偏多' in ma_label: score += 2
    elif '偏多' in ma_label: score += 1
    elif '偏空' in ma_label: score -= 1
    elif '强偏空' in ma_label: score -= 2
    
    # 映射到5档
    if score <= -4: return 0, '恐慌'
    elif score <= -1: return 1, '偏空'
    elif score <= 1: return 2, '震荡'
    elif score <= 4: return 3, '偏多'
    else: return 4, '过热'
    
    return 2, '震荡'


def fee(buy, sell, pc):
    if buy == 0 or sell == 0: return 0.0
    sh = int(pc / buy / 100) * 100
    if sh == 0: sh = 100
    c = sh * buy
    bf = max(c * CR, CM) + c * TF; tb = c + bf
    r = sh * sell
    sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100

# ============================================================
# 卖出策略
# ============================================================
def s_close(bars, bp): return bars[-1][1]

def s_trail(pct):
    def f(bars, bp):
        peak = bars[0][1]
        for b in bars:
            if b[1] > peak: peak = b[1]
            elif (peak-b[1])/peak*100 >= pct: return b[1]
        return bars[-1][1]
    return f

def s_near_limit(bars, bp):
    for b in bars:
        if b[1] >= bp*1.09: return b[1]
    return bars[-1][1]

def s_am_strong_or_1430(bars, bp):
    """上午强卖高否则14:30"""
    am_bars = [b for b in bars if int(b[0][11:13]) <= 11]
    am_ret = (am_bars[-1][1] - bars[0][1])/bars[0][1]*100 if am_bars else 0
    if am_ret > 1.5:
        return max(b[2] for b in am_bars)
    for b in bars:
        if '14:30' in b[0]: return b[1]
    return bars[-1][1]

def s_vol_climax(bars, bp):
    if len(bars) < 12: return bars[-1][1]
    v = np.array([b[5] for b in bars])
    vm5 = np.convolve(v, np.ones(5)/5, mode='same')
    for i in range(10, len(bars)):
        if v[i] > 3*vm5[i]: return bars[i][1]
    return bars[-1][1]

def s_1130(bars, bp):
    for b in bars:
        if '11:30' in b[0]: return b[1]
    return bars[-1][1]

def s_1430(bars, bp):
    for b in bars:
        if '14:30' in b[0]: return b[1]
    return bars[-1][1]

def s_morning_trail(bars, bp):
    """上午峰后下午紧追"""
    am = [b for b in bars if int(b[0][11:13]) <= 11]
    am_peak = max(b[2] for b in am) if am else bars[0][2]
    peak = am_peak
    for b in bars:
        if int(b[0][11:13]) >= 13:
            if b[1] > peak: peak = b[1]
            elif (peak-b[1])/peak*100 >= 1.0: return b[1]
    return bars[-1][1]

def s_gap_aware(bars, bp):
    gap = (bars[0][1]-bp)/bp*100
    if gap > 2: return bars[0][1]
    if gap < -2:
        for b in bars:
            if '10:30' in b[0]: return b[1]
        return bars[-1][1]
    return s_trail(1.0)(bars, bp)

def s_open_sell(bars, bp): return bars[0][1]  # 开盘即卖


# ============================================================
# 主流程
# ============================================================
print("="*100)
print("  策略311 — 按D-2情绪预判D-1环境 (实盘可用)")
print("  D-2收盘情绪已知 → D-1开盘前决定策略")
print("="*100)

print("\n加载数据...")
sigs = load_sigs(); tds = load_td(); di = {d:i for i,d in enumerate(tds)}
sentiment = load_sentiment()

# 构建交易数据
all_data = []
for d0 in sorted(sigs.keys()):
    es = sigs[d0]; d0i = di.get(d0)
    if d0i is None or d0i < 2: continue
    d1, d2 = tds[d0i-1], tds[d0i-2]
    # ★ 关键修正: 用D-2收盘情绪(D-1开盘前已知), 而不是D-1当日情绪
    sent_d2 = sentiment.get(d2, {})
    if not sent_d2: continue  # D-2 must have sentiment data
    env_code, env_name = classify_sentiment(sent_d2)
    
    for code, d1c in es:
        d2c = load_1d(code, d2)
        if d2c is None: continue
        bars = load_5m(code, d1)
        if bars is None or len(bars) < 10: continue
        all_data.append((code, d1, d2c, bars, env_code, env_name))

n = len(all_data)
order = sorted(range(n), key=lambda i: all_data[i][1])
all_data = [all_data[i] for i in order]

# 统计情绪分布
env_counts = defaultdict(int)
env_trades = defaultdict(int)
for d in all_data:
    env_counts[d[5]] += 1  # by day
    env_trades[d[5]] += 1  # by trade

days_by_env = defaultdict(set)
for d in all_data:
    days_by_env[d[5]].add(d[1])

print(f"总交易: {n}笔, 覆盖 {sum(len(v) for v in days_by_env.values())} 卖出日")

# ★ 验证: D-2情绪 vs D-1实际情绪的对应关系
print("\n情绪预判准确度 (D-2 → D-1):")
d2_to_d1 = defaultdict(lambda: defaultdict(int))
for code, d1, d2c, bars, env_code, env_name in all_data:
    sent_d1 = sentiment.get(d1, {})
    if sent_d1:
        actual_env, actual_name = classify_sentiment(sent_d1)
        d2_to_d1[env_name][actual_name] += 1

env_names = ['恐慌', '偏空', '震荡', '偏多', '过热']
print(f"  {'D-2(预判)':>8} → {'恐慌':>6} {'偏空':>6} {'震荡':>6} {'偏多':>6} {'过热':>6}  {'准确率':>8}")
for env in env_names:
    total = sum(d2_to_d1[env].values())
    if total == 0: continue
    correct = d2_to_d1[env].get(env, 0)
    row = f"  {env:>8} → "
    for ae in env_names:
        row += f" {d2_to_d1[env].get(ae, 0):>6}"
    row += f"  {correct/total*100:>7.1f}%"
    print(row)
print("\n情绪分布:")
for env in ['恐慌', '偏空', '震荡', '偏多', '过热']:
    if env in env_trades:
        print(f"  {env}: {len(days_by_env[env])}天, {env_trades[env]}笔交易 "
              f"({env_trades[env]/n*100:.1f}%)")

# 策略
strategies = {
    "01_baseline收盘": s_close,
    "02_新高回落1%": s_trail(1.0),
    "03_新高回落0.5%": s_trail(0.5),
    "04_新高回落2%": s_trail(2.0),
    "05_接近涨停卖": s_near_limit,
    "06_上午强卖高否则1430": s_am_strong_or_1430,
    "07_放量尖峰卖": s_vol_climax,
    "08_11:30固定卖": s_1130,
    "09_14:30固定卖": s_1430,
    "10_上午峰下午追": s_morning_trail,
    "11_跳空感知": s_gap_aware,
    "12_开盘即卖": s_open_sell,
}

# 全量和分环境回测
def backtest_by_env(data_list):
    """data_list: [(code, d1, d2c, bars, env_code, env_name), ...]"""
    results = {sn: [] for sn in strategies}
    by_d1 = defaultdict(list)
    for code, d1, d2c, bars, env_code, env_name in data_list:
        by_d1[d1].append((code, d2c, bars))
    
    for d1 in sorted(by_d1.keys()):
        trs = by_d1[d1]; pc = CAPITAL / len(trs)
        dr = {sn: [] for sn in strategies}
        for code, d2c, bars in trs:
            for sn, sf in strategies.items():
                sp = sf(bars, d2c)
                dr[sn].append(fee(d2c, sp, pc))
        for sn in strategies:
            rts = dr[sn]
            if rts:
                results[sn].append({'date': d1, 'ret': round(sum(rts)/len(rts), 4)})
    return results

def compute_metrics(results):
    if not results: return None
    data = results[list(results.keys())[0]]
    if not data: return None
    
    ranks = []
    for sn, d in results.items():
        if not d: continue
        cum = 1.0; peak = 1.0; max_dd = 0.0
        rets = [r['ret'] for r in d]
        for r in rets:
            cum *= (1+r/100)
            if cum > peak: peak = cum
            dd = (cum-peak)/peak*100
            if dd < max_dd: max_dd = dd
        wr = sum(1 for r in rets if r>0)/len(rets)*100 if rets else 0
        dly = np.array(rets); sh = np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
        ranks.append((cum, sn, (cum-1)*100, wr, max_dd, sh, len(d)))
    ranks.sort(key=lambda x: x[0], reverse=True)
    return ranks


# ============================================================
# Part 1: 全量(不分环境)
# ============================================================
print("\n"+"="*100)
print("  PART 1: 全量回测 (不分情绪, 基准)")
print("="*100)
all_results = backtest_by_env(all_data)
all_ranks = compute_metrics(all_results)
print(f"  {'策略':<28} {'净值':>8} {'总收益%':>10} {'胜率%':>7} {'回撤%':>8} {'夏普':>7} {'天':>5}")
print(f"  {'-'*80}")
for cum, sn, tr, wr, dd, sh, td in all_ranks[:8]:
    print(f"  {sn:<28} {cum:>8.4f} {tr:>10.2f} {wr:>7.1f} {dd:>8.2f} {sh:>7.2f} {td:>5}")

# ============================================================
# Part 2: 分环境
# ============================================================
env_names = ['恐慌', '偏空', '震荡', '偏多', '过热']
env_best = {}  # 每个环境的最佳策略

for env_name in env_names:
    env_data = [d for d in all_data if d[5] == env_name]
    if len(env_data) < 10: continue
    
    print("\n"+"="*100)
    print(f"  {env_name}环境 ({len(set(d[1] for d in env_data))}天, {len(env_data)}笔)")
    print("="*100)
    
    env_results = backtest_by_env(env_data)
    env_ranks = compute_metrics(env_results)
    
    if env_ranks:
        print(f"  {'策略':<28} {'净值':>8} {'总收益%':>10} {'胜率%':>7} {'回撤%':>8} {'夏普':>7}")
        print(f"  {'-'*75}")
        for cum, sn, tr, wr, dd, sh, td in env_ranks[:5]:
            marker = " *" if sn == env_ranks[0][1] else ""
            print(f"  {sn:<28} {cum:>8.4f} {tr:>10.2f} {wr:>7.1f} {dd:>8.2f} {sh:>7.2f}{marker}")
        env_best[env_name] = env_ranks[0]


# ============================================================
# Part 3: 环境自适应组合策略
# ============================================================
print("\n"+"="*100)
print("  PART 3: 环境自适应组合策略")
print("  每个环境用最优策略, 回测全量数据")
print("="*100)

# 构建自适应策略: 根据D-1情绪选择策略
class AdaptiveStrategy:
    def __init__(self, env_best):
        self.env_map = {}
        for env_name, (cum, sn, tr, wr, dd, sh, td) in env_best.items():
            # Map strategy name back to function
            for sname, sfunc in strategies.items():
                if sname == sn:
                    self.env_map[env_name] = sfunc
                    break
    
    def sell(self, env_name, bars, bp):
        func = self.env_map.get(env_name, s_close)  # default to close
        return func(bars, bp)

adaptive = AdaptiveStrategy(env_best)

# 回测自适应策略
adaptive_results = []
by_d1_adaptive = defaultdict(list)
for code, d1, d2c, bars, env_code, env_name in all_data:
    by_d1_adaptive[d1].append((code, d2c, bars, env_name))

for d1 in sorted(by_d1_adaptive.keys()):
    trs = by_d1_adaptive[d1]; pc = CAPITAL / len(trs)
    rets = []
    for code, d2c, bars, env_name in trs:
        sp = adaptive.sell(env_name, bars, d2c)
        rets.append(fee(d2c, sp, pc))
    if rets:
        adaptive_results.append({'date': d1, 'ret': round(sum(rets)/len(rets), 4)})

# 也回测单策略用于对比
baseline_results = []
by_d1_bl = defaultdict(list)
for code, d1, d2c, bars, env_code, env_name in all_data:
    by_d1_bl[d1].append((code, d2c, bars))
for d1 in sorted(by_d1_bl.keys()):
    trs = by_d1_bl[d1]; pc = CAPITAL / len(trs)
    rets_close = [fee(d2c, s_close(bars, d2c), pc) for code, d2c, bars in trs]
    rets_best = [fee(d2c, s_am_strong_or_1430(bars, d2c), pc) for code, d2c, bars in trs]
    baseline_results.append({
        'date': d1,
        'close_ret': round(sum(rets_close)/len(rets_close), 4),
        'best_ret': round(sum(rets_best)/len(rets_best), 4),
    })

# 计算自适应净值
for label, rets_data, key in [
    ("自适应(按情绪选最优)", adaptive_results, 'ret'),
    ("固定最优(上午强卖高否则1430)", baseline_results, 'best_ret'),
    ("固定baseline(收盘)", baseline_results, 'close_ret'),
]:
    cum = 1.0; peak = 1.0; max_dd = 0.0
    rets = [r[key] for r in rets_data]
    for r in rets:
        cum *= (1+r/100)
        if cum > peak: peak = cum
        dd = (cum-peak)/peak*100; max_dd = min(max_dd, dd)
    wr = sum(1 for r in rets if r>0)/len(rets)*100
    dly = np.array(rets); sh = np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
    print(f"  {label:<35}: 净值{cum:.4f} 总收益{(cum-1)*100:.1f}% 胜率{wr:.1f}% 回撤{max_dd:.1f}% 夏普{sh:.2f}")


# ============================================================
# Part 4: 环境-策略详细矩阵
# ============================================================
print("\n"+"="*100)
print("  PART 4: 各环境最优策略汇总")
print("="*100)
print(f"  {'环境':<8} {'最优策略':<30} {'净值':>8} {'收益%':>8} {'建议':<30}")
print(f"  {'-'*90}")

# 获取每个策略在每个环境的表现(取前3)
for env_name in env_names:
    env_data = [d for d in all_data if d[5] == env_name]
    if len(env_data) < 5: continue
    env_results = backtest_by_env(env_data)
    env_ranks = compute_metrics(env_results)
    if not env_ranks: continue
    
    # 找该环境最优策略 vs 全量最优策略在该环境的表现
    best_in_env = env_ranks[0]
    total_best = s_am_strong_or_1430  # 全量最优
    
    # 回测全量最优在该环境
    bl_r = backtest_by_env(env_data)
    total_best_rank = None
    for cum, sn, tr, wr, dd, sh, td in env_ranks:
        if sn == "06_上午强卖高否则1430":
            total_best_rank = (cum, tr)
            break
    
    suggestion = ""
    if best_in_env[1] != "06_上午强卖高否则1430":
        improvement = best_in_env[2] - (total_best_rank[1] if total_best_rank else 0)
        suggestion = f"换策略可多赚{improvement:.1f}%"
    
    print(f"  {env_name:<8} {best_in_env[1]:<30} {best_in_env[0]:>8.4f} {best_in_env[2]:>8.1f}% {suggestion:<30}")

print("\n"+"="*100)
print("  分析完成!")
print("="*100)
