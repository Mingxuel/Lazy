"""测试止损-5%规则 on 311 TOP1"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
M5=r'C:\Lazy\MarcoAI\AIData\5M'
CR=0.00025; CM=5.0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

def load_td():
    ds=[]
    with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
        for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and ds.append(l)
    return sorted(ds)
def load_kline(code):
    fp=os.path.join(K,code)
    if not os.path.exists(fp): return [],[]
    rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'): continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}
def check_ma5(code,dt,close):
    fp=os.path.join(M5,code)
    if not os.path.exists(fp): return 0,0
    df=dt[:4]+'-'+dt[4:6]+'-'+dt[6:8]
    bars=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<6: continue
            if p[0].startswith(df): bars.append((p[0],float(p[4]),float(p[2]),float(p[3]),float(p[1]),float(p[5])))
    if not bars or len(bars)<10: return 0,0
    for b in bars:
        bl,bc=b[3],b[1]
        if close>0:
            d=(bl-close)/close*100
            if -1.5<d<1.0:
                bounce=(bc-bl)/bl*100
                if bounce>1.5: return 1,bounce
    return 0,0

def extract(rows,d2i):
    r2=rows[d2i]; o2,h2,l2,c2,v2,pc2=r2[1],r2[2],r2[3],r2[4],r2[5],r2[6]
    r3=rows[d2i-1] if d2i>=1 else None
    cls=np.array([r[4] for r in rows[:d2i+1]])
    highs=np.array([r[2] for r in rows[:d2i+1]])
    lows=np.array([r[3] for r in rows[:d2i+1]])
    n=len(cls)
    f={}
    f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
    f['vol_contract']=1 if(r3 and v2<r3[5]*0.8) else 0
    f['ma5_dev']=(c2-np.mean(cls[-5:]))/np.mean(cls[-5:])*100 if n>=5 else 0
    if n>=10:
        trs=[]
        for i in range(d2i-9,d2i+1):
            h=highs[i]; l=lows[i]; pc=rows[i-1][4] if i>0 else rows[i][6]
            trs.append(max(h-l,abs(h-pc),abs(l-pc)))
        atr10=np.mean(trs) if trs else 1
    else:
        atr10=h2-l2 if h2>l2 else 1
    f['pc_vs_low_atr']=(pc2-l2)/atr10 if atr10>0 else 0
    f['high_vs_pc_atr']=(h2-pc2)/atr10 if atr10>0 else 0
    return f

FEATURES=['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr']

# Reload with D-1 OHLC
tds_all=load_td(); di={d:i for i,d in enumerate(tds_all)}
samples2=[]

for fn in sorted(os.listdir(S)):
    if not fn.isdigit(): continue
    d1=fn; d1i=di.get(d1)
    if d1i is None or d1i<3: continue
    d2=tds_all[d1i-1]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<2: continue
            name=p[0]; code=p[1]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]
            bp=r1[6]; sp_close=r1[4]
            d1_open=r1[1]; d1_high=r1[2]; d1_low=r1[3]
            if bp<=0: continue
            ret_close=(sp_close-bp)/bp*100
            f=extract(rows,d2i_k)
            f['ma5_support'],f['ma5_bounce']=check_ma5(code,d2,r1[6])
            samples2.append((f,ret_close,code,d1,bp,sp_close,name,d1_open,d1_high,d1_low))

samples2.sort(key=lambda x:x[3])

def fee(buy,sell):
    sh=int(CAPITAL/buy/100)*100
    if sh==0: sh=100
    c=sh*buy; bf=max(c*CR,CM)+c*TF; tb=c+bf
    r=sh*sell; sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

X2=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples2])
y2=np.array([s[1] for s in samples2])

daily_meta2=defaultdict(list)
for i,s in enumerate(samples2): daily_meta2[s[3]].append(i)
all_dates2=sorted(daily_meta2.keys())

def sell_stop(bp,o,h,l,c):
    if o/bp <= 0.95:
        return o, 'open'
    if l/bp <= 0.95:
        return bp*0.945, 'low'
    return c, 'close'

results={}
for label, sell_fn in [
    ('收盘卖', lambda bp,o,h,l,c: (c,'close')),
    ('止损-5%', sell_stop),
]:
    daily=[]
    stats=defaultdict(int)
    for d1_date in all_dates2:
        idxs=daily_meta2[d1_date]
        first_i=idxs[0]
        if first_i<100:
            best=samples2[idxs[0]]
        else:
            hist=[j for j in range(first_i)]
            Xh=X2[hist]; yh=y2[hist]
            mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
            Xn=(Xh-mean)/std
            try: w=solve(Xn.T@Xn+np.eye(5)*2.0, Xn.T@yh)
            except: w=np.zeros(5)
            Xt=np.array([(X2[i]-mean)/std for i in idxs])
            preds=Xt@w
            best=samples2[idxs[int(np.argmax(preds))]]
        
        bp=best[4]; o=best[7]; h=best[8]; l=best[9]; c=best[5]
        sp,mode=sell_fn(bp,o,h,l,c)
        daily.append(fee(bp,sp))
        stats[mode]+=1
    
    cum=1.0; peak=1.0; max_dd=0.0
    for r in daily:
        cum*=(1+r/100)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd: max_dd=dd
    wr=sum(1 for r in daily if r>0)/len(daily)*100
    results[label]=daily
    
    print(f'{label}: 净值{cum:.4f} 收益{(cum-1)*100:.1f}% 胜率{wr:.1f}% 回撤{max_dd:.1f}%')
    print(f'  卖出:{dict(stats)}')

# 样本外
cutoff='202604'
for label in ['收盘卖','止损-5%']:
    test=[r for i,r in enumerate(results[label]) if all_dates2[i]>=cutoff]
    tc=1.0
    for r in test: tc*=(1+r/100)
    print(f'{label} 样本外: 净值{tc:.4f} 收益{(tc-1)*100:.1f}%')

# 月度
print(f'\n========== 全量月度 ==========')
print(f'{"月份":<8} {"收盘卖":>10} {"止损-5%":>10}')
mall=defaultdict(list)
for mi,d in enumerate(all_dates2):
    mall[d[:6]+'cl']=mall.get(d[:6]+'cl',[])+[results['收盘卖'][mi]]
    mall[d[:6]+'st']=mall.get(d[:6]+'st',[])+[results['止损-5%'][mi]]
cum_cl=1.0; cum_st=1.0
for m in sorted(set(d[:6] for d in all_dates2)):
    bc=1.0; lc=1.0
    for r in mall.get(m+'cl',[]): bc*=(1+r/100)
    for r in mall.get(m+'st',[]): lc*=(1+r/100)
    cum_cl*=bc; cum_st*=lc
    print(f'{m:<8} {(bc-1)*100:>+9.2f}% {(lc-1)*100:>+9.2f}%')
print(f'{"合计":<8} {(cum_cl-1)*100:>+9.1f}% {(cum_st-1)*100:>+9.1f}%')

print(f'\n========== 年度 ==========')
ya=defaultdict(list)
for mi,d in enumerate(all_dates2):
    ya[d[:4]+'cl']=ya.get(d[:4]+'cl',[])+[results['收盘卖'][mi]]
    ya[d[:4]+'st']=ya.get(d[:4]+'st',[])+[results['止损-5%'][mi]]
print(f'{"年份":<8} {"收盘卖":>12} {"止损-5%":>12}')
for y in sorted(set(d[:4] for d in all_dates2)):
    bc=1.0; lc=1.0
    for r in ya.get(y+'cl',[]): bc*=(1+r/100)
    for r in ya.get(y+'st',[]): lc*=(1+r/100)
    print(f'{y:<8} {(bc-1)*100:>+11.1f}% {(lc-1)*100:>+11.1f}%')

# 样本外月度
cutoff='202604'
mb=defaultdict(list); ml=defaultdict(list)
for mi,d in enumerate(all_dates2):
    if d<cutoff: continue
    m=d[:6]
    mb[m].append(results['收盘卖'][mi])
    ml[m].append(results['止损-5%'][mi])
print(f'\n========== 样本外(≥{cutoff}) 月度 ==========')
print(f'{"月份":<8} {"收盘卖":>10} {"止损-5%":>10}')
for m in sorted(mb.keys()):
    bc=1.0; lc=1.0
    for r in mb[m]: bc*=(1+r/100)
    for r in ml[m]: lc*=(1+r/100)
    print(f'{m:<8} {(bc-1)*100:>+9.2f}% {(lc-1)*100:>+9.2f}%')
bc=1.0; lc=1.0
for r in [r for i,r in enumerate(results['收盘卖']) if all_dates2[i]>=cutoff]: bc*=(1+r/100)
for r in [r for i,r in enumerate(results['止损-5%']) if all_dates2[i]>=cutoff]: lc*=(1+r/100)
print(f'{"合计":<8} {(bc-1)*100:>+9.2f}% {(lc-1)*100:>+9.2f}%')
