#!/usr/bin/env python3
"""
311选股模型: 成交量+均线特征, 训练集≤202603, 测试集≥202604
"""
import os, numpy as np
from collections import defaultdict
np.random.seed(42)

S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
M5=r'C:\Lazy\MarcoAI\AIData\5M'
CR=0.00025; CM=5.0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

def load_td():
    ds=[]
    with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
        for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and ds.append(l)
    return sorted(ds)
def load_kline(code):
    fp=os.path.join(K,code)
    if not os.path.exists(fp): return [],[]
    rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith(chr(0xfeff)): continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}
def check_ma5_5m(code,dt,c2):
    fp=os.path.join(M5,code)
    if not os.path.exists(fp): return 0,0
    df=f'{dt[:4]}-{dt[4:6]}-{dt[6:8]}'
    with open(fp,encoding='utf-8') as f:
        bars=[]
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<6: continue
            if p[0].startswith(df): bars.append((p[0],float(p[4]),float(p[3]),float(p[1])))
    if not bars or len(bars)<10: return 0,0
    for b in bars:
        bl,bc=b[1],b[2]  # close, low
        if c2>0:
            d=(bc-c2)/c2*100
            if -1.5<d<1.0:
                bounce=(bl-bc)/bc*100
                if bounce>1.5: return 1,bounce
    return 0,0

def extract_features(rows,date_idx,d1,d2,code):
    d1i=date_idx.get(d1); d2i=date_idx.get(d2)
    if d1i is None or d2i is None or d2i<20: return None,None,None
    r1=rows[d1i]; r2=rows[d2i]
    bp=r1[6]; sp=r1[4]
    if bp<=0 or sp<=0: return None,None,None

    o2,h2,l2,c2,v2=r2[1],r2[2],r2[3],r2[4],r2[5]
    r3=rows[d2i-1] if d2i>=1 else None

    f={}
    # === 311模式特征 ===
    if r3:
        f['pullback']=(r3[4]-c2)/r3[4]*100
        f['vol_d3_d2']=r3[5]/v2 if v2>0 else 1
        f['vol_contract']=1 if v2<r3[5]*0.8 else 0
    else: f['pullback']=0; f['vol_d3_d2']=1; f['vol_contract']=0

    rng=h2-l2
    f['shadow']=(c2-l2)/rng*100 if rng>0 else 50
    f['amp']=(h2-l2)/o2*100 if o2>0 else 0
    f['close_pos']=(c2-l2)/rng*100 if rng>0 else 50

    # === 成交量特征 ===
    closes=np.array([r[4] for r in rows[:d2i+1]])
    vols=np.array([r[5] for r in rows[:d2i+1]])
    highs=np.array([r[2] for r in rows[:d2i+1]])
    lows=np.array([r[3] for r in rows[:d2i+1]])

    n=len(closes)

    # 量比
    if n>=5:  f['vol_ratio5']=vols[-1]/np.mean(vols[-5:])
    else:     f['vol_ratio5']=1
    if n>=10: f['vol_ratio10']=vols[-1]/np.mean(vols[-10:])
    else:     f['vol_ratio10']=1
    if n>=20: f['vol_ratio20']=vols[-1]/np.mean(vols[-20:])
    else:     f['vol_ratio20']=1

    # 量趋势
    if n>=10:
        f['vol_trend5']=np.mean(vols[-5:])/np.mean(vols[-10:-5]) if n>=10 else 1
        f['vol_trend10']=np.mean(vols[-10:])/np.mean(vols[-20:-10]) if n>=20 else 1
    else: f['vol_trend5']=1; f['vol_trend10']=1

    # 量价配合: D-2缩量+前期放量
    if n>=10:
        f['vol_surge_before']=1 if np.mean(vols[-6:-1])>np.mean(vols[-11:-6])*1.3 else 0
    else: f['vol_surge_before']=0

    # === 均线特征 ===
    if n>=5:
        ma5=np.mean(closes[-5:])
        f['ma5_ratio']=closes[-1]/ma5
        f['ma5_slope']=(ma5-np.mean(closes[-10:-5]))/np.mean(closes[-10:-5])*100 if n>=10 else 0
    else: f['ma5_ratio']=1; f['ma5_slope']=0

    if n>=10:
        ma10=np.mean(closes[-10:])
        f['ma10_ratio']=closes[-1]/ma10
        f['ma10_slope']=(ma10-np.mean(closes[-20:-10]))/np.mean(closes[-20:-10])*100 if n>=20 else 0
    else: f['ma10_ratio']=1; f['ma10_slope']=0

    if n>=20:
        ma20=np.mean(closes[-20:])
        f['ma20_ratio']=closes[-1]/ma20
    else: f['ma20_ratio']=1

    if n>=60:
        ma60=np.mean(closes[-60:])
        f['ma60_ratio']=closes[-1]/ma60
    else: f['ma60_ratio']=1

    # 均线排列
    if n>=20:
        f['ma_bullish']=1 if (f.get('ma5_ratio',1)>1 and f.get('ma10_ratio',1)>1 and f.get('ma20_ratio',1)>1) else 0
        f['ma5_above_ma10']=1 if f.get('ma5_ratio',1)>f.get('ma10_ratio',1) else 0
    else: f['ma_bullish']=0; f['ma5_above_ma10']=0

    # === 价格趋势 ===
    if n>=2:  f['ret_1d']=(closes[-1]-closes[-2])/closes[-2]*100
    else:     f['ret_1d']=0
    if n>=5:  f['ret_5d']=(closes[-1]-closes[-5])/closes[-5]*100
    else:     f['ret_5d']=0
    if n>=10: f['ret_10d']=(closes[-1]-closes[-10])/closes[-10]*100
    else:     f['ret_10d']=0
    if n>=20: f['ret_20d']=(closes[-1]-closes[-20])/closes[-20]*100
    else:     f['ret_20d']=0

    # 波动率
    if n>=10:
        dr=(closes[1:]-closes[:-1])/closes[:-1]*100
        f['vol10']=np.std(dr[-10:]) if len(dr)>=10 else 0
        f['vol20']=np.std(dr[-20:]) if len(dr)>=20 else 0
    else: f['vol10']=0; f['vol20']=0

    # 20日高低
    if n>=20:
        h20=np.max(highs[-20:]); l20=np.min(lows[-20:])
        f['dist_high20']=(h20-closes[-1])/h20*100 if h20>0 else 0
        f['dist_low20']=(closes[-1]-l20)/l20*100 if l20>0 else 0
    else: f['dist_high20']=0; f['dist_low20']=0

    # D-2新低
    f['new_low']=1 if (r3 and l2<r3[3]) else 0

    # 涨停强度D-4
    if d2i>=3:
        r4=rows[d2i-2]; r5=rows[d2i-3]
        f['limit_strength']=(r4[4]-r5[4])/r5[4]*100 if r5[4]>0 else 0
    else: f['limit_strength']=0

    # === MA5 5M弹起 ===
    has_ma5,bounce=check_ma5_5m(code,d2,c2)
    f['ma5_bounce']=1 if has_ma5 else 0
    f['ma5_bounce_str']=bounce

    return f,bp,sp


