"""仓位管理优化 — 在已选股序列上试不同仓位规则"""
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

# === 第一步: 跑一次WF回测, 记录每笔的买入价/卖出价/日期 ===
print('第一步: 提取选股序列...')
trades = []  # [(date, bp, sp, ret_full), ...]
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
    
    bp=best[3];o=best[6];h=best[7];l=best[8];c=best[4];code=best[1];name=best[5]
    sp,mode=sd(bp,o,h,l,c)
    ret_full=fee(bp,sp,CAPITAL)
    trades.append((d1_date, bp, sp, ret_full, mode, code, name))

print(f'选股序列: {len(trades)}笔')
nonzero=[t for t in trades if t[3]!=0]
wins=sum(1 for t in nonzero if t[3]>0)
print(f'满仓基准: 净值{(1+sum(t[3]/100 for t in nonzero)):.2f} 胜率{wins}/{len(nonzero)}({wins/len(nonzero)*100:.1f}%)')

# === 第二步: 扫不同仓位规则 ===
print('\n第二步: 仓位管理扫描...')

results = []

# 规则A: 固定仓位比例 (无动态管理)
for f in [1.0, 0.75, 0.5]:
    cum=1.0;pk=1.0;dd=0.0
    for t in trades:
        ret=fee(t[1],t[2],CAPITAL*f) if t[3]!=0 else 0
        cum*=(1+ret/100)
        if cum>pk:pk=cum
        ddd=(cum-pk)/pk*100
        if ddd<dd:dd=ddd
    results.append((f'固定{f*100:.0f}%', cum, dd, 0, 0))

# 规则B: 连亏减仓/跳过
for half_at in [1,2,3,4]:       # 连亏几次变半仓
    for skip_at in [3,4,5,6,99]: # 连亏几次跳过 (99=永不跳)
        if skip_at <= half_at and skip_at!=99: continue
        for half_pct in [0.25, 0.50, 0.75]:  # 半仓比例
            cum=1.0;pk=1.0;dd=0.0;con=0
            for t in trades:
                if t[3]==0:continue
                if con>=skip_at:con=0;continue
                cap=CAPITAL*half_pct if con>=half_at else CAPITAL
                ret=fee(t[1],t[2],cap)
                cum*=(1+ret/100)
                if cum>pk:pk=cum
                ddd=(cum-pk)/pk*100
                if ddd<dd:dd=ddd
                if ret<-0.05:con+=1
                elif ret>0.05:con=0
            results.append((f'半仓{half_pct*100:.0f}%@{half_at}连亏 跳过@{skip_at}', cum, dd, half_at, skip_at))

# 规则C: 指数衰减 (最平滑)
for decay in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
    for skip_at in [3,4,5,6,99]:
        cum=1.0;pk=1.0;dd=0.0;con=0
        for t in trades:
            if t[3]==0:continue
            if con>=skip_at:con=0;continue
            mul=decay**con
            cap=CAPITAL*mul
            ret=fee(t[1],t[2],cap)
            cum*=(1+ret/100)
            if cum>pk:pk=cum
            ddd=(cum-pk)/pk*100
            if ddd<dd:dd=ddd
            if ret<-0.05:con+=1
            elif ret>0.05:con=0
        results.append((f'衰减{decay:.2f} 跳过@{skip_at}', cum, dd, decay, skip_at))

# 排序
results.sort(key=lambda x:-x[1])

print("{:<30} {:>8} {:>7} {:>8}".format("规则","净值","回撤","vs基线"))
print('-'*60)
baseline_full = [r for r in results if r[0]=='固定100%'][0][1]
for label,cum,dd,_,_ in results[:20]:
    diff=cum-baseline_full
    print(f'{label:<30} {cum:>8.4f} {dd:>+6.1f}% {diff:>+8.4f}')

# 检查平滑度: 对衰减规则看相邻decay的净值波动
print()
print('=== 平滑度检查 (衰减规则, 跳过@3) ===')
decays=[];nvs=[]
for label,cum,dd,d,sk in results:
    if label.startswith('衰减') and '跳过@3' in label:
        decays.append(d);nvs.append(cum)
decays.sort()
hdr2 = "{:>6} {:>8} {:>8}".format("decay","净值","Δ净值")
print(hdr2)
for i in range(len(decays)):
    dd_nv=nvs[i]-nvs[i-1] if i>0 else 0
    print(f'{decays[i]:>6.2f} {nvs[i]:>8.4f} {dd_nv:>+8.4f}')

# 最优
best=results[0]
print(f'\n最优: {best[0]} 净值{best[1]:.4f} 回撤{best[2]:.1f}%')
print(f'vs满仓: {best[1]-baseline_full:+8.4f}')
