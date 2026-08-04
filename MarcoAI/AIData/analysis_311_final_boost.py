#!/usr/bin/env python3
"""策略311 极致优化"""
import os
import numpy as np
from collections import defaultdict

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
FIVEM_DIR = os.path.join(BASE, "5M")
KLINE_DIR = os.path.join(BASE, "1D")
CR = 0.00025
CM = 5.0
SD = 0.0005
TF = 0.00001
CAPITAL = 1_000_000

def load_td():
    ds = []
    with open(os.path.join(BASE, "TRADING_DATES")) as f:
        for l in f:
            l = l.strip()
            if l:
                ds.append(l)
    return sorted(ds)

def load_stock_info():
    info = {}
    with open(os.path.join(BASE, "STOCK_CODES_ALL"), encoding='utf-8') as f:
        for i, l in enumerate(f):
            l = l.strip()
            if not l:
                continue
            p = l.split('|')
            if len(p) >= 2:
                info[p[0]] = {'rank': i, 'name': p[1]}
    return info

def load_kline_range(code, dates):
    fp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fp):
        return {}
    r = {}
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            p = l.split('|')
            if len(p) < 7:
                continue
            if p[0] in dates:
                r[p[0]] = (float(p[1]), float(p[2]), float(p[3]),
                           float(p[4]), float(p[5]), float(p[6]))
    return r

def load_5m(code, dt):
    fp = os.path.join(FIVEM_DIR, code)
    if not os.path.exists(fp):
        return None
    df = f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}"
    bars = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            p = l.split('|')
            if len(p) < 6:
                continue
            if p[0].startswith(df):
                bars.append((p[0], float(p[4]), float(p[2]),
                            float(p[3]), float(p[1]), float(p[5])))
    return bars if bars else None

def load_sigs():
    sd = {}
    for fn in sorted(os.listdir(SIGNAL_DIR)):
        fp = os.path.join(SIGNAL_DIR, fn)
        if os.path.getsize(fp) <= 3:
            continue
        with open(fp, encoding='utf-8') as f:
            ls = [l.strip() for l in f if l.strip()]
        if not ls:
            continue
        es = []
        for l in ls:
            p = l.split('|')
            if len(p) >= 8:
                es.append((p[0], float(p[7])))
        if es:
            sd[fn] = es
    return sd

def load_sentiment():
    sent = defaultdict(dict)
    files = [
        ("1D_PANIC_INDEX", [('panic', float)]),
        ("1D_AVG_CHANGE", [('avg_chg', float)]),
        ("1D_MOTION_COUNT", [('net_motion', int)]),
        ("1D_TOTAL_AMOUNT", [
            ('amount', lambda x: float(x) if x != 'nan' else None),
            ('amount_ma5', lambda x: float(x) if x != 'nan' else None)
        ])
    ]
    for fname, convs in files:
        with open(os.path.join(BASE, fname)) as f:
            for l in f:
                l = l.strip()
                if not l:
                    continue
                p = l.split('|')
                for i, (k, conv) in enumerate(convs):
                    if len(p) > i + 1:
                        try:
                            sent[p[0]][k] = conv(p[i+1])
                        except:
                            pass
    return sent

def classify_sentiment(s):
    panic = s.get('panic', 20)
    avg_chg = s.get('avg_chg', 0)
    net = s.get('net_motion', 0)
    amt = s.get('amount')
    amt_ma5 = s.get('amount_ma5')
    score = 0
    if panic > 70:
        score -= 3
    elif panic > 50:
        score -= 2
    elif panic > 30:
        score -= 1
    elif panic < 5:
        score += 1
    if avg_chg < -2.0:
        score -= 3
    elif avg_chg < -1.0:
        score -= 2
    elif avg_chg < -0.3:
        score -= 1
    elif avg_chg > 2.0:
        score += 2
    elif avg_chg > 1.0:
        score += 1
    mp = net / 677 * 100
    if mp < -30:
        score -= 2
    elif mp < -10:
        score -= 1
    elif mp > 30:
        score += 2
    elif mp > 10:
        score += 1
    if amt and amt_ma5 and amt_ma5 > 0:
        if amt / amt_ma5 > 1.3:
            score += 1
        elif amt / amt_ma5 < 0.7:
            score -= 1
    if score <= -4:
        return '恐慌'
    elif score <= -1:
        return '偏空'
    elif score <= 1:
        return '震荡'
    elif score <= 4:
        return '偏多'
    else:
        return '过热'

