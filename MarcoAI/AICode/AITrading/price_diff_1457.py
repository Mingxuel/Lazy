"""分析14:55-14:57价格 vs 收盘价的差异"""
import os, numpy as np
from collections import defaultdict

M5DIR = r'C:\Lazy\MarcoAI\AIData\5M'
SRC = r'C:\Lazy\李明学的大A\Data\Strategy'

all_trades = []
for fn in sorted(os.listdir(SRC)):
    if not fn.isdigit(): continue
    d1 = fn
    with open(os.path.join(SRC, fn)) as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<2: continue
            all_trades.append((p[1], d1))

print(f'总策略样本: {len(all_trades)}')

diffs_pct = []
valid = 0; no_5m = 0; too_few = 0
diffs_by_stock = []

for code, d1 in all_trades:
    fp = os.path.join(M5DIR, code)
    if not os.path.exists(fp):
        no_5m += 1
        continue

    by_date = defaultdict(list)
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<6: continue
            d=p[0][:10].replace('-','')
            by_date[d].append((float(p[2]),float(p[3]),float(p[4])))

    all_dates = sorted(by_date.keys())
    if d1 not in all_dates: continue
    idx = all_dates.index(d1)
    if idx == 0: continue

    d2 = all_dates[idx-1]
    bars = by_date[d2]
    if len(bars) < 2:
        too_few += 1
        continue

    c_55 = bars[-2][2]     # 14:50-14:55 K线收盘价
    c_close = bars[-1][2]  # 14:55-15:00 K线收盘价=最终收盘价

    if c_55 > 0 and c_close > 0:
        diff = (c_close - c_55) / c_55 * 100
        diffs_pct.append(diff)
        diffs_by_stock.append((diff, code, d1))
        valid += 1

diffs = np.array(diffs_pct)
print(f'有5M且可分析: {valid} | 无5M: {no_5m} | bar不足: {too_few}')
print()

print(f'14:55价 → 收盘价 百分比差异:')
print(f'  均值:   {np.mean(diffs):+.4f}%')
print(f'  中位数: {np.median(diffs):+.4f}%')
print(f'  标准差: {np.std(diffs):.4f}%')
print(f'  P5:  {np.percentile(diffs,5):+.4f}%')
print(f'  P25: {np.percentile(diffs,25):+.4f}%')
print(f'  P75: {np.percentile(diffs,75):+.4f}%')
print(f'  P95: {np.percentile(diffs,95):+.4f}%')
print(f'  最小: {np.min(diffs):+.4f}%')
print(f'  最大: {np.max(diffs):+.4f}%')

print()
print('差异绝对值分布:')
abs_diffs = np.abs(diffs)
for th in [0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.0]:
    cnt = (abs_diffs < th).sum()
    pct = cnt/len(diffs)*100
    print(f'  |diff|<{th:5.2f}%: {cnt:>4}/{len(diffs)} ({pct:5.1f}%)')

# 极端样本
print()
print('偏差>0.3%的极端样本(前15):')
extreme = [(d, c, d1) for d, c, d1 in diffs_by_stock if abs(d) > 0.3]
extreme.sort(key=lambda x: -abs(x[0]))
for d, code, d1 in extreme[:15]:
    print(f'  {d:+.3f}% {code} 日期{d1}')

# 对评分的影响估算
print()
print('=== 对评分的影响分析 ===')
print('假设 bid=ask=lastPrice, 14:57价偏移对pb_depth的影响:')
print(f'  pb_depth = (昨收 - 现价) / 昨收')
print(f'  如果昨收=100, 14:57价=99 → pb=+1.0%')
print(f'  如果收盘价偏移 +0.5%(→99.5) → pb=+0.5%')
print(f'  单特征贡献差 = (+1.0-pb_mu)/pb_sg × pb_w − (+0.5-pb_mu)/pb_sg × pb_w')
print(f'             = 0.5 / 5.0 × 0.97 = 0.10 分/(0.5%价格偏移)')
print(f'  中位数偏移{np.median(diffs):+.3f}% → 评分偏差约 {abs(np.median(diffs))/5.0*0.97:.4f} 分')
print(f'  P95偏移{np.percentile(diffs,95):+.3f}% → 评分偏差约 {abs(np.percentile(diffs,95))/5.0*0.97:.4f} 分')
