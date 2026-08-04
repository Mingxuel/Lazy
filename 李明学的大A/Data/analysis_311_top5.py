"""测试多种TOP5特征组合的Walk-Forward性能"""
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

tds=load_td(); di={d:i for i,d in enumerate(tds)}

exec(open('analysis_311_wf.py').read().split('# === 收集样本 ===')[0])

ALLK=KEYS+['ma5_support','ma5_bounce']
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
            code=p[1]; name=p[0]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]; bp=r1[6]; sp=r1[4]
            if bp<=0: continue
            ret=(sp-bp)/bp*100
            f=extract(rows,d2i_k)
            f['ma5_support'],f['ma5_bounce']=check_ma5(code,d2,r1[6])
            samples.append(({k:f.get(k,0) for k in ALLK}, ret, code, d1, bp, sp))

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

def run_wf(feature_keys, label, lam=2.0):
    X=np.array([[s[0].get(k,0) for k in feature_keys] for s in samples])
    y=np.array([s[1] for s in samples])
    daily=[]
    for d1_date in all_dates:
        idxs=daily_meta[d1_date]
        first_i=idxs[0]
        if first_i<100:
            daily.append(fee(samples[idxs[0]][4],samples[idxs[0]][5]))
            continue
        hist=[j for j in range(first_i)]
        Xh=X[hist]; yh=y[hist]
        mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
        Xn=(Xh-mean)/std
        d=Xn.shape[1]
        try: w=solve(Xn.T@Xn+np.eye(d)*lam, Xn.T@yh)
        except: w=np.zeros(d)
        Xt=np.array([(X[i]-mean)/std for i in idxs])
        preds=Xt@w
        best_i=idxs[int(np.argmax(preds))]
        daily.append(fee(samples[best_i][4],samples[best_i][5]))
    cum=1.0
    for r in daily: cum*=(1+r/100)
    test=[r for i,r in enumerate(daily) if all_dates[i]>='202604']
    tc=1.0
    for r in test: tc*=(1+r/100)
    wr=sum(1 for r in daily if r>0)/len(daily)*100
    print(f'{label:<35} 全量{cum:.3f}({(cum-1)*100:+.0f}%)  样本外{tc:.3f}({(tc-1)*100:+.1f}%)  胜率{wr:.0f}%')
    return cum,tc,daily

baseline=[]
for d1 in all_dates:
    idxs=daily_meta[d1]
    pc=CAPITAL/len(idxs)
    baseline.append(np.mean([fee(samples[i][4],samples[i][5]) for i in idxs]))
cb=1.0
for r in baseline: cb*=(1+r/100)
test_bl=[r for i,r in enumerate(baseline) if all_dates[i]>='202604']
tb=1.0
for r in test_bl: tb*=(1+r/100)
print(f'{"等权全买":<35} 全量{cb:.3f}({(cb-1)*100:+.0f}%)  样本外{tb:.3f}({(tb-1)*100:+.1f}%)')

print()
combos=[
    (['pb_depth','pc_vs_low','high_vs_pc','ma5_dev','ma5_bounce'],           'A_权重TOP5'),
    (['pb_depth','pc_vs_low','high_vs_pc','ma5_dev','vol_contract'],         'B_替换vol'),
    (['pb_depth','pc_vs_low','ma5_dev','ma20_dev','ma5_bounce'],             'C_均线为主'),
    (['pb_depth','lower_shadow','vol_contract','amplitude','ma5_bounce'],    'D_简单因子'),
    (['pb_depth','pc_vs_low','close_pos','vol_contract','amplitude'],        'E_无均线'),
    (['high_vs_pc','pc_vs_low','gap_open','close_pos','amplitude'],          'F_纯价格'),
    (['pb_depth','pc_vs_low','vol_contract','amplitude','ma5_bounce'],       'G_混合'),
    (['pb_depth','pc_vs_low','close_pos','vol_contract','ret_5d'],           'H_趋势'),
    (['pb_depth','pc_vs_low','ma5_dev','vol_contract','consec_up'],          'I_动量'),
]

best_cum=0; best_name=''; best_daily=[]
for keys,label in combos:
    cum,tc,daily=run_wf(keys,label)
    if tc>best_cum:
        best_cum=tc; best_name=label; best_daily=daily

print(f'\n样本外最优: {best_name}')

# 月度对比
print(f'\n{"月份":<8} {"等权全买":>10} {"岭回归":>10}')
mb=defaultdict(list); mlr=defaultdict(list)
for mi,d in enumerate(all_dates):
    if d<'202604': continue
    m=d[:6]; mb[m].append(baseline[mi]); mlr[m].append(best_daily[mi])
for m in sorted(mb.keys()):
    b=1.0; l=1.0
    for r in mb[m]: b*=(1+r/100)
    for r in mlr[m]: l*=(1+r/100)
    print(f'{m:<8} {(b-1)*100:>+9.2f}% {(l-1)*100:>+9.2f}%')
ts_bl=[r for i,r in enumerate(baseline) if all_dates[i]>='202604']
ts_lr=[r for i,r in enumerate(best_daily) if all_dates[i]>='202604']
cb2=1.0; cl2=1.0
for r in ts_bl: cb2*=(1+r/100)
for r in ts_lr: cl2*=(1+r/100)
print(f'{"合计":<8} {(cb2-1)*100:>+9.2f}% {(cl2-1)*100:>+9.2f}%')
