#!/usr/bin/env python3
"""回测对比: 5特征(无vol_contract) vs 6特征"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
CR=0.0001; CM=0.0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000
FEATURES_6 = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
FEATURES_5 = ['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

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

samples_6=[]
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
            r1=rows[d1i_k]; bp=r1[6]; sp_close=r1[4]
            if bp<=0: continue
            r2=rows[d2i_k]; o2,h2,l2,c2,v2,pc2=r2[1],r2[2],r2[3],r2[4],r2[5],r2[6]
            r3=rows[d2i_k-1] if d2i_k>=1 else None
            cls=np.array([r[4] for r in rows[:d2i_k+1]])
            highs=np.array([r[2] for r in rows[:d2i_k+1]]); n=len(cls)
            f={}
            f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
            d2_vol_adj = v2 * 0.978
            f['vol_contract']=(r3[5]-d2_vol_adj)/r3[5]*100 if(r3 and r3[5]>0) else 0
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
            samples_6.append((f,code,d1,bp,sp_close,name,rows[d1i_k][1],rows[d1i_k][2],rows[d1i_k][3]))
samples_6.sort(key=lambda x:x[2])

def fee(buy, sell, capital):
    sh = int(capital / buy / 100) * 100
    if sh == 0: sh = 100
    c = sh * buy; bf = max(c * CR, CM) + c * TF; tb = c + bf
    r = sh * sell; sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100, sh

def sell_daily(bp, o, h, l, c):
    limit_up = round(bp * 1.10, 2); stop = bp * 0.94
    if o <= stop: return o, 'open_stop'
    if l <= stop: return stop, 'low_stop'
    if h >= limit_up * 0.999: return limit_up, 'limit_up'
    return c, 'close'

def backtest(samples, features):
    daily_meta=defaultdict(list)
    for i,s in enumerate(samples): daily_meta[s[2]].append(i)
    all_dates=sorted(daily_meta.keys())
    X=np.array([[s[0].get(k,0) for k in features] for s in samples])
    y=np.array([(s[4]-s[3])/s[3]*100 for s in samples])
    
    cum=1.0; peak=1.0; max_dd=0.0; wins=0; total_trade=0; consec=0
    monthly={}
    for d1_date in all_dates:
        idxs=daily_meta[d1_date]; first_i=idxs[0]
        if first_i<100:
            best=samples[idxs[0]]
        else:
            hist=[j for j in range(first_i)]
            Xh=X[hist]; yh=y[hist]
            mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
            Xn=(Xh-mean)/std; d=Xn.shape[1]
            try: w=solve(Xn.T@Xn+np.eye(d)*2.0,Xn.T@yh)
            except: w=np.zeros(d)
            Xt=np.array([(X[i]-mean)/std for i in idxs]); preds=Xt@w
            best=samples[idxs[int(np.argmax(preds))]]
        bp=best[3]; o=best[6]; h=best[7]; l=best[8]; c_d=best[4]
        cap=CAPITAL
        m=d1_date[:6]
        if consec>=3: consec=0; monthly.setdefault(m,[]).append(0)
        elif consec>=2:
            cap=CAPITAL*0.5; sp,mode=sell_daily(bp,o,h,l,c_d); ret,sh=fee(bp,sp,cap)
            cum*=(1+ret/100); total_trade+=1
            if ret<-0.05: consec+=1
            elif ret>0.05: consec=0
            if ret>0: wins+=1
            monthly.setdefault(m,[]).append(ret)
        else:
            sp,mode=sell_daily(bp,o,h,l,c_d); ret,sh=fee(bp,sp,cap)
            cum*=(1+ret/100); total_trade+=1
            if ret<-0.05: consec+=1
            elif ret>0.05: consec=0
            if ret>0: wins+=1
            monthly.setdefault(m,[]).append(ret)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd: max_dd=dd
    wr = wins/total_trade*100 if total_trade else 0
    return cum, (cum-1)*100, max_dd, wr, monthly

print("回测中...")
nv6,ret6,dd6,wr6,monthly6 = backtest(samples_6, FEATURES_6)
nv5,ret5,dd5,wr5,monthly5 = backtest(samples_6, FEATURES_5)

print(f"\n{'':12} {'5特征(无vol)':>14} {'6特征':>14} {'差异':>10}")
print(f"{'净值':12} {nv5:>14.4f} {nv6:>14.4f} {(nv5/nv6-1)*100:>+9.2f}%")
print(f"{'收益':12} {ret5:>+13.1f}% {ret6:>+13.1f}%")
print(f"{'胜率':12} {wr5:>13.1f}% {wr6:>13.1f}%")
print(f"{'最大回撤':12} {dd5:>13.1f}% {dd6:>13.1f}%")

# 月度对比差异
print(f"\n{'月份':8} {'5特征':>10} {'6特征':>10} {'差异':>8}")
common = sorted(set(monthly5.keys()) & set(monthly6.keys()))
for m in common:
    m5 = 1.0
    for r in monthly5[m]: m5*=(1+r/100)
    m6 = 1.0
    for r in monthly6[m]: m6*=(1+r/100)
    diff = ((m5-1)-(m6-1))*100
    if abs(diff) > 0.5:
        print(f"{m[:4]}-{m[4:]:<3} {(m5-1)*100:>+9.2f}% {(m6-1)*100:>+9.2f}% {diff:>+7.2f}pp")
print(f"\n结论: 去掉vol_contract净值变化 {(nv5/nv6-1)*100:+.1f}%")
