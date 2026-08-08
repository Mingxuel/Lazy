"""隔离级联效应: 固定WF权重, 纯比较特征差异对选股的影响"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D'
M5=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

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

def get_d2_1456(code,d2):
    bars=lm5(code).get(d2,[])
    if bars and len(bars)>=2:return bars[-2][3]
    return None

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

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001;CAP=1_000_000

def fee(bp,sp,cap):
    sh=int(cap/bp/100)*100
    return (sp*sh*(1-CR-SD-TF)-bp*sh*(1+CR))/(bp*sh)*100

def sd(bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o,'open_stop'
    if l<=st:return st,'low_stop'
    if h>=lu*0.999:return lu,'limit_up'
    return c,'close'

# ===== Stage 1: 用1D收盘价做完整WF, 记录每天的权重和选股 =====
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

# Stage 1: 记录每天WF权重和选股
daily_weights={}
daily_picks_1d={}
for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:best=sa[idxs[0]];continue
    hist=[j for j in range(fi)]
    Xh=X[hist];yh=yt[hist]
    mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
    Xn=(Xh-mu)/sg;d_dim=Xn.shape[1]
    try:w=solve(Xn.T@Xn+np.eye(d_dim)*2.0,Xn.T@yh)
    except:w=np.zeros(d_dim)
    Xt=np.array([(X[i]-mu)/sg for i in idxs]);preds=Xt@w
    best_i=idxs[int(np.argmax(preds))]
    daily_weights[d1_date]=(w,mu,sg)
    daily_picks_1d[d1_date]=sa[best_i]

# Stage 2: 使用Stage 1的固定权重, 但用5M价格重新评分选股
# 这模拟了"如果实盘14:56有准确的14:55价格, 选股会变吗"
pick_changes=0
pick_changes_detail=[]
total_days=0

for d1_date in ad:
    if d1_date not in daily_weights:continue
    w,mu,sg=daily_weights[d1_date]
    idxs=dm[d1_date]
    
    # 原版选股
    orig_pick=daily_picks_1d[d1_date]
    
    # 对每个候选, 用5M价格重算pb_depth和ma5_dev
    new_scores=[]
    has_5m=False
    for si in idxs:
        s=sa[si]
        code=s[1];d2_date=s[10];pre=s[11]
        c2_1d=s[9]  # 原D-2收盘
        
        c2_5m=get_d2_1456(code,d2_date)
        if c2_5m is None:
            c2_5m=c2_1d
        else:
            has_5m=True
        
        # Recompute pb_depth and ma5_dev with 5M price
        pb=(pre-c2_5m)/pre*100 if pre>0 else 0
        # ma5_dev: 用原始closes(从1D) + c2_5m
        # 简单近似: ma5_dev_diff ≈ (c2_5m-c2_1d)/ma5
        # 完整重算太慢, 用delta近似
        ma5_dev_orig=s[0]['ma5_dev']
        # ma5_dev = (D2_c - ma5) / ma5 → delta_ma5dev = delta_c2 / ma5
        # 从orig反推ma5: 用r3[4]附近近似
        ma5_est=abs(c2_1d/(1+ma5_dev_orig/100)) if abs(ma5_dev_orig)<50 else abs(c2_1d)
        if ma5_est>0:
            ma5_dev_new=(c2_5m-ma5_est)/ma5_est*100
        else:
            ma5_dev_new=ma5_dev_orig
        
        # Build new feature vector
        new_feat=np.array([pb,ma5_dev_new,
                          s[0]['pc_vs_low_atr'],s[0]['high_vs_pc_atr'],
                          s[0]['ma_golden']])
        score=float(((new_feat-mu)/sg)@w)
        new_scores.append((score,si))
    
    if not has_5m:continue
    total_days+=1
    
    new_scores.sort(key=lambda x:-x[0])
    new_pick=sa[new_scores[0][1]]
    
    if new_pick[1]!=orig_pick[1]:
        pick_changes+=1
        pick_changes_detail.append({
            'date':d1_date,
            'orig_name':orig_pick[5],'orig_code':orig_pick[1],
            'new_name':new_pick[5],'new_code':new_pick[1],
            'orig_score':float(((np.array([orig_pick[0].get(k,0) for k in FEATURES])-mu)/sg)@w),
            'new_score':new_scores[0][0]
        })

print(f'可验证天数: {total_days}')
print(f'选股变化(固定权重): {pick_changes}/{total_days} ({pick_changes/total_days*100:.1f}%)')
print()

if pick_changes_detail:
    print('变化详情 (前15):')
    for d in pick_changes_detail[:15]:
        print(f'  {d["date"]} {d["orig_name"]}→{d["new_name"]} score={d["orig_score"]:.3f}→{d["new_score"]:.3f}')

print()
print('='*60)
print('级联效应分解:')
print(f'  纯特征差异造成的选股变化: {pick_changes}/{total_days} = {pick_changes/total_days*100:.1f}%')
print(f'  WF级联放大的选股变化: 23.4% - {pick_changes/total_days*100:.1f}% = {23.4-pick_changes/total_days*100:.1f}%')
print(f'  级联放大倍数: {23.4/(pick_changes/total_days*100):.1f}x' if pick_changes>0 else '')
