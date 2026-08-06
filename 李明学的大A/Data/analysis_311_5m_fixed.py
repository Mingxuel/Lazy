#!/usr/bin/env python3
"""
311 5M回测修正版 — 解决复权不一致
  每条5M数据按 1D_close/5M_close 缩放, 消除后复权偏差
"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'
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

_5m_cache = {}
def load_5m_bars_scaled(code, date_str, d1_open, d1_close):
    """加载5M数据并按1D价格缩放"""
    if code not in _5m_cache:
        fp = os.path.join(M5DIR, code)
        if not os.path.exists(fp):
            _5m_cache[code] = {}
            return None
        by_date = defaultdict(list)
        with open(fp, encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if not l: continue
                p = l.split('|')
                if len(p) < 6: continue
                dt = p[0]; d = dt[:10].replace('-', '')
                bar = (dt, float(p[1]), float(p[2]), float(p[3]), float(p[4]), float(p[5]))
                by_date[d].append(bar)
        _5m_cache[code] = dict(by_date)
    
    raw_bars = _5m_cache[code].get(date_str)
    if not raw_bars or len(raw_bars) < 10:
        return None
    
    # 缩放因子: 用open做校准(更稳定), 回退到close
    m5_open = raw_bars[0][1]  # first bar open
    m5_close = raw_bars[-1][3]  # last bar close
    
    scale_open = d1_open / m5_open if m5_open > 0 else 1.0
    scale_close = d1_close / m5_close if m5_close > 0 else 1.0
    
    # 如果open偏差<1%用open校准, 否则用close
    if abs(scale_open - 1.0) < 0.02:
        scale = scale_open
    else:
        scale = scale_close
    
    scaled = []
    for dt, o, h, l, c, v in raw_bars:
        scaled.append((dt, o*scale, h*scale, l*scale, c*scale, v))
    return scaled


FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

def compute_ma_golden(rows, d2i):
    if d2i < 10: return 0
    closes = np.array([r[4] for r in rows[:d2i+1]])
    ma5_now = np.mean(closes[-5:]); ma10_now = np.mean(closes[-10:])
    ma5_prev = np.mean(closes[-6:-1]); ma10_prev = np.mean(closes[-11:-1])
    return 1 if (ma5_prev <= ma10_prev and ma5_now > ma10_now) else 0

def extract_all(rows, d2i, code):
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
    f['ma_golden']=compute_ma_golden(rows,d2i)
    return f

# 加载样本
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
            name=p[0]; code=p[1]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]
            bp=r1[6]; sp_close=r1[4]; d1_open=r1[1]; d1_high=r1[2]; d1_low=r1[3]
            if bp<=0: continue
            f=extract_all(rows,d2i_k,code)
            samples.append((f,code,d1,bp,sp_close,name,d1_open,d1_high,d1_low))

samples.sort(key=lambda x:x[2])
daily_meta=defaultdict(list)
for i,s in enumerate(samples): daily_meta[s[2]].append(i)
all_dates=sorted(daily_meta.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples])
y=np.array([(s[4]-s[3])/s[3]*100 for s in samples])
n=len(samples)
print(f"样本: {n}笔, {len(all_dates)}天")

def fee(buy, sell, pc=CAPITAL):
    sh = int(pc / buy / 100) * 100
    if sh == 0: sh = 100
    c = sh * buy; bf = max(c * CR, CM) + c * TF; tb = c + bf
    r = sh * sell; sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100


# ============================================================
# 5M日内卖出 (价格已缩放)
# ============================================================
def sell_5m(bars, bp, trigger_pct=1.03, trail_pct=0.01,
            time_filter=0, confirm_bars=1):
    if not bars: return bp, 'no_data'
    
    stop_price = bp * 0.94
    limit_up = round(bp * 1.10, 2)
    peak = bp
    triggered = False
    trail_count = 0
    
    for i, (dt, o, h, l, c, v) in enumerate(bars):
        if i == 0 and o <= stop_price:
            return o, 'open_stop'
        if l <= stop_price:
            return stop_price, 'low_stop'
        if h >= limit_up * 0.999:
            return limit_up, 'limit_up'
        
        bar_minute = int(dt[11:13]) * 60 + int(dt[14:16]) if len(dt) >= 16 else 0
        morning_start = 9 * 60 + 35
        
        if time_filter > 0 and bar_minute - morning_start < time_filter:
            continue
        
        if h >= bp * trigger_pct:
            triggered = True
            if h > peak: peak = h
        
        if triggered and c <= peak * (1 - trail_pct):
            trail_count += 1
            if trail_count >= confirm_bars:
                # 确认触发时按当前收盘价卖出，不是peak*0.99
                return max(c, stop_price), 'trail_stop'
        else:
            trail_count = 0
    
    return bars[-1][3], 'close'


def sell_daily(bp, o, h, l, c):
    limit_up = round(bp * 1.10, 2); stop = bp * 0.94
    if o <= stop: return o, 'open_stop'
    if l <= stop: return stop, 'low_stop'
    if h >= limit_up * 0.999: return limit_up, 'limit_up'
    return c, 'close'


# ============================================================
# 回测
# ============================================================
def backtest(samples, all_dates, daily_meta, X, y, name,
             trigger=1.03, trail=0.01, time_filter=0, confirm=1,
             use_5m=True, use_consec=True):
    rets = []; stats = defaultdict(int); consec = 0; fb = 0
    
    for d1_date in all_dates:
        idxs = daily_meta[d1_date]; first_i = idxs[0]
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
        
        bp=best[3]; o=best[6]; h_d=best[7]; l_d=best[8]; c_d=best[4]; code=best[1]
        
        cap = CAPITAL
        if use_consec:
            if consec >= 3:
                rets.append(0.0); stats['skip']+=1; consec=0; continue
            elif consec >= 2:
                cap = CAPITAL * 0.5; stats['half']+=1
        
        sold = False
        if use_5m:
            bars = load_5m_bars_scaled(code, d1_date, o, c_d)
            if bars and len(bars) >= 10:
                sp, mode = sell_5m(bars, bp, trigger, trail, time_filter, confirm)
            else:
                fb += 1
                sp, mode = sell_daily(bp, o, h_d, l_d, c_d)
        else:
            sp, mode = sell_daily(bp, o, h_d, l_d, c_d)
        
        ret = fee(bp, sp, cap)
        rets.append(ret); stats[mode]+=1
        if ret < -0.05: consec += 1
        elif ret > 0.05: consec = 0
    
    return rets, stats, fb


def metrics(rets):
    cum=1.0; peak=1.0; md=0.0
    for r in rets:
        if r==0: continue
        cum*=(1+r/100)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<md: md=dd
    wr=sum(1 for r in rets if r>0)/len(rets)*100 if rets else 0
    return cum,(cum-1)*100,wr,md


# ============================================================
# 全部变体扫描
# ============================================================
variants = [
    ('基准: 收盘+止损(1D)',              999, 0,   0,  1, False),
    ('5M: 收盘+止损',                   999, 0,   0,  1, True),
    ('5M: +3%/-1% 原始',              1.03, 0.01, 0,  1, True),
    ('5M: +3%/-1% 前30分禁用',          1.03, 0.01, 30, 1, True),
    ('5M: +3%/-1% 前60分禁用',          1.03, 0.01, 60, 1, True),
    ('5M: +3%/-1% 2K确认',             1.03, 0.01, 0,  2, True),
    ('5M: +3%/-1% 前30分+2K确认',       1.03, 0.01, 30, 2, True),
    ('5M: +3%/-2% 原始',              1.03, 0.02, 0,  1, True),
    ('5M: +3%/-2% 前30分禁用',          1.03, 0.02, 30, 1, True),
    ('5M: +3%/-2% 前30分+2K确认',       1.03, 0.02, 30, 2, True),
    ('5M: +3%/-3% 原始',              1.03, 0.03, 0,  1, True),
    ('5M: +2%/-2% 原始',              1.02, 0.02, 0,  1, True),
    ('5M: +4%/-2% 原始',              1.04, 0.02, 0,  1, True),
    ('5M: +5%/-2% 原始',              1.05, 0.02, 0,  1, True),
]

all_results = {}
print(f"\n{'='*100}")
print(f'  5M回测修正版 — 复权一致')
print(f"{'='*100}")
print(f"{'策略':<38} {'净值':>8} {'收益':>10} {'胜率':>7} {'回撤':>7}  {'卖出分布'}")

for label, trg, trl, tf, cb, use5 in variants:
    rets, st, fb = backtest(samples, all_dates, daily_meta, X, y, label, trg, trl, tf, cb, use5)
    c, tr, wr, dd = metrics(rets)
    mods = ', '.join(f'{k}:{v}' for k, v in sorted(st.items()))
    fb_str = f' [回退{fb}]' if fb > 0 else ''
    all_results[label] = (rets, c, tr, wr, dd, st)
    print(f"{label:<38} {c:>8.4f} {tr:>+9.1f}% {wr:>6.1f}% {dd:>6.1f}%  {mods}{fb_str}")


# ============================================================
# 最佳策略明细
# ============================================================
best = max(all_results, key=lambda k: all_results[k][1])
rets, cum, tr, wr, dd, st = all_results[best]

print(f"\n{'='*90}")
print(f'  最佳: {best}  净值{cum:.4f}  收益{tr:+.1f}%  胜率{wr:.1f}%')
print(f"{'='*90}")

m_rets = defaultdict(list)
for mi, d in enumerate(all_dates):
    m_rets[d[:6]].append(rets[mi])

print(f"\n{'月份':<8} {'天':>4} {'收益':>10} {'胜率':>7}  {'净值':>10}")
cv = 1.0
for m in sorted(m_rets.keys()):
    mr = 1.0
    for r in m_rets[m]:
        if r != 0: mr *= (1 + r / 100)
    cv *= mr
    days = sum(1 for r in m_rets[m] if r != 0)
    wrm = sum(1 for r in m_rets[m] if r > 0) / max(days, 1) * 100
    print(f'{m:<8} {days:>4} {(mr-1)*100:>+9.2f}% {wrm:>6.0f}%  {cv:>10.4f}')

# 年度
y_rets = defaultdict(list)
for mi, d in enumerate(all_dates):
    y_rets[d[:4]].append(rets[mi])
print(f"\n{'年份':<8} {'收益':>12}")
for y in sorted(y_rets.keys()):
    yr = 1.0
    for r in y_rets[y]:
        if r != 0: yr *= (1 + r / 100)
    print(f'{y:<8} {(yr-1)*100:>+11.1f}%')

ot = 1.0
for m in sorted(m_rets.keys()):
    if m < '202604': continue
    mr = 1.0
    for r in m_rets[m]:
        if r != 0: mr *= (1 + r / 100)
    ot *= mr
print(f'\n样本外(202604+) 累计: {(ot-1)*100:+.2f}%')


# ============================================================
# Top3对比
# ============================================================
print(f"\n{'='*90}")
print(f'  Top 3 月度对比')
top3 = sorted(all_results.items(), key=lambda x: -x[1][1])[:3]
for label, (rets, cum, tr, wr, dd, st) in top3:
    print(f"\n--- {label} (净值{cum:.4f} 收益{tr:+.1f}%) ---")
    mrets = defaultdict(list)
    for mi, d in enumerate(all_dates):
        mrets[d[:6]].append(rets[mi])
    cv_v = 1.0
    print(f"{'月份':<8} {'收益':>10} {'净值':>10}")
    for m in sorted(mrets.keys()):
        mr = 1.0
        for r in mrets[m]:
            if r != 0: mr *= (1 + r / 100)
        cv_v *= mr
        print(f'{m:<8} {(mr-1)*100:>+9.2f}% {cv_v:>10.4f}')

print(f"\n完成!")
