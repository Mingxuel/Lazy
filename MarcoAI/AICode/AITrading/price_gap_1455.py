"""14:55价 vs 收盘价 差距分布 — 策略股实盘数据"""
import os, numpy as np
from collections import defaultdict

M5=r'C:\Lazy\MarcoAI\AIData\5M'
S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'

# 收集所有策略中出现过的股票+日期
all_trades=[]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)>=2:all_trades.append((p[1],fn))

# 对每个trade, 找D-2的5M数据
diffs_pct=[]
diffs_abs=[]
valid=0;no_5m=0
by_date=defaultdict(list)

for code,d1_date in all_trades:
    fp=os.path.join(M5,code)
    if not os.path.exists(fp):no_5m+=1;continue
    
    bd=defaultdict(list)
    with open(fp) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','')
            bd[d].append((float(p[2]),float(p[3]),float(p[4])))
    bd=dict(bd)
    
    # 找D-2: 紧挨d1之前的日期
    dates=sorted(bd.keys())
    if d1_date not in dates:continue
    idx=dates.index(d1_date)
    if idx==0:continue
    d2=dates[idx-1]
    bars=bd[d2]
    if len(bars)<2:continue
    
    c_1455=bars[-2][2]  # 倒数第2根 close
    c_close=bars[-1][2] # 最后一根 close
    h_1455=max(b[0] for b in bars[:-1])
    h_close=max(b[0] for b in bars)
    l_1455=min(b[1] for b in bars[:-1])
    l_close=min(b[1] for b in bars)
    
    if c_1455>0 and c_close>0:
        diff_pct=(c_close-c_1455)/c_1455*100
        diff_abs=c_close-c_1455
        diffs_pct.append(diff_pct)
        diffs_abs.append(diff_abs)
        valid+=1
        by_date[d2[:6]].append(diff_pct)

diffs_pct=np.array(diffs_pct)
diffs_abs=np.array(diffs_abs)

print(f'总样本: {len(all_trades)}  5M覆盖: {valid}  缺失: {no_5m}')
print()
print('=== 14:55→收盘 价格差异 ===')
print(f'  均值: {np.mean(diffs_pct):+.3f}%  ({np.mean(np.abs(diffs_abs)):.3f}元)')
print(f'  中位数: {np.median(diffs_pct):+.3f}%')
print(f'  标准差: {np.std(diffs_pct):.3f}%')
print()
print(f'  P1:  {np.percentile(diffs_pct,1):+.3f}%')
print(f'  P5:  {np.percentile(diffs_pct,5):+.3f}%')
print(f'  P10: {np.percentile(diffs_pct,10):+.3f}%')
print(f'  P25: {np.percentile(diffs_pct,25):+.3f}%')
print(f'  P50: {np.median(diffs_pct):+.3f}%')
print(f'  P75: {np.percentile(diffs_pct,75):+.3f}%')
print(f'  P90: {np.percentile(diffs_pct,90):+.3f}%')
print(f'  P95: {np.percentile(diffs_pct,95):+.3f}%')
print(f'  P99: {np.percentile(diffs_pct,99):+.3f}%')
print()

# 按绝对值分桶
print('=== 绝对值分布 ===')
for th in [0.01,0.02,0.05,0.10,0.20,0.30,0.50,1.0]:
    cnt=(np.abs(diffs_pct)<th).sum()
    print(f'  |diff|<{th:.2f}%: {cnt}/{len(diffs_pct)} ({cnt/len(diffs_pct)*100:.1f}%)')

# 方向
pos=(diffs_pct>0.01).sum()
neg=(diffs_pct<-0.01).sum()
flat=((np.abs(diffs_pct)<=0.01)).sum()
print(f'\n  尾盘拉(>0.01%): {pos} ({pos/len(diffs_pct)*100:.1f}%)')
print(f'  尾盘砸(<-0.01%): {neg} ({neg/len(diffs_pct)*100:.1f}%)')
print(f'  平盘(±0.01%): {flat} ({flat/len(diffs_pct)*100:.1f}%)')

# 极端案例
print()
print('=== 极端案例 (|diff|>1%) ===')
extreme=[(d,c,d1) for d,c,d1 in zip(diffs_pct,
    [c for c,_ in [all_trades[i] for i in range(len(diffs_pct))]],
    [d for _,d in [all_trades[i] for i in range(len(diffs_pct))]]) if abs(d)>1]
extreme.sort(key=lambda x:-abs(x[0]))
for d,code,d1 in extreme[:15]:
    print(f'  {d:+.2f}% {code} {d1}')
