"""测试VWAP卖出规则 on 311 TOP1"""
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
def load_5m_bars(code,dt):
    fp=os.path.join(M5,code)
    if not os.path.exists(fp): return None
    df=dt[:4]+'-'+dt[4:6]+'-'+dt[6:8]
    bars=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<6: continue
            if p[0].startswith(df):
                bars.append((p[0],float(p[4]),float(p[2]),float(p[3]),float(p[1]),float(p[5])))
    return bars if bars else None

def check_ma5(code,dt,close):
    fp=os.path.join(M5,code)
    if not os.path.exists(fp): return 0,0
    bars=load_5m_bars(code,dt)
    if not bars: return 0,0
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

# 收集样本(含D-1 5M数据)
tds_all=load_td(); di={d:i for i,d in enumerate(tds_all)}
samples=[]

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
            f=extract(rows,d2i_k)
            f['ma5_support'],f['ma5_bounce']=check_ma5(code,d2,r1[6])
            bars_d1=load_5m_bars(code,d1)
            samples.append((f,code,d1,bp,sp_close,name,d1_open,d1_high,d1_low,bars_d1))

samples.sort(key=lambda x:x[2])
n=len(samples)

def fee(buy,sell):
    sh=int(CAPITAL/buy/100)*100
    if sh==0: sh=100
    c=sh*buy; bf=max(c*CR,CM)+c*TF; tb=c+bf
    r=sh*sell; sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples])
y=np.array([(s[4]-s[3])/s[3]*100 for s in samples])

daily_meta=defaultdict(list)
for i,s in enumerate(samples): daily_meta[s[2]].append(i)
all_dates=sorted(daily_meta.keys())

# ---- VWAP卖出逻辑 ----
def sell_vwap(bars,bp):
    """盘中跌破VWAP即卖"""
    if not bars: return bars[-1][1] if bars else bp, 'close'
    total_pv=0.0; total_v=0.0
    for b in bars:
        price=b[1]; vol=b[5]
        total_pv+=price*vol; total_v+=vol
        vwap=total_pv/total_v if total_v>0 else price
        if price<vwap and b[0]>bars[0][0]:
            return price, 'vwap'
    return bars[-1][1], 'close'

def sell_vwap_1130(bars,bp):
    """上午不管, 11:30后跌破VWAP卖"""
    if not bars: return bars[-1][1] if bars else bp, 'close'
    total_pv=0.0; total_v=0.0
    for b in bars:
        price=b[1]; vol=b[5]
        total_pv+=price*vol; total_v+=vol
        vwap=total_pv/total_v if total_v>0 else price
        hour=int(b[0][11:13])
        if hour>=13 and price<vwap:
            return price, 'vwap_pm'
    return bars[-1][1], 'close'

def sell_vwap_stop(bars,bp):
    """VWAP + -5%止损"""
    if not bars: return bars[-1][1] if bars else bp, 'close'
    total_pv=0.0; total_v=0.0
    for b in bars:
        price=b[1]; vol=b[5]
        total_pv+=price*vol; total_v+=vol
        vwap=total_pv/total_v if total_v>0 else price
        pct=(price-bp)/bp*100
        if pct<=-5.0:
            return price, 'stop'
        if price<vwap and b[0]>bars[0][0]:
            return price, 'vwap'
    return bars[-1][1], 'close'

def sell_vwap_above(bars,bp):
    """只有一直在VWAP上方才拿, 跌破就卖(不含第一分钟)"""
    if not bars: return bars[-1][1] if bars else bp, 'close'
    total_pv=0.0; total_v=0.0
    for i,b in enumerate(bars):
        price=b[1]; vol=b[5]
        total_pv+=price*vol; total_v+=vol
        vwap=total_pv/total_v if total_v>0 else price
        if i>2 and price<vwap:
            return price, 'vwap'
    return bars[-1][1], 'close'

# ---- 回测 ----
results={}
for label, sell_fn in [
    ('收盘卖', lambda bars,bp,cf: (bars[-1][1],'close')),
    ('止损-5%', lambda bars,bp,cf: (
        (bp*0.95, 'open_stop') if bars[0][1]/bp<=0.95 else
        (bp*0.945, 'low_stop') if min(b[3] for b in bars)/bp<=0.95 else
        (bars[-1][1], 'close')
    )),
    ('VWAP跌破卖', lambda bars,bp,cf: sell_vwap(bars,bp)),
    ('VWAP+下午', lambda bars,bp,cf: sell_vwap_1130(bars,bp)),
    ('VWAP+止损-5%', lambda bars,bp,cf: sell_vwap_stop(bars,bp)),
    ('VWAP窄版', lambda bars,bp,cf: sell_vwap_above(bars,bp)),
]:
    daily=[]
    stats=defaultdict(int)
    for d1_date in all_dates:
        idxs=daily_meta[d1_date]
        first_i=idxs[0]
        if first_i<100:
            best=samples[idxs[0]]
        else:
            hist=[j for j in range(first_i)]
            Xh=X[hist]; yh=y[hist]
            mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
            Xn=(Xh-mean)/std
            try: w=solve(Xn.T@Xn+np.eye(5)*2.0, Xn.T@yh)
            except: w=np.zeros(5)
            Xt=np.array([(X[i]-mean)/std for i in idxs])
            preds=Xt@w
            best=samples[idxs[int(np.argmax(preds))]]
        
        bp=best[3]; bars=best[9]; c_fallback=best[4]
        if bars is None or len(bars)<5:
            sp=c_fallback; mode='no5m'
        else:
            sp,mode=sell_fn(bars,bp,c_fallback)
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
    
    test=[r for i,r in enumerate(daily) if all_dates[i]>='202604']
    tc=1.0
    for r in test: tc*=(1+r/100)
    print(f'{label}: 净值{cum:.4f} 收益{(cum-1)*100:.1f}% 胜率{wr:.1f}% 回撤{max_dd:.1f}% 样本外{(tc-1)*100:.1f}%')
    print(f'  卖出: {dict(stats)}')