# ============================================================
class SimpleMLP:
    def __init__(self,sizes,lr=0.001):
        self.W=[]; self.B=[]
        for i in range(len(sizes)-1):
            f=sizes[i]
            self.W.append(np.random.randn(f,sizes[i+1])*np.sqrt(2.0/f))
            self.B.append(np.zeros(sizes[i+1]))
    def _r(self,x): return np.maximum(0,x)
    def _dr(self,x): return (x>0).astype(float)
    def predict(self,X):
        a=X
        for w,b in zip(self.W[:-1],self.B[:-1]): a=self._r(a@w+b)
        return (a@self.W[-1]+self.B[-1]).flatten()
    def fit(self,X,y,Xv,yv,epochs=300,bs=128,pat=30):
        bl=float('inf'); bw=None; bb=None; ni=0
        for ep in range(epochs):
            idx=np.random.permutation(X.shape[0])
            for s in range(0,X.shape[0],bs):
                e=min(s+bs,X.shape[0]); bi=idx[s:e]; Xb=X[bi]; yb=y[bi]
                acts=[Xb]; pas=[]
                for w,b in zip(self.W[:-1],self.B[:-1]):
                    z=acts[-1]@w+b; pas.append(z); acts.append(self._r(z))
                z=acts[-1]@self.W[-1]+self.B[-1]; pas.append(z); acts.append(z)
                err=(acts[-1].flatten()-yb)/len(bi); delta=err.reshape(-1,1)
                for l in range(len(self.W)-1,-1,-1):
                    if l<len(self.W)-1: delta=delta@self.W[l+1].T*self._dr(pas[l])
                    dw=acts[l].T@delta+1e-5*self.W[l]; db=np.sum(delta,axis=0)
                    self.W[l]-=0.001*dw; self.B[l]-=0.001*db
            vl=np.mean((self.predict(Xv)-yv)**2) if Xv is not None else 0
            if vl<bl: bl=vl; bw=[w.copy() for w in self.W]; bb=[b.copy() for b in self.B]; ni=0
            else: ni+=1
            if ni>=pat: break
        if bw: self.W=bw; self.B=bb
        return bl

class Scaler:
    def fit(self,X): self.m=np.mean(X,axis=0); self.s=np.std(X,axis=0); self.s[self.s<1e-10]=1.0; return self
    def transform(self,X): return (X-self.m)/self.s

def fee(buy,sell,pc):
    if buy==0 or sell==0: return 0.0
    sh=int(pc/buy/100)*100; sh=sh or 100
    c=sh*buy; bf=max(c*CR,CM)+c*TF; tb=c+bf
    r=sh*sell; sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

# ============================================================
print("="*80)
print("  311选股模型 (成交量+均线+MA5, 真实切分)")
print("  训练: ≤202603  测试: ≥202604")
print("="*80)

