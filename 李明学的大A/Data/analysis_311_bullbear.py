"""增强多空特征：空头砸多深 + 多头还多强"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
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
            if not l or l.startswith('\ufeff'): continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}
def check_ma5(code,dt,close):
    fp=os.path.join(M5,code)
    if not os.path.exists(fp): return 0,0
    df=dt[:4]+'-'+dt[4:6]+'-'+dt[6:8]
    bars=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<6: continue
            if p[0].startswith(df): bars.append((p[0],float(p[4]),float(p[2]),float(p[3]),float(p[1]),float(p[5])))
    if not bars or len(bars)<10: return 0,0
    for b in bars:
        bl,bc=b[3],b[1]
        if close>0:
            d=(bl-close)/close*100
            if -1.5<d<1.0:
                bounce=(bc-bl)/bl*100
                if bounce>1.5: return 1,bounce
    return 0,0

def extract(rows,d2i):
    r2=rows[d2i]; o2,h2,l2,c2,v2,pc2=r2[1],r2[2],r2[3],r2[4],r2[5],r2[6]
    r3=rows[d2i-1] if d2i>=1 else None
    cls=np.array([r[4] for r in rows[:d2i+1]])
    highs=np.array([r[2] for r in rows[:d2i+1]])
    lows=np.array([r[3] for r in rows[:d2i+1]])
    n=len(cls)
    
    f={}
    
    # ====== 增强版空头砸多深 (pc_vs_low) ======
    # V1: 原始 — 昨收-最低 / 昨收
    f['raw_pc_vs_low']=(pc2-l2)/pc2*100 if pc2>0 else 0
    
    # V2: ATR标准化 — 砸的深度 / 近期波动幅度 (真正的恐慌程度)
    if n>=10:
        trs=[]
        for i in range(d2i-9,d2i+1):
            h=highs[i]; l=lows[i]; pc=rows[i-1][4] if i>0 else rows[i][6]
            tr=max(h-l,abs(h-pc),abs(l-pc))
            trs.append(tr)
        atr10=np.mean(trs)
    else:
        atr10=h2-l2 if h2>l2 else 1
    f['pc_vs_low_atr']=(pc2-l2)/atr10 if atr10>0 else 0
    
    # V3: vs 近5日平均最低 — 今天砸得比平时深多少
    if n>=5: 
        avg_low5=np.mean(lows[-5:])
        f['low_vs_avg5']=(l2-avg_low5)/avg_low5*100
    else: f['low_vs_avg5']=0
    
    # V4: 破位程度 — 低点 vs MA5/MA10/MA20
    if n>=5: f['low_vs_ma5']=(l2-np.mean(cls[-5:]))/np.mean(cls[-5:])*100
    else: f['low_vs_ma5']=0
    if n>=10: f['low_vs_ma10']=(l2-np.mean(cls[-10:]))/np.mean(cls[-10:])*100
    else: f['low_vs_ma10']=0
    if n>=20: f['low_vs_ma20']=(l2-np.mean(cls[-20:]))/np.mean(cls[-20:])*100
    else: f['low_vs_ma20']=0
    
    # V5: 盘中砸盘的"质量" — 最低点出现在何时? (上午砸穿下午拉回=强支撑)
    # 这里用下影线比例替代 (已在close_pos中)
    f['bear_quality']=f['raw_pc_vs_low']*(1-f['close_pos_hint']) if False else 0
    # 实际: 大砸+收盘收回来 = 假摔
    
    # ====== 增强版多头还多强 (high_vs_pc) ======
    # V1: 原始
    f['raw_high_vs_pc']=(h2-pc2)/pc2*100 if pc2>0 else 0
    
    # V2: ATR标准化
    f['high_vs_pc_atr']=(h2-pc2)/atr10 if atr10>0 else 0
    
    # V3: 高点vs近期高点 — 创新高了吗
    if n>=10: f['high_vs_10d']=(h2-max(highs[-10:]))/max(highs[-10:])*100 if max(highs[-10:])>0 else 0
    else: f['high_vs_10d']=0
    if n>=20: f['high_vs_20d']=(h2-max(highs[-20:]))/max(highs[-20:])*100 if max(highs[-20:])>0 else 0
    else: f['high_vs_20d']=0
    
    # V4: 冲高回落幅度 — (high-close)/(high-low) (收盘留了多少)
    f['retrace_ratio']=(h2-c2)/(h2-l2)*100 if h2>l2 else 0
    
    # 占位
    f['close_pos_hint']=0  # placeholder, not used
    
    # 基础特征(保持简版)
    f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
    f['vol_contract']=1 if(r3 and v2<r3[5]*0.8) else 0
    if n>=5: f['ma5_dev']=(c2-np.mean(cls[-5:]))/np.mean(cls[-5:])*100
    else: f['ma5_dev']=0
    
    return f

# ======================
tds=load_td(); di={d:i for i,d in enumerate(tds)}
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
            r1=rows[d1i_k]; bp=r1[6]; sp=r1[4]
            if bp<=0: continue
            ret=(sp-bp)/bp*100
            f=extract(rows,d2i_k)
            f['ma5_support'],f['ma5_bounce']=check_ma5(code,d2,r1[6])
            samples.append((f,ret,code,d1,bp,sp))

samples.sort(key=lambda x:x[3])
n=len(samples)

def fee(buy,sell):
    sh=int(CAPITAL/buy/100)*100
    if sh==0: sh=100
    c=sh*buy; bf=max(c*CR,CM)+c*TF; tb=c+bf
    r=sh*sell; sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

daily_meta=defaultdict(list)
for i,s in enumerate(samples): daily_meta[s[3]].append(i)
all_dates=sorted(daily_meta.keys())

# baseline
baseline=[]
for d1 in all_dates:
    idxs=daily_meta[d1]
    pc=CAPITAL/len(idxs)
    baseline.append(np.mean([fee(samples[i][4],samples[i][5]) for i in idxs]))

# 测试多种空头/多头增强组合
# 固定pb_depth+vol_contract+ma5_dev, 只替换空头和多头特征
tests = []

# 原始TOP5 (baseline)
tests.append((['pb_depth','vol_contract','ma5_dev','raw_pc_vs_low','raw_high_vs_pc'],
              '原始V1(pc_vs_low + high_vs_pc)'))

# 空头增强版本
tests.append((['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','raw_high_vs_pc'],
              '空头ATR标准化'))

tests.append((['pb_depth','vol_contract','ma5_dev','low_vs_avg5','raw_high_vs_pc'],
              '空头vs近5日均低'))

tests.append((['pb_depth','vol_contract','ma5_dev','low_vs_ma20','raw_high_vs_pc'],
              '空头破MA20程度'))

# 多头增强版本
tests.append((['pb_depth','vol_contract','ma5_dev','raw_pc_vs_low','high_vs_pc_atr'],
              '多头ATR标准化'))

tests.append((['pb_depth','vol_contract','ma5_dev','raw_pc_vs_low','high_vs_10d'],
              '多头vs近10日高'))

tests.append((['pb_depth','vol_contract','ma5_dev','raw_pc_vs_low','retrace_ratio'],
              '多头冲高回落比'))

# 双增强
tests.append((['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr'],
              '双ATR标准化(空+多)'))

tests.append((['pb_depth','vol_contract','ma5_dev','low_vs_avg5','high_vs_10d'],
              '空vs均低+多vs近高'))

tests.append((['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','retrace_ratio'],
              '空ATR+多冲高回落'))

# 加一个综合评分版：空头分+多头分+基本分
tests.append((['pb_depth','vol_contract','ma5_dev','raw_pc_vs_low','raw_high_vs_pc',
               'pc_vs_low_atr','high_vs_pc_atr','retrace_ratio'],
              '6特征_基础3+空2+多1'))

# 完整多空特征
tests.append((['pb_depth','vol_contract','ma5_dev',
               'raw_pc_vs_low','pc_vs_low_atr','low_vs_ma20',
               'raw_high_vs_pc','high_vs_pc_atr','high_vs_10d','retrace_ratio'],
              '10特征_全方位'))

print(f'样本: {n}笔, {len(all_dates)}天')
print(f'{"策略":<30} {"全量净值":>8} {"全量收益":>10} {"样本外":>10} {"胜率":>6}')
print('-'*72)

ALL_FEATURES = set()
for keys,_ in tests: ALL_FEATURES.update(keys)
ALL_FEATURES = sorted(ALL_FEATURES)

for keys,label in tests:
    X=np.array([[s[0].get(k,0) for k in keys] for s in samples])
    y=np.array([s[1] for s in samples])
    daily=[]
    for d1_date in all_dates:
        idxs=daily_meta[d1_date]
        first_i=idxs[0]
        if first_i<100:
            daily.append(fee(samples[idxs[0]][4],samples[idxs[0]][5]))
            continue
        hist=[j for j in range(first_i)]
        Xh=X[hist]; yh=y[hist]
        mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
        Xn=(Xh-mean)/std
        d=Xn.shape[1]
        try: w=solve(Xn.T@Xn+np.eye(d)*2.0, Xn.T@yh)
        except: w=np.zeros(d)
        Xt=np.array([(X[i]-mean)/std for i in idxs])
        preds=Xt@w
        best_i=idxs[int(np.argmax(preds))]
        daily.append(fee(samples[best_i][4],samples[best_i][5]))
    
    cum=1.0
    for r in daily: cum*=(1+r/100)
    test=[r for i,r in enumerate(daily) if all_dates[i]>='202604']
    tc=1.0
    for r in test: tc*=(1+r/100)
    wr=sum(1 for r in daily if r>0)/len(daily)*100
    print(f'{label:<30} {cum:>8.3f} {(cum-1)*100:>+9.0f}% {(tc-1)*100:>+9.1f}% {wr:>5.0f}%')

# 最好的跑月度
print()
print('特征相关性检查(与收益率):')
for fname in ALL_FEATURES:
    vals=[s[0].get(fname,0) for s in samples]
    labels=[s[1] for s in samples]
    corr=np.corrcoef(vals,labels)[0,1]
    if abs(corr)>0.05:
        print(f'  {fname:<25} corr={corr:+.4f}')
