# -*- coding: utf-8 -*-
"""
养家心法回测: 周期环境 (上升期/震荡期/退潮期) → 动态仓位

判断标准 (周级别):
  上升期: 上证在MA20之上 + 5日成交额在MA20之上 + 近5日累计涨>0
  退潮期: 上证在MA20之下 + 成交额连缩 + 近5日累计跌<0
  震荡期: 其余

仓位规则:
  上升期 = 满仓; 震荡期 = 半仓; 退潮期 = 空仓
"""
import os, numpy as np, json, urllib.request
from collections import defaultdict
from numpy.linalg import solve

S = r'C:\Lazy\李明学的大A\Data\Strategy'
K = r'C:\Lazy\李明学的大A\Data\1D'
AD = r'C:\Lazy\MarcoAI\AIData'
FEATURES = ['pb_depth', 'ma5_dev', 'pc_vs_low_atr', 'high_vs_pc_atr', 'ma_golden']
CR = 0.0001; CM = 0.0; SD = 0.0005; TF = 0.00001; CAPITAL = 1_000_000

# ===== 获取上证指数日线 (从腾讯API) =====
def fetch_sh_index():
    """拉上证指数日线"""
    try:
        url = 'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000001,day,,,600,qfq'
        resp = urllib.request.urlopen(url, timeout=15).read()
        d = json.loads(resp)
        if 'data' not in d or 'sh000001' not in d['data']:
            return None
        sd = d['data']['sh000001']
        key = 'day' if 'day' in sd else 'qfqday'
        if key not in sd:
            return None
        rows = []
        for k in sd[key]:
            date = k[0].replace('-', '')  # "2024-02-20" → "20240220"
            close = float(k[2])
            rows.append((date, close))
        return rows
    except Exception as e:
        print(f'Warning: 上证指数获取失败 {e}, 使用本地数据')
        return None

print('获取上证指数日线...')
sh_rows = fetch_sh_index()
if sh_rows is None:
    print('❌ 无法获取上证指数, 退出')
    exit(1)
sh_dict = {r[0]: r[1] for r in sh_rows}
sh_dates = sorted(sh_dict.keys())
print(f'  上证数据: {len(sh_dates)}天, {sh_dates[0]} ~ {sh_dates[-1]}')

# ===== 加载市场成交额 =====
amount = {}
with open(os.path.join(AD, '1D_TOTAL_AMOUNT')) as f:
    for l in f:
        p = l.strip().split('|')
        if len(p) >= 4:
            try: amount[p[0]] = (float(p[1]), float(p[2]), float(p[3]))
            except: pass

# ===== 定义周期环境 (周级别趋势) =====
def classify_environment(date):
    """
    上升期: 上证>MA20 + 成交额5MA>成交额20MA + 近5日累计涨>0
    退潮期: 上证<MA20 + 成交额5MA<成交额20MA + 近5日累计跌<0
    震荡期: 其余
    """
    if date not in sh_dict or date not in amount:
        return '未知', 1.0  # 满仓兜底

    # 上证 MA20
    if date not in sh_dates:
        return '未知', 1.0
    idx = sh_dates.index(date)
    if idx < 25:
        return '未知', 1.0

    sh_closes = [sh_dict[d] for d in sh_dates[max(0, idx - 25): idx + 1]]
    n = len(sh_closes)
    if n < 20:
        return '未知', 1.0

    sh_ma20 = np.mean(sh_closes[-20:])

    # 成交额 MA5 vs MA20
    amts = []
    for d in sh_dates[max(0, idx - 24): idx + 1]:
        if d in amount:
            amts.append(amount[d][0])  # today amount
    if len(amts) < 20:
        return '未知', 1.0

    amt_ma5 = np.mean(amts[-5:])
    amt_ma20 = np.mean(amts[-20:])

    # 近5日累计涨跌
    sh_5d_chg = (sh_closes[-1] / sh_closes[-6] - 1) * 100 if n >= 6 else 0

    # 分类
    price_above = sh_closes[-1] > sh_ma20 * 1.01      # 上证在MA20上1%+
    price_below = sh_closes[-1] < sh_ma20 * 0.99      # 上证在MA20下1%-
    vol_expand = amt_ma5 > amt_ma20 * 1.02            # 成交额扩张
    vol_contract = amt_ma5 < amt_ma20 * 0.98          # 成交额萎缩

    if price_above and vol_expand and sh_5d_chg > 0:
        env = '上升期'
        pos = 1.0
    elif price_below and vol_contract and sh_5d_chg < 0:
        env = '退潮期'
        pos = 0.0
    else:
        env = '震荡期'
        pos = 0.5

    return env, pos


