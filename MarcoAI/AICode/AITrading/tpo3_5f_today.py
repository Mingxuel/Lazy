"""5特征 TPO3 快速分析"""
import os, numpy as np, urllib.request
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
FEATURES = ['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

def load_kline(code):
    fp=os.path.join(K,code); rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'): continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds=sorted(tds); di={d:i for i,d in enumerate(tds)}

samples=[]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit(): continue
    d1=fn; d1i=di.get(d1)
    if d1i is None or d1i<3: continue
    d2=tds[d1i-1]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<2: continue
            code=p[1]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]; bp=r1[6]; sp_c=r1[4]
            if bp<=0: continue
            r2=rows[d2i_k]; o2,h2,l2,c2,v2,pc2=r2[1],r2[2],r2[3],r2[4],r2[5],r2[6]
            r3=rows[d2i_k-1] if d2i_k>=1 else None
            cls=np.array([r[4] for r in rows[:d2i_k+1]])
            highs=np.array([r[2] for r in rows[:d2i_k+1]]); n=len(cls)
            f={}
            f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
            f['ma5_dev']=(c2-np.mean(cls[-5:]))/np.mean(cls[-5:])*100 if n>=5 else 0
            if n>=10:
                trs=[]
                for i in range(d2i_k-9,d2i_k+1):
                    h=highs[i]; l=rows[i][3]; pc=rows[i-1][4] if i>0 else rows[i][6]
                    trs.append(max(h-l,abs(h-pc),abs(l-pc)))
                atr10=np.mean(trs) if trs else 1
            else: atr10=h2-l2 if h2>l2 else 1
            f['pc_vs_low_atr']=(pc2-rows[d2i_k][3])/atr10 if atr10>0 else 0
            f['high_vs_pc_atr']=(h2-pc2)/atr10 if atr10>0 else 0
            ma_golden=0
            if d2i_k>=10:
                c_arr=[r[4] for r in rows[:d2i_k+1]]
                ma5=np.mean(c_arr[-5:]); ma10=np.mean(c_arr[-10:])
                ma5p=np.mean(c_arr[-6:-1]); ma10p=np.mean(c_arr[-11:-1])
                ma_golden=1 if(ma5p<=ma10p and ma5>ma10) else 0
            f['ma_golden']=ma_golden
            samples.append((f,code,d1,bp,sp_c))

X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples])
y_target=np.array([(s[4]-s[3])/s[3]*100 for s in samples])
mean=X.mean(axis=0); std=X.std(axis=0)+1e-8
Xn=(X-mean)/std
w=solve(Xn.T@Xn+np.eye(5)*2.0,Xn.T@y_target)

print('=== 5特征WF权重 (670样本) ===')
for nm,wt,mu,sg in zip(FEATURES,w,mean,std):
    print(f'  {nm:18s}: w={wt:+.4f}  mu={mu:+.2f}  sigma={sg:.2f}')
print()

codes=['000657.SZ','002636.SZ','601869.SH','603268.SH']
names_cn={'000657.SZ':'中钨高新','002636.SZ':'金安国纪','601869.SH':'长飞光纤','603268.SH':'松发股份'}
mkt_map={'000657.SZ':'sz000657','002636.SZ':'sz002636','601869.SH':'sh601869','603268.SH':'sh603268'}

results=[]
pre={}
for code in codes:
    rows,date_idx=load_kline(code)
    d3i=date_idx.get('20260806')
    if d3i is None: continue
    cls=np.array([r[4] for r in rows[:d3i+1]])
    highs=np.array([r[2] for r in rows[:d3i+1]])
    trs=[]
    for i in range(d3i-9,d3i+1):
        h=highs[i]; l=rows[i][3]; pc=rows[i-1][4] if i>0 else rows[i][6]
        trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    atr10=np.mean(trs)
    ma5=np.mean(cls[-5:]); ma10=np.mean(cls[-10:])
    last_ma5=np.mean(cls[-6:-1]); last_ma10=np.mean(cls[-11:-1])
    oldest_5=cls[-6]; oldest_10=cls[-11]
    pre[code]=(atr10,ma5,ma10,last_ma5,last_ma10,oldest_5,oldest_10)

print('TPO3 5特征分析  D-3=0806 → D-2=0807')
print('='*70)
for code in codes:
    try:
        resp=urllib.request.urlopen(f'http://qt.gtimg.cn/q={mkt_map[code]}',timeout=5).read().decode('gbk')
        p=resp.split('~')
        cur,prc,hi,lo=float(p[3]),float(p[4]),float(p[33]),float(p[34])
    except: continue
    atr10,ma5,ma10,last_ma5,last_ma10,oldest_5,oldest_10=pre[code]
    pb=(prc-cur)/prc*100
    ma5_now=(ma5*5-oldest_5+cur)/5
    ma10_now=(ma10*10-oldest_10+cur)/10
    ma5_dev=(cur-ma5_now)/ma5_now*100 if ma5_now>0 else 0
    bear=(prc-lo)/atr10 if atr10>0 else 0
    bull=(hi-prc)/atr10 if atr10>0 else 0
    golden=1 if(last_ma5<=last_ma10 and ma5_now>ma10_now) else 0
    feat=np.array([pb,ma5_dev,bear,bull,golden])
    Xs=(feat-mean)/(std+1e-8)
    score=float(Xs@w)
    chg=(cur-prc)/prc*100
    print(f'\n── {names_cn[code]}({code}) ──')
    print(f'  C={cur:.2f} 涨{chg:+.2f}%  pb={pb:+.2f}  ma5_dev={ma5_dev:+.2f}  bear={bear:.2f}  bull={bull:.2f}  golden={golden}')
    print(f'  得分: pb={Xs[0]*w[0]:+.3f}  ma5={Xs[1]*w[1]:+.3f}  bear={Xs[2]*w[2]:+.3f}  bull={Xs[3]*w[3]:+.3f}  golden={Xs[4]*w[4]:+.3f}')
    print(f'  ★ 总分: {score:+.4f}')
    results.append((code,names_cn[code],score,pb,ma5_dev,bear,bull,golden))

print('\n'+'='*50)
print('TPO3 5特征最终排序')
results.sort(key=lambda x:-x[2])
for i,(code,name,sc,pb,ma5,bear,bull,gld) in enumerate(results):
    m=' ★★★ 尾盘买入' if i==0 else ''
    print(f'  {i+1}. {name}({code}) 总分:{sc:+.4f}  pb={pb:+.2f}  bull={bull:.2f}  bear={bear:.2f}{m}')
