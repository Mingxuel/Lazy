"""TPO3随机选股: 1D止损优先 vs 5M逐根, 各10次"""
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
    if not os.path.exists(fp): _5m[code] = {}; return {}
    bd = defaultdict(list)
    with open(fp) as f:
        for l in f:
            l = l.strip(); p = l.split('|')
            if len(p) < 6: continue
            d = p[0][:10].replace('-', '')
            bd[d].append((float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    _5m[code] = dict(bd)
    return _5m[code]

def trade(bp, sp, cpt, factor=1.0):
    cpt_use = cpt * factor
    sh = int(cpt_use / bp / 100) * 100
    if sh < 100: return None
    b = sh * bp; cb = b * CR
    sa = sh * sp; cs = sa * CR; st = sa * SD; tf = sa * TF
    ret = (sa - cs - st - tf - b - cb) / (b + cb) * 100
    return ret

def sell_1d(bp, o, h, l, c):
    """止损-6% > 涨停 > 收盘"""
    st = bp * 0.94; lu = round(bp * 1.10, 2)
    if o <= st:       return o, 'stop_open'
    if l <= st:       return st, 'stop_intra'
    if h >= lu*0.999: return lu, 'limit_up'
    return c, 'close'

def sell_5m(bars, bp, d1_close):
    """5M逐根: 止损/涨停/收盘"""
    if not bars: return d1_close
    last_close = bars[-1][3]
    # 校验5M与1D一致性
    if last_close > 0 and d1_close > 0 and abs(last_close / d1_close - 1) >= 0.02:
        return d1_close  # 不一致→回退1D
    lu = round(bp * 1.10, 2); st = bp * 0.94
    for bar in bars:
        if bar[2] <= st: return st
        if bar[1] >= lu * 0.999: return lu
    return d1_close  # 收盘卖出统一用1D收盘价

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
print(f'TPO3: {len(days)}天, {sum(len(v) for v in daily_cands.values())}只\n')

# === 1D止损优先 (含仓位控制) ===
print('=== 1D 止损优先 (止损-6% > 涨停 > 收盘) + 仓位控制 ===')
r1d = []
for seed in range(10):
    random.seed(seed)
    asset = INIT; consec = 0; skips = 0
    monthly = defaultdict(list)
    for d1 in days:
        cands = daily_cands[d1]
        code, name = random.choice(cands)
        rs, dx = lk(code); d1k = dx.get(d1)
        if d1k is None: continue
        r1 = rs[d1k]; bp = r1[6]
        if bp <= 0: continue
        # 仓位控制
        if consec >= 3: consec = 0; skips += 1; continue
        factor = 0.5 if consec >= 2 else 1.0
        sp, _ = sell_1d(bp, r1[1], r1[2], r1[3], r1[4])
        ret = trade(bp, sp, asset, factor)
        if ret is None: continue
        # ret%是对投入资金(asset*factor)的收益率，需要换算为总资产变动
        cny_profit = (asset * factor) * ret / 100
        asset += cny_profit
        monthly[d1[:6]].append(ret)
        # 连亏统计
        if ret < -5: consec += 1
        elif ret > 5: consec = 0
    n = asset / INIT
    wr = sum(1 for m in monthly.values() if sum(m) > 0) / len(monthly) * 100
    r1d.append({'seed': seed, 'asset': asset, 'nav': n, 'wr': wr, 'monthly': monthly, 'skips': skips})

assets = [r['asset'] for r in r1d]; navs = [r['nav'] for r in r1d]
print(f'  均值: ¥{np.mean(assets):,.0f}  净值{np.mean(navs):.2f}  +{(np.mean(navs)-1)*100:+.1f}%')
print(f'  最佳: ¥{max(assets):,.0f}  净值{max(navs):.2f}  +{(max(navs)-1)*100:+.1f}%')
print(f'  最差: ¥{min(assets):,.0f}  净值{min(navs):.2f}  +{(min(navs)-1)*100:+.1f}%')
for r in r1d:
    print(f'  seed={r["seed"]}: ¥{r["asset"]:,.0f}  {r["nav"]:.2f}  盈利月{r["wr"]:.0f}%  跳过{r["skips"]}天')

# === 5M逐根 (含仓位控制) ===
print('\n=== 5M 逐根卖出 + 仓位控制 ===')
r5m = []
for seed in range(10):
    random.seed(seed)
    asset = INIT; consec = 0; skips = 0
    monthly = defaultdict(list)
    for d1 in days:
        cands = daily_cands[d1]
        code, name = random.choice(cands)
        rs, dx = lk(code); d1k = dx.get(d1)
        if d1k is None: continue
        r1 = rs[d1k]; bp = r1[6]
        if bp <= 0: continue
        # 仓位控制
        if consec >= 3: consec = 0; skips += 1; continue
        factor = 0.5 if consec >= 2 else 1.0
        bars = lm5(code).get(d1, [])
        sp = sell_5m(bars, bp, r1[4])
        ret = trade(bp, sp, asset, factor)
        if ret is None: continue
        cny_profit = (asset * factor) * ret / 100
        asset += cny_profit
        monthly[d1[:6]].append(ret)
        if ret < -5: consec += 1
        elif ret > 5: consec = 0
    n = asset / INIT
    wr = sum(1 for m in monthly.values() if sum(m) > 0) / len(monthly) * 100
    r5m.append({'seed': seed, 'asset': asset, 'nav': n, 'wr': wr, 'monthly': monthly, 'skips': skips})

assets5 = [r['asset'] for r in r5m]; navs5 = [r['nav'] for r in r5m]
print(f'  均值: ¥{np.mean(assets5):,.0f}  净值{np.mean(navs5):.2f}  +{(np.mean(navs5)-1)*100:+.1f}%')
print(f'  最佳: ¥{max(assets5):,.0f}  净值{max(navs5):.2f}  +{(max(navs5)-1)*100:+.1f}%')
print(f'  最差: ¥{min(assets5):,.0f}  净值{min(navs5):.2f}  +{(min(navs5)-1)*100:+.1f}%')
for r in r5m:
    print(f'  seed={r["seed"]}: ¥{r["asset"]:,.0f}  {r["nav"]:.2f}  盈利月{r["wr"]:.0f}%  跳过{r["skips"]}天')

print('\n=== 对比 ===')
print(f'  1D止损优先均值: {np.mean(navs):.2f}')
print(f'  5M逐根均值:     {np.mean(navs5):.2f}')
print(f'  差异: {(np.mean(navs5)/np.mean(navs)-1)*100:+.1f}%')

# 月度明细 (seed=0, 复利计算)
print('\n=== 月度明细 (5M, seed=0) ===')
print(f'{"月份":>8} {"笔数":>4} {"月收益":>12} {"月复利":>8} {"胜率":>5}')
print('-'*42)
m5 = r5m[0]['monthly']
for m in sorted(m5.keys()):
    rets = m5[m]; cnt = len(rets)
    compound = 1.0
    for r in rets: compound *= (1 + r/100)
    compound = (compound - 1) * 100
    total_ret = sum(rets)
    wr = sum(1 for r in rets if r > 0) / cnt * 100
    print(f'{m:>8} {cnt:>4} {total_ret:>+10.1f}% {compound:>+7.1f}% {wr:>4.0f}%')