# ===== 加载交易数据 =====
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

tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:
        l = l.strip()
        l and l.isdigit() and len(l) == 8 and tds.append(l)
tds = sorted(tds)
di = {d: i for i, d in enumerate(tds)}

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

sa.sort(key=lambda x: x[2])
dm2 = defaultdict(list)
for i, s in enumerate(sa): dm2[s[2]].append(i)
dm = dm2; ad = sorted(dm.keys())
X = np.array([[s[0].get(k, 0) for k in FEATURES] for s in sa])
yt = np.array([(s[4] - s[3]) / s[3] * 100 for s in sa])

# ===== 回测: 多方案对比 =====
schemes = [
    ('基线(无环境过滤)', None),
    ('养家: 上升满/震荡半/退潮空', 'yangjia'),
    ('养家: 退潮半仓(非空仓)', 'yangjia_half'),
]

results = {}

for label, scheme in schemes:
    consec = 0; cum = 1.0; peak = 1.0; max_dd = 0.0
    trades = []
    env_stats = defaultdict(lambda: {'count': 0, 'rets': [], 'skipped': 0})
    env_seq = []

    for d1_date in ad:
        idxs = dm[d1_date]; fi = idxs[0]
        if fi < 100: best = sa[idxs[0]]
        else:
            hist = [j for j in range(fi)]
            Xh = X[hist]; yh = yt[hist]
            mu = Xh.mean(axis=0); sg = Xh.std(axis=0) + 1e-8
            Xn = (Xh - mu) / sg; d = Xn.shape[1]
            try: w = solve(Xn.T @ Xn + np.eye(d) * 2.0, Xn.T @ yh)
            except: w = np.zeros(d)
            Xt = np.array([(X[i] - mu) / sg for i in idxs])
            best = sa[idxs[int(np.argmax(Xt @ w))]]

        bp0 = best[3]; o0 = best[6]; h0 = best[7]; l0 = best[8]; c0 = best[4]
        sp0, mode0 = sd(bp0, o0, h0, l0, c0)
        d2_date = best[10]
        ret0 = fee(bp0, sp0, CAPITAL)

        env, env_pos = classify_environment(d2_date)

        env_stats[env]['count'] += 1

        # 仓位
        if scheme == 'yangjia':
            pos_pct = env_pos
        elif scheme == 'yangjia_half':
            # 退潮半仓: 上升=1.0, 震荡=0.5, 退潮=0.5(非空)
            pos_half_map = {'上升期': 1.0, '震荡期': 0.5, '退潮期': 0.5, '未知': 1.0}
            pos_pct = pos_half_map.get(env, 1.0)
        else:
            pos_pct = 1.0

        if pos_pct == 0:
            env_stats[env]['skipped'] += 1
            env_seq.append((d2_date, env, 0, 0))
            continue

        # 连亏管理
        if consec >= 3:
            consec = 0
            env_seq.append((d2_date, env, 0, 0))
            continue

        if consec >= 2:
            pos_pct *= 0.5

        cap = CAPITAL * pos_pct
        ret = fee(bp0, sp0, cap)

        cum *= (1 + ret / 100)
        if cum > peak: peak = cum
        dd = (cum - peak) / peak * 100
        if dd < max_dd: max_dd = dd

        trades.append({
            'd2': d2_date, 'ret': ret, 'env': env, 'pos': pos_pct,
            'name': best[5], 'code': best[1], 'mode': mode0,
            'cum': cum, 'dd': dd
        })
        env_stats[env]['rets'].append(ret)
        env_seq.append((d2_date, env, ret, cum))

        if ret < -0.05: consec += 1
        elif ret > 0.05: consec = 0

    results[label] = {
        'cum': cum, 'max_dd': max_dd, 'trades': len(trades),
        'env_stats': dict(env_stats), 'env_seq': env_seq
    }

    total_ret = (cum - 1) * 100

# ===== 输出 =====
print()
print('=' * 75)
print('  养家心法回测 (上升满仓 / 震荡半仓 / 退潮空仓)')
print('=' * 75)
print()

baseline = results['基线(无环境过滤)']
y = results['养家: 上升满/震荡半/退潮空']

