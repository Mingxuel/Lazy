"""TPO3随机选股 + 5M逐根卖出, 10次"""
import os, random, numpy as np
from collections import defaultdict

S = r'C:\Lazy\李明学的大A\Data\Strategy'
K = r'C:\Lazy\李明学的大A\Data\1D'
M5 = r'C:\Lazy\MarcoAI\AIData\5M'
INIT = 100_000
CR, SD, TF = 0.0001, 0.0005, 0.00001

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

_5m = {}
def lm5(code):
    if code in _5m: return _5m[code]
    fp = os.path.join(M5, code)
    if not os.path.exists(fp):
        _5m[code] = {}
        return {}
    bd = defaultdict(list)
    with open(fp) as f:
        for l in f:
            l = l.strip(); p = l.split('|')
            if len(p) < 6: continue
            d = p[0][:10].replace('-', '')
            bd[d].append((float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    _5m[code] = dict(bd)
    return _5m[code]

def trade(bp, sp, cpt):
    sh = int(cpt / bp / 100) * 100
    if sh < 100: return None
    b = sh * bp; cb = b * CR
    sa = sh * sp; cs = sa * CR; st = sa * SD; tf = sa * TF
    ret = (sa - cs - st - tf - b - cb) / (b + cb) * 100
    return ret

tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:
        l = l.strip()
        if l and l.isdigit() and len(l) == 8:
            tds.append(l)
tds = sorted(tds)
di = {d: i for i, d in enumerate(tds)}

daily_cands = defaultdict(list)
for fn in sorted(os.listdir(S)):
    if not fn.isdigit() or fn < '20250101': continue
    d1 = fn; d1i = di.get(d1)
    if d1i is None or d1i < 4: continue
    with open(os.path.join(S, fn)) as f:
        for l in f:
            l = l.strip(); p = l.split('|')
            if len(p) < 2: continue
            daily_cands[d1].append((p[1], p[0]))

days = sorted(daily_cands.keys())
total_cands = sum(len(v) for v in daily_cands.values())
print(f'TPO3: {len(days)}天, {total_cands}只, 日均{total_cands/len(days):.1f}只\n')

results = []
for seed in range(10):
    random.seed(seed)
    asset = INIT; trades = 0; no_data = 0; fallback_1d = 0
    monthly = defaultdict(list)
    for d1 in days:
        cands = daily_cands[d1]
        code, name = random.choice(cands)
        rs, dx = lk(code); d1k = dx.get(d1)
        if d1k is None: continue
        r1 = rs[d1k]; bp = r1[6]
        if bp <= 0: continue

        bars = lm5(code).get(d1, [])
        sp = None
        if bars:
            last_close = bars[-1][3]
            if last_close > 0 and r1[4] > 0 and abs(last_close / r1[4] - 1) < 0.02:
                lu = round(bp * 1.10, 2); st = bp * 0.94
                for bar in bars:
                    if bar[2] <= st: sp = st; break
                    if bar[1] >= lu * 0.999: sp = lu; break
                if sp is None: sp = last_close
            else:
                fallback_1d += 1; sp = r1[4]
        else:
            no_data += 1; sp = r1[4]

        ret = trade(bp, sp, asset)
        if ret is None: continue
        asset += asset * ret / 100
        trades += 1
        monthly[d1[:6]].append(ret)

    results.append({
        'seed': seed, 'asset': asset, 'trades': trades,
        'monthly': monthly, 'no_data': no_data, 'fb': fallback_1d
    })

assets = [r['asset'] for r in results]
navs = [a / INIT for a in assets]
print('随机10次 (5M逐根卖出, 止损/涨停/收盘):')
print(f'  均值: ¥{np.mean(assets):,.0f}  净值{np.mean(navs):.2f}  +{(np.mean(navs)-1)*100:+.1f}%')
print(f'  最佳: ¥{max(assets):,.0f}  净值{max(navs):.2f}  +{(max(navs)-1)*100:+.1f}%')
print(f'  最差: ¥{min(assets):,.0f}  净值{min(navs):.2f}  +{(min(navs)-1)*100:+.1f}%')
print(f'  标准差: ¥{np.std(assets):,.0f}')
print()
for r in results:
    n = r['asset'] / INIT
    wr = sum(1 for m in r['monthly'].values() if sum(m) > 0) / len(r['monthly']) * 100
    print(f'  seed={r["seed"]}: ¥{r["asset"]:,.0f}  {n:.2f}  {r["trades"]}笔  盈利月{wr:.0f}%  无5M:{r["no_data"]}  回退1D:{r["fb"]}')
