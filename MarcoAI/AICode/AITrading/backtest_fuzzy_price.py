"""
模糊收盘价回测: 5M有数据用真实14:55价, 2024年用校准分布模拟
分布: 均值+0.055%, std=0.307% (来自548样本实测)
"""
import os, numpy as np, random
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D'
M5=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001;CAP=1_000_000

# === 校准: 14:55→收盘差异分布 (548样本实测) ===
GAP_MEAN=0.055   # 均值+0.055%
GAP_STD=0.307    # 标准差0.307%

random.seed(42)  # 固定种子, 可复现

# === 5M缓存 ===
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

def get_1456_price(code,d2):
    """获取14:55价: 5M有→倒数第2根; 无→模拟"""
    bars=lm5(code).get(d2,[])
    if bars and len(bars)>=2:
        return bars[-2][3],'5m'
    return None,'no5m'

# === 公共 ===
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

# === 三套样本 ===
# A: 纯1D收盘 (旧版)
# B: 5M有→5M, 无→1D (之前跑的)
# C: 5M有→5M, 无→模拟模糊 (新方案)

sa_A=[];sa_B=[];sa_C=[]
ct_5m=0;ct_sim=0

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
            
            c2_1d=r2[4]
            c2_1456,src=get_1456_price(code,d2)
            
            if c2_1456 is not None:
                c2_B=c2_1456;c2_C=c2_1456;ct_5m+=1
            else:
                c2_B=c2_1d
                # 模拟: 1D收盘价 + N(μ,σ) 噪声, 模拟14:55不确定性
                noise=random.gauss(GAP_MEAN/100,GAP_STD/100)
                c2_C=c2_1d*(1-noise)  # 闭盘价=14:55×(1+diff)→14:55=闭盘/(1+diff)
                ct_sim+=1
            
            cl=np.array([r[4] for r in rs[:d2k+1]])
            hi_arr=np.array([r[2] for r in rs[:d2k+1]]);n=len(cl)
            
            def build_f(c2):
                f={}
                f['pb_depth']=(r3[4]-c2)/r3[4]*100 if r3[4]>0 else 0
                f['ma5_dev']=(c2-np.mean(cl[-5:]))/np.mean(cl[-5:])*100 if n>=5 else 0
                if n>=10:
                    tr=[]
                    for i in range(d2k-9,d2k+1):
                        h=hi_arr[i];l_=rs[i][3];pc=rs[i-1][4] if i>0 else rs[i][6]
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
                return f
            
            base=(code,d1,bp,sc,name,r1[1],r1[2],r1[3])
            sa_A.append((build_f(c2_1d),*base))
            sa_B.append((build_f(c2_B),*base))
            sa_C.append((build_f(c2_C),*base))

print(f'样本: {len(sa_A)}  (5M真实:{ct_5m}, 模拟:{ct_sim})')
# Verify simulation distribution
sim_diffs=[]
real_diffs=[]
for sB,sC in zip(sa_B,sa_C):
    cB=sB[0]['pb_depth']
    cC=sC[0]['pb_depth']
    # The difference in pb_depth reflects the price difference
    # Not exact but indicative
    if abs(cB-cC)>1e-6:
        sim_diffs.append(cC-cB)
for sA,sB in zip(sa_A,sa_B):
    if abs(sA[0]['pb_depth']-sB[0]['pb_depth'])>1e-6:
        real_diffs.append(sB[0]['pb_depth']-sA[0]['pb_depth'])

print(f'  模拟pb差异: mean={np.mean(sim_diffs) if sim_diffs else 0:+.4f}, std={np.std(sim_diffs) if sim_diffs else 0:.4f}')
print()

