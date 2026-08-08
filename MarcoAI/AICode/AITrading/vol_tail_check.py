# -*- coding: utf-8 -*-
"""vol_contract 尾盘量偏差: D-2量×1.0 vs ×0.97"""
import os, numpy as np
from collections import defaultdict

KDIR = r'C:\Lazy\李明学的大A\Data\1D'
SRC  = r'C:\Lazy\李明学的大A\Data\Strategy'

tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds = sorted(tds); di = {d:i for i,d in enumerate(tds)}

def load_kline(code):
    fp = os.path.join(KDIR, code)
    rows = []; idx = {}
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'): continue
            c=l.split()
            if len(c) < 10 or not c[0].isdigit(): continue
            idx[c[0]] = len(rows)
            rows.append((c[0], float(c[1]), float(c[2]), float(c[3]),
                        float(c[4]), float(c[5]), float(c[9])))
    return rows, idx

samples_1p0 = []; samples_097 = []; meta = []
for fn in sorted(os.listdir(SRC)):
    if not fn.isdigit(): continue
    d1 = fn; d1i = di.get(d1)
    if d1i is None or d1i < 3: continue
    d2 = tds[d1i - 1]
    with open(os.path.join(SRC, fn)) as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p) < 2: continue
            name,code = p[0],p[1]
            rows,date_idx = load_kline(code)
            d2i_k = date_idx.get(d2)
            if d2i_k is None or d2i_k < 1: continue
            r2=rows[d2i_k]; r3=rows[d2i_k-1]
            v2f=r2[5]; v3=r3[5]
            if v3<=0: continue
            vc_full=(v3-v2f)/v3*100
            vc_adj=(v3-v2f*0.97)/v3*100
            samples_1p0.append(vc_full); samples_097.append(vc_adj)
            meta.append((code,name,d1,vc_full,vc_adj,v2f,v3))

print(f'总样本: {len(samples_1p0)}')
print(f'\n{"="*70}')
print(f'{"指标":<20} {"vc(x1.0)":>15} {"vc(x0.97)":>15} {"差值":>10}')
print('-'*60)
print(f'{"均值":<20} {np.mean(samples_1p0):>+15.2f}% {np.mean(samples_097):>+15.2f}% {np.mean(samples_097)-np.mean(samples_1p0):>+10.2f}%')
print(f'{"中位数":<20} {np.median(samples_1p0):>+15.2f}% {np.median(samples_097):>+15.2f}% {np.median(samples_097)-np.median(samples_1p0):>+10.2f}%')
print(f'{"标准差":<20} {np.std(samples_1p0):>15.2f}  {np.std(samples_097):>15.2f}')
print(f'{"最小值":<20} {np.min(samples_1p0):>+15.2f}% {np.min(samples_097):>+15.2f}%')
print(f'{"最大值":<20} {np.max(samples_1p0):>+15.2f}% {np.max(samples_097):>+15.2f}%')

# ── 符号反转 ──
reversals = []
for i in range(len(samples_1p0)):
    v1=samples_1p0[i]; v2=samples_097[i]
    if (v1>0 and v2<0) or (v1<0 and v2>0):
        code,name,d1,vc_full,vc_adj,v2f,v3 = meta[i]
        reversals.append((code,name,d1,v1,v2,v2f,v3))

print(f'\n{"="*80}')
print(f'符号反转 (vc_full正->vc_adj负, 或反之): {len(reversals)}/{len(samples_1p0)} ({len(reversals)/len(samples_1p0)*100:.2f}%)')
if reversals:
    print(f'{"代码":<14} {"名称":<8} {"日期":<10} {"vcx1.0":>8} {"vcx0.97":>8} {"D-2量":>10} {"D-3量":>10} {"方向"}')
    for code,name,d1,v1,v2,v2f,v3 in sorted(reversals, key=lambda x: abs(x[3]-x[4]))[:20]:
        d='缩->放' if v1>0 else '放->缩'
        print(f'  {code:<14} {name:<8} {d1:<10} {v1:>+8.2f}% {v2:>+8.2f}% {v2f:>10.0f} {v3:>10.0f} {d}')

# ── 差值分布 ──
diffs = np.abs(np.array(samples_097) - np.array(samples_1p0))
print(f'\n{"="*60}')
print('|vc_adj - vc_full| 分布')
bins=[0,0.1,0.5,1.0,2.0,5.0,100]
for lo,hi in zip(bins[:-1],bins[1:]):
    cnt=np.sum((diffs>=lo)&(diffs<hi))
    pct=cnt/len(diffs)*100
    print(f'  [{lo:>4.1f}~{hi:>4.1f}%): {cnt:>5} ({pct:>5.1f}%)')

# ── 每日排名影响 ──
print(f'\n{"="*80}')
print('每日vol_contract排名变化')
daily_meta=defaultdict(list)
for code,name,d1,vcf,vca,v2f,v3 in meta:
    daily_meta[d1].append((code,name,vcf,vca,v2f,v3))

rank_changes=0; total_days=0; details=[]
for d1 in sorted(daily_meta.keys()):
    items=daily_meta[d1]
    if len(items)<2: continue
    total_days+=1
    bf=sorted(items,key=lambda x:-x[2])
    ba=sorted(items,key=lambda x:-x[3])
    if any(bf[i][0]!=ba[i][0] for i in range(min(len(bf),len(ba)))):
        rank_changes+=1
        if len(details)<8: details.append((d1,bf,ba))

print(f'总天数(>=2候选): {total_days}')
print(f'vc排名变化: {rank_changes}天 ({rank_changes/total_days*100:.1f}%)')
for d1,bf,ba in details:
    print(f'\n  {d1}:')
    print(f'    x1.0: '+' > '.join(f'{n}({vc:+.1f})' for c,n,vc,_,_,_ in bf))
    print(f'    x0.97: '+' > '.join(f'{n}({vc:+.1f})' for _,n,_,vc,_,_ in ba))

# ── MU/SG ──
X1=np.array(samples_1p0); X2=np.array(samples_097)
mu1=np.mean(X1); sg1=np.std(X1); mu2=np.mean(X2); sg2=np.std(X2)
shift=(mu2-mu1)/sg1*100
print(f'\n标准化参数:')
print(f'  x1.0  MU={mu1:.2f}  SG={sg1:.2f}')
print(f'  x0.97 MU={mu2:.2f}  SG={sg2:.2f}')
print(f'  MU偏移 {shift:+.1f}% SG (SG差异 {(sg2/sg1-1)*100:+.1f}%)')
print(f'\n结论: 3%尾盘量使vc均值上移{mu2-mu1:.2f}pp, 仅占{abs(shift):.1f}%标准差 => {"可忽略" if abs(shift)<5 else "需关注"}')
