# -*- coding: utf-8 -*-
"""实测尾盘集合竞价量占比: 5M数据最后一根K线量 / 全天量"""
import os, numpy as np
from collections import defaultdict

M5DIR = r'C:\Lazy\MarcoAI\AIData\5M'
SRC   = r'C:\Lazy\李明学的大A\Data\Strategy'

# ── 从Strategy文件收集所有出现过的股票 ──
all_codes = set()
for fn in sorted(os.listdir(SRC)):
    if not fn.isdigit(): continue
    with open(os.path.join(SRC, fn)) as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p) >= 2: all_codes.add(p[1])

print(f'策略候选股: {len(all_codes)} 只')

# ── 逐只扫5M数据, 统计尾盘占比 ──
tail_ratios = []   # 每只股票的每个交易日一个样本
stock_stats = {}
zero_samples = 0

for code in sorted(all_codes):
    fp = os.path.join(M5DIR, code)
    if not os.path.exists(fp): continue

    by_date = defaultdict(list)
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p) < 6: continue
            d = p[0][:10].replace('-', '')
            vol = float(p[5])  # 成交量(手)
            by_date[d].append((p[0], vol))

    if len(by_date) < 20: continue  # 至少20个交易日

    stock_ratios = []
    for d, bars in by_date.items():
        if len(bars) < 48: continue  # 全天48根5M K线
        total_vol_day = sum(b[1] for b in bars)
        if total_vol_day <= 0: continue
        last_bar_vol = bars[-1][1]  # 最后一根 K 线 (14:55-15:00)
        ratio = last_bar_vol / total_vol_day * 100
        if ratio > 20:  # 极端值(涨停封板日)过滤
            continue
        stock_ratios.append(ratio)
        tail_ratios.append(ratio)

    if stock_ratios:
        stock_stats[code] = (np.mean(stock_ratios), np.median(stock_ratios),
                            np.std(stock_ratios), len(stock_ratios))

tail_ratios = np.array(tail_ratios)
print(f'有效 5M 数据: {len(tail_ratios)} 个交易日')
print(f'涉及股票: {len(stock_stats)} 只')

print(f'\n{"="*60}')
print('尾盘集合竞价量占比 (最后一根5M K线 / 全天量)')
print(f'{"="*60}')
pcts = [1, 5, 10, 25, 50, 75, 90, 95, 99]
print(f'{"分位":>6}  {"占比%":>8}')
print('-' * 18)
for p in pcts:
    v = np.percentile(tail_ratios, p)
    print(f'  P{p:>2}   {v:>8.3f}%')

print(f'\n  均值:  {np.mean(tail_ratios):.3f}%')
print(f'  中位数: {np.median(tail_ratios):.3f}%')
print(f'  标准差: {np.std(tail_ratios):.3f}%')

# ── 分布 ──
print(f'\n{"="*60}')
print('占比分布')
print(f'{"="*60}')
bins=[0,1,2,3,4,5,7,10,100]
for lo,hi in zip(bins[:-1],bins[1:]):
    cnt=np.sum((tail_ratios>=lo)&(tail_ratios<hi))
    pct=cnt/len(tail_ratios)*100
    bar='#'*int(pct)
    print(f'  [{lo}%~{hi}%): {cnt:>6} ({pct:>5.1f}%) {bar}')

# ── 极值排除后的稳健估计 ──
print(f'\n{"="*60}')
print('排除 >10% 极端值后 (涨停封板日):')
trimmed=tail_ratios[tail_ratios<=10]
print(f'  样本: {len(trimmed)} ({len(trimmed)/len(tail_ratios)*100:.1f}%)')
print(f'  均值: {np.mean(trimmed):.3f}%')
print(f'  中位数: {np.median(trimmed):.3f}%')
print(f'  P90: {np.percentile(trimmed,90):.3f}%')

# ── 排除 >5% 极端值 ──
print(f'\n排除 >5% 极端值后:')
trimmed2=tail_ratios[tail_ratios<=5]
print(f'  样本: {len(trimmed2)} ({len(trimmed2)/len(tail_ratios)*100:.1f}%)')
print(f'  均值: {np.mean(trimmed2):.3f}%')
print(f'  P90: {np.percentile(trimmed2,90):.3f}%')

# ── 建议系数 ──
print(f'\n{"="*60}')
print('建议回测系数:')
for coef in [0.97, 0.975, 0.98, 0.985]:
    tail_implied = (1 - coef) * 100
    print(f'  ×{coef} => 模拟尾盘{tail_implied:.1f}%')
print(f'\n  实测中位数 {np.median(tail_ratios):.2f}% => 系数 ×{1-np.median(tail_ratios)/100:.4f}')