def fee(buy, sell, pc):
    if buy == 0 or sell == 0:
        return 0.0
    sh = int(pc / buy / 100) * 100
    if sh == 0:
        sh = 100
    c = sh * buy
    bf = max(c * CR, CM) + c * TF
    tb = c + bf
    r = sh * sell
    sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100

def compute_factors(code, kd2, kd3, kd4, stock_info):
    if not kd2 or not kd3:
        return None
    o2, h2, l2, c2, v2, a2 = kd2
    o3, h3, l3, c3, v3, a3 = kd3
    f = {}
    f['pullback_depth'] = (c3 - c2) / c3 * 100 if c3 else 0
    f['lower_shadow'] = (c2 - l2) / (h2 - l2) * 100 if h2 > l2 else 50
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
    if 0 < f['pullback_depth'] < 8:
        score += 2
    elif f['pullback_depth'] > 15:
        score -= 1
    if f['lower_shadow'] > 60:
        score += 2
    if f['vol_contract']:
        score += 2
    if f['vol_ratio_d3_d2'] > 1.5:
        score += 1
    if f['shadow_support']:
        score += 1
    f['quality_score'] = score
    return f

def select_stocks(candidates, env_name, top_n=1):
    if env_name == '过热':
        return []
    if env_name in ('恐慌', '偏空', '偏多'):
        scored = []
        for code, d2c, bars, f in candidates:
            if f is None:
                continue
            s = f.get('is_mega_cap', 0) * 5
            s += f.get('shadow_support', 0) * 3
            s += f.get('vol_contract', 0) * 2
            scored.append((s, code, d2c, bars, f))
        scored.sort(key=lambda x: -x[0])
        return scored[:top_n]
    elif env_name == '震荡':
        scored = []
        for code, d2c, bars, f in candidates:
            if f is None:
                continue
            s = (1 - f.get('cap_rank_norm', 0.5)) * 5
            if f.get('vol_ratio_d3_d2', 1) > 1.2:
                s += 2
            if 0 < f.get('pullback_depth', 0) < 10:
                s += 1
            scored.append((s, code, d2c, bars, f))
        scored.sort(key=lambda x: -x[0])
        return scored[:top_n]
    return []

def sell_close(bars, bp):
    return bars[-1][1]

def sell_trail(pct):
    def f(bars, bp):
        peak = bars[0][1]
        for b in bars:
            if b[1] > peak:
                peak = b[1]
            elif (peak - b[1]) / peak * 100 >= pct:
                return b[1]
        return bars[-1][1]
    return f

# ============================================================
print("=" * 100)
print("  策略311 极致优化")
print("=" * 100)

sigs = load_sigs()
tds = load_td()
di = {d: i for i, d in enumerate(tds)}
stock_info = load_stock_info()
sentiment = load_sentiment()

by_d1 = defaultdict(list)
for d0 in sorted(sigs.keys()):
    es = sigs[d0]
    d0i = di.get(d0)
    if d0i is None or d0i < 3:
        continue
    d1 = tds[d0i - 1]
    d2 = tds[d0i - 2]
    d3 = tds[d0i - 3]
    d4 = tds[d0i - 4] if d0i >= 4 else None
    sent_d2 = sentiment.get(d2, {})
    if not sent_d2:
        continue
    env_name = classify_sentiment(sent_d2)
    if env_name == '过热':
        continue

    for code, d1_close in es:
        klines = load_kline_range(code, set(filter(None, [d2, d3, d4])))
        kd2 = klines.get(d2)
        kd3 = klines.get(d3)
        kd4 = klines.get(d4) if d4 else None
        if not kd2 or not kd3:
            continue
        d2_close = kd2[3]
        factors = compute_factors(code, kd2, kd3, kd4, stock_info)
        if not factors:
            continue
        bars = load_5m(code, d1)
        if not bars or len(bars) < 10:
            continue
        by_d1[d1].append((code, d2_close, bars, factors, env_name))

