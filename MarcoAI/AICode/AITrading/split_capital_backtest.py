"""分仓买入回测: #1#2评分接近时平分资金"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001;CAP=1_000_000

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

def fee(bp,sp,cap):
    sh=int(cap/bp/100)*100
    return (sp*sh*(1-CR-SD-TF)-bp*sh*(1+CR))/(bp*sh)*100,sh,sp*sh

def sd(bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o,'open_stop'
    if l<=st:return st,'low_stop'
    if h>=lu*0.999:return lu,'limit_up'
    return c,'close'

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
            sa.append((f,code,d1,bp,sc,name,r1[1],r1[2],r1[3],r2[4],d2,r3[4]))

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

def run_split(thresh):
    """thresh: #1#2评分差<此值时分仓买入"""
    consec=0;cum=1.0;peak=1.0;max_dd=0.0
    trades=[];split_days=0;m_data=defaultdict(list)
    
    for d1_date in ad:
        idxs=dm[d1_date];fi=idxs[0]
        if fi<100:best=sa[idxs[0]];picks=[best];cap_frac=[1.0]
        else:
            hist=[j for j in range(fi)]
            Xh=X[hist];yh=yt[hist]
            mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
            Xn=(Xh-mu)/sg;d_dim=Xn.shape[1]
            try:w=solve(Xn.T@Xn+np.eye(d_dim)*2.0,Xn.T@yh)
            except:continue
            Xt=np.array([(X[i]-mu)/sg for i in idxs]);preds=Xt@w
            ranked=np.argsort(-preds)
            
            if len(ranked)>=2:
                gap=preds[ranked[0]]-preds[ranked[1]]
            else:
                gap=999
            
            if len(ranked)>=2 and gap<thresh:
                # 分仓: #1和#2各半
                picks=[sa[idxs[ranked[0]]],sa[idxs[ranked[1]]]]
                cap_frac=[0.5,0.5]
                split_days+=1
            else:
                picks=[sa[idxs[ranked[0]]]]
                cap_frac=[1.0]
        
        if consec>=3:consec=0;continue
        
        for pk,cf in zip(picks,cap_frac):
            bp=pk[3];o=pk[6];h=pk[7];l=pk[8];c=pk[4]
            sp,mode=sd(bp,o,h,l,c)
            cap_used=CAP*cf
            if consec>=2:cap_used*=0.5
            
            ret,sh,amt=fee(bp,sp,cap_used)
            cum*=(1+ret/100)
            if cum>peak:peak=cum
            dd=(cum-peak)/peak*100
            if dd<max_dd:max_dd=dd
            m=d1_date[:6]
            m_data[m].append(ret)
            
            if ret<-0.05:consec+=1
            elif ret>0.05:consec=0
    
    return cum,max_dd,split_days,m_data

# Baseline
print('分仓阈值扫描 (基线=12.55)...')
print(f'{"阈值":<8} {"净值":>8} {"收益":>9} {"回撤":>7} {"分仓天数":>8}')
print('-'*48)

results={}
for th in [0.05,0.08,0.10,0.12,0.15,0.20,0.30,0.50,0.80,1.00,999]:
    cum,dd,sd_days,m_data=run_split(th)
    tr=(cum-1)*100
    vs_baseline=(cum/12.55-1)*100
    results[th]=(cum,dd,sd_days,vs_baseline)
    flag=' ←' if cum>12.55 else ''
    print(f'{th:<8.2f} {cum:>8.2f} {tr:>+8.1f}% {dd:>+6.1f}% {sd_days:>8}{flag}')

# Find best
best_th=max(results,key=lambda t:results[t][0])
print()
print(f'最优阈值: {best_th:.2f} (净值{results[best_th][0]:.2f}, 分仓{results[best_th][2]}天)')

# Show score gap distribution
print()
print('=== 每日#1#2评分差距分布 ===')
gaps=[]
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
    if len(ranked)>=2:
        gaps.append(preds[ranked[0]]-preds[ranked[1]])

gaps=np.array(gaps)
print(f'样本: {len(gaps)}')
print(f'均值={np.mean(gaps):.3f}  中位数={np.median(gaps):.3f}')
print(f'P10={np.percentile(gaps,10):.3f}  P25={np.percentile(gaps,25):.3f}  P50={np.median(gaps):.3f}  P75={np.percentile(gaps,75):.3f}  P90={np.percentile(gaps,90):.3f}')
for th in [0.05,0.10,0.15,0.20,0.30,0.50]:
    cnt=(gaps<th).sum()
    print(f'  gap<{th:.2f}: {cnt}/{len(gaps)} ({cnt/len(gaps)*100:.1f}%)')