# === 跑三套回测 ===
def run_backtest(X_in,sa_in):
    dm2=defaultdict(list)
    for i,s in enumerate(sa_in):dm2[s[2]].append(i)
    ad=sorted(dm2.keys())
    
    consec=0;cum=1.0;peak=1.0;max_dd=0.0
    trades=[];m_data=defaultdict(list);y_data=defaultdict(list)
    
    for d1_date in ad:
        idxs=dm2[d1_date];fi=idxs[0]
        if fi<100:best=sa_in[idxs[0]]
        else:
            hist=[j for j in range(fi)]
            Xh=X_in[hist];yh=yt[hist]
            mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
            Xn=(Xh-mu)/sg;d_dim=Xn.shape[1]
            try:w=solve(Xn.T@Xn+np.eye(d_dim)*2.0,Xn.T@yh)
            except:w=np.zeros(d_dim)
            Xt=np.array([(X_in[i]-mu)/sg for i in idxs])
            best=sa_in[idxs[int(np.argmax(Xt@w))]]
        
        bp=best[3];o=best[6];h=best[7];l=best[8];c=best[4]
        sp,mode=sd(bp,o,h,l,c)
        if consec>=3:consec=0;continue
        cap=CAP*(0.5 if consec>=2 else 1)
        ret=fee(bp,sp,cap)
        m=d1_date[:6];y=d1_date[:4]
        m_data[m].append(ret);y_data[y].append(ret)
        cum*=(1+ret/100)
        if cum>peak:peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd:max_dd=dd
        trades.append({'ret':ret,'code':best[1],'name':best[5]})
        if ret<-0.05:consec+=1
        elif ret>0.05:consec=0
    
    return cum,max_dd,trades,m_data,y_data

sa_list=[('A:1D收盘',sa_A,None),('B:5M+1D回退',sa_B,None),('C:5M+模拟模糊',sa_C,None)]

print('回测中...')
results={}
for label,sa_data,_ in sa_list:
    X_in=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa_data])
    yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa_data])
    cum,dd,tr,m_data,y_data=run_backtest(X_in,sa_data)
    results[label]=(cum,dd,tr,m_data,y_data)
    print(f'  {label}: 净值{cum:.2f}')

print()
print('='*65)
print(f'{"方案":<20} {"净值":>8} {"收益":>9} {"回撤":>7} {"笔数":>5}')
print('-'*55)
for label in ['A:1D收盘','B:5M+1D回退','C:5M+模拟模糊']:
    cum,dd,tr,_,_=results[label]
    print(f'{label:<20} {cum:>8.2f} {(cum-1)*100:>+8.1f}% {dd:>+6.1f}% {len(tr):>5}')

# 年度对比
print()
print('=== 年度 ===')
print(f'{"年份":<8} {"A:1D收盘":>10} {"C:模糊":>10} {"差":>8}')
for yk in ['2024','2025','2026']:
    _,_,_,_,yd_A=results['A:1D收盘']
    _,_,_,_,yd_C=results['C:5M+模拟模糊']
    yrA=1.0;yrC=1.0
    for rv in yd_A.get(yk,[]):yrA*=(1+rv/100)
    for rv in yd_C.get(yk,[]):yrC*=(1+rv/100)
    print(f'{yk:<8} {(yrA-1)*100:>+9.1f}% {(yrC-1)*100:>+9.1f}% {(yrC-yrA)/yrA*100:>+7.1f}%')

# 选股变化
print()
saA=sa_A;saC=sa_C
dmA=defaultdict(list);dmC=defaultdict(list)
for i,s in enumerate(saA):dmA[s[2]].append(i)
for i,s in enumerate(saC):dmC[s[2]].append(i)
ad_A=sorted(dmA.keys());ad_C=sorted(dmC.keys())
picks_A=[results['A:1D收盘'][2][i]['code'] for i in range(len(results['A:1D收盘'][2]))]
picks_C=[results['C:5M+模拟模糊'][2][i]['code'] for i in range(len(results['C:5M+模拟模糊'][2]))]
diff=sum(1 for a,c in zip(picks_A,picks_C) if a!=c)
print(f'选股变化 A→C: {diff}/{len(picks_A)} ({diff/len(picks_A)*100:.1f}%)')
