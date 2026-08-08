"""验证 pb_depth 14:56 vs 收盘差异是否改变当日选股排名"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
M5=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

def lk(code):
    fp=os.path.join(K,code);rows=[]
    with open(fp) as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'):continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit():continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),
                         float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}

_5m={}
def lm5(code):
    if code in _5m:return _5m[code]
    fp=os.path.join(M5,code)
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
            r1=rs[d1k];bp=r1[6];sc=r1[4]
            if bp<=0:continue
            r2=rs[d2k];r3=rs[d2k-1] if d2k>=1 else None
            if r3 is None:continue
            cl=np.array([r[4] for r in rs[:d2k+1]]);hi=np.array([r[2] for r in rs[:d2k+1]]);n=len(cl)
            f={}
            f['pb_depth']=(r3[4]-r2[4])/r3[4]*100 if r3[4]>0 else 0
            f['ma5_dev']=(r2[4]-np.mean(cl[-5:]))/np.mean(cl[-5:])*100 if n>=5 else 0
            if n>=10:
                tr=[]
                for i in range(d2k-9,d2k+1):
                    h=hi[i];l_=rs[i][3];pc=rs[i-1][4] if i>0 else rs[i][6]
                    tr.append(max(h-l_,abs(h-pc),abs(l_-pc)))
                atr=np.mean(tr)
            else:atr=r2[2]-r2[3] if r2[2]>r2[3] else 1
            f['pc_vs_low_atr']=(r2[6]-r2[3])/atr if atr>0 else 0
            f['high_vs_pc_atr']=(r2[2]-r2[6])/atr if atr>0 else 0
            mg=0
            if d2k>=10:
                ca=[r[4] for r in rs[:d2k+1]]
                ma5=np.mean(ca[-5:]);ma10=np.mean(ca[-10:])
                ma5p=np.mean(ca[-6:-1]);ma10p=np.mean(ca[-11:-1])
                mg=1 if(ma5p<=ma10p and ma5>ma10)else 0
            f['ma_golden']=mg
            sa.append((f,code,d1,bp,sc,name,r2[4],r3[4],d2))

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

rank_flips=0;total_days=0;all_flips=[]

for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:continue
    hist=[j for j in range(fi)]
    Xh=X[hist];yh=yt[hist]
    mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
    Xn=(Xh-mu)/sg;d_dim=Xn.shape[1]
    try:w=solve(Xn.T@Xn+np.eye(d_dim)*2.0,Xn.T@yh)
    except:continue
    Xt=np.array([(X[i]-mu)/sg for i in idxs]);preds=Xt@w
    ranked=np.argsort(-preds)
    if len(ranked)<2:continue

    cand1=sa[idxs[ranked[0]]];cand2=sa[idxs[ranked[1]]]
    d2=cand1[8]
    bars1=lm5(cand1[1]).get(d2,[])
    bars2=lm5(cand2[1]).get(d2,[])
    if not bars1 or len(bars1)<2 or not bars2 or len(bars2)<2:continue
    total_days+=1

    pre1=cand1[7];pre2=cand2[7]
    pb1_1456=(pre1-bars1[-2][3])/pre1*100
    pb1_close=(pre1-bars1[-1][3])/pre1*100
    pb2_1456=(pre2-bars2[-2][3])/pre2*100
    pb2_close=(pre2-bars2[-1][3])/pre2*100

    pb_w=w[0];pb_sg=sg[0]
    d1_adj=(pb1_1456-pb1_close)/pb_sg*pb_w
    d2_adj=(pb2_1456-pb2_close)/pb_sg*pb_w
    gap=preds[ranked[0]]-preds[ranked[1]]
    flip=d1_adj-d2_adj

    if abs(flip)>gap:
        rank_flips+=1
        all_flips.append({
            'date':d2,'name1':cand1[5],'name2':cand2[5],
            'gap':round(gap,4),'flip':round(flip,4),
            'pb1_1456':round(pb1_1456,2),'pb1_close':round(pb1_close,2)
        })

print(f'可验证天数: {total_days}')
print(f'排名翻转: {rank_flips}/{total_days} ({rank_flips/total_days*100:.1f}%)' if total_days else '0')
print()
if all_flips:
    print('翻转详情 (前10):')
    for fd in all_flips[:10]:
        print(f'  {fd["date"]} {fd["name1"]}→{fd["name2"]} gap={fd["gap"]} flip={fd["flip"]:+}')
else:
    print('✅ 14:56价格差异从未改变当日排名')
    print(f'  验证了{total_days}个交易日, #1和#2的评分差距始终大于pb偏差。')
