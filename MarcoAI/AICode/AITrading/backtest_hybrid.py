import os,numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;SD=0.0005;TF=0.00001;INIT=100_000

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
            l=l.strip();p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','');bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    _5m[code]=dict(bd);return _5m[code]
def get_bar(code,d,o):
    bars=lm5(code).get(d,[])
    if len(bars)>=abs(o):return bars[o]
    return None
def tr(bp,sp,cpt):
    sh=int(cpt/bp/100)*100
    if sh<100:return None
    b=sh*bp;cb=b*CR;sa=sh*sp;cs=sa*CR;st=sa*SD;tf=sa*TF
    return ((sa-cs-st-tf-b-cb)/(b+cb)*100,sa-cs-st-tf-b-cb)
def sd(bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o
    if l<=st:return bp*0.94
    if h>=lu*0.999:return lu
    return c

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

sa=[];dm=defaultdict(list)
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    d2=tds[d1i-1];d4=tds[d1i-3]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip();p=l.split('|')
            if len(p)<2:continue
            code=p[1];name=p[0]
            bars=lm5(code).get(d4,[])
            rs,dx=lk(code);d1k=dx.get(d1);d2k=dx.get(d2);d4k=dx.get(d4)
            if d1k is None or d2k is None:continue
            if d4k is not None and d4k>0 and len(bars)>=6:
                d4_lu=round(rs[d4k-1][4]*1.10,2);early=False
                for bi in range(min(6,len(bars))):
                    if bars[bi][2]>=d4_lu*0.999:early=bi<=5;break
                if early:continue
            r1=rs[d1k];bp=r1[6];sp_c=r1[4]
            if bp<=0:continue
            r2=rs[d2k];r3=rs[d2k-1] if d2k>=1 else None
            if r3 is None:continue
            bar55=get_bar(code,d2,-2)
            if bar55 is None:bar55=(r2[1],r2[2],r2[3],r2[4])
            o5,h5,l5,c5=bar55;pre_pb=r3[4]
            cl=np.array([r[4] for r in rs[:d2k+1]]);hi=np.array([r[2] for r in rs[:d2k+1]]);n=len(cl)
            f={}
            f['pb_depth']=(r3[4]-c5)/r3[4]*100 if r3[4]>0 else 0
            f['ma5_dev']=(c5-np.mean(cl[-5:]))/np.mean(cl[-5:])*100 if n>=5 else 0
            if n>=10:
                trs=[max(hi[i]-rs[i][3],abs(hi[i]-rs[i-1][4]) if i>0 else abs(hi[i]-rs[i][6]),abs(rs[i][3]-rs[i-1][4]) if i>0 else abs(rs[i][3]-rs[i][6])) for i in range(d2k-9,d2k+1)]
                atr=np.mean(trs)
            else:atr=r2[2]-r2[3] if r2[2]>r2[3] else 1
            f['pc_vs_low_atr']=(pre_pb-l5)/atr if atr>0 else 0
            f['high_vs_pc_atr']=(h5-pre_pb)/atr if atr>0 else 0
            mg=0
            if d2k>=10:
                ca=[r[4] for r in rs[:d2k+1]]
                m5=np.mean(ca[-5:]);m10=np.mean(ca[-10:]);m5p=np.mean(ca[-6:-1]);m10p=np.mean(ca[-11:-1])
                mg=1 if(m5p<=m10p and m5>m10)else 0
            f['ma_golden']=mg
            sa.append((f,code,d1,bp,sp_c,name,o5,h5,l5,c5,pre_pb,d2,r1[1],r1[2],r1[3],r1[4]))
sa.sort(key=lambda x:x[2])
for i,s in enumerate(sa):dm[s[2]].append(i)
ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

# === A: WF全选(基准) ===
consec=0;asset=INIT;peak=INIT;max_dd=0.0;skips=0;trades=0
for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:best=sa[idxs[0]]
    else:
        hist=[j for j in range(fi)];Xh=X[hist];yh=yt[hist];mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
        Xn=(Xh-mu)/sg
        try:w=solve(Xn.T@Xn+np.eye(Xn.shape[1])*2.0,Xn.T@yh)
        except:w=np.zeros(Xn.shape[1])
        Xt=np.array([(X[j]-mu)/sg for j in idxs]);best=sa[idxs[int(np.argmax(Xt@w))]]
    if consec>=3:consec=0;skips+=1;continue
    factor=0.5 if consec>=2 else 1.0
    r=tr(best[3],sd(best[3],best[12],best[13],best[14],best[15]),asset*factor)
    if r is None:skips+=1;continue
    ret_pct,profit=r
    asset+=profit
    if asset>peak:peak=asset
    dd=(asset-peak)/peak*100
    if dd<max_dd:max_dd=dd
    if ret_pct<-0.05:consec+=1
    elif ret_pct>0.05:consec=0
    trades+=1
print(f'WF全选: ¥{asset:,.0f} 净值{asset/INIT:.2f} +{(asset/INIT-1)*100:.1f}%  回撤{max_dd:.1f}%  {trades}笔  跳过{skips}天')

# === B: 回踩3-5%内WF ===
consec=0;asset=INIT;peak=INIT;max_dd=0.0;skips=0;trades=0
for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    deep_idxs=[i for i in idxs if 3<=sa[i][0]['pb_depth']<=5]
    if not deep_idxs:skips+=1;continue
    if fi<100:best=sa[deep_idxs[0]]
    else:
        hist=[j for j in range(fi)];Xh=X[hist];yh=yt[hist];mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
        Xn=(Xh-mu)/sg
        try:w=solve(Xn.T@Xn+np.eye(Xn.shape[1])*2.0,Xn.T@yh)
        except:w=np.zeros(Xn.shape[1])
        Xt=np.array([(X[j]-mu)/sg for j in deep_idxs])
        best=sa[deep_idxs[int(np.argmax(Xt@w))]]
    if consec>=3:consec=0;skips+=1;continue
    factor=0.5 if consec>=2 else 1.0
    r=tr(best[3],sd(best[3],best[12],best[13],best[14],best[15]),asset*factor)
    if r is None:skips+=1;continue
    ret_pct,profit=r
    asset+=profit
    if asset>peak:peak=asset
    dd=(asset-peak)/peak*100
    if dd<max_dd:max_dd=dd
    if ret_pct<-0.05:consec+=1
    elif ret_pct>0.05:consec=0
    trades+=1
print(f'回踩3-5%+WF: ¥{asset:,.0f} 净值{asset/INIT:.2f} +{(asset/INIT-1)*100:.1f}%  回撤{max_dd:.1f}%  {trades}笔  跳过{skips}天')

# === C: 回踩3-5%内WF, 否则回踩最深 ===
consec=0;asset=INIT;peak=INIT;max_dd=0.0;skips=0;trades=0
for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    deep_idxs=[i for i in idxs if 3<=sa[i][0]['pb_depth']<=5]
    if deep_idxs:
        if fi<100:best=sa[deep_idxs[0]]
        else:
            hist=[j for j in range(fi)];Xh=X[hist];yh=yt[hist];mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
            Xn=(Xh-mu)/sg
            try:w=solve(Xn.T@Xn+np.eye(Xn.shape[1])*2.0,Xn.T@yh)
            except:w=np.zeros(Xn.shape[1])
            Xt=np.array([(X[j]-mu)/sg for j in deep_idxs])
            best=sa[deep_idxs[int(np.argmax(Xt@w))]]
    else:
        # fallback: 选回踩最深(旧版,无限制)
        best=sa[max(idxs,key=lambda i:sa[i][0]['pb_depth'])]
    if consec>=3:consec=0;skips+=1;continue
    factor=0.5 if consec>=2 else 1.0
    r=tr(best[3],sd(best[3],best[12],best[13],best[14],best[15]),asset*factor)
    if r is None:skips+=1;continue
    ret_pct,profit=r
    asset+=profit
    if asset>peak:peak=asset
    dd=(asset-peak)/peak*100
    if dd<max_dd:max_dd=dd
    if ret_pct<-0.05:consec+=1
    elif ret_pct>0.05:consec=0
    trades+=1
print(f'3-5%WF/否则最深(旧): ¥{asset:,.0f} 净值{asset/INIT:.2f} +{(asset/INIT-1)*100:.1f}%  回撤{max_dd:.1f}%  {trades}笔  跳过{skips}天')

# === D: 3-5%WF / 最深>=2%才买 / 否则空仓 ===
consec=0;asset=INIT;peak=INIT;max_dd=0.0;skips=0;trades=0
for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    deep_idxs=[i for i in idxs if 3<=sa[i][0]['pb_depth']<=5]
    if deep_idxs:
        if fi<100:best=sa[deep_idxs[0]]
        else:
            hist=[j for j in range(fi)];Xh=X[hist];yh=yt[hist];mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
            Xn=(Xh-mu)/sg
            try:w=solve(Xn.T@Xn+np.eye(Xn.shape[1])*2.0,Xn.T@yh)
            except:w=np.zeros(Xn.shape[1])
            Xt=np.array([(X[j]-mu)/sg for j in deep_idxs])
            best=sa[deep_idxs[int(np.argmax(Xt@w))]]
    else:
        # fallback修正: 最深>=2%才买, 否则跳过
        deepest_i=max(idxs,key=lambda i:sa[i][0]['pb_depth'])
        if sa[deepest_i][0]['pb_depth']>=2:
            best=sa[deepest_i]
        else:
            skips+=1;continue
    if consec>=3:consec=0;skips+=1;continue
    factor=0.5 if consec>=2 else 1.0
    r=tr(best[3],sd(best[3],best[12],best[13],best[14],best[15]),asset*factor)
    if r is None:skips+=1;continue
    ret_pct,profit=r
    asset+=profit
    if asset>peak:peak=asset
    dd=(asset-peak)/peak*100
    if dd<max_dd:max_dd=dd
    if ret_pct<-0.05:consec+=1
    elif ret_pct>0.05:consec=0
    trades+=1
print(f'3-5%WF/最深>=2%/否则空: ¥{asset:,.0f} 净值{asset/INIT:.2f} +{(asset/INIT-1)*100:.1f}%  回撤{max_dd:.1f}%  {trades}笔  跳过{skips}天')
