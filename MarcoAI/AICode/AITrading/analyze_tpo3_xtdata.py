# -*- coding: utf-8 -*-
"""TPO3分析 — 使用xtdata日线(全天量), 和回测100%一致"""
import os, sys, numpy as np
from collections import defaultdict

FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
SRC = r'C:\Lazy\李明学的大A\Data\Strategy'
KDIR = r'C:\Lazy\李明学的大A\Data\1D'

# 加载交易日
tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds = sorted(tds)
di = {d:i for i,d in enumerate(tds)}

def load_kline_file(code):
    fp = os.path.join(KDIR, code)
    rows = []
    with open(fp) as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'): continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows, {r[0]:i for i,r in enumerate(rows)}

# 加载所有历史样本(WF训练)
samples_all = []
for fn in sorted(os.listdir(SRC)):
    if not fn.isdigit(): continue
    d1 = fn; d1i = di.get(d1)
    if d1i is None or d1i<3: continue
    d2 = tds[d1i-1]
    with open(os.path.join(SRC, fn)) as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<2: continue
            name,code = p[0],p[1]
            rows,date_idx = load_kline_file(code)
            d1i_k = date_idx.get(d1); d2i_k = date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1 = rows[d1i_k]; bp = r1[6]; sp_c = r1[4]
            if bp<=0: continue
            r2=rows[d2i_k]; r3=rows[d2i_k-1] if d2i_k>=1 else None
            cls=np.array([r[4] for r in rows[:d2i_k+1]])
            highs=np.array([r[2] for r in rows[:d2i_k+1]])
            lows=np.array([r[3] for r in rows[:d2i_k+1]])
            n=len(cls)
            f={}
            f['pb_depth']=(r3[4]-r2[4])/r3[4]*100 if(r3 and r3[4]>0) else 0
            f['vol_contract']=1 if(r3 and r2[5]<r3[5]*0.8) else 0
            f['ma5_dev']=(r2[4]-np.mean(cls[-5:]))/np.mean(cls[-5:])*100 if n>=5 else 0
            if n>=10:
                trs=[]
                for i in range(d2i_k-9,d2i_k+1):
                    h=highs[i]; l=lows[i]; pc=rows[i-1][4] if i>0 else rows[i][6]
                    trs.append(max(h-l,abs(h-pc),abs(l-pc)))
                atr10=np.mean(trs) if trs else 1
            else: atr10=r2[2]-r2[3] if r2[2]>r2[3] else 1
            f['pc_vs_low_atr']=(r2[6]-r2[3])/atr10 if atr10>0 else 0
            f['high_vs_pc_atr']=(r2[2]-r2[6])/atr10 if atr10>0 else 0
            c_arr=np.array([r[4] for r in rows[:d2i_k+1]])
            f['ma_golden']=0
            if d2i_k>=10:
                ma5=np.mean(c_arr[-5:]); ma10=np.mean(c_arr[-10:])
                ma5p=np.mean(c_arr[-6:-1]); ma10p=np.mean(c_arr[-11:-1])
                f['ma_golden']=1 if(ma5p<=ma10p and ma5>ma10) else 0
            samples_all.append((f,code,d1,bp,sp_c,name))

print(f'WF训练样本: {len(samples_all)}')

X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples_all])
y=np.array([(s[4]-s[3])/s[3]*100 for s in samples_all])
mean=X.mean(axis=0); std=X.std(axis=0)+1e-8
Xn=(X-mean)/std
w=np.linalg.solve(Xn.T@Xn+np.eye(Xn.shape[1])*2.0,Xn.T@y)

nm_cn=['回踩深度','量能收缩','MA5偏离','空头砸多深','多头还多强','均线金叉']
print('=== 6特征权重 (Walk-Forward) ===')
for nm,wt in zip(nm_cn,w):
    print(f'  {nm}: {wt:+.4f}')

# === 今日TPO3 xtdata日线 ===
from xtquant import xtdata
codes = ['000657.SZ','002636.SZ','601869.SH','603268.SH']
names_cn = {'000657.SZ':'中钨高新','002636.SZ':'金安国纪','601869.SH':'长飞光纤','603268.SH':'松发股份'}

xtdata.download_history_data2(codes, '1d', '20260801', '20260807')

print(f'\n{"="*70}')
print(f'TPO3 今日分析 (D-2=20260807, D-3=20260805)')
print(f'vol_contract: xtdata日线全天量 vs 日线全天量, 和回测100%一致')
print(f'{"="*70}')