tds=load_td(); di={d:i for i,d in enumerate(tds)}

samples=[]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit(): continue
    d1=fn; d1i=di.get(d1)
    if d1i is None or d1i<1: continue
    d2=tds[d1i-1]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<2: continue
            code=p[1]
            rows,date_idx=load_kline(code)
            f,bp,sp=extract_features(rows,date_idx,d1,d2,code)
            if f is None: continue
            ret=(sp-bp)/bp*100
            samples.append((f,ret,code,d1,bp,sp))

n=len(samples); keys=sorted(samples[0][0].keys())
print(f"样本: {n}笔, 特征: {len(keys)}维")
print(f"特征: {keys}")

# 切分
cutoff='202604'
in_idx=[i for i,s in enumerate(samples) if s[3]<cutoff]
out_idx=[i for i,s in enumerate(samples) if s[3]>=cutoff]
print(f"\n训练集(<{cutoff}): {len(in_idx)}笔")
print(f"测试集(≥{cutoff}): {len(out_idx)}笔")

# 训练集内再切10%验证
np.random.shuffle(in_idx)
val_n=int(len(in_idx)*0.1)
tr_idx=in_idx[val_n:]
vl_idx=in_idx[:val_n]

X_all=np.array([[s[0][k] for k in keys] for s in samples])
y_all=np.array([s[1] for s in samples])

Xt=X_all[tr_idx]; yt=y_all[tr_idx]
Xv=X_all[vl_idx]; yv=y_all[vl_idx]
X_test=X_all[out_idx]

sc=Scaler().fit(Xt)
Xts=sc.transform(Xt); Xvs=sc.transform(Xv)

# 训练
print("\n训练...")
n_feat=Xt.shape[1]
models=[]
for hidden,lr in [([n_feat,512,256,128,1],0.0003),([n_feat,256,128,64,1],0.001),([n_feat,128,64,32,1],0.002)]:
    m=SimpleMLP(hidden,lr=lr)
    vl=m.fit(Xts,yt,Xvs,yv,epochs=300,pat=30)
    print(f"  {hidden}: val_MSE={vl:.4f}")
    models.append((vl,m))

best_vl,best_m=min(models,key=lambda x:x[0])

# 回测测试集
print("\n回测测试集...")
by_date=defaultdict(list)
for i in out_idx:
    by_date[samples[i][3]].append(i)

daily_ml=[]; daily_rule=[]
for d1 in sorted(by_date.keys()):
    idxs=by_date[d1]
    preds=[]; rule_scores=[]
    for i in idxs:
        Xi=np.array([[samples[i][0][k] for k in keys]])
        Xis=sc.transform(Xi)
        preds.append(best_m.predict(Xis)[0])
        
        f=samples[i][0]
        rs=0
        if f.get('vol_contract'): rs+=2
        if f.get('shadow',0)>50: rs+=2
        if 0<f.get('pullback',0)<8: rs+=2
        if f.get('ma5_bounce'): rs+=5
        if f.get('ma_bullish'): rs+=2
        rule_scores.append(rs)
    
    # ML TOP1
    best_i=int(np.argmax(preds))
    daily_ml.append(fee(samples[idxs[best_i]][4],samples[idxs[best_i]][5],CAPITAL))
    # 规则 TOP1
    best_ri=int(np.argmax(rule_scores))
    daily_rule.append(fee(samples[idxs[best_ri]][4],samples[idxs[best_ri]][5],CAPITAL))

# 测试集月收益
print(f"\n{'='*70}")
print(f"  测试集 ({len(daily_ml)}天, ≥{cutoff})")
print(f"{'='*70}")
monthly=defaultdict(list)
for i,d1 in enumerate(sorted(by_date.keys())):
    monthly[d1[:6]].append(daily_ml[i])

cum=1.0; peak=1.0; max_dd=0.0
for m in sorted(monthly.keys()):
    d=monthly[m]; mr=1.0
    for r in d: mr*=(1+r/100)
    cum*=mr
    if cum>peak: peak=cum
    dd=(cum-peak)/peak*100
    if dd<max_dd: max_dd=dd
    n=len(d); w=sum(1 for r in d if r>0)
    print(f"  {m}: {n}天 月收益{(mr-1)*100:>+7.2f}% 胜率{w/n*100:.0f}% 净值{cum:.4f} 回撤{dd:.1f}%")

wr=sum(1 for r in daily_ml if r>0)/len(daily_ml)*100
print(f"\n  ML选TOP1: 净值{cum:.4f} 总收益{(cum-1)*100:.1f}% 胜率{wr:.1f}% 回撤{max_dd:.1f}%")

# 规则对比
cum2=1.0
for r in daily_rule: cum2*=(1+r/100)
wr2=sum(1 for r in daily_rule if r>0)/len(daily_rule)*100
print(f"  规则选TOP1: 净值{cum2:.4f} 总收益{(cum2-1)*100:.1f}% 胜率{wr2:.1f}%")

print(f"\n完成!")
