# -*- coding: utf-8 -*-
"""分析评分与收益/胜率的关系"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001
CAPITAL=100_000

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

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

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
            dm[d1].append(len(sa)-1)

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

def sd(bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o,'open_stop'
    if l<=st:return st,'low_stop'
    if h>=lu*0.999:return lu,'limit_up'
    return c,'close'

def trade(bp,sp,cap):
    shares=int(cap/bp/100)*100
    if shares<100:return None
    ba=bp*shares;sa_amt=sp*shares
    cost=ba*(1+CR);ret_amt=sa_amt*(1-CR-SD-TF)
    profit=ret_amt-cost
    return profit/cost*100,profit,cost,ret_amt,shares

# WF回测 + 记录评分
records=[]
for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:
        best=sa[idxs[0]];best_score=0
    else:
        hist=[j for j in range(fi)]
        Xh=X[hist];yh=yt[hist]
        mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
        Xn=(Xh-mu)/sg;d_dim=Xn.shape[1]
        try:w=solve(Xn.T@Xn+np.eye(d_dim)*2.0,Xn.T@yh)
        except:w=np.zeros(d_dim)
        Xt=np.array([(X[i]-mu)/sg for i in idxs])
        preds=Xt@w
        best=sa[idxs[int(np.argmax(preds))]]
        best_score=preds.max()

    code=best[1];name=best[5];bp=best[3]
    o=best[12];h=best[13];l=best[14];c=best[15]
    sp,mode=sd(bp,o,h,l,c)
    result=trade(bp,sp,1000000)  # 固定满仓, 排除资金影响
    if result is None:continue
    ret_pct=result[0]

    records.append({
        'date':d1_date,'name':name,'code':code,
        'score':best_score,'ret':ret_pct,'mode':mode,
        'pb':best[0]['pb_depth'],'bull':best[0]['high_vs_pc_atr'],
        'bear':best[0]['pc_vs_low_atr']
    })

# ====== 分析 ======
print('评分与收益分析 (271笔交易)')
print('='*70)

# 1. 相关性
scores=np.array([r['score'] for r in records])
rets=np.array([r['ret'] for r in records])
corr=np.corrcoef(scores,rets)[0,1]
print(f'\n1. 评分-收益 Pearson 相关系数: {corr:+.4f}')
print(f'   (0=无关, >0=正相关, <0=负相关)')
if abs(corr)<0.05:print('   → 几乎无关')
elif corr>0:print(f'   → 微弱正相关, 评分高→收益略高')
else:print(f'   → 微弱负相关, 评分高→收益略低')

# 2. 分档统计
print(f'\n2. 评分分档:')
bins=[-5,-1,-0.5,0,0.5,1,2,5]
print(f'  {"评分区间":<14} {"笔数":>6} {"胜率":>8} {"均收益":>8} {"中位收益":>8} {"涨停率":>8}')
print(f'  {"-"*55}')
for i in range(len(bins)-1):
    lo,hi=bins[i],bins[i+1]
    mask=(scores>=lo)&(scores<hi)
    cnt=mask.sum()
    if cnt==0:
        print(f'  [{lo:+.0f}, {hi:+.0f})     {"0":>6} {"—":>8} {"—":>8} {"—":>8} {"—":>8}')
        continue
    sub_r=rets[mask]
    sub_m=[r['mode'] for j,r in enumerate(records) if mask[j]]
    wr=sum(1 for r in sub_r if r>0)/cnt*100
    avg_r=np.mean(sub_r)
    med_r=np.median(sub_r)
    lu_rate=sum(1 for m in sub_m if m=='limit_up')/cnt*100
    bar='█'*max(1,int(cnt/3))
    print(f'  [{lo:+.0f}, {hi:+.0f})     {cnt:>6} {wr:>7.1f}% {avg_r:>+7.2f}% {med_r:>+7.2f}% {lu_rate:>7.1f}% {bar}')

# 3. 正分 vs 负分
print(f'\n3. 正分 vs 负分:')
pos_mask=scores>=0;neg_mask=scores<0
for label, mask in [('正分(≥0)',pos_mask),('负分(<0)',neg_mask)]:
    cnt=mask.sum()
    if cnt==0:continue
    sub_r=rets[mask]
    wr=sum(1 for r in sub_r if r>0)/cnt*100
    avg_r=np.mean(sub_r)
    med_r=np.median(sub_r)
    cum=1.0
    for r in sub_r:cum*=(1+r/100)
    print(f'  {label}: {cnt}笔  胜率{wr:.1f}%  均值{avg_r:+.2f}%  中位{med_r:+.2f}%  累计{((cum-1)*100):+.1f}%')

# 4. 分位数
print(f'\n4. 评分五分位:')
for q,label in [(0,'最低'),(1,'P25'),(2,'P50'),(3,'P75'),(4,'最高')]:
    if q==0:
        lo,q_hi=scores.min(),np.percentile(scores,25)
    elif q==4:
        lo,q_hi=np.percentile(scores,75),scores.max()
    else:
        lo=np.percentile(scores,25*q)
        q_hi=np.percentile(scores,25*(q+1))
    mask=(scores>=lo)&(scores<=q_hi)
    cnt=mask.sum()
    sub_r=rets[mask]
    wr=sum(1 for r in sub_r if r>0)/cnt*100
    avg_r=np.mean(sub_r)
    print(f'  {label:>4} ({lo:+.2f}~{q_hi:+.2f}): {cnt}笔  胜率{wr:.1f}%  均收益{avg_r:+.2f}%')

# 5. 评分是否能区分"大赢家"
print(f'\n5. 涨停日 vs 非涨停日 评分对比:')
lu_mask=np.array([r['mode']=='limit_up' for r in records])
no_lu_mask=~lu_mask
for label,mask in [('涨停日',lu_mask),('非涨停',no_lu_mask)]:
    cnt=mask.sum()
    if cnt==0:continue
    avg_s=np.mean(scores[mask])
    avg_r=np.mean(rets[mask])
    print(f'  {label}: {cnt}笔  平均评分{avg_s:+.3f}  平均收益{avg_r:+.2f}%')

# 6. 评分最高10% vs 最低10%
print(f'\n6. 评分Top10% vs Bottom10%:')
n=len(records)
idx_top=np.argsort(-scores)[:n//10]
idx_bot=np.argsort(scores)[:n//10]
for label,idx in [('Top10%',idx_top),('Bot10%',idx_bot)]:
    cnt=len(idx)
    sub_r=rets[idx]
    wr=sum(1 for r in sub_r if r>0)/cnt*100
    avg_r=np.mean(sub_r)
    cum=1.0
    for r in sub_r:cum*=(1+r/100)
    print(f'  {label}: {cnt}笔  胜率{wr:.1f}%  均收益{avg_r:+.2f}%  累计{((cum-1)*100):+.1f}%')
