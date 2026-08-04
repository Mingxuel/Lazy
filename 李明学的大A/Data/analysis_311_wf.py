"""
311策略 — 33维特征 Walk-Forward 岭回归选股
无行业过滤，纯特征驱动
训练<202604, 测试>=202604
"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
M5=r'C:\Lazy\MarcoAI\AIData\5M'
CR=0.00025; CM=5.0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

def load_td():
    ds=[]
    with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
        for l in f:
            l=l.strip()
            if l and l.isdigit() and len(l)==8: ds.append(l)
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
    df=f'{dt[:4]}-{dt[4:6]}-{dt[6:8]}'
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
    
    f={}
    # A: 多空博弈
    f['high_vs_pc']=(h2-pc2)/pc2*100 if pc2>0 else 0
    f['pc_vs_low']=(pc2-l2)/pc2*100 if pc2>0 else 0
    f['gap_open']=(o2-pc2)/pc2*100 if pc2>0 else 0
    f['close_pos']=(c2-l2)/(h2-l2) if h2>l2 else 0.5
    f['upper_shadow']=(h2-max(o2,c2))/(h2-l2)*100 if h2>l2 else 0
    f['lower_shadow']=(min(o2,c2)-l2)/(h2-l2)*100 if h2>l2 else 0
    # B: 量价
    f['vol_contract']=1 if (r3 and v2<r3[5]*0.8) else 0
    f['vol_ratio']=v2/r3[5] if (r3 and r3[5]>0) else 1
    f['amplitude']=(h2-l2)/o2*100 if o2>0 else 0
    f['body_ratio']=abs(c2-o2)/(h2-l2)*100 if h2>l2 else 0
    f['vol_abnormal']=1 if (r3 and v2>r3[5]*2) else 0
    # C: 均线
    cls=np.array([r[4] for r in rows[:d2i+1]])
    n=len(cls)
    f['ma5_dev']=(c2-np.mean(cls[-5:]))/np.mean(cls[-5:])*100 if n>=5 else 0
    f['ma5_slope']=(cls[-1]-cls[-5])/cls[-5]*100 if n>=5 and cls[-5]>0 else 0
    f['ma10_dev']=(c2-np.mean(cls[-10:]))/np.mean(cls[-10:])*100 if n>=10 else 0
    f['ma20_dev']=(c2-np.mean(cls[-20:]))/np.mean(cls[-20:])*100 if n>=20 else 0
    if n>=20:
        ma5=np.mean(cls[-5:]); ma10=np.mean(cls[-10:]); ma20=np.mean(cls[-20:])
        f['ma_bullish']=1 if(c2>ma5 and ma5>ma10 and ma10>ma20) else 0
    else: f['ma_bullish']=0
    # D: 趋势
    f['consec_up']=0
    if n>=2:
        for i in range(d2i,max(0,d2i-10),-1):
            if cls[i]>cls[i-1]: f['consec_up']+=1
            else: break
    f['ret_5d']=(cls[-1]-cls[-6])/cls[-6]*100 if n>=6 and cls[-6]>0 else 0
    f['ret_10d']=(cls[-1]-cls[-11])/cls[-11]*100 if n>=11 and cls[-11]>0 else 0
    f['ret_20d']=(cls[-1]-cls[-21])/cls[-21]*100 if n>=21 and cls[-21]>0 else 0
    if n>=10:
        rets=[(cls[i]-cls[i-1])/cls[i-1]*100 for i in range(d2i-8,d2i+1) if cls[i-1]>0]
        f['volatility']=np.std(rets) if rets else 0
    else: f['volatility']=0
    # E: 回踩
    f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
    f['pb_speed']=f['pb_depth']/f['amplitude'] if f['amplitude']>0 else 0
    f['broke_d3']=1 if(r3 and l2<r3[3]) else 0
    f['d3_strong']=1 if(r3 and (r3[4]-r3[1])/r3[1]*100>7) else 0
    # G: 价格区间
    f['price_level']=c2
    f['vs_60h']=c2/max(cls[-60:]) if n>=60 and max(cls[-60:])>0 else 1
    f['vs_60l']=c2/min(cls[-60:]) if n>=60 and min(cls[-60:])>0 else 1
    
    return f

KEYS=['high_vs_pc','pc_vs_low','gap_open','close_pos','upper_shadow','lower_shadow',
      'vol_contract','vol_ratio','amplitude','body_ratio','vol_abnormal',
      'ma5_dev','ma5_slope','ma10_dev','ma20_dev','ma_bullish',
      'consec_up','ret_5d','ret_10d','ret_20d','volatility',
      'pb_depth','pb_speed','broke_d3','d3_strong',
      'price_level','vs_60h','vs_60l']
ALLK=KEYS+['ma5_support','ma5_bounce']
print(f'特征: {len(ALLK)}维')

# === 收集样本 ===
tds=load_td(); di={d:i for i,d in enumerate(tds)}
samples=[]  # (X_arr, ret, code, d1, bp, sp, name)

for fn in sorted(os.listdir(S)):
    if not fn.isdigit(): continue
    d1=fn; d1i=di.get(d1)
    if d1i is None or d1i<3: continue
    d2=tds[d1i-1]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<2: continue
            code=p[1]; name=p[0]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]; bp=r1[6]; sp=r1[4]
            if bp<=0: continue
            ret=(sp-bp)/bp*100
            f=extract(rows,d2i_k)
            f['ma5_support'],f['ma5_bounce']=check_ma5(code,d2,r1[6])
            X_arr=np.array([f.get(k,0) for k in ALLK])
            samples.append((X_arr,ret,code,d1,bp,sp,name))

samples.sort(key=lambda x:x[3])
X_all=np.array([s[0] for s in samples])
y_all=np.array([s[1] for s in samples])
n=len(samples)
print(f'总样本: {n}笔')

def fee(buy,sell):
    sh=int(CAPITAL/buy/100)*100
    if sh==0: sh=100
    c=sh*buy; bf=max(c*CR,CM)+c*TF; tb=c+bf
    r=sh*sell; sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

# === Walk-forward ===
cutoff='202604'
daily_meta=defaultdict(list)
for i,s in enumerate(samples): daily_meta[s[3]].append(i)
all_dates=sorted(daily_meta.keys())

daily_bl=[]; daily_lr=[]
min_train=150; lam=3.0

for d1_date in all_dates:
    idxs=daily_meta[d1_date]
    
    # 等权
    pc=CAPITAL/len(idxs)
    bl_rets=[fee(samples[i][4],samples[i][5]) for i in idxs]
    daily_bl.append(np.mean(bl_rets))
    
    # 岭回归
    first_i=idxs[0]
    if first_i<min_train:
        daily_lr.append(fee(samples[idxs[0]][4],samples[idxs[0]][5]))
        continue
    
    hist=[j for j in range(first_i)]
    Xh=X_all[hist]; yh=y_all[hist]
    mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
    Xn=(Xh-mean)/std
    d=Xn.shape[1]
    try:
        w=solve(Xn.T@Xn+np.eye(d)*lam, Xn.T@yh)
    except:
        w=np.zeros(d)
    
    Xt=np.array([(X_all[i]-mean)/std for i in idxs])
    preds=Xt@w
    best_i=idxs[int(np.argmax(preds))]
    daily_lr.append(fee(samples[best_i][4],samples[best_i][5]))

# === 评估 ===
def metrics(rets):
    cum=1.0; peak=1.0; max_dd=0.0
    for r in rets:
        cum*=(1+r/100)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd: max_dd=dd
    wr=sum(1 for r in rets if r>0)/len(rets)*100
    dly=np.array(rets)
    sh=np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
    return cum,(cum-1)*100,wr,max_dd,sh

print()
print(f'{"策略":<25} {"净值":>8} {"收益":>10} {"胜率":>7} {"回撤":>8} {"夏普":>7}')
print('-'*72)
for label,rets in [('等权全买',daily_bl),('岭回归_WF_33维',daily_lr)]:
    cum,tr,wr,dd,sh=metrics(rets)
    print(f'{label:<25} {cum:>8.4f} {tr:>10.1f}% {wr:>7.1f}% {dd:>8.1f}% {sh:>7.2f}')

# 样本外月度
print()
print(f'{"月份":<8} {"等权全买":>10} {"岭回归33维":>10}')
print('-'*32)
mb=defaultdict(list); mlr=defaultdict(list)
for mi,d in enumerate(all_dates):
    if d<'202604': continue
    m=d[:6]; mb[m].append(daily_bl[mi]); mlr[m].append(daily_lr[mi])

for m in sorted(set(list(mb.keys()))):
    b=1.0; l=1.0
    for r in mb[m]: b*=(1+r/100)
    for r in mlr[m]: l*=(1+r/100)
    print(f'{m:<8} {(b-1)*100:>+9.2f}% {(l-1)*100:>+9.2f}%')

tb=[r for i,r in enumerate(daily_bl) if all_dates[i]>='202604']
tl=[r for i,r in enumerate(daily_lr) if all_dates[i]>='202604']
cb=1.0; cl=1.0
for r in tb: cb*=(1+r/100)
for r in tl: cl*=(1+r/100)
print(f'{"样本外合计":<8} {(cb-1)*100:>+9.2f}% {(cl-1)*100:>+9.2f}%')

# 权重
print(f'\n最终岭回归权重(λ={lam}):')
for i,idx in enumerate(np.argsort(-np.abs(w))[:12]):
    print(f'  {i+1:>2}. {ALLK[idx]:<20} {w[idx]:>+8.4f}')
