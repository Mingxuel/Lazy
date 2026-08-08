"""TPO3随机选股: 一仓 vs 两仓, 5M逐根卖出"""
import os, random, numpy as np
from collections import defaultdict

S = r'C:\Lazy\李明学的大A\Data\Strategy'
K = r'C:\Lazy\李明学的大A\Data\1D'
M5 = r'C:\Lazy\MarcoAI\AIData\5M'
INIT = 100_000
CR, SD, TF = 0.0001, 0.0005, 0.00001

def lk(code):
    fp = os.path.join(K, code); rows = []
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
    if not os.path.exists(fp): _5m[code] = {}; return {}
    bd = defaultdict(list)
    with open(fp) as f:
        for l in f:
            l = l.strip(); p = l.split('|')
            if len(p) < 6: continue
            d = p[0][:10].replace('-', '')
            bd[d].append((float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    _5m[code] = dict(bd); return _5m[code]

def trade(bp, sp, cpt):
    sh = int(cpt / bp / 100) * 100
    if sh < 100: return None
    b = sh * bp; cb = b * CR
    sa = sh * sp; cs = sa * CR; st = sa * SD; tf = sa * TF
    ret = (sa - cs - st - tf - b - cb) / (b + cb) * 100
    return ret, (sa - cs - st - tf - b - cb)

def sell_5m(bars, bp, d1_close):
    if not bars: return d1_close
    last_close = bars[-1][3]
    if last_close > 0 and d1_close > 0 and abs(last_close / d1_close - 1) >= 0.02:
        return d1_close
    lu = round(bp * 1.10, 2); st = bp * 0.94
    for bar in bars:
        if bar[2] <= st: return st
        if bar[1] >= lu * 0.999: return lu
    return d1_close

tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:
        l = l.strip()
        if l and l.isdigit() and len(l) == 8: tds.append(l)
tds = sorted(tds); di = {d: i for i, d in enumerate(tds)}

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

single_day = sum(1 for d in days if len(daily_cands[d]) < 2)
print(f'TPO3: {len(days)}天, {sum(len(v) for v in daily_cands.values())}只')
print(f'只有1只候选的天: {single_day} ({single_day/len(days)*100:.0f}%)')
print()

# === 一仓(基准) ===
navs_1 = []
for seed in range(10):
    random.seed(seed)
    asset = INIT
    for d1 in days:
        cands = daily_cands[d1]
        code, name = random.choice(cands)
        rs, dx = lk(code); d1k = dx.get(d1)
        if d1k is None: continue
        r1 = rs[d1k]; bp = r1[6]
        if bp <= 0: continue
        bars = lm5(code).get(d1, [])
        sp = sell_5m(bars, bp, r1[4])
        r = trade(bp, sp, asset)
        if r is not None: asset += r[1]
    navs_1.append(asset / INIT)

# === 两仓 ===
navs_2 = []
for seed in range(10):
    random.seed(seed)
    asset = INIT
    for d1 in days:
        cands = daily_cands[d1]
        if len(cands) >= 2:
            c1, c2 = random.sample(cands, 2)
            for code, name in [c1, c2]:
                rs, dx = lk(code); d1k = dx.get(d1)
                if d1k is None: continue
                r1 = rs[d1k]; bp = r1[6]
                if bp <= 0: continue
                bars = lm5(code).get(d1, [])
                sp = sell_5m(bars, bp, r1[4])
                r = trade(bp, sp, asset * 0.5)
                if r is not None: asset += r[1]
        else:
            code, name = random.choice(cands)
            rs, dx = lk(code); d1k = dx.get(d1)
            if d1k is None: continue
            r1 = rs[d1k]; bp = r1[6]
            if bp <= 0: continue
            bars = lm5(code).get(d1, [])
            sp = sell_5m(bars, bp, r1[4])
            r = trade(bp, sp, asset)
            if r is not None: asset += r[1]
    navs_2.append(asset / INIT)

print('=== 分仓对比 ===')
print(f'一仓(基准): 均值{np.mean(navs_1):.2f}  最佳{max(navs_1):.2f}  最差{min(navs_1):.2f}  标准差{np.std(navs_1):.2f}')
print(f'两仓:       均值{np.mean(navs_2):.2f}  最佳{max(navs_2):.2f}  最差{min(navs_2):.2f}  标准差{np.std(navs_2):.2f}')
print()
for i in range(10):
    d = navs_2[i] - navs_1[i]
    print(f'  seed={i}: 一仓{navs_1[i]:.2f}  两仓{navs_2[i]:.2f}  差{d:+.2f}')
