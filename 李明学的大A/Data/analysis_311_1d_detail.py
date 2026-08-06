#!/usr/bin/env python3
"""
311 1D基准回测 — 全部交易明细
  止损-6% > 涨停 > 收盘卖出
"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
CR=0.0001; CM=0.0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

def load_kline(code):
    fp=os.path.join(K,code)
    rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'): continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}

# 加载交易日
tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds=sorted(tds); di={d:i for i,d in enumerate(tds)}

# 加载所有样本
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
            # 提取特征
            r2=rows[d2i_k]; o2,h2,l2,c2,v2,pc2=r2[1],r2[2],r2[3],r2[4],r2[5],r2[6]
            r3=rows[d2i_k-1] if d2i_k>=1 else None
            cls=np.array([r[4] for r in rows[:d2i_k+1]])
            highs=np.array([r[2] for r in rows[:d2i_k+1]]); n=len(cls)
            f={}
            f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
            f['vol_contract']=1 if(r3 and v2<r3[5]*0.8) else 0
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
daily_meta=defaultdict(list)
for i,s in enumerate(samples): daily_meta[s[2]].append(i)
all_dates=sorted(daily_meta.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples])
y=np.array([(s[4]-s[3])/s[3]*100 for s in samples])

def fee(buy, sell, capital):
    sh = int(capital / buy / 100) * 100
    if sh == 0: sh = 100
    c = sh * buy; bf = max(c * CR, CM) + c * TF; tb = c + bf
    r = sh * sell; sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100, sh

def sell_daily(bp, o, h, l, c):
    limit_up = round(bp * 1.10, 2); stop = bp * 0.94
    if o <= stop: return o, '开盘止损'
    if l <= stop: return stop, '日内止损'
    if h >= limit_up * 0.999: return limit_up, '涨停卖出'
    return c, '收盘卖出'

# 回测
trades = []
consec = 0
cum = 1.0; peak = 1.0; max_dd = 0.0
year_cum = defaultdict(float)
month_cum = defaultdict(float)

for d1_date in all_dates:
    idxs = daily_meta[d1_date]; first_i = idxs[0]
    
    # WF选股
    if first_i < 100:
        best = samples[idxs[0]]
    else:
        hist = [j for j in range(first_i)]
        Xh = X[hist]; yh = y[hist]
        mean = Xh.mean(axis=0); std = Xh.std(axis=0) + 1e-8
        Xn = (Xh - mean) / std; d = Xn.shape[1]
        try: w = solve(Xn.T @ Xn + np.eye(d) * 2.0, Xn.T @ yh)
        except: w = np.zeros(d)
        Xt = np.array([(X[i] - mean) / std for i in idxs])
        preds = Xt @ w; best = samples[idxs[int(np.argmax(preds))]]
    
    code = best[1]; name = best[5]; bp = best[3]
    o = best[6]; h = best[7]; l = best[8]; c_d = best[4]
    
    # 连续亏损管理
    cap = CAPITAL
    force = ''
    if consec >= 3:
        trades.append({'date': d1_date, 'name': name, 'code': code,
            'bp': 0, 'sp': 0, 'ret': 0.0, 'mode': '跳过(连亏3次)',
            'cum': cum, 'shares': 0})
        consec = 0
        continue
    elif consec >= 2:
        cap = CAPITAL * 0.5
        force = ' [半仓]'
    
    sp, mode = sell_daily(bp, o, h, l, c_d)
    ret, sh = fee(bp, sp, cap)
    cum *= (1 + ret/100)
    if cum > peak: peak = cum
    dd = (cum - peak)/peak*100
    if dd < max_dd: max_dd = dd
    
    trades.append({
        'date': d1_date, 'name': name, 'code': code,
        'bp': bp, 'sp': sp, 'ret': ret, 'mode': mode + force,
        'cum': cum, 'shares': sh
    })
    
    if ret < -0.05: consec += 1
    else: consec = 0

# ============ 输出 ============
print(f"\n{'='*120}")
print(f'  311基准回测 — 全部交易明细 (1D日线)')
print(f'  止损-6% → 涨停卖出 → 收盘卖出')
print(f"{'='*120}\n")

# 年份汇总
y_sum = defaultdict(lambda: {'ret': 0, 'w': 0, 'l': 0})
for t in trades:
    y = t['date'][:4]
    if t['ret'] != 0:
        yr = 1.0
        for r in [x['ret'] for x in trades if x['ret'] != 0 and x['date'][:4]==y and x['date']<=t['date']]:
            pass
    if t['ret'] > 0: y_sum[y]['w'] += 1
    elif t['ret'] < 0: y_sum[y]['l'] += 1

# 每笔
print(f"{'日期':<10} {'名称':<8} {'代码':<10} {'买入价':>8} {'卖出价':>8} {'盈亏':>9} {'累计净值':>9} {'卖出方式':<20}")
print('-'*120)

total_w = 0; total_l = 0; total_trades = 0

for t in trades:
    d = t['date']
    dt_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    if t['ret'] == 0:
        print(f"{dt_str:<10} {'':>8} {'':>10} {'':>8} {'':>8} {'跳过':>9} {t['cum']:>9.4f} {t['mode']:<20}")
        continue
    sign = '+' if t['ret'] > 0 else ''
    profit = (t['sp'] - t['bp']) * t['shares']
    print(f"{dt_str:<10} {t['name']:<8} {t['code']:<10} {t['bp']:>8.2f} {t['sp']:>8.2f} {sign}{t['ret']:>+8.2f}% {t['cum']:>9.4f} {t['mode']:<20}")
    total_trades += 1
    if t['ret'] > 0: total_w += 1
    elif t['ret'] < 0: total_l += 1

# 汇总
wr = total_w/total_trades*100 if total_trades>0 else 0
print(f"\n{'='*120}")
print(f'  总计: {total_trades}笔 | 胜{total_w}负{total_l} | 胜率{wr:.1f}% | 净值{cum:.4f} | 收益{(cum-1)*100:+.1f}% | 最大回撤{max_dd:.1f}%')
print(f"{'='*120}")

# 月度汇总
print(f"\n{'月份':<8} {'笔数':>4} {'月收益':>10} {'累计净值':>10}")
m_cum = 1.0
m_data = defaultdict(list)
for t in trades:
    m_data[t['date'][:6]].append(t['ret'])

for m in sorted(m_data.keys()):
    mr = 1.0
    valid = [r for r in m_data[m] if r != 0]
    for r in valid: mr *= (1 + r/100)
    m_cum *= mr
    print(f"{m[:4]}-{m[4:]:<3} {len(valid):>4} {(mr-1)*100:>+9.2f}% {m_cum:>10.4f}")

# 季度汇总
print(f"\n{'季度':<10} {'笔数':>4} {'季度收益':>10} {'累计净值':>10}")
q_cum = 1.0
q_data = defaultdict(list)
for t in trades:
    ym = t['date'][:6]
    q = t['date'][:4] + 'Q' + str((int(t['date'][4:6]) - 1) // 3 + 1)
    q_data[q].append(t['ret'])

for q in sorted(q_data.keys()):
    qr = 1.0
    valid = [r for r in q_data[q] if r != 0]
    for r in valid: qr *= (1 + r/100)
    q_cum *= qr
    print(f"{q:<10} {len(valid):>4} {(qr-1)*100:>+9.2f}% {q_cum:>10.4f}")

# 年度
print(f"\n{'年份':<8} {'收益':>12}")
for y in sorted(set(t['date'][:4] for t in trades)):
    yr = 1.0
    for t in trades:
        if t['date'][:4] == y and t['ret'] != 0:
            yr *= (1 + t['ret']/100)
    print(f'{y:<8} {(yr-1)*100:>+11.1f}%')

# 卖出方式统计
print(f"\n{'卖出方式':<20} {'次数':>6}")
mode_count = defaultdict(int)
for t in trades:
    mode_count[t['mode']] += 1
for m, c in sorted(mode_count.items(), key=lambda x: -x[1]):
    print(f'{m:<20} {c:>6}')
