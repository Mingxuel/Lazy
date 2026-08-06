"""TPO3 明日买池评估: 601611.SH / 601865.SH / 603156.SH"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

SRC = r'C:\Lazy\李明学的大A\Data\Strategy'
KDIR = r'C:\Lazy\李明学的大A\Data\1D'
M5 = r'C:\Lazy\MarcoAI\AIData\5M'

FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

def load_td():
    ds=[]
    with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
        for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and ds.append(l)
    return sorted(ds)

def load_kline(code):
    fp=os.path.join(KDIR,code)
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

def compute_ma_golden(rows, d2i):
    if d2i < 10: return 0
    c = np.array([r[4] for r in rows[:d2i+1]])
    ma5 = np.mean(c[-5:]); ma10 = np.mean(c[-10:])
    ma5p = np.mean(c[-6:-1]); ma10p = np.mean(c[-11:-1])
    return 1 if (ma5p <= ma10p and ma5 > ma10) else 0

def extract_all(rows,d2i,code):
    r2=rows[d2i]; o2,h2,l2,c2,v2,pc2=r2[1],r2[2],r2[3],r2[4],r2[5],r2[6]
    r3=rows[d2i-1] if d2i>=1 else None
    cls=np.array([r[4] for r in rows[:d2i+1]])
    highs=np.array([r[2] for r in rows[:d2i+1]])
    lows=np.array([r[3] for r in rows[:d2i+1]])
    n=len(cls)
    f={}
    f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
    f['vol_contract']=1 if(r3 and v2<r3[5]*0.8) else 0
    f['ma5_dev']=(c2-np.mean(cls[-5:]))/np.mean(cls[-5:])*100 if n>=5 else 0
    if n>=10:
        trs=[]
        for i in range(d2i-9,d2i+1):
            h=highs[i]; l=lows[i]; pc=rows[i-1][4] if i>0 else rows[i][6]
            trs.append(max(h-l,abs(h-pc),abs(l-pc)))
        atr10=np.mean(trs) if trs else 1
    else:
        atr10=h2-l2 if h2>l2 else 1
    f['pc_vs_low_atr']=(pc2-l2)/atr10 if atr10>0 else 0
    f['high_vs_pc_atr']=(h2-pc2)/atr10 if atr10>0 else 0
    f['ma5_support'],f['ma5_bounce']=check_ma5(code,'',c2)
    f['ma_golden']=compute_ma_golden(rows,d2i)
    return f

# ============ 1. 训练模型 ============
tds = load_td(); di = {d:i for i,d in enumerate(tds)}
samples_all = []
for fn in sorted(os.listdir(SRC)):
    if not fn.isdigit(): continue
    d1 = fn; d1i = di.get(d1)
    if d1i is None or d1i < 3: continue
    d2 = tds[d1i-1]
    with open(os.path.join(SRC, fn)) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) < 2: continue
            name,code = p[0],p[1]
            rows,date_idx = load_kline(code)
            d1i_k = date_idx.get(d1); d2i_k = date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1 = rows[d1i_k]; bp = r1[6]; sp_close = r1[4]
            if bp <= 0: continue
            f = extract_all(rows, d2i_k, code)
            f['ma5_support'], f['ma5_bounce'] = check_ma5(code, d2, r1[6])
            samples_all.append((f, code, d1, bp, sp_close, name))
samples_all.sort(key=lambda x: x[2])

X = np.array([[s[0].get(k,0) for k in FEATURES] for s in samples_all])
y = np.array([(s[4]-s[3])/s[3]*100 for s in samples_all])
mask = np.array([s[2] < '20260806' for s in samples_all])
X_tr = X[mask]; y_tr = y[mask]

mean = X_tr.mean(axis=0); std = X_tr.std(axis=0) + 1e-8
Xn = (X_tr - mean) / std
w = solve(Xn.T @ Xn + np.eye(Xn.shape[1])*2.0, Xn.T @ y_tr)

nm_cn = ['回踩深度','量能收缩','MA5偏离','空头砸多深','多头还多强','均线金叉']
print("=== 6特征权重 ===")
for nm,wt in zip(nm_cn,w): print(f"  {nm}: {wt:+.4f}")

# ============ 2. 找最新D-2日 ============
# TPO3是明日买池, 明天(2026-08-06)回踩, 对应D-2=20260806
# 但今天收盘了, 应该用今天(20260805)的数据作为D-2前一天
# 实际上: TPO3里的票会在明天回踩(D-2=明天), 后天卖出(D-1)
# 我们用今天的数据来预判明天的特征

# 找到数据中最新日期
usable = None
for code in ['601611.SH','601865.SH','603156.SH']:
    rows,_ = load_kline(code)
    if rows:
        last = rows[-1][0]
        if usable is None or last > usable:
            usable = last
print(f"\n数据最新日期: {usable}")

# ============ 3. 逐只分析 ============
print("\n" + "="*60)
print("TPO3 明日买池 (明天 D-2 回踩, 后天 D-1 卖出)")
print("="*60)

candidates = []
for code in ['601611.SH','601865.SH','603156.SH']:
    rows,date_idx = load_kline(code)
    if not rows:
        print(f"\n{code}: 无数据")
        continue
    
    today_i = date_idx.get(usable)
    if today_i is None:
        today_i = len(rows)-1
    
    # 明天回踩, 但明天数据没有。用今天数据作为特征替代, 做最接近的估算
    # 实际明天买, 后天卖; 我们用今天的数据近似明天的D-2特征
    r = rows[today_i]
    
    # 验证311: D-4 涨停, D-3 放量(相对于明天)
    # 明天是D-2, 今天就是D-3, ... 
    # 实际上302结构的验证需要看: 今天=?, 昨天=D-3, 前天=D-4
    # 明天是回踩日, 所以: 昨天(0804)=D-3放量, 前天(0731)=D-4涨停
    # 我们用today_i来近似(latest data)
    
    zt_ok = False; fl_ok = False
    if today_i >= 3:
        r_d4 = rows[today_i-1]  # D-3的昨天 = D-4? 不对...
        # 简化: 看最近两个交易日结构
        # today_i = 今天的数据(D-2的前一天, 即D-3)
        # 实际明天回踩, 所以今天已经是放量日或者涨停日之后了
        # 我们验证: today_i 和 today_i-1
    
    f = extract_all(rows, today_i, code)
    Xt = np.array([[f.get(k,0) for k in FEATURES]])
    Xt = (Xt - mean) / std
    pred = Xt @ w
    
    # 近5日
    recent = []
    for j in range(max(0,today_i-4), today_i+1):
        rr = rows[j]
        chg = (rr[4]-rr[6])/rr[6]*100
        recent.append(f"{rr[0][4:]}: C={rr[4]:.2f}({chg:+.2f}%)")
    
    # 311验证
    if today_i >= 2:
        r_2 = rows[today_i-2]  # 可能是D-4
        r_1 = rows[today_i-1]  # 可能是D-3
        r_3_pc = rows[today_i-3][4] if today_i>=3 else 0
        zt_ok = r_2[4] >= r_3_pc * 1.09 if r_3_pc > 0 else False
        fl_ok = r_1[5] > r_2[5] * 0.8
    
    print(f"\n--- {code} ---")
    print(f"  最新({r[0]}): O={r[1]:.2f} H={r[2]:.2f} L={r[3]:.2f} C={r[4]:.2f} V={r[5]:.0f}")
    if today_i >= 2:
        r2 = rows[today_i-2]; r1 = rows[today_i-1]
        print(f"  D-4候选({r2[0]}): C={r2[4]:.2f} 涨停={zt_ok} | D-3候选({r1[0]}): C={r1[4]:.2f} V={r1[5]:.0f}")
    print(f"  pb_depth={f['pb_depth']:+.2f} vol_ct={f['vol_contract']} ma5_dev={f['ma5_dev']:+.2f}")
    print(f"  bear={f['pc_vs_low_atr']:.2f} bull={f['high_vs_pc_atr']:.2f} golden={f['ma_golden']}")
    print(f"  ★ 预测收益: {pred[0]:+.2f}%")
    print(f"  {' | '.join(recent)}")
    
    candidates.append({'code':code,'pred':pred[0],'zt':zt_ok,'fl':fl_ok})

print("\n" + "="*50)
print("TPO3 推荐排序 (明天买入)")
candidates.sort(key=lambda x:x['pred'], reverse=True)
for i,c in enumerate(candidates):
    badge = " ★★★" if i==0 else ""
    print(f"  {i+1}. {c['code']}  预测:{c['pred']:+.2f}%  涨停/放量:{c['zt']}/{c['fl']}{badge}")
