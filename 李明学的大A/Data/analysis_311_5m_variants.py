#!/usr/bin/env python3
"""
311策略 5M回测变体扫描 — 解决日内噪音杀移动止盈
测试: 时间过滤/多K确认/宽trail/弱化移动止盈
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
def load_5m_bars(code, date_str):
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
    return _5m_cache[code].get(date_str)

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
n=len(samples)
daily_meta=defaultdict(list)
for i,s in enumerate(samples): daily_meta[s[2]].append(i)
all_dates=sorted(daily_meta.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples])
y=np.array([(s[4]-s[3])/s[3]*100 for s in samples])
print(f"样本: {n}笔, {len(all_dates)}天")

def fee(buy, sell, pc=CAPITAL):
    sh = int(pc / buy / 100) * 100
    if sh == 0: sh = 100
    c = sh * buy; bf = max(c * CR, CM) + c * TF; tb = c + bf
    r = sh * sell; sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100


# ============================================================
# 5M卖出变体
# ============================================================
def sell_5m_variant(bars, bp, trigger_pct=1.03, trail_pct=0.01,
                     time_filter_min=0,      # 0=不启用, 30=前30分钟禁用移动止盈
                     confirm_bars=1,          # 连续触发K线数, 1=即时触发
                     ):
    """
    5M日内卖出, 支持多种变体
    bars: [(dt, open, high, low, close, volume), ...]
    """
    if not bars:
        return bp, 'no_data'
    
    stop_price = bp * 0.94
    limit_up = round(bp * 1.10, 2)
    peak = bp
    triggered = False
    trail_count = 0  # 连续触发计数
    
    for i, (dt, o, h, l, c, v) in enumerate(bars):
        # 1. 开盘止损
        if i == 0 and o <= stop_price:
            return o, 'open_stop'
        
        # 2. 盘中最低止损
        if l <= stop_price:
            return stop_price, 'low_stop'
        
        # 3. 涨停
        if h >= limit_up * 0.999:
            return limit_up, 'limit_up'
        
        # 4. 移动止盈 (受时间过滤)
        bar_minute = int(dt[11:13]) * 60 + int(dt[14:16]) if len(dt) >= 16 else 0
        morning_start = 9 * 60 + 35  # 09:35
        
        if time_filter_min > 0:
            # 前N分钟不启用
            if bar_minute - morning_start < time_filter_min:
                continue
        
        if h >= bp * trigger_pct:
            triggered = True
            if h > peak:
                peak = h
        
        if triggered and c <= peak * (1 - trail_pct):
            trail_count += 1
            if trail_count >= confirm_bars:
                sell_price = max(peak * (1 - trail_pct), stop_price)
                return sell_price, 'trail_stop'
        else:
            trail_count = 0  # 没触发就重置
    
    return bars[-1][3], 'close'


def sell_daily_fallback(bp, o, h, l, c, trigger_pct=1.03, trail_pct=0.01):
    limit_up = round(bp * 1.10, 2); stop_price = bp * 0.94
    if o <= stop_price: return o, 'open_stop'
    if l <= stop_price: return stop_price, 'low_stop'
    if h >= bp * trigger_pct:
        trail_sell = h * (1 - trail_pct)
        if l <= trail_sell: return max(trail_sell, stop_price), 'trail_stop'
        if h >= limit_up * 0.999: return limit_up, 'limit_up'
        return c, 'close'
    if h >= limit_up * 0.999: return limit_up, 'limit_up'
    return c, 'close'


# ============================================================
# 回测执行
# ============================================================
def backtest_variant(samples, all_dates, daily_meta, X, y,
                     trigger_pct=1.03, trail_pct=0.01,
                     time_filter=0, confirm_bars=1,
                     use_consec_loss=True):
    ridge_daily = []; stats = defaultdict(int); consec_loss = 0
    
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
        
        bp=best[3]; o=best[6]; h=best[7]; l=best[8]; c=best[4]; code=best[1]
        
        actual_capital = CAPITAL
        if use_consec_loss:
            if consec_loss >= 3:
                ridge_daily.append(0.0); stats['skip'] += 1; consec_loss = 0; continue
            elif consec_loss >= 2:
                actual_capital = CAPITAL * 0.5; stats['half'] += 1
        
        bars_5m = load_5m_bars(code, d1_date)
        if bars_5m and len(bars_5m) >= 10:
            sp, mode = sell_5m_variant(bars_5m, bp, trigger_pct, trail_pct,
                                        time_filter, confirm_bars)
        else:
            sp, mode = sell_daily_fallback(bp, o, h, l, c, trigger_pct, trail_pct)
        
        ret = fee(bp, sp, actual_capital)
        ridge_daily.append(ret); stats[mode] += 1
        if ret < -0.05: consec_loss += 1
        elif ret > 0.05: consec_loss = 0
    
    return ridge_daily, stats


# ============================================================
# 对比测试
# ============================================================
def calc_metrics(rets):
    cum = 1.0; peak = 1.0; max_dd = 0.0
    for r in rets:
        if r == 0: continue
        cum *= (1 + r / 100)
        if cum > peak: peak = cum
        dd = (cum - peak) / peak * 100
        if dd < max_dd: max_dd = dd
    wr = sum(1 for r in rets if r > 0) / len(rets) * 100 if rets else 0
    return cum, (cum - 1) * 100, wr, max_dd


variants = [
    # (标签, trigger, trail, time_filter, confirm_bars, 说明)
    ('基准: 收盘卖', 999, 0, 0, 1),
    ('基准: 止损-6%', 999, 0, 0, 1),
    ('V0: +3%/-1% (原始)', 1.03, 0.01, 0, 1),
    ('V1: +3%/-1% 前30分禁用', 1.03, 0.01, 30, 1),
    ('V2: +3%/-1% 前60分禁用', 1.03, 0.01, 60, 1),
    ('V3: +3%/-1% 2K确认', 1.03, 0.01, 0, 2),
    ('V4: +3%/-1% 前30分+2K确认', 1.03, 0.01, 30, 2),
    ('V5: +3%/-2% 原始', 1.03, 0.02, 0, 1),
    ('V6: +3%/-2% 前30分禁用', 1.03, 0.02, 30, 1),
    ('V7: +3%/-2% 2K确认', 1.03, 0.02, 0, 2),
    ('V8: +3%/-3% 原始', 1.03, 0.03, 0, 1),
    ('V9: +3%/-3% 前30分禁用', 1.03, 0.03, 30, 1),
    ('V10: +5%/-2% 原始', 1.05, 0.02, 0, 1),
    ('V11: +5%/-2% 前30分禁用', 1.05, 0.02, 30, 1),
    ('V12: +2%/-2% 原始', 1.02, 0.02, 0, 1),
    ('V13: 收盘+止损 only', 999, 0, 0, 1),
]

print(f"\n{'='*90}")
print(f'  5M回测变体扫描')
print(f"{'='*90}")
print(f"{'变体':<35} {'净值':>8} {'收益':>10} {'胜率':>7} {'回撤':>7}  {'卖出分布'}")
print(f"{'-'*100}")

all_variant_results = {}
for label, trg, trl, tf, cb in variants:
    rets, st = backtest_variant(samples, all_dates, daily_meta, X, y, trg, trl, tf, cb, True)
    c, tr, wr, dd = calc_metrics(rets)
    mods = ', '.join(f'{k}:{v}' for k, v in sorted(st.items()))
    all_variant_results[label] = (rets, c, tr, wr, dd, st)
    print(f"{label:<35} {c:>8.4f} {tr:>+9.1f}% {wr:>6.1f}% {dd:>6.1f}%  {mods}")


# ============================================================
# 最佳策略月度年度明细
# ============================================================
# 找最好的一个
best_label = max(all_variant_results, key=lambda k: all_variant_results[k][1])
print(f"\n{'='*90}")
print(f'  最佳: {best_label}')
print(f"{'='*90}")

rets, cum, tr, wr, dd, st = all_variant_results[best_label]

# 月度
m_rets = defaultdict(list)
for mi, d in enumerate(all_dates):
    m_rets[d[:6]].append(rets[mi])

print(f"\n{'月份':<8} {'天':>4} {'收益':>10} {'胜率':>7}  {'净值':>10}")
print(f"{'-'*50}")
cum_v = 1.0
for m in sorted(m_rets.keys()):
    mr = 1.0
    for r in m_rets[m]:
        if r != 0: mr *= (1 + r / 100)
    cum_v *= mr
    days = sum(1 for r in m_rets[m] if r != 0)
    wr_m = sum(1 for r in m_rets[m] if r > 0) / max(days, 1) * 100
    print(f'{m:<8} {days:>4} {(mr-1)*100:>+9.2f}% {wr_m:>6.0f}%  {cum_v:>10.4f}')

print(f'{"合计":<8} {len(rets):>4} {(cum_v-1)*100:>+9.1f}%')

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

# 样本外
cutoff = '202604'
ot = 1.0
for m in sorted(m_rets.keys()):
    if m < cutoff: continue
    mr = 1.0
    for r in m_rets[m]:
        if r != 0: mr *= (1 + r / 100)
    ot *= mr
print(f'\n样本外({cutoff}+) 累计: {(ot-1)*100:+.2f}%')


# ============================================================
# 也打印原始的日线版前三名用于对比
# ============================================================
print(f"\n{'='*90}")
print(f'  Top 3 变体 月度对比')
print(f"{'='*90}")

top3 = sorted(all_variant_results.items(), key=lambda x: -x[1][1])[:3]
for label, (rets, cum, tr, wr, dd, st) in top3:
    m_rets = defaultdict(list)
    for mi, d in enumerate(all_dates):
        m_rets[d[:6]].append(rets[mi])
    
    print(f"\n--- {label} (净值{cum:.4f} 收益{tr:+.1f}%) ---")
    print(f"{'月份':<8} {'收益':>10} {'净值':>10}")
    cum_v = 1.0
    for m in sorted(m_rets.keys()):
        mr = 1.0
        for r in m_rets[m]:
            if r != 0: mr *= (1 + r / 100)
        cum_v *= mr
        print(f'{m:<8} {(mr-1)*100:>+9.2f}% {cum_v:>10.4f}')

print(f"\n完成!")