# 原始特征表
print(f'\n=== 四只原始特征值 ===')
print(f'{"特征":<16} {"000657 中钨":>12} {"002636 金安":>12} {"601869 长飞":>12} {"603268 松发":>12}')
print('-'*70)

raw_features = {}
for code in codes:
    k = xtdata.get_market_data_ex(field_list=['close','volume','high','low','preClose'],
        stock_list=[code], period='1d', start_time='20260601', end_time='20260807')
    if code not in k: continue
    r = k[code]
    closes = r['close'].values; vols = r['volume'].values
    highs = r['high'].values; lows = r['low'].values; preCloses = r['preClose'].values
    n = len(closes)
    if n < 15: continue
    
    d3_close = closes[-3]; d3_vol = vols[-3]
    d2_close = closes[-1]; d2_vol = vols[-1]
    d2_high = highs[-1]; d2_low = lows[-1]; d2_pre = preCloses[-1]
    
    pb = (d3_close - d2_close) / d3_close * 100
    vol_ct = 1 if d3_vol > 0 and d2_vol < d3_vol * 0.8 else 0
    vol_ratio = d2_vol / d3_vol if d3_vol > 0 else 0
    
    ma5_arr = closes[-6:-1]; ma5 = np.mean(ma5_arr)
    ma5_dev = (d2_close - ma5) / ma5 * 100 if ma5 > 0 else 0
    
    trs = []
    for i in range(-13, -2):
        h = highs[i]; l = lows[i]; pc = closes[i-1] if i > -13 else preCloses[i]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    atr10 = np.mean(trs) if trs else 1
    
    bear = (d2_pre - d2_low) / atr10
    bull = (d2_high - d2_pre) / atr10
    
    golden = 0
    if n >= 12:
        ma5_now = np.mean(closes[-6:-1]); ma10_now = np.mean(closes[-11:-1])
        ma5_prev = np.mean(closes[-7:-2]); ma10_prev = np.mean(closes[-12:-2])
        golden = 1 if (ma5_prev <= ma10_prev and ma5_now > ma10_now) else 0
    
    raw_features[code] = [pb, vol_ct, ma5_dev, bear, bull, golden, vol_ratio]
    
    chg = (d2_close - d3_close) / d3_close * 100
    print(f'  D-3收/V: {d3_close:.1f}/{d3_vol/10000:.0f}万手')
    print(f'  D-2收/V: {d2_close:.1f}/{d2_vol/10000:.0f}万手 V比={vol_ratio:.2f}x')

for feat_name in FEATURES:
    vals = []
    for code in codes:
        if code in raw_features:
            idx = FEATURES.index(feat_name)
            vals.append(f'{raw_features[code][idx]:>+12.2f}')
        else:
            vals.append(f'{"N/A":>12}')
    print(f'  {feat_name:<14}' + ''.join(vals))

# 得分贡献
print(f'\n=== 每项特征得分贡献 ===')
print(f'{"特征":<16} {"000657 中钨":>12} {"002636 金安":>12} {"601869 长飞":>12} {"603268 松发":>12}')
print('-'*70)

candidates = []
total_scores = {}
for code in codes:
    if code not in raw_features: continue
    feat = np.array([raw_features[code][i] for i in range(6)])
    Xs = (feat - mean) / (std + 1e-8)
    score = float(Xs @ w)
    total_scores[code] = score
    
    # Print per-feature contribution for this stock
    for i, fn in enumerate(FEATURES):
        contrib = Xs[i] * w[i]
        print(f'  {fn:<14} {contrib:>+12.4f}')
    print(f'  {"总分→":<14} {score:>+12.4f}')
    print()
    
    vr = raw_features[code][6]  # vol_ratio (7th element)
    candidates.append((code, names_cn[code], score,
        feat[0],      # pb_depth
        feat[1],      # vol_contract
        feat[4],      # high_vs_pc_atr (bull)
        feat[3],      # pc_vs_low_atr (bear)
        feat[5],      # ma_golden
        vr            # vol_ratio
    ))

print(f'\n{"="*50}')
print(f'TPO3 最终排序')
candidates.sort(key=lambda x: -x[2])
for i,(code,name,sc,pb,vc,bull,bear,gld,vr) in enumerate(candidates):
    m = ' ★★★ 尾盘买入' if i==0 else ''
    print(f'  {i+1}. {name}({code}) 得分:{sc:+.4f} pb={pb:+.2f} vol_ct={vc}({vr:.2f}x) bull={bull:.2f}{m}')
