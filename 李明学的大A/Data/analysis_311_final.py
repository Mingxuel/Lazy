"""311策略 最终版 — 双ATR标准化5特征 + 完整明细"""
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

FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr']

def extract_all(rows,d2i):
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
    
    # ATR
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
    f['ma5_support'],f['ma5_bounce']=check_ma5(code,'',c2)
    
    # 原始值(展示用)
    f['pc_vs_low_raw']=(pc2-l2)/pc2*100 if pc2>0 else 0
    f['high_vs_pc_raw']=(h2-pc2)/pc2*100 if pc2>0 else 0
    f['atr10']=atr10
    
    return f

tds=load_td(); di={d:i for i,d in enumerate(tds)}
samples=[]

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
            name=p[0]; code=p[1]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]; bp=r1[6]; sp=r1[4]
            if bp<=0: continue
            ret=(sp-bp)/bp*100
            f=extract_all(rows,d2i_k)
            f['ma5_support'],f['ma5_bounce']=check_ma5(code,d2,r1[6])
            samples.append((f,ret,code,d1,bp,sp,name))

samples.sort(key=lambda x:x[3])
n=len(samples)

def fee(buy,sell):
    sh=int(CAPITAL/buy/100)*100
    if sh==0: sh=100
    c=sh*buy; bf=max(c*CR,CM)+c*TF; tb=c+bf
    r=sh*sell; sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

daily_meta=defaultdict(list)
for i,s in enumerate(samples): daily_meta[s[3]].append(i)
all_dates=sorted(daily_meta.keys())

# === 等权 ===
baseline=[]
for d1 in all_dates:
    idxs=daily_meta[d1]
    pc=CAPITAL/len(idxs)
    baseline.append(np.mean([fee(samples[i][4],samples[i][5]) for i in idxs]))

# === 岭回归5特征 ===
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples])
y=np.array([s[1] for s in samples])
ridge_daily=[]; ridge_picks=[]; ridge_w_history=[]

for d1_date in all_dates:
    idxs=daily_meta[d1_date]
    first_i=idxs[0]
    if first_i<100:
        ridge_daily.append(fee(samples[idxs[0]][4],samples[idxs[0]][5]))
        ridge_picks.append(samples[idxs[0]])
        continue
    hist=[j for j in range(first_i)]
    Xh=X[hist]; yh=y[hist]
    mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
    Xn=(Xh-mean)/std
    d=Xn.shape[1]
    try: w=solve(Xn.T@Xn+np.eye(d)*2.0, Xn.T@yh)
    except: w=np.zeros(d)
    Xt=np.array([(X[i]-mean)/std for i in idxs])
    preds=Xt@w
    best_i=idxs[int(np.argmax(preds))]
    ridge_daily.append(fee(samples[best_i][4],samples[best_i][5]))
    ridge_picks.append(samples[best_i])

# === 结果 ===
def metrics(rets):
    cum=1.0; peak=1.0; max_dd=0.0
    for r in rets:
        cum*=(1+r/100)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd: max_dd=dd
    wr=sum(1 for r in rets if r>0)/len(rets)*100 if rets else 0
    return cum,(cum-1)*100,wr,max_dd

cb,trb,wrb,ddb=metrics(baseline)
cr,trr,wrr,ddr=metrics(ridge_daily)

print(f'{"="*80}')
print(f'  311策略 最终版 — 双ATR标准化(Walk-Forward岭回归)')
print(f'{"="*80}')
print(f'特征: {" + ".join(FEATURES)}')
print(f'样本: {n}笔, {len(all_dates)}天')
print()
print(f'{"指标":<20} {"等权全买":>12} {"岭回归5特征":>12}')
print(f'{"-"*44}')
print(f'{"净值":<20} {cb:>12.4f} {cr:>12.4f}')
print(f'{"总收益":<20} {trb:>+10.1f}% {trr:>+10.1f}%')
print(f'{"胜率":<20} {wrb:>11.1f}% {wrr:>11.1f}%')
print(f'{"最大回撤":<20} {ddb:>11.1f}% {ddr:>11.1f}%')

# 月度明细
print(f'\n{"="*90}')
print(f'  月度盈亏明细')
print(f'{"="*90}')
print(f'{"月份":<8} {"天":>4} {"等权收益":>10} {"等权胜率":>7} {"岭回归收益":>10} {"岭回胜率":>7} {"选股":>12} {"选股收益":>8}')
print(f'{"-"*74}')

