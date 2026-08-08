"""5特征权重敏感性扫描"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S = r'C:\Lazy\李明学的大A\Data\Strategy'; K = r'C:\Lazy\李明学的大A\Data\1D'
FEATURES = ['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001; CM=0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

def load_kline(code):
    fp=os.path.join(K,code); rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'): continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds=sorted(tds); di={d:i for i,d in enumerate(tds)}

samples_all=[]
daily_meta=defaultdict(list)
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
            name,code=p[0],p[1]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]; bp=r1[6]; sp_c=r1[4]
            o1,h1,l1=r1[1],r1[2],r1[3]
            if bp<=0: continue
            r2=rows[d2i_k]; o2,h2,l2,c2,v2,pc2=r2[1],r2[2],r2[3],r2[4],r2[5],r2[6]
            r3=rows[d2i_k-1] if d2i_k>=1 else None
            cls=np.array([r[4] for r in rows[:d2i_k+1]])
            highs=np.array([r[2] for r in rows[:d2i_k+1]]); n=len(cls)
            f={}
            f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
            f['ma5_dev']=(c2-np.mean(cls[-5:]))/np.mean(cls[-5:])*100 if n>=5 else 0
            if n>=10:
                trs=[]
                for i in range(d2i_k-9,d2i_k+1):
                    h=highs[i]; l=rows[i][3]; pc=rows[i-1][4] if i>0 else rows[i][6]
                    trs.append(max(h-l,abs(h-pc),abs(l-pc)))
                atr10=np.mean(trs) if trs else 1
            else: atr10=h2-l2 if h2>l2 else 1
            f['pc_vs_low_atr']=(pc2-rows[d2i_k][3])/atr10 if atr10>0 else 0
            f['high_vs_pc_atr']=(h2-pc2)/atr10 if atr10>0 else 0
            ma_golden=0
            if d2i_k>=10:
                c_arr=[r[4] for r in rows[:d2i_k+1]]
                ma5=np.mean(c_arr[-5:]); ma10=np.mean(c_arr[-10:])
                ma5p=np.mean(c_arr[-6:-1]); ma10p=np.mean(c_arr[-11:-1])
                ma_golden=1 if(ma5p<=ma10p and ma5>ma10) else 0
            f['ma_golden']=ma_golden
            samples_all.append((f,code,d1,bp,sp_c,name,o1,h1,l1,o2,h2,l2,c2,pc2))
            daily_meta[d1].append(len(samples_all)-1)
samples_all.sort(key=lambda x:x[2])
daily_meta=defaultdict(list)
for i,s in enumerate(samples_all):
    daily_meta[s[2]].append(i)

X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples_all])
y_target=np.array([(s[4]-s[3])/s[3]*100 for s in samples_all])
all_dates=sorted(daily_meta.keys())

def sell_daily(bp,o,h,l,c):
    limit_up=round(bp*1.10,2); stop=bp*0.94
    if o>0 and o<=stop: return o,'open_stop'
    if l<=stop: return stop,'low_stop'
    if h>=limit_up*0.999: return limit_up,'limit_up'
    return c,'close'

def fee(bp,sp,capital):
    buy_s=capital*CR+int(capital/bp/100)*100*SD
    shares=int(capital/bp/100)*100
    sell_s=shares*sp*(CR+SD)+TF
    return (shares*(sp-bp)-buy_s-sell_s)/capital*100, shares

def backtest_with_fixed_w(fixed_w):
    """用固定权重(非WF)回测"""
    consec_loss=0; cum=1.0; peak=1.0; max_dd=0.0
    skip_count=0; rets=[]

    for d1_date in all_dates:
        idxs=daily_meta[d1_date]
        first_i=idxs[0]
        if first_i<100:
            best=samples_all[idxs[0]]
        else:
            # 用固定权重评分
            hist=[j for j in range(first_i)]
            Xh=X[hist]; yh=y_target[hist]
            mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
            Xt=np.array([(X[i]-mean)/std for i in idxs])
            preds=Xt @ fixed_w
            best=samples_all[idxs[int(np.argmax(preds))]]

        bp=best[3]; o=best[6]; h=best[7]; l=best[8]; c_d=best[4]
        cap=CAPITAL
        if consec_loss>=3: consec_loss=0; skip_count+=1; rets.append(0.0); continue
        elif consec_loss>=2: cap=CAPITAL*0.5
        sp,mode=sell_daily(bp,o,h,l,c_d)
        ret,sh=fee(bp,sp,cap)
        cum*=(1+ret/100); rets.append(ret)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd: max_dd=dd
        if ret<-0.05: consec_loss+=1
        elif ret>0.05: consec_loss=0

    return cum, max_dd

# ---- 基线: 全量WF训练的"平均"权重 ----
X_full_mean=X.mean(axis=0); X_full_std=X.std(axis=0)+1e-8
Xn_full=(X-X_full_mean)/X_full_std
w_baseline=solve(Xn_full.T@Xn_full+np.eye(5)*2.0,Xn_full.T@y_target)

print('=== 5特征全量WF权重 ===')
for nm,wt in zip(FEATURES,w_baseline):
    print(f'  {nm}: {wt:+.4f}')

baseline_nv, baseline_dd = backtest_with_fixed_w(w_baseline)
print(f'\n基线净值: {baseline_nv:.4f}  回撤: {baseline_dd:.1f}%')
print()

# ---- 逐一扰动 ±5%, ±10%, ±20%, ±30% ----
perturbations = [-0.30, -0.20, -0.10, -0.05, 0.0, +0.05, +0.10, +0.20, +0.30]
results = {}

for fi, feat_name in enumerate(FEATURES):
    nvs = []
    print(f'{feat_name}:')
    print(f'  {"扰动":>8}  {"净值":>8}  {"vs基线":>8}')
    for p in perturbations:
        w_test = w_baseline.copy()
        w_test[fi] = w_baseline[fi] * (1 + p)
        nv, dd = backtest_with_fixed_w(w_test)
        delta = (nv - baseline_nv) / baseline_nv * 100
        marker = ' ◄ 最优' if p == 0 else ''
        print(f'  {p:>+8.0%}  {nv:>8.4f}  {delta:>+7.2f}%{marker}')
        nvs.append((p, nv))
    results[feat_name] = nvs
    print()

# 找最优单体扰动
print('=== 各特征最优单体扰动 ===')
best_pert = {}
for feat_name, nvs in results.items():
    best = max(nvs, key=lambda x: x[1])
    base_nv = [nv for p,nv in nvs if p==0][0]
    improvement = (best[1] - base_nv) / base_nv * 100
    print(f'  {feat_name}: {best[0]:+5.0%} → 净值{best[1]:.4f} ({improvement:+.2f}%)')
    best_pert[feat_name] = best[0]

# 组合最优
w_combined = w_baseline.copy()
for fi, feat_name in enumerate(FEATURES):
    w_combined[fi] *= (1 + best_pert[feat_name])

nv_combined, dd_combined = backtest_with_fixed_w(w_combined)
delta = (nv_combined - baseline_nv) / baseline_nv * 100
print(f'\n组合最优: 净值 {nv_combined:.4f} ({delta:+.2f}% vs 基线)')
print(f'  权重: {np.array2string(w_combined, precision=3)}')
