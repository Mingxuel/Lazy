"""
全面验证 5M 数据与 1D 数据一致性
检查所有 TPO3 候选涉及的全部日期：
- D-4 (涨停日): 5M bars
- D-2 (回踩日): 5M bars (尾盘价用于 pb_depth)
- D-1 (卖出日): 5M bars
"""
import os
from collections import defaultdict

M5DIR = r'C:\Lazy\MarcoAI\AIData\5M'
K = r'C:\Lazy\李明学的大A\Data\1D'
S = r'C:\Lazy\李明学的大A\Data\Strategy'

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
def load_5m(code):
    if code in _5m: return _5m[code]
    fp = os.path.join(M5DIR, code)
    if not os.path.exists(fp):
        _5m[code] = {}
        return {}
    bd = defaultdict(list)
    with open(fp) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) < 6: continue
            d = p[0][:10].replace('-', '')
            bd[d].append((float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    _5m[code] = dict(bd)
    return _5m[code]

tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:
        l = l.strip()
        if l and l.isdigit() and len(l) == 8:
            tds.append(l)
tds = sorted(tds)
di = {d: i for i, d in enumerate(tds)}

print("=" * 80)
print("5M 与 1D 数据一致性全面验证")
print("=" * 80)

# 收集所有需要检查的 (stock, date) 对
# 以及它们在 1D 中的 OHLC
checks = []
seen = set()

for fn in sorted(os.listdir(S)):
    if not fn.isdigit(): continue
    d1 = fn
    d1i = di.get(d1)
    if d1i is None or d1i < 4: continue
    d2 = tds[d1i - 1]
    d3 = tds[d1i - 2]
    d4 = tds[d1i - 3]

    with open(os.path.join(S, fn)) as f:
        for l in f:
            l = l.strip()
            p = l.split('|')
            if len(p) < 2: continue
            code = p[1]

            rs, dx = lk(code)
            for check_date, label in [(d4, 'D-4'), (d2, 'D-2'), (d1, 'D-1')]:
                key = (code, check_date)
                if key in seen: continue
                seen.add(key)
                k_idx = dx.get(check_date)
                if k_idx is not None:
                    r = rs[k_idx]
                    checks.append({
                        'code': code, 'date': check_date, 'label': label,
                        'o1': r[1], 'h1': r[2], 'l1': r[3], 'c1': r[4]
                    })

print(f"需要校验的 (股票, 日期) 对: {len(checks)}")
print(f"涉及唯一股票: {len(set(c['code'] for c in checks))}")
print()

# ===== 检查1: 5M 文件是否存在 =====
missing_file = [c for c in checks if not load_5m(c['code'])]
print(f"1. 5M文件缺失: {len(missing_file)} 个 ({len(missing_file)/len(checks)*100:.1f}%)")
if missing_file:
    for c in missing_file[:10]:
        print(f"   {c['code']}: {c['date']} ({c['label']})")
    if len(missing_file) > 10:
        print(f"   ... 还有 {len(missing_file)-10} 个")

# ===== 检查2: 5M 文件有但日期数据缺失 =====
missing_date = []
for c in checks:
    bars = load_5m(c['code']).get(c['date'])
    if bars is None:
        missing_date.append(c)

print(f"\n2. 5M日期数据缺失: {len(missing_date)} 个 ({len(missing_date)/len(checks)*100:.1f}%)")
if missing_date:
    # 按年份统计
    yr = defaultdict(int)
    for c in missing_date:
        yr[c['date'][:4]] += 1
    for y in sorted(yr):
        print(f"   {y}: {yr[y]}个")

# ===== 检查3: 有5M数据, 比对首bar开盘 vs 1D开盘 =====
with_data = [c for c in checks if load_5m(c['code']).get(c['date'])]

# 首bar开盘偏差
open_bad = []
open_ok = []
for c in with_data:
    bars = load_5m(c['code'])[c['date']]
    o5 = bars[0][0]
    o1 = c['o1']
    if o1 <= 0: continue
    ratio = o5 / o1
    if ratio < 0.98 or ratio > 1.02:
        open_bad.append((c, o5, o1, ratio))
    else:
        open_ok.append((c, o5, o1, ratio))

print(f"\n3. 首bar开盘偏差检查 (阈值 ±2%):")
print(f"   正常: {len(open_ok)} 个")
print(f"   异常: {len(open_bad)} 个 ({len(open_bad)/max(len(with_data),1)*100:.1f}%)")

if open_bad:
    print(f"\n   异常明细 (共{len(open_bad)}个):")
    # 按ratio分组
    for c, o5, o1, ratio in sorted(open_bad, key=lambda x: x[3]):
        bars = load_5m(c['code'])[c['date']]
        is_sell = (c['label'] == 'D-1')
        marker = "← 卖出日!" if is_sell else ""
        print(f"   {c['date']} {c['code']}({c['label']}) "
              f"1D开{o1:.2f} 5M首{o5:.2f} 比{ratio:.3f} bars={len(bars)} {marker}")

# ===== 检查4: 末bar收盘偏差 =====
close_bad = []
close_ok = []
for c in with_data:
    bars = load_5m(c['code'])[c['date']]
    c5 = bars[-1][3]
    c1 = c['c1']
    if c1 <= 0: continue
    ratio = c5 / c1
    if ratio < 0.98 or ratio > 1.02:
        close_bad.append((c, c5, c1, ratio))
    else:
        close_ok.append((c, c5, c1, ratio))

print(f"\n4. 末bar收盘偏差检查 (阈值 ±2%):")
print(f"   正常: {len(close_ok)} 个")
print(f"   异常: {len(close_bad)} 个 ({len(close_bad)/max(len(with_data),1)*100:.1f}%)")

if close_bad:
    print(f"\n   异常明细 (共{len(close_bad)}个):")
    for c, c5, c1, ratio in sorted(close_bad, key=lambda x: x[3]):
        bars = load_5m(c['code'])[c['date']]
        is_sell = (c['label'] == 'D-1')
        marker = "← 卖出日!" if is_sell else ""
        print(f"   {c['date']} {c['code']}({c['label']}) "
              f"1D收{c1:.2f} 5M收{c5:.2f} 比{ratio:.3f} bars={len(bars)} {marker}")

# ===== 检查5: 所有5M日期偏差的分位分布 =====
all_ratios = []
for c in with_data:
    bars = load_5m(c['code'])[c['date']]
    c5 = bars[-1][3]
    c1 = c['c1']
    o5 = bars[0][0]
    o1 = c['o1']
    if c1 > 0:
        all_ratios.append(('close', c5 / c1))
    if o1 > 0:
        all_ratios.append(('open', o5 / o1))

import numpy as np
close_ratios = sorted([r for t, r in all_ratios if t == 'close'])
open_ratios = sorted([r for t, r in all_ratios if t == 'open'])

print(f"\n5. 收盘价比值分位分布 (n={len(close_ratios)}):")
for pct in [0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100]:
    idx = int(len(close_ratios) * pct / 100)
    idx = min(idx, len(close_ratios) - 1)
    print(f"   P{pct:>3}: {close_ratios[idx]:.4f}")

print(f"\n6. 开盘价比值分位分布 (n={len(open_ratios)}):")
for pct in [0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100]:
    idx = int(len(open_ratios) * pct / 100)
    idx = min(idx, len(open_ratios) - 1)
    print(f"   P{pct:>3}: {open_ratios[idx]:.4f}")

# ===== 检查6: 按年份/标签统计异常 =====
print(f"\n7. 收盘异常按年份+标签:")
bad_by = defaultdict(list)
for c, c5, c1, ratio in close_bad:
    yr = c['date'][:4]
    bad_by[f"{yr}-{c['label']}"].append(ratio)
for k in sorted(bad_by):
    print(f"   {k}: {len(bad_by[k])}个")

# ===== 检查7: 5M bars数量分布 =====
bar_cnt = defaultdict(int)
for c in with_data:
    bars = load_5m(c['code'])[c['date']]
    bar_cnt[len(bars)] += 1

print(f"\n8. 5M bars数量分布:")
for k in sorted(bar_cnt):
    print(f"   {k}根: {bar_cnt[k]}个 ({bar_cnt[k]/len(with_data)*100:.1f}%)")

# ===== 总结 =====
print(f"\n{'='*80}")
print(f"总结")
print(f"{'='*80}")
total = len(checks)
has_5m_file = total - len(missing_file)
has_5m_date = has_5m_file - len(missing_date)
close_good = len(close_ok)
close_bad_n = len(close_bad)

print(f"  总检查: {total}")
print(f"    ├─ 5M文件缺失: {len(missing_file)} ({len(missing_file)/total*100:.1f}%)")
print(f"    ├─ 5M日期缺失: {len(missing_date)} ({len(missing_date)/total*100:.1f}%)")
print(f"    ├─ 5M收盘一致(<2%): {close_good} ({close_good/total*100:.1f}%)")
print(f"    └─ 5M收盘异常(>2%): {close_bad_n} ({close_bad_n/total*100:.1f}%)")

# 特别关注卖出日(D-1)的异常
sell_bad = [(c, r) for c, _, _, r in close_bad if c['label'] == 'D-1']
print(f"\n  其中 卖出日(D-1) 收盘异常: {len(sell_bad)} 个")
print(f"  如果不做校验, 这{len(sell_bad)}笔的5M卖出会有假止损/假信号")

print(f"\n  建议: 末bar收盘 vs 1D收盘 偏差>2% → 回退1D OHLC (已实施)")
print(f"  覆盖率: {close_good/total*100:.1f}% 用5M, {len(missing_file)/total*100:.1f}%无文件+{len(missing_date)/total*100:.1f}%无日期+{close_bad_n/total*100:.1f}%异常→回退1D")
print(f"\n验证完成 ✓")