m_bl=defaultdict(list); m_lr=defaultdict(list); m_picks=defaultdict(list)
for mi,d in enumerate(all_dates):
    m=d[:6]; m_bl[m].append(baseline[mi]); m_lr[m].append(ridge_daily[mi])
    m_picks[m].append(ridge_picks[mi])

cum_bl=1.0; cum_lr=1.0; peak_bl=1.0; peak_lr=1.0

for m in sorted(m_bl.keys()):
    bl_c=1.0; lr_c=1.0
    for r in m_bl[m]: bl_c*=(1+r/100)
    for r in m_lr[m]: lr_c*=(1+r/100)
    cum_bl*=bl_c; cum_lr*=lr_c
    
    bl_wr=sum(1 for r in m_bl[m] if r>0)/len(m_bl[m])*100
    lr_wr=sum(1 for r in m_lr[m] if r>0)/len(m_lr[m])*100
    
    # 选股
    picks=m_picks[m]
    pick_names=set(s[6] for s in picks)
    pick_ret=np.mean([s[1] for s in picks])
    
    print(f'{m:<8} {len(m_bl[m]):>4} {(bl_c-1)*100:>+9.2f}% {bl_wr:>6.0f}% {(lr_c-1)*100:>+9.2f}% {lr_wr:>6.0f}% {len(pick_names):>8}只 {pick_ret:>+7.2f}%')

print(f'{"合计":<8} {len(baseline):>4} {(cum_bl-1)*100:>+9.1f}% {(cum_lr-1)*100:>+9.1f}%')

# 年度
print(f'\n{"年份":<8} {"等权收益":>12} {"岭回归收益":>12}')
y_bl=defaultdict(list); y_lr=defaultdict(list)
for mi,d in enumerate(all_dates):
    y_bl[d[:4]].append(baseline[mi]); y_lr[d[:4]].append(ridge_daily[mi])
for y in sorted(y_bl.keys()):
    bc=1.0; lc=1.0
    for r in y_bl[y]: bc*=(1+r/100)
    for r in y_lr[y]: lc*=(1+r/100)
    print(f'{y:<8} {(bc-1)*100:>+11.1f}% {(lc-1)*100:>+11.1f}%')

# 样本外汇总
print(f'\n{"="*60}')
print(f'  样本外(≥202604) 逐月对比')
print(f'{"="*60}')
print(f'{"月份":<8} {"等权":>10} {"岭回归":>10}')
for m in sorted(m_bl.keys()):
    if m<'202604': continue
    bc=1.0; lc=1.0
    for r in m_bl[m]: bc*=(1+r/100)
    for r in m_lr[m]: lc*=(1+r/100)
    print(f'{m:<8} {(bc-1)*100:>+9.2f}% {(lc-1)*100:>+9.2f}%')
bc=1.0; lc=1.0
for r in [r for i,r in enumerate(baseline) if all_dates[i]>='202604']: bc*=(1+r/100)
for r in [r for i,r in enumerate(ridge_daily) if all_dates[i]>='202604']: lc*=(1+r/100)
print(f'{"合计":<8} {(bc-1)*100:>+9.2f}% {(lc-1)*100:>+9.2f}%')

# 选股示例(样本外每天选了谁)
print(f'\n{"="*100}')
print(f'  样本外每日选股明细')
print(f'{"="*100}')
print(f'{"日期":<10} {"名称":<10} {"代码":<14} {"买入":>8} {"卖出":>8} {"收益":>8} {"特征(pb/vol/ma5/bear/bull)":>30}')
print(f'{"-"*90}')

test_picks=[(d,s) for mi,(d,s) in enumerate(zip(all_dates,ridge_picks)) if d>='202604']
for d,s in test_picks[:15]:
    f=s[0]
    feat_str=f'pb={f["pb_depth"]:+.1f} vc={f["vol_contract"]:.0f} ma5={f["ma5_dev"]:+.1f} bearATR={f["pc_vs_low_atr"]:.1f} bullATR={f["high_vs_pc_atr"]:.1f}'
    print(f'{d:<10} {s[6]:<10} {s[2]:<14} {s[4]:>8.2f} {s[5]:>8.2f} {s[1]:>+7.2f}%  {feat_str}')

# ...more
if len(test_picks)>15:
    print(f'  ... (共{len(test_picks)}天, 省略{len(test_picks)-15})')