print(f'{"方案":<30} {"净值":>8} {"收益":>9} {"回撤":>7} {"交易":>5}')
print('-' * 65)
for label, r in results.items():
    tr = (r['cum'] - 1) * 100
    print(f'{label:<30} {r["cum"]:>8.2f} {tr:>+8.1f}% {r["max_dd"]:>+6.1f}% {r["trades"]:>5}')

print()

# 环境分布 (退潮空仓)
y_empty = results['养家: 上升满/震荡半/退潮空']
print('=== 退潮空仓 — 环境分布 ===')
print(f'{"环境":<16} {"总天数":>6} {"交易天数":>6} {"跳过":>6} {"胜率":>7} {"平均收益":>8} {"净值贡献":>8}')
print('-' * 70)
for env in ['上升期', '震荡期', '退潮期', '未知']:
    es = y_empty['env_stats'].get(env, {'count': 0, 'rets': [], 'skipped': 0})
    total_days = es['count']
    skipped = es['skipped']
    rets = es['rets']
    traded = len(rets)
    wr = sum(1 for r in rets if r > 0) / len(rets) * 100 if rets else 0
    avg_r = np.mean(rets) if rets else 0
    cum_contrib = 1.0
    for r in rets: cum_contrib *= (1 + r / 100)
    print(f'{env:<16} {total_days:>6} {traded:>6} {skipped:>6} {wr:>6.1f}% {avg_r:>+7.2f}% {cum_contrib:>7.2f}x')

print()

# 环境分布 (退潮半仓)
y_half = results['养家: 退潮半仓(非空仓)']
print('=== 退潮半仓 — 环境分布 ===')
print(f'{"环境":<16} {"总天数":>6} {"交易天数":>6} {"胜率":>7} {"平均收益":>8} {"净值贡献":>8}')
print('-' * 65)
for env in ['上升期', '震荡期', '退潮期', '未知']:
    es = y_half['env_stats'].get(env, {'count': 0, 'rets': [], 'skipped': 0})
    total_days = es['count']
    rets = es['rets']
    traded = len(rets)
    wr = sum(1 for r in rets if r > 0) / len(rets) * 100 if rets else 0
    avg_r = np.mean(rets) if rets else 0
    cum_contrib = 1.0
    for r in rets: cum_contrib *= (1 + r / 100)
    print(f'{env:<16} {total_days:>6} {traded:>6} {wr:>6.1f}% {avg_r:>+7.2f}% {cum_contrib:>7.2f}x')

# 年度对比
print()
print('=== 年度对比 ===')
for label in results:
    r = results[label]
    ann = defaultdict(list)
    for r_date, r_env, r_ret, r_cum in r['env_seq']:
        if r_ret != 0:
            ann[r_date[:4]].append(r_ret)
    print(f'\n{label}:')
    for yk in sorted(ann.keys()):
        yr = 1.0
        for rv in ann[yk]: yr *= (1 + rv / 100)
        wins = sum(1 for rv in ann[yk] if rv > 0)
        nall = len(ann[yk])
        print(f'  {yk}: +{(yr-1)*100:.1f}% ({wins}/{nall}wr={wins/nall*100:.0f}%)')

# 月度对比 (只看有差异的)
print()
print('=== 退潮期跳过的月份 ===')
y_baseline_monthly = defaultdict(list)
y_yangjia_monthly = defaultdict(list)
for r_date, r_env, r_ret, r_cum in baseline['env_seq']:
    if r_ret != 0:
        y_baseline_monthly[r_date[:6]].append(r_ret)
for r_date, r_env, r_ret, r_cum in y['env_seq']:
    if r_ret != 0:
        y_yangjia_monthly[r_date[:6]].append(r_ret)

for m in sorted(set(list(y_baseline_monthly.keys()) + list(y_yangjia_monthly.keys()))):
    br = 1.0; yr2 = 1.0
    for rv in y_baseline_monthly.get(m, []): br *= (1 + rv / 100)
    for rv in y_yangjia_monthly.get(m, []): yr2 *= (1 + rv / 100)
    if abs((br - 1) * 100 - (yr2 - 1) * 100) > 1:
        skip_count = y['env_stats'].get('退潮期', {}).get('skipped', 0)
        print(f'  {m}: 基线{(br-1)*100:+.1f}% → 养家{(yr2-1)*100:+.1f}% '
              f'(差{(br-yr2)*100:+.1f}pp)')
