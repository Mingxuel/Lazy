"""5M回测: 尾盘不同时间点卖出"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'; S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001;CAPITAL=1_000_000
SELL_BARS=range(1,9)  # 倒数第1~8根(15:00~14:25)

def lk(code):
    fp=os.path.join(K,code);rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith(chr(65279)):continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit():continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}

def lm(code):
    fp=os.path.join(M5DIR,code)
    if not os.path.exists(fp):return{}
    bd=defaultdict(list)
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','')
            bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    return dict(bd)

def fee(bp,sp,cap):
    sh=int(cap/bp/100)*100;ba=bp*sh;sa=sp*sh
    return (sa-sa*(CR+SD+TF)-ba*(1+CR))/ba*100

def sd(bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o,'open_stop'
    if l<=st:return st,'low_stop'
    if h>=lu*0.999:return lu,'limit_up'
    return c,'close'

# 加载样本
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
            rs,dx=lk(code)
            d1k=dx.get(d1);d2k=dx.get(d2)
            if d1k is None or d2k is None:continue
            r1=rs[d1k];bp=r1[6];sc=r1[4]
            if bp<=0:continue
            r2=rs[d2k];r3=rs[d2k-1] if d2k>=1 else None
            if r3 is None:continue
            cl=np.array([r[4] for r in rs[:d2k+1]])
            hi=np.array([r[2] for r in rs[:d2k+1]]);n=len(cl)
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
            sa.append((f,code,d1,bp,sc,name,r1[1],r1[2],r1[3],r2[4]))

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())

X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

# 预加载5M
print(f'样本:{len(sa)} 交易日:{len(ad)}')
print('加载5M...')
m5={}
for code in set(s[1] for s in sa):
    d=lm(code)
    if d:m5[code]=d
print(f'5M覆盖{len(m5)}只')

# 取样本看时间
scode=list(m5.keys())[0]
sdate=sorted(m5[scode].keys())[-1]
sbar=m5[scode][sdate]
print(f'5M结构: {sbar[-1][:1]} bar, 末={sdate}, len={len(sbar)}')
for i,b in enumerate(sbar[-8:],len(sbar)-7):
    o,h,l,c=b
    print(f'  #{i}: C={c:.4f}')

# 回测
con=[0]*len(SELL_BARS);cv=[1.0]*len(SELL_BARS)
pk=[1.0]*len(SELL_BARS);dd=[0.0]*len(SELL_BARS)
tc=[0]*len(SELL_BARS);win=[0]*len(SELL_BARS)

for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:best=sa[idxs[0]]
    else:
        hist=[j for j in range(fi)]
        Xh=X[hist];yh=yt[hist]
        mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
        Xn=(Xh-mu)/sg;d=Xn.shape[1]
        try:w=solve(Xn.T@Xn+np.eye(d)*2.0,Xn.T@yh)
        except:w=np.zeros(d)
        Xt=np.array([(X[i]-mu)/sg for i in idxs])
        best=sa[idxs[int(np.argmax(Xt@w))]]
    
    bp=best[3];o=best[6];h=best[7];l=best[8];c1d=best[4];code=best[1]
    sp1d,mode1d=sd(bp,o,h,l,c1d)
    bars5=m5.get(code,{}).get(d1_date,[])
    
    for ti,nb in enumerate(SELL_BARS):
        if con[ti]>=3:con[ti]=0;continue
        cap=CAPITAL*(0.5 if con[ti]>=2 else 1)
        
        if mode1d in('open_stop','low_stop','limit_up'):
            sp=sp1d;mode=mode1d
        else:
            if len(bars5)>=nb and nb<=len(bars5):
                b5=bars5[-nb];c5m=b5[3]
                if c1d>0 and bars5[-1][3]>0:
                    scale=c1d/bars5[-1][3]
                else:scale=1.0
                sp=c5m*scale;mode=f'{nb}'
            else:
                sp=c1d;mode=f'{nb}(1D)'
        
        ret=fee(bp,sp,cap)
        tc[ti]+=1
        if ret>0:win[ti]+=1
        cv[ti]*=(1+ret/100)
        if cv[ti]>pk[ti]:pk[ti]=cv[ti]
        ddd=(cv[ti]-pk[ti])/pk[ti]*100
        if ddd<dd[ti]:dd[ti]=ddd
        if ret<-0.05:con[ti]+=1
        elif ret>0.05:con[ti]=0

# 时间标签
times={}
for nb in SELL_BARS:
    idx=len(sbar)-nb
    if idx>=0:times[nb]=f'{sbar[idx][0]:.0f}:00'[:5]
    else:times[nb]=f'T-{nb}'

# 输出
print()
print('='*85)
print(f'{"卖出时间":<12} {"净值":>8} {"收益":>10} {"胜率":>7} {"回撤":>7} {"笔":>5} {"vs15:00差"}')
print('-'*85)
ref=cv[0]
for ti,nb in enumerate(SELL_BARS):
    wr=win[ti]/tc[ti]*100 if tc[ti]>0 else 0
    diff=cv[ti]-ref
    label=times.get(nb,str(nb))
    print(f'{label:<12} {cv[ti]:>8.4f} {(cv[ti]-1)*100:>+9.2f}% {wr:>6.1f}% {dd[ti]:>+6.1f}% {tc[ti]:>5} {diff:>+9.4f}')

# 月度
best_ti=max(range(len(SELL_BARS)),key=lambda i:cv[i])
best_n=SELL_BARS[best_ti]
print(f'\n最佳: 倒数第{best_n}根({times.get(best_n,"?")}) 净值{cv[best_ti]:.4f}')
print(f'\n{"月":<8} {"收益":>10} {"累计":>10}')
mb=defaultdict(list);con2=0
for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:best=sa[idxs[0]]
    else:
        hist=[j for j in range(fi)]
        Xh=X[hist];yh=yt[hist]
        mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
        Xn=(Xh-mu)/sg;d=Xn.shape[1]
        try:w2=solve(Xn.T@Xn+np.eye(d)*2.0,Xn.T@yh)
        except:w2=np.zeros(d)
        Xt=np.array([(X[i]-mu)/sg for i in idxs])
        best=sa[idxs[int(np.argmax(Xt@w2))]]
    bp=best[3];o=best[6];h=best[7];l=best[8];c1d=best[4];code=best[1]
    sp1d,m1d=sd(bp,o,h,l,c1d)
    if m1d in('open_stop','low_stop','limit_up'):sp=sp1d
    else:
        bars5=m5.get(code,{}).get(d1_date,[])
        if len(bars5)>=best_n and c1d>0 and bars5[-1][3]>0:
            sp=bars5[-best_n][3]*(c1d/bars5[-1][3])
        else:sp=c1d
    if con2>=3:con2=0;continue
    cap=CAPITAL*(0.5 if con2>=2 else 1)
    ret=fee(bp,sp,cap)
    mb[d1_date[:6]].append(ret)
    if ret<-0.05:con2+=1
    elif ret>0.05:con2=0

cum2=1.0
for m in sorted(mb.keys()):
    mr=1.0
    for rv in mb[m]:mr*=(1+rv/100)
    cum2*=mr
    if m>='202601':print(f'{m[:4]}-{m[4:]:<3} {(mr-1)*100:>+9.2f}% {cum2:>10.4f}')
