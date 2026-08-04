#!/usr/bin/env python3
"""
311深度学习选股 v2: 1D特征 + 5M MA5支撑
"""
import os, numpy as np
from collections import defaultdict
np.random.seed(42)

STRATEGY_DIR = r"C:\Lazy\李明学的大A\Data\Strategy"
KLINE_DIR   = r"C:\Lazy\李明学的大A\Data\1D"
FIVEM_DIR   = r"C:\Lazy\MarcoAI\AIData\5M"

CR=0.00025; CM=5.0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

def load_td():
    ds=[]
    with open(r"C:\Lazy\李明学的大A\Data\交易日.config") as f:
        for l in f:
            l=l.strip()
            if l and l.isdigit() and len(l)==8: ds.append(l)
    return sorted(ds)

def load_kline(code):
    fp=os.path.join(KLINE_DIR,code)
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

def load_5m_bars(code, dt):
    fp=os.path.join(FIVEM_DIR,code)
    if not os.path.exists(fp): return None
    df=f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}"
    bars=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<6: continue
            if p[0].startswith(df):
                bars.append((p[0],float(p[4]),float(p[2]),float(p[3]),float(p[1]),float(p[5])))
    return bars if bars else None

def check_ma5_bounce(code, d2_date, d2_close):
    """5M数据检查D-2回踩日MA5支撑"""
    bars=load_5m_bars(code,d2_date)
    if not bars or len(bars)<10: return 0,0
    for b in bars:
        bl,bc=b[3],b[1]
        if d2_close>0:
            d=(bl-d2_close)/d2_close*100
            if -1.5<d<1.0:
                bounce=(bc-bl)/bl*100
                if bounce>1.5: return 1,bounce
    return 0,0

def extract_features(rows, date_idx, d1_date, d2_date, code):
    d1i=date_idx.get(d1_date)
    d2i=date_idx.get(d2_date)
    if d1i is None or d2i is None or d2i<20: return None,None,None

    r1=rows[d1i]; r2=rows[d2i]
    bp=r1[6]; sp=r1[4]
    if bp<=0 or sp<=0: return None,None,None
    o2,h2,l2,c2,v2=r2[1],r2[2],r2[3],r2[4],r2[5]
    r3=rows[d2i-1] if d2i>=1 else None

    f={}

    # 311模式
    if r3:
        f['pullback']=(r3[4]-c2)/r3[4]*100
        f['vol_surge']=r3[5]/v2 if v2>0 else 1
        f['vol_contract']=1 if v2<r3[5]*0.8 else 0
    else:
        f['pullback']=0; f['vol_surge']=1; f['vol_contract']=0

    # 下影线
    rng=h2-l2
    f['shadow']=(c2-l2)/rng*100 if rng>0 else 50
    f['shadow_support']=1 if (f['shadow']>50 and f['pullback']>1) else 0

    # D-2收盘位置
    f['close_pos']=(c2-l2)/rng*100 if rng>0 else 50
    f['amp']=(h2-l2)/o2*100 if o2>0 else 0

    # ★ MA5弹起(从5M)
    has_ma5,bounce=check_ma5_bounce(code,d2_date,c2)
    f['ma5_support']=has_ma5
    f['ma5_bounce']=bounce

    # 趋势(截止D-2)
    closes=np.array([r[4] for r in rows[:d2i+1]])
    vols=np.array([r[5] for r in rows[:d2i+1]])
    highs=np.array([r[2] for r in rows[:d2i+1]])
    lows=np.array([r[3] for r in rows[:d2i+1]])

    n=len(closes)
    if n>=5:  f['ma5_ratio']=closes[-1]/np.mean(closes[-5:])
    else:     f['ma5_ratio']=1
    if n>=10: f['ma10_ratio']=closes[-1]/np.mean(closes[-10:])
    else:     f['ma10_ratio']=1
    if n>=20: f['ma20_ratio']=closes[-1]/np.mean(closes[-20:])
    else:     f['ma20_ratio']=1

    if n>=2:  f['ret_1d']=(closes[-1]-closes[-2])/closes[-2]*100
    else:     f['ret_1d']=0
    if n>=5:  f['ret_5d']=(closes[-1]-closes[-5])/closes[-5]*100
    else:     f['ret_5d']=0
    if n>=10: f['ret_10d']=(closes[-1]-closes[-10])/closes[-10]*100
    else:     f['ret_10d']=0

    # 波动率
    if n>=10:
        dr=(closes[1:]-closes[:-1])/closes[:-1]*100
        f['vol10']=np.std(dr[-10:]) if len(dr)>=10 else 0
        f['vol20']=np.std(dr[-20:]) if len(dr)>=20 else 0
    else: f['vol10']=0; f['vol20']=0

    # 量比
    if n>=5: f['vol_ratio5']=vols[-1]/np.mean(vols[-5:])
    else:    f['vol_ratio5']=1
    if n>=10: f['vol_ratio10']=vols[-1]/np.mean(vols[-10:])
    else:     f['vol_ratio10']=1

    # 20日高低
    if n>=20:
        h20=np.max(highs[-20:]); l20=np.min(lows[-20:])
        f['dist_high20']=(h20-closes[-1])/h20*100 if h20>0 else 0
        f['dist_low20']=(closes[-1]-l20)/l20*100 if l20>0 else 0
    else: f['dist_high20']=0; f['dist_low20']=0

    # D-2 vs D-3新低
    f['new_low']=1 if (r3 and l2<r3[3]) else 0

    # 涨停强度(D-4)
    if d2i>=3:
        r4=rows[d2i-2]; r5=rows[d2i-3]
        f['limit_strength']=(r4[4]-r5[4])/r5[4]*100
    else: f['limit_strength']=0

    return f,bp,sp


