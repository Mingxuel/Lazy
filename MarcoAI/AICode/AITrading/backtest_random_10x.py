# -*- coding: utf-8 -*-
"""311 随机选股 ×10次回测 — 对照 WF 评分"""
import os, numpy as np, random
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001; CM=0.0; SD=0.0005; TF=0.00001
INIT_CAPITAL=100_000
N_RUNS=10

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
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','')
            bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    _5m[code]=dict(bd)
    return _5m[code]

def get_bar(code,d2_date,offset):
    bars=lm5(code).get(d2_date,[])
    if len(bars)>=abs(offset):return bars[offset]
    return None

def trade(bp,sp,capital):
    shares=int(capital/bp/100)*100
    if shares<100:return None
    buy_amt=bp*shares
    comm_buy=buy_amt*CR
    sell_amt=sp*shares
    comm_sell=sell_amt*CR
    stamp=sell_amt*SD
    tfee=sell_amt*TF
    total_cost=buy_amt+comm_buy
    total_return=sell_amt-comm_sell-stamp-tfee
    profit=total_return-total_cost
    ret_pct=profit/total_cost*100
    return ret_pct, profit, total_cost, total_return, shares

def sell_decision(bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o,'open_stop'
    if l<=st:return bp*0.94,'low_stop'
    if h>=lu*0.999:return lu,'limit_up'
    return c,'close'

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

# ====== 构建样本 (只建一次) ======
sa=[];dm=defaultdict(list)
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<3:continue
    d2=tds[d1i-1]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<2:continue
            code=p[1];name=p[0]
            rs,dx=lk(code);d1k=dx.get(d1);d2k=dx.get(d2)
            if d1k is None or d2k is None:continue
            r1=rs[d1k];bp=r1[6];sp_c=r1[4]
            if bp<=0:continue
            r2=rs[d2k];r3=rs[d2k-1] if d2k>=1 else None
            if r3 is None:continue
            bar55=get_bar(code,d2,-2)
            if bar55 is None:bar55=(r2[1],r2[2],r2[3],r2[4])
            o5,h5,l5,c5=bar55
            pre_pb=r3[4]
            cl=np.array([r[4] for r in rs[:d2k+1]])
            hi=np.array([r[2] for r in rs[:d2k+1]]);n=len(cl)
            f={}
            f['pb_depth']=(r3[4]-c5)/r3[4]*100 if r3[4]>0 else 0
            f['ma5_dev']=(c5-np.mean(cl[-5:]))/np.mean(cl[-5:])*100 if n>=5 else 0
            if n>=10:
                tr=[]
                for i in range(d2k-9,d2k+1):
                    hh=hi[i];l_=rs[i][3];pc=rs[i-1][4] if i>0 else rs[i][6]
                    tr.append(max(hh-l_,abs(hh-pc),abs(l_-pc)))
                atr=np.mean(tr)
            else:atr=r2[2]-r2[3] if r2[2]>r2[3] else 1
            f['pc_vs_low_atr']=(pre_pb-l5)/atr if atr>0 else 0
            f['high_vs_pc_atr']=(h5-pre_pb)/atr if atr>0 else 0
            mg=0
            if d2k>=10:
                ca=[r[4] for r in rs[:d2k+1]]
                ma5=np.mean(ca[-5:]);ma10=np.mean(ca[-10:])
                ma5p=np.mean(ca[-6:-1]);ma10p=np.mean(ca[-11:-1])
                mg=1 if(ma5p<=ma10p and ma5>ma10)else 0
            f['ma_golden']=mg
            sa.append((f,code,d1,bp,sp_c,name,o5,h5,l5,c5,pre_pb,d2,
                       r1[1],r1[2],r1[3],r1[4]))

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

def run_once(seed):
    """一次随机选股回测"""
    rng=random.Random(seed)
    consec=0
    asset=INIT_CAPITAL
    peak=INIT_CAPITAL
    max_dd=0.0
    trades=[]

    for d1_date in ad:
        idxs=dm[d1_date]
        # 随机选一只
        chosen=rng.choice(idxs)
        best=sa[chosen]
        code=best[1];name=best[5];bp=best[3]
        o=best[12];h=best[13];l=best[14];c=best[15]

        # 仓位管理
        if consec>=3:
            trades.append({'date':d1_date,'ret':0,'asset':asset,'mode':'skip'})
            consec=0;continue

        factor=0.5 if consec>=2 else 1.0
        capital_use=asset*factor
        sp,mode=sell_decision(bp,o,h,l,c)
        result=trade(bp,sp,capital_use)
        if result is None:
            trades.append({'date':d1_date,'ret':0,'asset':asset,'mode':'funds'})
            continue

        ret_pct,profit,buy_amt,sell_amt,shares=result
        asset+=profit
        if asset>peak:peak=asset
        dd=(asset-peak)/peak*100
        if dd<max_dd:max_dd=dd

        if ret_pct<-0.05:consec+=1
        elif ret_pct>0.05:consec=0

        trades.append({'date':d1_date,'ret':ret_pct,'asset':asset,'mode':mode})

    trade_recs=[t for t in trades if t['mode']!='skip']
    wr=sum(1 for t in trade_recs if t['ret']>0)/len(trade_recs)*100 if trade_recs else 0
    return asset, max_dd, len(trade_recs), wr

print("随机选股 ×10次...")
print(f"{'次数':<6} {'最终资产':>14} {'净值':>8} {'总收益':>8} {'最大回撤':>8} {'笔数':>6} {'胜率':>8}")
print("-"*65)

results=[]
for run in range(N_RUNS):
    seed=run*42+1
    final,dd,n,wr=run_once(seed)
    nv=final/INIT_CAPITAL
    results.append((final,nv,dd,n,wr))
    pct=(nv-1)*100
    print(f"  #{run+1:<4} ¥{final:>12,.0f} {nv:>8.4f} {pct:>+7.1f}% {dd:>7.1f}% {n:>6} {wr:>7.1f}%")

# 统计
finals=[r[0] for r in results]
nvs=[r[1] for r in results]
dds=[r[2] for r in results]
ns=[r[3] for r in results]
wrs=[r[4] for r in results]

print()
print(f"{'平均':<6} ¥{np.mean(finals):>12,.0f} {np.mean(nvs):>8.4f} {(np.mean(nvs)-1)*100:>+7.1f}% {np.mean(dds):>7.1f}% {np.mean(ns):>6.0f} {np.mean(wrs):>7.1f}%")
print(f"{'中位':<6} ¥{np.median(finals):>12,.0f} {np.median(nvs):>8.4f} {(np.median(nvs)-1)*100:>+7.1f}% {np.median(dds):>7.1f}% {np.median(ns):>6.0f} {np.median(wrs):>7.1f}%")
print(f"{'最差':<6} ¥{min(finals):>12,.0f} {min(nvs):>8.4f} {(min(nvs)-1)*100:>+7.1f}% {max(dds):>7.1f}% {min(ns):>6} {min(wrs):>7.1f}%")
print(f"{'最佳':<6} ¥{max(finals):>12,.0f} {max(nvs):>8.4f} {(max(nvs)-1)*100:>+7.1f}% {min(dds):>7.1f}% {max(ns):>6} {max(wrs):>7.1f}%")
print()
print(f"  WF评分版: ¥786,779  净值7.87  +686.8%")
print(f"  随机均值: ¥{np.mean(finals):,.0f}  净值{np.mean(nvs):.2f}  +{(np.mean(nvs)-1)*100:.1f}%")
print(f"  WF vs 随机: ×{7.87/np.mean(nvs):.1f}")
