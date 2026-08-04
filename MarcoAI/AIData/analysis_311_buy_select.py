#!/usr/bin/env python3
"""
策略311 买点选股优化
- 从D-4/D-3/D-2 1D K线提取选股因子
- 按情绪环境分档测试选股策略
- 对比: 全买 vs 精选 vs 情绪选股
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

def load_stock_info():
    """加载股票市值排名 {code: rank}"""
    info = {}
    with open(os.path.join(BASE, "STOCK_CODES_ALL"), encoding='utf-8') as f:
        for i, l in enumerate(f):
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 2:
                info[p[0]] = {'rank': i, 'name': p[1]}
    return info

def load_kline_range(code, dates_needed):
    """加载某只股票多个日期的K线, 返回 {date: (open,high,low,close,volume,amount)}"""
    fp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fp): return {}
    result = {}
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) < 7: continue
            if p[0] in dates_needed:
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
        es = []
        for l in ls:
            p = l.split('|')
            if len(p) < 8: continue
            es.append((p[0], float(p[7])))
        if es: sd[fn] = es
    return sd

def load_sentiment():
    sent = defaultdict(dict)
    with open(os.path.join(BASE, "1D_PANIC_INDEX")) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 2:
                try: sent[p[0]]['panic'] = float(p[1])
                except: pass
    with open(os.path.join(BASE, "1D_AVG_CHANGE")) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 4:
                try: sent[p[0]]['avg_chg'] = float(p[1])
                except: pass
    with open(os.path.join(BASE, "1D_MOTION_COUNT")) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 2:
                try: sent[p[0]]['net_motion'] = int(p[1])
                except: pass
    with open(os.path.join(BASE, "1D_TOTAL_AMOUNT")) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) >= 4:
                try:
                    sent[p[0]]['amount'] = float(p[1]) if p[1]!='nan' else None
                    sent[p[0]]['amount_ma5'] = float(p[2]) if p[2]!='nan' else None
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
# 选股因子计算
# ============================================================
def compute_factors(code, d2, d3, d4, stock_info, sentiment_env):
    """
    从D-2/D-3/D-4 K线计算选股因子
    d2/d3/d4: (open,high,low,close,volume,amount) 或 None
    """
    if not d2 or not d3: return None
    
    factors = {}
    o2, h2, l2, c2, v2, a2 = d2
    o3, h3, l3, c3, v3, a3 = d3
    
    # 回踩深度: D-2 close vs D-3 close
    factors['pullback_depth'] = (c3 - c2) / c3 * 100  # 正值=回踩, 负值=未回踩
    
    # D-2 下影线比例 (支撑信号)
    if h2 > l2:
        factors['lower_shadow'] = (c2 - l2) / (h2 - l2) * 100
    else:
        factors['lower_shadow'] = 50
    
    # D-2 振幅
    factors['amp_d2'] = (h2 - l2) / o2 * 100 if o2 else 0
    
    # D-2 收盘位置在当天K线的相对位置
    if h2 > l2:
        factors['close_position'] = (c2 - l2) / (h2 - l2) * 100
    else:
        factors['close_position'] = 50
    
    # 放量倍数: D-3 vol / D-2 vol
    factors['vol_ratio_d3_d2'] = v3 / v2 if v2 else 1
    
    # D-4 涨停强度 (如果有d4)
    if d4:
        o4, h4, l4, c4, v4, a4 = d4
        factors['limit_up_gain'] = (c4 - o3) / o3 * 100 if o3 else 0  # D-4相对D-3开盘
        factors['vol_ratio_d3_d4'] = v3 / v4 if v4 else 1
    else:
        factors['limit_up_gain'] = 0
        factors['vol_ratio_d3_d4'] = 1
    
    # 市值排名 (0=最大, 676=最小)
    factors['cap_rank'] = stock_info.get(code, {}).get('rank', 338)
    factors['cap_rank_norm'] = factors['cap_rank'] / 677.0
    
    # 是否是超大市值 (前100)
    factors['is_mega_cap'] = 1 if factors['cap_rank'] < 100 else 0
    factors['is_small_cap'] = 1 if factors['cap_rank'] > 500 else 0
    
    # D-2是否创新低 (低于D-3低点)
    factors['new_low'] = 1 if l2 < l3 else 0
    
    # 量价配合: 缩量回踩 = 好信号
    factors['vol_contract'] = 1 if v2 < v3 * 0.8 else 0
    
    # D-2 下影线确认: 下影线 > 50% 且 回踩了
    factors['shadow_support'] = 1 if (factors['lower_shadow'] > 50 and factors['pullback_depth'] > 1) else 0
    
    # 综合质量评分
    score = 0
    if 0 < factors['pullback_depth'] < 8: score += 2  # 适度回踩
    elif factors['pullback_depth'] > 15: score -= 1  # 回踩太深
    if factors['lower_shadow'] > 60: score += 2     # 强支撑
    if factors['vol_contract']: score += 2          # 缩量回踩
    if factors['vol_ratio_d3_d2'] > 1.5: score += 1 # 放量充分
    if factors['shadow_support']: score += 1
    factors['quality_score'] = score
    
    return factors


def compute_target_return(code, d2_close, bars, sell_strategy_fn):
    """计算某只股票的D-1目标收益(使用指定卖出策略)"""
    if bars is None: return None
    sell_price = sell_strategy_fn(bars, d2_close)
    return fee(d2_close, sell_price, CAPITAL)  # 简化: 单只算


def s_am_strong_or_1430(bars, bp):
    am_bars = [b for b in bars if int(b[0][11:13]) <= 11]
    am_ret = (am_bars[-1][1] - bars[0][1])/bars[0][1]*100 if am_bars else 0
    if am_ret > 1.5:
        return max(b[2] for b in am_bars)
    for b in bars:
        if '14:30' in b[0]: return b[1]
    return bars[-1][1]


# ============================================================
# 选股策略
# ============================================================
def select_all(stocks, env, n=1):
    """全买"""
    return stocks

def select_top_quality(stocks, env, n=1):
    """只买质量最高的N只"""
    scored = [(s[6].get('quality_score', 0) if s[6] else 0, s) for s in stocks]
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:max(n, 1)]]

def select_top_pullback(stocks, env, n=1):
    """只买回踩最深但不过分的N只(恐慌后反弹选超跌)"""
    valid = []
    for s in stocks:
        if s[6]:
            pb = s[6].get('pullback_depth', 0)
            if 1 < pb < 15:
                valid.append((pb, s))
    valid.sort(key=lambda x: -x[0])
    if not valid: return select_top_quality(stocks, env, n)
    return [s for _, s in valid[:max(n, 1)]]

def select_shadow_support(stocks, env, n=1):
    """只买有下影线支撑+缩量回踩的"""
    valid = []
    for s in stocks:
        if s[6] and s[6].get('shadow_support', 0) == 1:
            valid.append((s[6].get('quality_score', 0), s))
    if not valid: return select_top_quality(stocks, env, n)
    valid.sort(key=lambda x: -x[0])
    return [s for _, s in valid[:max(n, 1)]]

def select_small_cap_momentum(stocks, env, n=1):
    """偏多环境: 选小市值+放量好的"""
    valid = []
    for s in stocks:
        if s[6]:
            score = (1 - s[6].get('cap_rank_norm', 0.5)) * 5  # 小市值加分
            if s[6].get('vol_ratio_d3_d2', 1) > 1.2: score += 2
            if 0 < s[6].get('pullback_depth', 0) < 10: score += 1
            valid.append((score, s))
    if not valid: return select_top_quality(stocks, env, n)
    valid.sort(key=lambda x: -x[0])
    return [s for _, s in valid[:max(n, 1)]]

def select_defensive(stocks, env, n=1):
    """偏空环境: 选大市值+有支撑的"""
    valid = []
    for s in stocks:
        if s[6]:
            score = s[6].get('is_mega_cap', 0) * 4  # 大市值加分
            score += s[6].get('shadow_support', 0) * 3  # 支撑加分
            valid.append((score, s))
    if not valid: return select_top_quality(stocks, env, n)
    valid.sort(key=lambda x: -x[0])
    return [s for _, s in valid[:max(n, 1)]]

def select_sentiment_aware(stocks, env_name, n=1):
    """情绪自适应选股"""
    if env_name == '恐慌':
        return select_top_pullback(stocks, env_name, n)  # 恐慌后反弹选超跌
    elif env_name == '偏空':
        return select_defensive(stocks, env_name, n)     # 偏空选防御
    elif env_name in ('偏多', '过热'):
        return select_small_cap_momentum(stocks, env_name, n)  # 偏多选动量
    else:  # 震荡
        return select_shadow_support(stocks, env_name, n)  # 震荡选质优


# ============================================================
# 主流程
# ============================================================
print("="*100)
print("  策略311 买点选股优化 — 结合情绪模式")
print("="*100)

print("\n加载数据...")
sigs = load_sigs(); tds = load_td(); di = {d:i for i,d in enumerate(tds)}
stock_info = load_stock_info()
sentiment = load_sentiment()

# 构建数据: [(code, d2, d3, d4, d2_close, bars, factors, env_name), ...]
all_trades = []
env_counts = defaultdict(int)

for d0 in sorted(sigs.keys()):
    es = sigs[d0]; d0i = di.get(d0)
    if d0i is None or d0i < 3: continue  # 需要D-2/D-3/D-4
    d1, d2, d3 = tds[d0i-1], tds[d0i-2], tds[d0i-3]
    d4 = tds[d0i-4] if d0i >= 4 else None
    
    # D-2情绪预判D-1
    sent_d2 = sentiment.get(d2, {})
    if not sent_d2: continue
    env_code, env_name = classify_sentiment(sent_d2)
    
    for code, d1_close in es:
        # 加载D-2/D-3/D-4 K线
        klines = load_kline_range(code, set(filter(None, [d2, d3, d4])))
        kd2 = klines.get(d2)
        kd3 = klines.get(d3)
        kd4 = klines.get(d4) if d4 else None
        if not kd2 or not kd3: continue
        
        d2_close = kd2[3]  # D-2 close = buy price
        factors = compute_factors(code, kd2, kd3, kd4, stock_info, env_name)
        if not factors: continue
        
        # 加载D-1 5M数据 (用于计算卖出收益)
        bars = load_5m(code, d1)
        if not bars or len(bars) < 10: continue
        
        # 计算D-1收益 (用最优卖出策略)
        target_ret = compute_target_return(code, d2_close, bars, s_am_strong_or_1430)
        if target_ret is None: continue
        
        all_trades.append((code, d1, env_name, d2_close, bars, target_ret, factors, kd2, kd3))
        env_counts[env_name] += 1

print(f"有效交易: {len(all_trades)}笔")
print(f"情绪分布: {dict(env_counts)}")

# 回测各选股策略
selection_strategies = {
    "全买(等权)": lambda stocks, env: select_all(stocks, env, 99),
    "精选最佳质量TOP1": lambda stocks, env: select_top_quality(stocks, env, 1),
    "精选回踩最深TOP1": lambda stocks, env: select_top_pullback(stocks, env, 1),
    "精选下影支撑TOP1": lambda stocks, env: select_shadow_support(stocks, env, 1),
    "精选小市值动量TOP1": lambda stocks, env: select_small_cap_momentum(stocks, env, 1),
    "精选防御大市值TOP1": lambda stocks, env: select_defensive(stocks, env, 1),
    "情绪自适应选股TOP1": lambda stocks, env: select_sentiment_aware(stocks, env, 1),
}

# 按D-1日期分组
by_d1 = defaultdict(list)
for t in all_trades:
    by_d1[t[1]].append(t)  # t[1] = d1

# 回测
results = {sn: [] for sn in selection_strategies}
for d1 in sorted(by_d1.keys()):
    day_trades = by_d1[d1]
    # 获取该日所有交易的共同环境(同一D-1的所有311信号应该来自同一D-2)
    env = day_trades[0][2] if day_trades else '震荡'
    
    for sname, sfunc in selection_strategies.items():
        selected = sfunc(day_trades, env)
        if not selected: continue
        
        n = len(selected)
        pc = CAPITAL / n
        rets = []
        for t in selected:
            rets.append(fee(t[3], s_am_strong_or_1430(t[4], t[3]), pc))
        if rets:
            results[sname].append({'date': d1, 'ret': round(sum(rets)/len(rets), 4), 'cnt': n, 'env': env})

# 输出总览
print("\n"+"="*100)
print("  选股策略对比 (全量)")
print("="*100)
print(f"  {'策略':<28} {'净值':>8} {'总收益%':>10} {'胜率%':>7} {'回撤%':>8} {'夏普':>7} {'天':>5} {'均只':>5}")
print(f"  {'-'*86}")

ranks = []
for sn in selection_strategies:
    data = results[sn]
    if not data: continue
    cum = 1.0; peak = 1.0; max_dd = 0.0
    rets_list = [r['ret'] for r in data]
    for r in rets_list:
        cum *= (1+r/100)
        if cum > peak: peak = cum
        dd = (cum-peak)/peak*100
        if dd < max_dd: max_dd = dd
    wr = sum(1 for r in rets_list if r>0)/len(rets_list)*100
    dly = np.array(rets_list)
    sh = np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
    avg_cnt = np.mean([r['cnt'] for r in data])
    ranks.append((cum, sn, (cum-1)*100, wr, max_dd, sh, len(data), avg_cnt))
ranks.sort(key=lambda x: x[0], reverse=True)

for cum, sn, tr, wr, dd, sh, td, ac in ranks:
    print(f"  {sn:<28} {cum:>8.4f} {tr:>10.2f} {wr:>7.1f} {dd:>8.2f} {sh:>7.2f} {td:>5} {ac:>5.1f}")

# 分环境明细
print("\n"+"="*100)
print("  各选股策略 × 各情绪环境 净值矩阵")
print("="*100)

env_labels = ['恐慌', '偏空', '震荡', '偏多', '过热']
strats = [x[1] for x in ranks[:5]]
print(f"  {'策略':<22}", end="")
for el in env_labels: print(f" {el:>8}", end="")
print(f" {'全量':>8}")
print(f"  {'-'*70}")

for sn in strats:
    print(f"  {sn:<22}", end="")
    total_cum = 1.0
    for el in env_labels:
        env_data = [r for r in results[sn] if r.get('env') == el]
        if env_data:
            cum = 1.0
            for r in env_data: cum *= (1+r['ret']/100)
            total_cum *= cum
            print(f" {cum:>8.3f}", end="")
        else:
            print(f" {'-':>8}", end="")
    # 全量
    all_data = results[sn]
    cum = 1.0
    for r in all_data: cum *= (1+r['ret']/100)
    print(f" {cum:>8.4f}")

# 最佳组合: 情绪自适应选股 + 过滤过热不开仓
print("\n"+"="*100)
print("  推荐策略: 情绪自适应选股 + D-2过热跳过")
print("="*100)

adaptive_data = results["情绪自适应选股TOP1"]
filtered = []
skipped = 0
for r in adaptive_data:
    if r.get('env') == '过热':
        skipped += 1
        continue
    filtered.append(r)

cum = 1.0; peak = 1.0; max_dd = 0.0
for r in filtered:
    cum *= (1+r['ret']/100)
    if cum > peak: peak = cum
    dd = (cum-peak)/peak*100; max_dd = min(max_dd, dd)
rets_flt = [r['ret'] for r in filtered]
wr = sum(1 for r in rets_flt if r>0)/len(rets_flt)*100
dly = np.array(rets_flt)
sh = np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
print(f"  净值{cum:.4f} 收益{(cum-1)*100:.1f}% 胜率{wr:.1f}% 回撤{max_dd:.1f}% 夏普{sh:.2f} "
      f"({len(filtered)}天, 过滤{skipped}天过热)")

# 对比
print("\n  全量对比:")
print(f"    全买(等权)               : 净值{ranks[0][0] if ranks[0][1]=='全买(等权)' else [x for x in ranks if x[1]=='全买(等权)'][0][0]:.4f}")
for x in ranks:
    if x[1] == '全买(等权)':
        print(f"    全买(等权)               : 净值{x[0]:.4f} 收益{(x[0]-1)*100:.1f}%")
    if x[1] == '情绪自适应选股TOP1':
        print(f"    情绪自适应选股(全)         : 净值{x[0]:.4f} 收益{(x[0]-1)*100:.1f}%")
print(f"    情绪自适应选股(过滤过热)    : 净值{cum:.4f} 收益{(cum-1)*100:.1f}%")

print("\n"+"="*100)
print("  分析完成!")
print("="*100)
