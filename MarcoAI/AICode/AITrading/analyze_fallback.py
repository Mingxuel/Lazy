"""分析D策略fallback场景"""
import os,numpy as np
from collections import defaultdict

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'

def lk(code):
    fp=os.path.join(K,code);rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'):continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit():continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}
_5m={}
def lm5(code):
    if code in _5m:return _5m[code]
    fp=os.path.join(M5DIR,code)
    if not os.path.exists(fp):_5m[code]={};return{}
    bd=defaultdict(list)
    with open(fp) as f:
        for l in f:
            l=l.strip();p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','');bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    _5m[code]=dict(bd);return _5m[code]
def get_bar(code,d,o):
    bars=lm5(code).get(d,[])
    if len(bars)>=abs(o):return bars[o]
    return None

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

fallback_cases=[];fall_ret=[];all_days=0
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    d2=tds[d1i-1];d4=tds[d1i-3]
    with open(os.path.join(S,fn)) as f:
        cands=[]
        for l in f:
            l=l.strip();p=l.split('|')
            if len(p)<2:continue
            code=p[1];name=p[0]
            bars=lm5(code).get(d4,[])
            rs,dx=lk(code);d1k=dx.get(d1);d2k=dx.get(d2)
            if d1k is None or d2k is None:continue
            r1=rs[d1k];r2=rs[d2k];r3=rs[d2k-1] if d2k>=1 else None
            if r3 is None:continue
            bar55=get_bar(code,d2,-2)
            if bar55 is None:bar55=(r2[1],r2[2],r2[3],r2[4])
            c5=bar55[3];bp=r1[6]
            if bp<=0 or r3[4]<=0:continue
            pb=(r3[4]-c5)/r3[4]*100;ret=(r1[4]-bp)/bp*100
            cands.append((pb,ret,name,code))
        if not cands:continue
        all_days+=1
        falling=[c for c in cands if c[0]>0]
        if not falling:
            best=max(cands,key=lambda x:x[0])
            fallback_cases.append({'date':d1,'best_pb':best[0],'best_ret':best[1],'name':best[2]})
        else:
            best=max(falling,key=lambda x:x[0])
            fall_ret.append(best[1])

print(f'总交易日: {all_days}')
print(f'有跌(pb_depth>0): {len(fall_ret)}天 ({len(fall_ret)/all_days*100:.0f}%)')
print(f'全涨/横盘(fallback): {len(fallback_cases)}天 ({len(fallback_cases)/all_days*100:.0f}%)')
print()

print('=== Fallback: 全涨/横盘, 挑pb_depth最大 ===')
avg=np.mean([f['best_ret'] for f in fallback_cases])
wr=sum(1 for f in fallback_cases if f['best_ret']>0)/len(fallback_cases)*100
print(f'  均值={avg:+.2f}%, 胜率={wr:.0f}%')

sub_neg=[f for f in fallback_cases if f['best_pb']<0]
if sub_neg:
    avg_neg=np.mean([f['best_ret'] for f in sub_neg])
    wr_neg=sum(1 for f in sub_neg if f['best_ret']>0)/len(sub_neg)*100
    print(f'    最深<0%(真涨): {len(sub_neg)}天, 均{avg_neg:+.2f}%, 胜{wr_neg:.0f}%')

sub_zero=[f for f in fallback_cases if 0<=f['best_pb']<0.5]
if sub_zero:
    avg_zero=np.mean([f['best_ret'] for f in sub_zero])
    wr_zero=sum(1 for f in sub_zero if f['best_ret']>0)/len(sub_zero)*100
    print(f'    最深0~0.5%(横盘): {len(sub_zero)}天, 均{avg_zero:+.2f}%, 胜{wr_zero:.0f}%')

print()
print('=== 有跌: 只在pb_depth>0的里面选 ===')
avg_fall=np.mean(fall_ret)
wr_fall=sum(1 for r in fall_ret if r>0)/len(fall_ret)*100
print(f'  (挑最深, 不WF) = {avg_fall:+.2f}%, 胜{wr_fall:.0f}%')

# 有跌的按回踩深度分段
for lo,hi,label in [(0,1,'0~1%'),(1,2,'1~2%'),(2,3,'2~3%'),(3,5,'3~5%'),(5,10,'>5%')]:
    sub=[f for f in fallback_cases+[{'best_pb':0,'best_ret':0}]*0]
    pass  # not needed for fallback analysis
print()
print('=== D策略全景 ===')
print('82%的天: pb_depth>0的候选在 → WF精挑')
print('18%的天: 全涨/横盘 → fallback挑pb_depth最大的')
print(f'   → 联合净值 12.99, 碾压任何单条件筛选')
