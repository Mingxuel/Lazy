# -*- coding: utf-8 -*-
"""
情绪周期与回撤分析

用市场情绪信号 (成交额趋势/平均涨跌幅/连跌天数) 逐笔交叉验证,
看亏损是否集中在特定情绪环境中, 能否通过情绪过滤减少回撤。

数据源: 1D_TOTAL_AMOUNT (市场成交额), 1D_AVG_CHANGE (平均涨跌幅)
"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S = r'C:\Lazy\李明学的大A\Data\Strategy'
K = r'C:\Lazy\李明学的大A\Data\1D'
AD = r'C:\Lazy\MarcoAI\AIData'
FEATURES = ['pb_depth', 'ma5_dev', 'pc_vs_low_atr', 'high_vs_pc_atr', 'ma_golden']
CR = 0.0001; CM = 0.0; SD = 0.0005; TF = 0.00001; CAPITAL = 1_000_000

# ===== 加载情绪数据 =====
def load_sentiment():
    amount = {}
    with open(os.path.join(AD, '1D_TOTAL_AMOUNT')) as f:
        for l in f:
            p = l.strip().split('|')
            if len(p) >= 4:
                try:
                    amount[p[0]] = (float(p[1]), float(p[2]), float(p[3]))
                except: pass

    change = {}
    with open(os.path.join(AD, '1D_AVG_CHANGE')) as f:
        for l in f:
            p = l.strip().split('|')
            if len(p) >= 4:
                try:
                    change[p[0]] = (float(p[1]), float(p[2]), float(p[3]))
                except: pass
    return amount, change

amount, avg_change = load_sentiment()
all_sent_dates = sorted(set(amount.keys()) & set(avg_change.keys()))
print(f'情绪数据覆盖: {all_sent_dates[0]} ~ {all_sent_dates[-1]} ({len(all_sent_dates)}天)')

# ===== 定义情绪状态 =====
def get_sentiment_state(date, amount, avg_change):
    """返回 (state_name, detail_dict)"""
    if date not in amount or date not in avg_change:
        return None, None

    amt_today, amt_yest, amt_5ma = amount[date]
    chg_today, chg_yest, chg_5ma = avg_change[date]

    if amt_today <= 0 or chg_today == 0:
        return None, None

    detail = {
        'amt_today': amt_today, 'amt_5ma': amt_5ma,
        'chg_today': chg_today, 'chg_5ma': chg_5ma,
        'amt_ratio': amt_today / amt_5ma if amt_5ma > 0 else 1.0,  # >1=放量
    }

    # 情绪分类: 4象限
    # 量增价涨 = 进攻
    # 量增价跌 = 恐慌
    # 量缩价涨 = 犹豫涨
    # 量缩价跌 = 阴跌

    vol_up = amt_today > amt_5ma * 1.02       # 放量>2%
    vol_down = amt_today < amt_5ma * 0.98     # 缩量<-2%
    price_up = chg_today > 0.2                # 市场涨>0.2%
    price_down = chg_today < -0.2             # 市场跌<-0.2%

    if vol_up and price_up:
        state = '进攻(量增价涨)'
    elif vol_up and price_down:
        state = '恐慌(量增价跌)'
    elif vol_down and price_up:
        state = '犹豫涨(量缩价涨)'
    elif vol_down and price_down:
        state = '阴跌(量缩价跌)'
    elif price_up:
        state = '温和涨'
    elif price_down:
        state = '温和跌'
    else:
        state = '横盘'

    return state, detail

# ===== 加载K线 =====
def lk(code):
    fp = os.path.join(K, code)
    rows = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('\ufeff'): continue
            c = l.split()
            if len(c) < 10 or not c[0].isdigit(): continue
            rows.append((c[0], float(c[1]), float(c[2]), float(c[3]),
                         float(c[4]), float(c[5]), float(c[9])))
    return rows, {r[0]: i for i, r in enumerate(rows)}

def fee(bp, sp, cap):
    sh = int(cap / bp / 100) * 100
    return (sp * sh * (1 - CR - SD - TF) - bp * sh * (1 + CR)) / (bp * sh) * 100

def sd(bp, o, h, l, c):
    st = bp * 0.94; lu = round(bp * 1.10, 2)
    if o <= st: return o, 'open_stop'
    if l <= st: return st, 'low_stop'
    if h >= lu * 0.999: return lu, 'limit_up'
    return c, 'close'

# ===== 加载交易数据 =====
tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:
        l = l.strip()
        l and l.isdigit() and len(l) == 8 and tds.append(l)
tds = sorted(tds)
di = {d: i for i, d in enumerate(tds)}

# 构建全部样本
sa = []
dm = defaultdict(list)
for fn in sorted(os.listdir(S)):
    if not fn.isdigit(): continue
    d1 = fn; d1i = di.get(d1)
    if d1i is None or d1i < 3: continue
    d2 = tds[d1i - 1]
    with open(os.path.join(S, fn)) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) < 2: continue
            code = p[1]; name = p[0]
            rs, dx = lk(code)
            d1k = dx.get(d1); d2k = dx.get(d2)
            if d1k is None or d2k is None: continue
            r1 = rs[d1k]; bp = r1[6]; sc = r1[4]
            if bp <= 0: continue
            r2 = rs[d2k]; r3 = rs[d2k - 1] if d2k >= 1 else None
            if r3 is None: continue
            cl = np.array([r[4] for r in rs[:d2k + 1]])
            hi = np.array([r[2] for r in rs[:d2k + 1]])
            n = len(cl)
            f = {}
            f['pb_depth'] = (r3[4] - r2[4]) / r3[4] * 100 if r3[4] > 0 else 0
            f['ma5_dev'] = (r2[4] - np.mean(cl[-5:])) / np.mean(cl[-5:]) * 100 if n >= 5 else 0
            if n >= 10:
                tr = []
                for i in range(d2k - 9, d2k + 1):
                    h = hi[i]; l_ = rs[i][3]; pc = rs[i - 1][4] if i > 0 else rs[i][6]
                    tr.append(max(h - l_, abs(h - pc), abs(l_ - pc)))
                atr = np.mean(tr)
            else:
                atr = r2[2] - r2[3] if r2[2] > r2[3] else 1
            f['pc_vs_low_atr'] = (r2[6] - r2[3]) / atr if atr > 0 else 0
            f['high_vs_pc_atr'] = (r2[2] - r2[6]) / atr if atr > 0 else 0
            mg = 0
            if d2k >= 10:
                ca = [r[4] for r in rs[:d2k + 1]]
                ma5 = np.mean(ca[-5:]); ma10 = np.mean(ca[-10:])
                ma5p = np.mean(ca[-6:-1]); ma10p = np.mean(ca[-11:-1])
                mg = 1 if (ma5p <= ma10p and ma5 > ma10) else 0
            f['ma_golden'] = mg
            sa.append((f, code, d1, bp, sc, name, r1[1], r1[2], r1[3], r2[4], d2))

# WF backtest
sa.sort(key=lambda x: x[2])
dm2 = defaultdict(list)
for i, s in enumerate(sa): dm2[s[2]].append(i)
dm = dm2; ad = sorted(dm.keys())
X = np.array([[s[0].get(k, 0) for k in FEATURES] for s in sa])
yt = np.array([(s[4] - s[3]) / s[3] * 100 for s in sa])

consec = 0
cum = 1.0; peak = 1.0; max_dd = 0.0
all_trades = []  # (d1_date, d2_date, ret, name, code, mode, sentiment_state, sent_detail)

for d1_date in ad:
    idxs = dm[d1_date]; fi = idxs[0]
    if fi < 100:
        best = sa[idxs[0]]
    else:
        hist = [j for j in range(fi)]
        Xh = X[hist]; yh = yt[hist]
        mu = Xh.mean(axis=0); sg = Xh.std(axis=0) + 1e-8
        Xn = (Xh - mu) / sg; d = Xn.shape[1]
        try: w = solve(Xn.T @ Xn + np.eye(d) * 2.0, Xn.T @ yh)
        except: w = np.zeros(d)
        Xt = np.array([(X[i] - mu) / sg for i in idxs])
        best = sa[idxs[int(np.argmax(Xt @ w))]]

    bp = best[3]; o = best[6]; h = best[7]; l = best[8]; c = best[4]
    sp, mode = sd(bp, o, h, l, c)
    d2_date = best[10]

    if consec >= 3:
        consec = 0
        continue
    cap = CAPITAL * (0.5 if consec >= 2 else 1)
    ret = fee(bp, sp, cap)

    cum *= (1 + ret / 100)
    if cum > peak: peak = cum
    dd = (cum - peak) / peak * 100
    if dd < max_dd: max_dd = dd

    sent_state, sent_detail = get_sentiment_state(d2_date, amount, avg_change)

    all_trades.append({
        'd1': d1_date, 'd2': d2_date, 'ret': ret, 'name': best[5], 'code': best[1],
        'mode': mode, 'bp': bp, 'sp': sp,
        'sent_state': sent_state, 'sent_detail': sent_detail,
        'cum': cum, 'dd': dd,
    })

    if ret < -0.05: consec += 1
    elif ret > 0.05: consec = 0

# ===== 按情绪状态分组统计 =====
print(f'\n总交易: {len(all_trades)}笔 | 净值{cum:.2f} | 最大回撤{max_dd:.1f}%')
print()

by_sent = defaultdict(list)
by_price = defaultdict(list)
by_volume = defaultdict(list)

for t in all_trades:
    s = t['sent_state'] or '无数据'
    by_sent[s].append(t['ret'])

    if t['sent_detail']:
        chg = t['sent_detail']['chg_today']
        if chg > 0.5: by_price['涨>0.5%'].append(t['ret'])
        elif chg > 0: by_price['涨0~0.5%'].append(t['ret'])
        elif chg > -0.5: by_price['跌0~0.5%'].append(t['ret'])
        else: by_price['跌>0.5%'].append(t['ret'])

        vr = t['sent_detail']['amt_ratio']
        if vr > 1.05: by_volume['放量>5%'].append(t['ret'])
        elif vr > 1.0: by_volume['平量'].append(t['ret'])
        else: by_volume['缩量>0%'].append(t['ret'])

print(f'{"情绪状态":<20} {"笔数":>5} {"胜率":>7} {"平均收益":>8} {"波动率":>8}')
print('-' * 55)
for state in sorted(by_sent.keys(), key=lambda k: np.mean(by_sent[k])):
    rets = by_sent[state]
    wr = sum(1 for r in rets if r > 0) / len(rets) * 100
    avg_r = np.mean(rets)
    std_r = np.std(rets)
    bar = '█' * len(rets)
    print(f'{state:<20} {len(rets):>5} {wr:>6.1f}% {avg_r:>+7.2f}% {std_r:>7.2f}% {bar}')

print()
print(f'{"市场涨跌":<20} {"笔数":>5} {"胜率":>7} {"平均收益":>8}')
print('-' * 45)
for state in ['涨>0.5%', '涨0~0.5%', '跌0~0.5%', '跌>0.5%']:
    rets = by_price.get(state, [])
    if not rets: continue
    wr = sum(1 for r in rets if r > 0) / len(rets) * 100
    print(f'{state:<20} {len(rets):>5} {wr:>6.1f}% {np.mean(rets):>+7.2f}%')

print()
print(f'{"成交量":<20} {"笔数":>5} {"胜率":>7} {"平均收益":>8}')
print('-' * 45)
for state in ['放量>5%', '平量', '缩量>0%']:
    rets = by_volume.get(state, [])
    if not rets: continue
    wr = sum(1 for r in rets if r > 0) / len(rets) * 100
    print(f'{state:<20} {len(rets):>5} {wr:>6.1f}% {np.mean(rets):>+7.2f}%')

# ===== 回测：按情绪状态过滤 =====
print()
print('=' * 60)
print('  情绪过滤回测: 在某类情绪日跳过不交易')
print('=' * 60)
print(f'{"过滤条件":<30} {"净值":>8} {"回撤":>7} {"笔数":>5} {"vs基线"}')

baseline_nv = cum

for label, skip_states in [
    ('无过滤(基准)', []),
    ('跳过恐慌日', ['恐慌(量增价跌)']),
    ('跳过恐慌+阴跌', ['恐慌(量增价跌)', '阴跌(量缩价跌)']),
    ('仅进攻+温和涨', ['恐慌(量增价跌)', '阴跌(量缩价跌)', '温和跌', '横盘', '犹豫涨(量缩价涨)']),
    ('跳过跌>0.5%', []),  # special handling below
    ('跳过跌>0%', []),    # special
    ('跳过缩量', []),     # special
    ('仅放量>5%', []),    # special
]:
    consec_test = 0
    cum_test = 1.0; peak_test = 1.0; max_dd_test = 0.0
    trade_count = 0

    for t in all_trades:
        state = t['sent_state'] or '无数据'
        detail = t['sent_detail']

        skip = False
        if label == '跳过跌>0.5%':
            if detail and detail['chg_today'] < -0.5:
                skip = True
        elif label == '跳过跌>0%':
            if detail and detail['chg_today'] < 0:
                skip = True
        elif label == '跳过缩量':
            if detail and detail['amt_ratio'] < 0.98:
                skip = True
        elif label == '仅放量>5%':
            if detail and not (detail['amt_ratio'] > 1.05):
                skip = True
        elif skip_states and state in skip_states:
            skip = True

        if skip:
            continue

        if consec_test >= 3:
            consec_test = 0
            continue

        cap_test = CAPITAL * (0.5 if consec_test >= 2 else 1)
        ret_test = t['ret']
        cum_test *= (1 + ret_test / 100)
        if cum_test > peak_test: peak_test = cum_test
        dd_test = (cum_test - peak_test) / peak_test * 100
        if dd_test < max_dd_test: max_dd_test = dd_test
        trade_count += 1

        if ret_test < -0.05: consec_test += 1
        elif ret_test > 0.05: consec_test = 0

    diff = (cum_test / baseline_nv - 1) * 100
    sign = '+' if diff > 0 else ''
    print(f'{label:<30} {cum_test:>8.2f} {max_dd_test:>+6.1f}% {trade_count:>5} {sign}{diff:+.1f}%')

# ===== 连亏发生时市场情绪 =====
print()
print('=' * 60)
print('  连亏 3+ 次时的市场情绪')
print('=' * 60)
consec_check = 0
streak_trades = []
for t in all_trades:
    if t['ret'] < 0:
        consec_check += 1
        streak_trades.append(t)
    else:
        if consec_check >= 3:
            print(f'\n连亏{consec_check}次 (日期: {streak_trades[0]["d2"]} ~ {streak_trades[-1]["d2"]})')
            for st in streak_trades:
                d = st['sent_detail']
                amt_r = d['amt_ratio'] if d else '?'
                chg = d['chg_today'] if d else '?'
                print(f'  {st["d2"]} {st["name"]}({st["code"]}) {st["ret"]:+.2f}% '
                      f'[{st["sent_state"]}] 放量比={amt_r:.2f}x 市场涨={chg:+.2f}%')
        consec_check = 0
        streak_trades = []
if consec_check >= 3:
    print(f'\n连亏{consec_check}次')
    for st in streak_trades:
        d = st['sent_detail']
        print(f'  {st["d2"]} {st["name"]} {st["ret"]:+.2f}% [{st["sent_state"]}]')

# ===== 最大回撤区间情绪 =====
print()
print('=' * 60)
print('  最大回撤区间 (top 5 drawdown events)')
print('=' * 60)
dd_events = sorted([t for t in all_trades if t['dd'] < -5], key=lambda t: t['dd'])
for t in dd_events[:10]:
    d = t['sent_detail']
    amt_r = d['amt_ratio'] if d else -1
    chg = d['chg_today'] if d else -99
    print(f'  {t["d2"]} 净值{t["cum"]:.2f} DD={t["dd"]:.1f}% '
          f'{t["name"]}({t["code"]}) {t["ret"]:+.2f}% '
          f'[{t["sent_state"]}] 市场{chg:+.2f}%')

print()
print('基线净值:', baseline_nv)
