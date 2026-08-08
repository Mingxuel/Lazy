"""
分析 pb_depth(回踩深度) 与次日收益的关系，验证均值回归假设
"""
import os, numpy as np
from collections import defaultdict

S = r'C:\Lazy\李明学的大A\Data\Strategy'
K = r'C:\Lazy\李明学的大A\Data\1D'
M5DIR = r'C:\Lazy\MarcoAI\AIData\5M'


def lk(code):
    fp = os.path.join(K, code)
    rows = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('\ufeff'):
                continue
            c = l.split()
            if len(c) < 10 or not c[0].isdigit():
                continue
            rows.append((c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5]), float(c[9])))
    return rows, {r[0]: i for i, r in enumerate(rows)}


_5m = {}
def lm5(code):
    if code in _5m:
        return _5m[code]
    fp = os.path.join(M5DIR, code)
    if not os.path.exists(fp):
        _5m[code] = {}
        return {}
    bd = defaultdict(list)
    with open(fp) as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            p = l.split('|')
            if len(p) < 6:
                continue
            d = p[0][:10].replace('-', '')
            bd[d].append((float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    _5m[code] = dict(bd)
    return _5m[code]


def get_bar(code, d, o):
    bars = lm5(code).get(d, [])
    if len(bars) >= abs(o):
        return bars[o]
    return None


tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:
        l = l.strip()
        l and l.isdigit() and len(l) == 8 and tds.append(l)
tds = sorted(tds)
di = {d: i for i, d in enumerate(tds)}

# ===== 收集所有候选的 pb_depth 和 次日收益率 =====
all_candidates = []

for fn in sorted(os.listdir(S)):
    if not fn.isdigit():
        continue
    d1 = fn
    d1i = di.get(d1)
    if d1i is None or d1i < 4:
        continue
    d2 = tds[d1i - 1]
    d4 = tds[d1i - 3]

    with open(os.path.join(S, fn)) as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            p = l.split('|')
            if len(p) < 2:
                continue
            code = p[1]
            name = p[0]

            rs, dx = lk(code)
            d1k = dx.get(d1)
            d2k = dx.get(d2)
            d4k = dx.get(d4)
            if d1k is None or d2k is None:
                continue

            r1 = rs[d1k]
            r2 = rs[d2k]
            r3 = rs[d2k - 1] if d2k >= 1 else None
            if r3 is None:
                continue

            # D-4早封涨停标记
            d4_early = False
            bars_d4 = lm5(code).get(d4, [])
            if d4k is not None and d4k > 0 and len(bars_d4) >= 6:
                d4_lu = round(rs[d4k - 1][4] * 1.10, 2)
                for bi in range(min(6, len(bars_d4))):
                    if bars_d4[bi][2] >= d4_lu * 0.999:
                        d4_early = bi <= 5
                        break

            # pb_depth: D-3收盘 vs D-2 5M 14:55收盘价
            bar55 = get_bar(code, d2, -2)
            if bar55 is None:
                c5 = r2[4]  # fallback: 1D收盘
            else:
                c5 = bar55[3]

            bp = r1[6]  # D-1买入价 = preClose = D-2收盘价
            if bp <= 0 or r3[4] <= 0:
                continue

            pb_depth = (r3[4] - c5) / r3[4] * 100  # 正数=回踩，负数=上涨
            ret_next = (r1[4] - bp) / bp * 100  # 次日收益

            all_candidates.append({
                'name': name, 'code': code, 'date': d1,
                'pb_depth': pb_depth, 'ret_next': ret_next,
                'd4_early': d4_early,
            })

print(f"总候选样本: {len(all_candidates)}")

# ===== 1. 按 pb_depth 细粒度分段 =====
print("\n" + "=" * 70)
print("=== 回踩深度分段统计 (每0.5%一段) ===")
print(f"{'区间':>12} {'样本':>6} {'均收益':>8} {'胜率':>6} {'>2%':>6} {'<-2%':>6} {'<-6%':>6}")
print("-" * 70)

bins = []
step = 0.5
for lo in np.arange(-2, 10, step):
    hi = lo + step
    grp = [s for s in all_candidates if lo <= s['pb_depth'] < hi]
    if not grp:
        continue
    n = len(grp)
    avg = np.mean([s['ret_next'] for s in grp])
    wr = sum(1 for s in grp if s['ret_next'] > 0) / n * 100
    gt2 = sum(1 for s in grp if s['ret_next'] > 2) / n * 100
    lt2 = sum(1 for s in grp if s['ret_next'] < -2) / n * 100
    lt6 = sum(1 for s in grp if s['ret_next'] < -6) / n * 100
    bar = "█" * int(abs(avg) * 10)
    print(f"[{lo:5.1f}~{hi:5.1f}) {n:>5}  {avg:>+7.2f}%  {wr:>5.1f}%  {gt2:>5.1f}%  {lt2:>5.1f}%  {lt6:>5.1f}%  {bar}")
    bins.append((lo, hi, n, avg, wr))

# ===== 2. 大区间统计 (含D-4早封 vs 非早封拆分) =====
print("\n" + "=" * 70)
print("=== 大区间统计 (含早封分拆) ===")
print(f"{'区间':>15} {'全部':>10} {'早封':>10} {'非早封':>10} {'胜率差':>8}")
print("-" * 70)

for label, lo, hi in [
    ("回踩<1%", -10, 1),
    ("回踩1-2%", 1, 2),
    ("回踩2-3%", 2, 3),
    ("回踩3-4%", 3, 4),
    ("回踩4-5%", 4, 5),
    ("回踩5-7%", 5, 7),
    ("回踩>7%", 7, 20),
]:
    all_grp = [s for s in all_candidates if lo <= s['pb_depth'] < hi]
    early_grp = [s for s in all_grp if s['d4_early']]
    clean_grp = [s for s in all_grp if not s['d4_early']]

    all_avg = np.mean([s['ret_next'] for s in all_grp]) if all_grp else 0
    early_avg = np.mean([s['ret_next'] for s in early_grp]) if early_grp else 0
    clean_avg = np.mean([s['ret_next'] for s in clean_grp]) if clean_grp else 0
    clean_wr = sum(1 for s in clean_grp if s['ret_next'] > 0) / len(clean_grp) * 100 if clean_grp else 0

    print(f"{label:>15}  {all_avg:>+7.2f}%({len(all_grp):>3})  "
          f"{early_avg:>+7.2f}%({len(early_grp):>2})  "
          f"{clean_avg:>+7.2f}%({len(clean_grp):>3})  "
          f"WR{clean_wr:.0f}%")

# ===== 3. 混搭策略反事实分析 =====
print("\n" + "=" * 70)
print("=== 反事实: '没有3-5%就挑最深' 是否合理 ===")

# 场景: 当日TPO3所有候选回踩都<3%
shallow_days = defaultdict(list)
for s in all_candidates:
    shallow_days[s['date']].append(s)

# 找出所有候选回踩都在1-3%的天
mixed_days = []
for date, cands in shallow_days.items():
    max_depth = max(c['pb_depth'] for c in cands)
    deep_cands = [c for c in cands if 3 <= c['pb_depth'] <= 5]
    all_shallow = all(c['pb_depth'] < 3 for c in cands)
    if all_shallow:
        # 挑最深的
        deepest = max(cands, key=lambda c: c['pb_depth'])
        mixed_days.append({
            'date': date,
            'deepest_depth': deepest['pb_depth'],
            'deepest_ret': deepest['ret_next'],
            'name': deepest['name'],
            'n_cands': len(cands),
            'avg_ret': np.mean([c['ret_next'] for c in cands]),
            'max_ret': max(c['ret_next'] for c in cands),
            'min_ret': min(c['ret_next'] for c in cands),
        })

print(f"\n候选全部回踩<3%的天: {len(mixed_days)}天")
print(f"挑最深(均值): pb_depth={np.mean([d['deepest_depth'] for d in mixed_days]):.2f}%, "
      f"次日收益={np.mean([d['deepest_ret'] for d in mixed_days]):+.2f}%")
print(f"当天随机平均: {np.mean([d['avg_ret'] for d in mixed_days]):+.2f}%")
print(f"当天最佳: {np.mean([d['max_ret'] for d in mixed_days]):+.2f}%")

# 按回踩深浅再拆
for lo, hi, label in [(0, 1, "0-1%"), (1, 2, "1-2%"), (2, 3, "2-3%")]:
    sub = [d for d in mixed_days if lo <= d['deepest_depth'] < hi]
    if not sub:
        continue
    avg_ret = np.mean([d['deepest_ret'] for d in sub])
    wr = sum(1 for d in sub if d['deepest_ret'] > 0) / len(sub) * 100
    print(f"  最深在{label}: {len(sub)}天, 均{avg_ret:+.2f}%, 胜{wr:.0f}%")

# ===== 4. 核心问题: pb_depth vs ret_next 散点统计 =====
print("\n" + "=" * 70)
print("=== pb_depth vs ret_next 相关性 ===")
depths = np.array([s['pb_depth'] for s in all_candidates])
rets = np.array([s['ret_next'] for s in all_candidates])
# 只看非早封
clean = [s for s in all_candidates if not s['d4_early']]
depths_c = np.array([s['pb_depth'] for s in clean])
rets_c = np.array([s['ret_next'] for s in clean])

print(f"全样本 Pearson r = {np.corrcoef(depths, rets)[0, 1]:.4f}")
print(f"非早封 Pearson r = {np.corrcoef(depths_c, rets_c)[0, 1]:.4f}")

# 分段相关性
for lo, hi, label in [(0, 3, "回踩<3%"), (3, 5, "回踩3-5%"), (5, 10, "回踩>5%")]:
    seg = [s for s in clean if lo <= s['pb_depth'] < hi]
    if len(seg) < 20:
        continue
    d_seg = np.array([s['pb_depth'] for s in seg])
    r_seg = np.array([s['ret_next'] for s in seg])
    r_val = np.corrcoef(d_seg, r_seg)[0, 1] if len(seg) >= 3 else 0
    avg_r = np.mean(r_seg)
    print(f"  {label} ({len(seg)}笔): r={r_val:.3f}, 均收益={avg_r:+.2f}%")
