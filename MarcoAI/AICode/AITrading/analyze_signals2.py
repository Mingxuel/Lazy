import os,numpy as np
from collections import defaultdict

K=r'C:\Lazy\李明学的大A\Data\1D'
S=r'C:\Lazy\李明学的大A\Data\Strategy'
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

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

_5m={}
def lm5(code):
    if code in _5m:return _5m[code]
    fp=os.path.join(M5DIR,code)
    if not os.path.exists(fp):_5m[code]={};return{}
    bd=defaultdict(list)
    with open(fp) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','')
            bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    _5m[code]=dict(bd)
    return _5m[code]

# 1. 早封涨停过滤
samples=[]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    d2=tds[d1i-1];d3=tds[d1i-2];d4=tds[d1i-3]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<2:continue
            code=p[1]
            rs,dx=lk(code)
            d4k=dx.get(d4);d1k=dx.get(d1)
            if d4k is None or d1k is None:continue
            r4=rs[d4k];r1=rs[d1k]
            d4_pre=r4[6] if d4k==0 else rs[d4k-1][4]
            d4_lu=round(d4_pre*1.10,2)
            d4_bars=lm5(code).get(d4,[])
            early=False
            for bi,bar in enumerate(d4_bars):
                if bar[2]>=d4_lu*0.999: early=bi<=5;break
            bp=r1[6];ret=(r1[4]-bp)/bp*100
            samples.append({'ret':ret,'early':early})

print('=== 1. 早封过滤 ===')
all_ret=[s['ret'] for s in samples];all_n=len(samples)
early=[s for s in samples if s['early']];other=[s for s in samples if not s['early']]
print(f'全样本: {all_n}笔, 均{np.mean(all_ret):+.2f}%, 胜{sum(1 for r in all_ret if r>0)/all_n*100:.1f}%')
print(f'早封(前25min): {len(early)}笔, 均{np.mean([s["ret"] for s in early]):+.2f}%, 胜{sum(1 for s in early if s["ret"]>0)/len(early)*100:.1f}%')
print(f'过滤后: {len(other)}笔, 均{np.mean([s["ret"] for s in other]):+.2f}%, 胜{sum(1 for s in other if s["ret"]>0)/len(other)*100:.1f}%')
a1=np.mean(all_ret);a2=np.mean([s["ret"] for s in other])
n2=len(other)
gain=((1+a2/100)/(1+a1/100))**n2-1
print(f'估值提升: +{gain*100:.1f}%')

# 2. D-3下影线
print()
print('=== 2. D-3下影线 ===')
ws=[]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    d3=tds[d1i-2]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<2:continue
            code=p[1]
            rs,dx=lk(code)
            d3k=dx.get(d3);d1k=dx.get(d1)
            if d3k is None or d1k is None:continue
            r3=rs[d3k];r1=rs[d1k]
            bp=r1[6];ret_next=(r1[4]-bp)/bp*100
            wick=(r3[4]-r3[3])/r3[4]*100 if r3[4]>0 else 0
            ws.append({'ret':ret_next,'wick':wick})

for lo,hi in [(-10,-2),(-2,-1),(-1,-0.3),(-0.3,0),(0,5)]:
    grp=[s for s in ws if lo<=s['wick']<hi]
    if not grp:continue
    avg=np.mean([s['ret'] for s in grp])
    wr=sum(1 for s in grp if s['ret']>0)/len(grp)*100
    print(f'  下影{lo}~{hi}%: {len(grp)}笔, 均{avg:+.2f}%, 胜{wr:.1f}%')

# 3. D-3收阳但缩量(量比<1.5)
print()
print('=== 3. D-3 缩量回踩 vs 放量回踩 ===')
vs=[]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    d3=tds[d1i-2]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<2:continue
            code=p[1]
            rs,dx=lk(code)
            d3k=dx.get(d3);d1k=dx.get(d1)
            if d3k is None or d1k is None or d3k<20:continue
            r3=rs[d3k];r1=rs[d1k]
            avg20=np.mean([rs[i][5] for i in range(d3k-19,d3k+1)])
            vr=r3[5]/avg20 if avg20>0 else 1
            bp=r1[6];ret=(r1[4]-bp)/bp*100
            vs.append({'ret':ret,'vr':vr,'d3_up':r3[4]>r3[1]})

# 缩量回踩: 量比<1.5
shrink=[s for s in vs if s['vr']<1.5]
expand=[s for s in vs if s['vr']>=1.5]
for label,grp in [('缩量回踩(<1.5)',shrink),('放量回踩(>=1.5)',expand)]:
    avg=np.mean([s['ret'] for s in grp]);wr=sum(1 for s in grp if s['ret']>0)/len(grp)*100
    print(f'  {label}: {len(grp)}笔, 均{avg:+.2f}%, 胜{wr:.1f}%')

# 4. 交叉: 回踩3-5% + 非早封
print()
print('=== 4. 组合: 回踩-3%~-5% + 非早封 ===')
combo=[]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    d2=tds[d1i-1];d3=tds[d1i-2];d4=tds[d1i-3]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<2:continue
            code=p[1]
            rs,dx=lk(code)
            d4k=dx.get(d4);d3k=dx.get(d3);d1k=dx.get(d1)
            if d4k is None or d3k is None or d1k is None:continue
            r4=rs[d4k];r3=rs[d3k];r1=rs[d1k]
            d4_pre=r4[6] if d4k==0 else rs[d4k-1][4]
            d4_lu=round(d4_pre*1.10,2)
            d4_bars=lm5(code).get(d4,[])
            early=False
            for bi,bar in enumerate(d4_bars):
                if bar[2]>=d4_lu*0.999: early=bi<=5;break
            pb=(r3[4]-r3[2])/r3[2]*100 if r3[2]>0 else 0
            if -5<=pb<-3 and not early:
                bp=r1[6];ret=(r1[4]-bp)/bp*100
                combo.append(ret)

if combo:
    print(f'  组合: {len(combo)}笔, 均{np.mean(combo):+.2f}%, 胜{sum(1 for r in combo if r>0)/len(combo)*100:.1f}%')
