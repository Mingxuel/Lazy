"""
评估TPO31候选 (002015.SZ / 600588.SH / 603337.SH)
基于截至2026-08-04的1D数据, 用6特征WF Ridge预测
"""
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

# ============ 1. 加载历史311样本, 训练WF Ridge ============
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
            name = p[0]; code = p[1]
            rows, date_idx = load_kline(code)
            d1i_k = date_idx.get(d1); d2i_k = date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1 = rows[d1i_k]
            bp = r1[6]; sp_close = r1[4]
            if bp <= 0: continue
            f = extract_all(rows, d2i_k, code)
            f['ma5_support'], f['ma5_bounce'] = check_ma5(code, d2, r1[6])
            samples_all.append((f, code, d1, bp, sp_close, name))

samples_all.sort(key=lambda x: x[2])
print(f"历史311样本: {len(samples_all)} 笔, D-1日期范围: {samples_all[0][2]} ~ {samples_all[-1][2]}")

# Walk-Forward: 用所有样本训练
X = np.array([[s[0].get(k, 0) for k in FEATURES] for s in samples_all])
y = np.array([(s[4] - s[3]) / s[3] * 100 for s in samples_all])

# 只用到20260804之前的样本
cutoff = '20260805'
mask = np.array([s[2] < cutoff for s in samples_all])
X_tr = X[mask]; y_tr = y[mask]
print(f"训练集: {len(X_tr)} (D-1 < 20260805)")

mean = X_tr.mean(axis=0); std = X_tr.std(axis=0) + 1e-8
Xn = (X_tr - mean) / std
d = Xn.shape[1]
w = solve(Xn.T @ Xn + np.eye(d) * 2.0, Xn.T @ y_tr)

print("\n=== 6特征权重 ===")
nm_cn = ['回踩深度', '量能收缩', 'MA5偏离', '空头砸多深', '多头还多强', '均线金叉']
for nm, wt in zip(nm_cn, w):
    print(f"  {nm:>8}: {wt:+.4f}")

# ============ 2. 检查交易日和TPO31候选 ============
print(f"\n交易日最新: {tds[-5:]}")
print(f"今日 20260805 {'是' if '20260805' in di else '不是'}交易日")

# 找到最新可用的D-2日
usable_d2 = None
for d in reversed(tds):
    if d < '20260806':  # 不超过明天
        rows, date_idx = load_kline('603337.SH')
        if d in date_idx:
            usable_d2 = d
            break

if usable_d2:
    d2_i = di[usable_d2]
    d1_date = tds[d2_i+1] if d2_i+1 < len(tds) else '?'
    print(f"使用 D-2={usable_d2}, D-1(卖出日)={d1_date} 进行评估")
else:
    usable_d2 = '20260804'
    print(f"回退使用 D-2=20260804")

# ============ 3. 评估三只候选 ============
print("\n" + "="*60)
print("=== TPO31 候选评估 ===")

candidates = []
for code_raw in ['002015.SZ', '600588.SH', '603337.SH']:
    rows, date_idx = load_kline(code_raw)
    d2i = date_idx.get(usable_d2)
    if d2i is None:
        print(f"\n{code_raw}: 无 {usable_d2} 数据, 用最新日期")
        # 找最新日期
        if rows:
            latest = rows[-1][0]
            d2i = len(rows) - 1
            print(f"  使用最新: {latest}")
        else:
            continue
    
    r = rows[d2i]
    
    # 311结构验证
    d4_ok = False; d3_ok = False
    if d2i >= 3:
        r4 = rows[d2i-2]  # D-4
        r3 = rows[d2i-1]  # D-3
        r4_pc = rows[d2i-3][4] if d2i >= 3 else rows[d2i-2][6]
        d4_ok = r4[4] >= r4_pc * 1.09
        d3_ok = r3[5] > rows[d2i-2][5] * 0.8 if d2i>=2 else False
    
    f = extract_all(rows, d2i, code_raw)
    
    Xt = np.array([[f.get(k, 0) for k in FEATURES]])
    Xt = (Xt - mean) / std
    pred = Xt @ w
    
    # 近5日K线
    recent = []
    for j in range(max(0, d2i-4), d2i+1):
        rr = rows[j]
        chg = (rr[4] - rr[6]) / rr[6] * 100
        recent.append(f"{rr[0]}: C={rr[4]:.2f} ({chg:+.2f}%)")
    
    is_held = " [当前持仓]" if code_raw == '603337.SH' else ""
    print(f"\n--- {code_raw}{is_held} ---")
    print(f"  D-2={rows[d2i][0]}: O={r[1]:.2f} H={r[2]:.2f} L={r[3]:.2f} C={r[4]:.2f} V={r[5]:.0f}")
    if d2i >= 3:
        print(f"  311: D-4涨停={d4_ok} D-3放量={d3_ok}")
    print(f"  特征: pb={f['pb_depth']:+.2f} vol_ct={f['vol_contract']} ma5_dev={f['ma5_dev']:+.2f}")
    print(f"         bear={f['pc_vs_low_atr']:.2f} bull={f['high_vs_pc_atr']:.2f} golden={f['ma_golden']}")
    print(f"  ★ 预测收益: {pred[0]:+.2f}%")
    print(f"  近5日: {' | '.join(recent)}")
    
    candidates.append({
        'code': code_raw,
        'pred': pred[0],
        'feats': f,
        'd4_ok': d4_ok,
        'd3_ok': d3_ok,
        'held': code_raw == '603337.SH'
    })

print("\n" + "="*50)
print("=== 推荐排序 ===")
candidates.sort(key=lambda x: x['pred'], reverse=True)
for i, c in enumerate(candidates):
    badge = "★首选" if i==0 else ""
    held = "[持仓]" if c['held'] else ""
    print(f"  {i+1}. {c['code']} {held}  预测:{c['pred']:+.2f}%  311:{c['d4_ok']}/{c['d3_ok']}  {badge}")