# 测试组合
env_position = {'恐慌': 1.5, '偏空': 1.0, '震荡': 1.0, '偏多': 1.3}

env_sell = {
    '恐慌': sell_close,
    '偏空': sell_close,
    '震荡': sell_trail(1.5),
    '偏多': sell_close,
}

combos = [
    ("baseline_等权全买+收盘卖", 99, sell_close, {}, False),
    ("精选TOP1+收盘卖", 1, sell_close, {}, False),
    ("精选TOP2+收盘卖", 2, sell_close, {}, False),
    ("精选TOP3+收盘卖", 3, sell_close, {}, False),
    ("TOP1+分环境卖点", 1, None, {}, False),
    ("TOP1+环境仓位+收盘卖", 1, sell_close, env_position, False),
    ("TOP1+环境仓位+分环境卖点", 1, None, env_position, False),
    ("TOP2+环境仓位+收盘卖", 2, sell_close, env_position, False),
    ("TOP1+质量过滤QS>=4", 1, sell_close, {}, True),
    ("TOP1+环境仓位+质量过滤+收盘卖", 1, sell_close, env_position, True),
]

results_all = {}

for label, top_n, sell_fn, pos_scale, quality_filter in combos:
    daily_rets = []

    for d1 in sorted(by_d1.keys()):
        trades = by_d1[d1]
        env_name = trades[0][4]

        candidates = [(t[0], t[1], t[2], t[3]) for t in trades]
        if quality_filter:
            candidates = [c for c in candidates if c[3] and c[3].get('quality_score', 0) >= 4]
        picks = select_stocks(candidates, env_name, top_n)
        if not picks:
            continue

        mult = pos_scale.get(env_name, 1.0)
        total_cap = CAPITAL * mult
        n_pick = len(picks)
        pc = total_cap / n_pick
        rets = []
        for _, code, d2c, bars, f in picks:
            if sell_fn is None:
                sf = env_sell.get(env_name, sell_close)
            else:
                sf = sell_fn
            sp = sf(bars, d2c)
            rets.append(fee(d2c, sp, pc))

        if rets:
            daily_rets.append(sum(rets) / len(rets))

    if not daily_rets:
        continue

    cum = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in daily_rets:
        cum *= (1 + r / 100)
        if cum > peak:
            peak = cum
        dd = (cum - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    wr = sum(1 for r in daily_rets if r > 0) / len(daily_rets) * 100
    dly = np.array(daily_rets)
    sh = np.mean(dly) / np.std(dly) * np.sqrt(252) if np.std(dly) > 0 else 0
    results_all[label] = (cum, (cum - 1) * 100, wr, max_dd, sh)

    tags = []
    if pos_scale:
        tags.append("仓位管理")
    if quality_filter:
        tags.append("质量过滤")
    if sell_fn is None:
        tags.append("分环境卖点")
    tag_str = " + ".join(tags) if tags else ""
    print(f"  {label:<40}: 净值{cum:.4f} 收益{(cum-1)*100:.1f}% 胜率{wr:.1f}% 回撤{max_dd:.1f}% 夏普{sh:.2f}  [{tag_str}]")

# 最佳
best_label = max(results_all, key=lambda k: results_all[k][0])
best = results_all[best_label]
print(f"\n🏆 最佳: {best_label}")
print(f"   净值{best[0]:.4f}  收益{best[1]:.1f}%  胜率{best[2]:.1f}%  回撤{best[3]:.1f}%  夏普{best[4]:.2f}")

print("\n" + "=" * 100)
print("  完成!")
print("=" * 100)