# ============================================================
class SimpleMLP:
    def __init__(self, sizes, lr=0.001):
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
    sh=int(pc/buy/100)*100
    if sh==0: sh=100
    c=sh*buy; bf=max(c*CR,CM)+c*TF; tb=c+bf
    r=sh*sell; sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

# ============================================================
print("="*80)
print("  311深度学习选股 v2 (1D+5M)")
print("="*80)

tds=load_td(); di={d:i for i,d in enumerate(tds)}

# 收集样本
samples=[]
for fn in sorted(os.listdir(STRATEGY_DIR)):
    if not fn.isdigit(): continue
    d1=fn; d1i=di.get(d1)
    if d1i is None or d1i<3: continue
    d2=tds[d1i-1]
    with open(os.path.join(STRATEGY_DIR,fn)) as f:
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

n=len(samples)
print(f"样本: {n}笔")
keys=sorted(samples[0][0].keys())
print(f"特征: {len(keys)}维")
for k in keys: print(f"  {k}")

# 构建X,y
X_all=np.array([[s[0][k] for k in keys] for s in samples])
y_all=np.array([s[1] for s in samples])

# 时间切分70/15/15
tr_end=int(n*0.70); vl_end=int(n*0.85)
Xt=X_all[:tr_end]; yt=y_all[:tr_end]
Xv=X_all[tr_end:vl_end]; yv=y_all[tr_end:vl_end]
print(f"\n训练:{tr_end} 验证:{vl_end-tr_end} 测试:{n-vl_end}")

sc=Scaler().fit(Xt)
Xts=sc.transform(Xt); Xvs=sc.transform(Xv)

# 训练
print("\n训练神经网络...")
n_feat=Xt.shape[1]
archs=[
    ([n_feat,256,128,64,1],0.001),
    ([n_feat,512,256,128,1],0.0005),
    ([n_feat,128,64,32,1],0.002),
]
best_m=None; best_vl=float('inf')
for arch,lr in archs:
    print(f"  {arch}...",end=" ")
    m=SimpleMLP(arch,lr=lr)
    vl=m.fit(Xts,yt,Xvs,yv,epochs=300,pat=30)
    print(f"val_MSE={vl:.4f}")
    if vl<best_vl: best_vl=vl; best_m=m

# 回测
print("\n回测...")
by_date=defaultdict(list)
for i in range(vl_end,n):
    by_date[samples[i][3]].append(i)

daily_bl=[]; daily_ml=[]; daily_rule=[]
for d1 in sorted(by_date.keys()):
    idxs=by_date[d1]; n_st=len(idxs)
    
    # baseline
    pc=CAPITAL/n_st
    bl_rets=[]
    m_preds=[]
    r_scores=[]
    
    for i in idxs:
        Xi=np.array([[samples[i][0][k] for k in keys]])
        Xis=sc.transform(Xi)
        pred=best_m.predict(Xis)[0]
        
        bp,sp=samples[i][4],samples[i][5]
        bl_rets.append(fee(bp,sp,pc))
        m_preds.append(pred)
        
        # 规则评分
        f=samples[i][0]
        rs=0
        if f.get('shadow_support'): rs+=3
        if f.get('vol_contract'): rs+=2
        if f.get('ma5_support'): rs+=6
        if 0<f.get('pullback',0)<8: rs+=2
        if f.get('shadow',0)>60: rs+=2
        r_scores.append(rs)
    
    daily_bl.append(np.mean(bl_rets))
    
    # ML选最优
    best_i=int(np.argmax(m_preds))
    daily_ml.append(fee(samples[idxs[best_i]][4],samples[idxs[best_i]][5],CAPITAL))
    
    # 规则选最优
    best_ri=int(np.argmax(r_scores))
    daily_rule.append(fee(samples[idxs[best_ri]][4],samples[idxs[best_ri]][5],CAPITAL))

def metrics(rets):
    cum=1.0; peak=1.0; max_dd=0.0
    for r in rets:
        cum*=(1+r/100)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd: max_dd=dd
    wr=sum(1 for r in rets if r>0)/len(rets)*100
    return cum,(cum-1)*100,wr,max_dd

print(f"\n{'='*70}")
print(f"  测试集 ({len(daily_bl)}天)")
print(f"{'='*70}")
for label,rets in [("等权全买",daily_bl),("规则评分选TOP1",daily_rule),("ML选TOP1",daily_ml)]:
    cum,tr,wr,dd=metrics(rets)
    print(f"  {label:<20}: 净值{cum:.4f} 收益{tr:>8.1f}% 胜率{wr:.1f}% 回撤{dd:.1f}%")
print("完成!")
