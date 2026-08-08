"""连亏统计"""
import os,numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001;CAPITAL=1_000_000

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

def fee(bp,sp,cap):
    sh=int(cap/bp/100)*100
    return (sp*sh*(1-CR-SD-TF)-bp*sh*(1+CR))/(bp*sh)*100

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

rets=[]
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
    bp=best[3];o=best[6];h=best[7];l=best[8];c=best[4]
    sp,mode=sd(bp,o,h,l,c)
    ret=fee(bp,sp,CAPITAL)
    rets.append((d1_date,ret,best[5],best[1],mode,sp,bp))

streaks=defaultdict(list)
cs=[]
for date,ret,name,code,mode,sp,bp in rets:
    if ret<0:cs.append((date,ret,name,code,mode,sp,bp))
    else:
        if cs:streaks[len(cs)].append(cs)
        cs=[]
if cs:streaks[len(cs)].append(cs)

print('=== 连亏分布 ===')
ts=sum(len(v) for v in streaks.values())
tl=sum(k*len(v) for k,v in streaks.items())
print(f'总亏损: {sum(1 for _,r,_,_,_,_,_ in rets if r<0)}笔')
print(f'总盈利: {sum(1 for _,r,_,_,_,_,_ in rets if r>=0)}笔')
print(f'连亏序列: {ts}个')
print()
print('{:10s} {:>8s} {:>8s} {:>8s}'.format('连亏长度','次数','占比','占总亏'))
for k in sorted(streaks.keys()):
    cnt=len(streaks[k])
    pct=cnt/ts*100 if ts else 0
    lpct=k*cnt/tl*100 if tl else 0
    bar=chr(9608)*cnt
    print('{:4d}     {:>8d} {:>7.1f}% {:>7.1f}% {}'.format(k,cnt,pct,lpct,bar))

print()
print('=== 连亏>=3 详情 ===')
for k in sorted(streaks.keys()):
    if k<3:continue
    for i,seq in enumerate(streaks[k],1):
        tl2=sum(r for _,r,_,_,_,_,_ in seq)
        print('\n序列{}: {}连亏 合计{:+.1f}%'.format(i,k,tl2))
        for date,ret,name,code,mode,sp,bp in seq:
            print('  {} {}({}) 买{:.2f} 卖{:.2f} 亏{:+.2f}% [{}]'.format(date,name,code,bp,sp,ret,mode))
