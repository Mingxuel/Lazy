"""TPO3选股: 按股票代码升序取最后一只, 5M卖出"""
import os, random, numpy as np
from collections import defaultdict

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D'
M5=r'C:\Lazy\MarcoAI\AIData\5M';INIT=100_000
CR,SD,TF=0.0001,0.0005,0.00001

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
    fp=os.path.join(M5,code)
    if not os.path.exists(fp):_5m[code]={};return{}
    bd=defaultdict(list)
    with open(fp) as f:
        for l in f:
            l=l.strip();p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','');bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    _5m[code]=dict(bd);return _5m[code]
def trade(bp,sp,cpt):
    sh=int(cpt/bp/100)*100
    if sh<100:return None
    b=sh*bp;cb=b*CR;sa=sh*sp;cs=sa*CR;st=sa*SD;tf=sa*TF
    return(sa-cs-st-tf-b-cb)/(b+cb)*100,(sa-cs-st-tf-b-cb)
def sell_5m(bars,bp,d1_close):
    if not bars:return d1_close
    lc=bars[-1][3]
    if lc>0 and d1_close>0 and abs(lc/d1_close-1)>=0.02:return d1_close
    lu=round(bp*1.10,2);st=bp*0.94
    for bar in bars:
        if bar[2]<=st:return st
        if bar[1]>=lu*0.999:return lu
    return d1_close

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}
daily_cands=defaultdict(list)
for fn in sorted(os.listdir(S)):
    if not fn.isdigit() or fn<'20250101':continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip();p=l.split('|')
            if len(p)<2:continue
            daily_cands[d1].append((p[1],p[0]))
days=sorted(daily_cands.keys())

# === 升序取最后一只(code最大) ===
asset=INIT;trades=0;monthly=defaultdict(list)
for d1 in days:
    cands=sorted(daily_cands[d1],key=lambda c:c[0])
    code,name=cands[-1]
    rs,dx=lk(code);d1k=dx.get(d1)
    if d1k is None:continue
    r1=rs[d1k];bp=r1[6]
    if bp<=0:continue
    bars=lm5(code).get(d1,[])
    sp=sell_5m(bars,bp,r1[4])
    r=trade(bp,sp,asset)
    if r is None:continue
    asset+=r[1];trades+=1
    monthly[d1[:6]].append(r[0])

nav=asset/INIT
wr=sum(1 for m in monthly.values() if sum(m)>0)/len(monthly)*100
print(f'=== 升序取最后(code最大) ===')
print(f'净值{nav:.2f}  +{(nav-1)*100:.1f}%  {trades}笔  盈利月{wr:.0f}%')
print()

# === 随机基准 ===
navs=[]
for seed in range(10):
    random.seed(seed);a=INIT
    for d1 in days:
        cands=daily_cands[d1]
        code,name=random.choice(cands)
        rs,dx=lk(code);d1k=dx.get(d1)
        if d1k is None:continue
        r1=rs[d1k];bp=r1[6]
        if bp<=0:continue
        bars=lm5(code).get(d1,[])
        sp=sell_5m(bars,bp,r1[4])
        r=trade(bp,sp,a)
        if r is not None:a+=r[1]
    navs.append(a/INIT)
print(f'=== 随机基准 ===')
print(f'均值{np.mean(navs):.2f}  最佳{max(navs):.2f}  最差{min(navs):.2f}')
print()

print('=== 月度明细 ===')
for m in sorted(monthly.keys()):
    rets=monthly[m];cnt=len(rets)
    cpd=1.0
    for r in rets:cpd*=(1+r/100)
    cpd=(cpd-1)*100
    wr_m=sum(1 for r in rets if r>0)/cnt*100
    print(f'{m} {cnt:>3}笔  月复利{cpd:>+7.1f}%  胜率{wr_m:>4.0f}%')
