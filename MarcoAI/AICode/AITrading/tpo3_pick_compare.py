"""TPO3池子内: 多种选股策略对比, 5M逐根卖出"""
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
    return (sa - cs - st - tf - b - cb) / (b + cb) * 100

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

# 收集每天候选 + D-2特征
daily_cands = defaultdict(list)  # d1 -> [(code, name, pb_depth, d2_vol, d2_chg, ...)]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit() or fn < '20250101': continue
    d1 = fn; d1i = di.get(d1)
    if d1i is None or d1i < 4: continue
    d2 = tds[d1i-1]; d3 = tds[d1i-2]
    with open(os.path.join(S, fn)) as f:
        for l in f:
            l = l.strip(); p = l.split('|')
            if len(p) < 2: continue
            code, name = p[1], p[0]
            rs, dx = lk(code); d2k = dx.get(d2); d1k = dx.get(d1)
            if d2k is None or d1k is None: continue
            r2 = rs[d2k]; r3 = rs[d2k-1] if d2k >= 1 else None
            if r3 is None: continue
            r1 = rs[d1k]; bp = r1[6]
            if bp <= 0 or r3[4] <= 0: continue
            # pb_depth: D-3收盘 vs D-2 14:55尾盘
            d2_bars = lm5(code).get(d2, [])
            if len(d2_bars) >= 2:
                tail_price = d2_bars[-2][3]  # 倒数第2根 = 14:55
            else:
                tail_price = r2[4]  # fallback: D-2收盘
            pb_depth = (r3[4] - tail_price) / r3[4] * 100
            d2_vol = r2[5]  # D-2成交量
            d3_vol = r3[5]  # D-3成交量
            d2_day_chg = (r2[4] - r2[6]) / r2[6] * 100  # D-2当日涨跌幅
            daily_cands[d1].append((code, name, pb_depth, d2_vol, d3_vol, d2_day_chg, bp))

days = sorted(daily_cands.keys())
total_cands = sum(len(v) for v in daily_cands.values())
print(f'TPO3池: {len(days)}天, {total_cands}只, 日均{total_cands/len(days):.1f}只')
print()

# === 策略定义 ===
strategies = {}

# 1. 随机
def pick_random(cands):
    return random.choice(cands)
strategies['随机(基准)'] = pick_random

# 2. pb_depth最大(跌最深)
def pick_deepest(cands):
    return max(cands, key=lambda c: c[2])
strategies['pb_depth最大'] = pick_deepest

# 3. pb_depth 2-5%内选最大
def pick_2to5(cands):
    in_range = [c for c in cands if 2 <= c[2] <= 5]
    if in_range: return max(in_range, key=lambda c: c[2])
    return max(cands, key=lambda c: c[2])  # fallback: 最深
strategies['pb_depth 2-5%'] = pick_2to5

# 4. pb_depth > 0 (只买跌的), WF选最深
def pick_falling(cands):
    falling = [c for c in cands if c[2] > 0]
    if falling: return max(falling, key=lambda c: c[2])
    return max(cands, key=lambda c: c[2])
strategies['pb_depth>0选最深'] = pick_falling

# 5. 只买pb_depth>0的, 否则跳过
def pick_falling_skip(cands):
    falling = [c for c in cands if c[2] > 0]
    if not falling: return None
    return max(falling, key=lambda c: c[2])
strategies['pb_depth>0/否则跳过'] = pick_falling_skip

# 6. D-2缩量最狠的 (vol最小)
def pick_lowest_vol(cands):
    return min(cands, key=lambda c: c[3])
strategies['D-2量最小'] = pick_lowest_vol

# 7. pb_depth>0内选D-2量最小的
def pick_falling_lowvol(cands):
    falling = [c for c in cands if c[2] > 0]
    if falling: return min(falling, key=lambda c: c[3])
    return min(cands, key=lambda c: c[3])
strategies['跌中选量最小'] = pick_falling_lowvol

# 8. 跌中选pb_depth最大且量最小的 (排序: pb_depth/vol)
def pick_deep_thin(cands):
    falling = [c for c in cands if c[2] > 0]
    if falling: return max(falling, key=lambda c: c[2] / (c[3] + 1))
    return max(cands, key=lambda c: c[2] / (c[3] + 1))
strategies['跌深+量缩比'] = pick_deep_thin

# 9. 避开pb_depth<0: 有跌的随机挑, 全涨则跳过
def avoid_rising_skip(cands):
    falling = [c for c in cands if c[2] > 0]
    if not falling: return None
    return random.choice(falling)
strategies['有跌随机/全涨跳过'] = avoid_rising_skip

# 10. 避开pb_depth<0, 否则随机
def avoid_rising_fallback(cands):
    falling = [c for c in cands if c[2] > 0]
    if falling: return random.choice(falling)
    return random.choice(cands)
strategies['有跌随机/全涨随机'] = avoid_rising_fallback

# 11. 极端缩量内随机
def avoid_not_thin(cands):
    thin = [c for c in cands if c[3] < c[4] * 0.5]
    if not thin: return None
    return random.choice(thin)
strategies['极端缩量随机'] = avoid_not_thin

# 12. 跌+缩量内随机
def avoid_rising_not_thin(cands):
    good = [c for c in cands if c[2] > 0 and c[3] < c[4] * 0.8]
    if not good: return None
    return random.choice(good)
strategies['跌+缩量随机'] = avoid_rising_not_thin

# === 回测 ===
for sname, pick_fn in strategies.items():
    is_random_based = '随机' in sname
    n_runs = 10 if is_random_based else 1
    navs = []
    for run_i in range(n_runs):
        random.seed(run_i)
        asset = INIT; trades = 0; skips = 0
        monthly = defaultdict(list)
        for d1 in days:
            cands = daily_cands[d1]
            picked = pick_fn(cands)
            if picked is None: skips += 1; continue
            code, name, pb, d2v, d3v, chg, bp = picked
            rs, dx = lk(code); d1k = dx.get(d1)
            if d1k is None: continue
            r1 = rs[d1k]
            bars = lm5(code).get(d1, [])
            sp = sell_5m(bars, bp, r1[4])
            ret = trade(bp, sp, asset)
            if ret is None: continue
            asset += asset * ret / 100; trades += 1
            monthly[d1[:6]].append(ret)
        navs.append(asset / INIT)
    nav_mean = np.mean(navs)
    nav_str = f'{nav_mean:.2f}'
    if n_runs > 1:
        nav_str += f' (最佳{max(navs):.2f}/最差{min(navs):.2f})'
    wr = sum(1 for m in monthly.values() if sum(m) > 0) / len(monthly) * 100 if n_runs == 1 else '-'
    print(f'{sname:<20} 净值{nav_str:<20} {trades}笔 跳过{skips}天')
