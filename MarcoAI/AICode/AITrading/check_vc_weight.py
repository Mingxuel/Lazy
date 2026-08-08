import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

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
            name=p[0]; code=p[1]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]; bp=r1[6]; sp_close=r1[4]
            if bp<=0: continue
            r2=rows[d2i_k]; o2,h2,l2,c2,v2,pc2=r2[1],r2[2],r2[3],r2[4],r2[5],r2[6]
            r3=rows[d2i_k-1] if d2i_k>=1 else None
            cls=np.array([r[4] for r in rows[:d2i_k+1]])
            highs=np.array([r[2] for r in rows[:d2i_k+1]]); n=len(cls)
            f={}
            f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
            d2_vol_adj = v2 * 0.978
            f['vol_contract']=(r3[5]-d2_vol_adj)/r3[5]*100 if(r3 and r3[5]>0) else 0
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
            samples.append((f,code,d1,bp,sp_close,name,rows[d1i_k][1],rows[d1i_k][2],rows[d1i_k][3]))
samples.sort(key=lambda x:x[2])

X_full = np.array([[s[0].get(k,0) for k in FEATURES] for s in samples])
y = np.array([(s[4]-s[3])/s[3]*100 for s in samples])

mean=X_full.mean(axis=0); std=X_full.std(axis=0)+1e-8
Xn=(X_full-mean)/std
w=solve(Xn.T@Xn+np.eye(Xn.shape[1])*2.0,Xn.T@y)

print(f'样本数: {len(samples)}')
print('全量WF权重:')
for nm,wt in zip(FEATURES,w):
    print(f'  {nm:<18} {wt:+.4f}')
print()

# 去掉 vol_contract
FEATURES_5 = ['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
X5 = np.array([[s[0].get(k,0) for k in FEATURES_5] for s in samples])
mean5=X5.mean(axis=0); std5=X5.std(axis=0)+1e-8
Xn5=(X5-mean5)/std5
w5=solve(Xn5.T@Xn5+np.eye(Xn5.shape[1])*2.0,Xn5.T@y)

print('5特征权重 (去掉vol_contract):')
for nm,wt in zip(FEATURES_5,w5):
    print(f'  {nm:<18} {wt:+.4f}')

# R2 比较
y_pred_full = Xn @ w
sst = np.sum((y-np.mean(y))**2)
r2_full = 1 - np.sum((y-y_pred_full)**2) / sst

y_pred_5 = Xn5 @ w5
r2_5 = 1 - np.sum((y-y_pred_5)**2) / sst

print(f'\nR-squared 全量(6特征): {r2_full:.4f}')
print(f'R-squared 5特征:      {r2_5:.4f}')
print(f'vol_contract 贡献:    {r2_full-r2_5:+.4f}')
