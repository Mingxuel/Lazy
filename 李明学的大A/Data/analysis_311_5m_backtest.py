#!/usr/bin/env python3
"""
311策略 5分钟数据回测 — 精确日内卖出模拟
  卖出优先级(逐根K线): 止损-6% > 移动止盈 > 涨停 > 收盘
  5M无数据 → 回退到日线模拟
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

# ============================================================
# 5分钟数据加载 & 缓存
# ============================================================
_5m_cache = {}  # code -> {date_str: [(dt,o,h,l,c,v), ...]}

def load_5m_bars(code, date_str):
    """加载某只股票某日的5分钟K线, 返回 [(open,high,low,close,volume), ...]"""
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
                dt = p[0]  # '2025-01-02 09:35:00'
                d = dt[:10].replace('-', '')  # '20250102'
                bar = (float(p[1]), float(p[2]), float(p[3]), float(p[4]), float(p[5]))
                by_date[d].append(bar)
        _5m_cache[code] = dict(by_date)
    
    return _5m_cache[code].get(date_str)


# ============================================================
# 特征提取 (同1D版本, 6特征+ma_golden)
# ============================================================
FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

def compute_ma_golden(rows, d2i):
    if d2i < 10: return 0
    closes = np.array([r[4] for r in rows[:d2i+1]])
    ma5_now = np.mean(closes[-5:])
    ma10_now = np.mean(closes[-10:])
    ma5_prev = np.mean(closes[-6:-1])
    ma10_prev = np.mean(closes[-11:-1])
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


# ============================================================
# 加载样本
# ============================================================
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
print(f"样本: {n}笔")

daily_meta=defaultdict(list)
for i,s in enumerate(samples): daily_meta[s[2]].append(i)
all_dates=sorted(daily_meta.keys())

X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples])
y=np.array([(s[4]-s[3])/s[3]*100 for s in samples])


# ============================================================
# 5分钟日内卖出模拟
# ============================================================
def sell_intraday_5m(bars, bp, trigger_pct=1.03, trail_pct=0.01):
    """
    逐根5分钟K线模拟卖出, 返回 (sell_price, mode)
    bars: [(open,high,low,close,volume), ...] 按时间排序
    """
    if not bars:
        return bp, 'no_data'
    
    stop_price = bp * 0.94
    limit_up = round(bp * 1.10, 2)
    peak = bp
    triggered = False
    
    for i, (o, h, l, c, v) in enumerate(bars):
        # 1. 开盘止损 (第一根K线)
        if i == 0 and o <= stop_price:
            return o, 'open_stop'
        
        # 2. 盘中最低止损
        if l <= stop_price:
            return stop_price, 'low_stop'
        
        # 3. 涨停 (high触及即卖)
        if h >= limit_up * 0.999:
            return limit_up, 'limit_up'
        
        # 4. 更新移动止盈峰值
        if h >= bp * trigger_pct:
            triggered = True
            if h > peak:
                peak = h
        
        # 5. 移动止盈回撤触发
        if triggered and c <= peak * (1 - trail_pct):
            sell_price = max(peak * (1 - trail_pct), stop_price)
            return sell_price, 'trail_stop'
    
    # 所有K线走完 → 收盘卖出
    return bars[-1][3], 'close'


# ============================================================
# 日线回退卖出 (5M无数据时)
# ============================================================
def sell_intraday_daily(bp, o, h, l, c, trigger_pct=1.03, trail_pct=0.01):
    """日线回退版本 (同之前的保守逻辑)"""
    limit_up = round(bp * 1.10, 2)
    stop_price = bp * 0.94
    
    if o <= stop_price: return o, 'open_stop'
    if l <= stop_price: return stop_price, 'low_stop'
    
    if h >= bp * trigger_pct:
        trail_sell = h * (1 - trail_pct)
        if l <= trail_sell:
            return max(trail_sell, stop_price), 'trail_stop'
        if h >= limit_up * 0.999:
            return limit_up, 'limit_up'
        return c, 'close'
    
    if h >= limit_up * 0.999:
        return limit_up, 'limit_up'
    return c, 'close'


# ============================================================
# 手续费计算
# ============================================================
def fee(buy, sell, pc=CAPITAL):
    sh = int(pc / buy / 100) * 100
    if sh == 0: sh = 100
    c = sh * buy; bf = max(c * CR, CM) + c * TF; tb = c + bf
    r = sh * sell; sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100


# ============================================================
# 回测主函数
# ============================================================
def backtest_5m(samples, all_dates, daily_meta, X, y, trigger_pct, trail_pct, use_consec_loss=True):
    ridge_daily = []
    ridge_picks = []
    stats = defaultdict(int)
    fallback_count = 0  # 回退到日线的次数
    consec_loss = 0
    
    for d1_date in all_dates:
        idxs = daily_meta[d1_date]
        first_i = idxs[0]
        
        # Walk-Forward 选股
        if first_i < 100:
            best = samples[idxs[0]]
        else:
            hist = [j for j in range(first_i)]
            Xh = X[hist]; yh = y[hist]
            mean = Xh.mean(axis=0); std = Xh.std(axis=0) + 1e-8
            Xn = (Xh - mean) / std
            d = Xn.shape[1]
            try:
                w = solve(Xn.T @ Xn + np.eye(d) * 2.0, Xn.T @ yh)
            except:
                w = np.zeros(d)
            Xt = np.array([(X[i] - mean) / std for i in idxs])
            preds = Xt @ w
            best = samples[idxs[int(np.argmax(preds))]]
        
        bp = best[3]; o = best[6]; h = best[7]; l = best[8]; c = best[4]
        code = best[1]; name = best[5]
        
        # 连续亏损管理
        actual_capital = CAPITAL
        if use_consec_loss:
            if consec_loss >= 3:
                ridge_daily.append(0.0)
                ridge_picks.append(best)
                stats['skip'] += 1
                consec_loss = 0
                continue
            elif consec_loss >= 2:
                actual_capital = CAPITAL * 0.5
                stats['half'] += 1
        
        # 尝试5M数据卖出
        bars_5m = load_5m_bars(code, d1_date)
        if bars_5m and len(bars_5m) >= 10:
            sp, mode = sell_intraday_5m(bars_5m, bp, trigger_pct, trail_pct)
        else:
            # 回退到日线模拟
            sp, mode = sell_intraday_daily(bp, o, h, l, c, trigger_pct, trail_pct)
            fallback_count += 1
        
        ret = fee(bp, sp, actual_capital)
        ridge_daily.append(ret)
        ridge_picks.append(best)
        stats[mode] += 1
        
        if ret < -0.05:
            consec_loss += 1
        elif ret > 0.05:
            consec_loss = 0
    
    if fallback_count > 0:
        print(f"  [回退日线: {fallback_count}天]")
    return ridge_daily, ridge_picks, stats


# ============================================================
# 对比回测
# ============================================================
print(f"\n{'='*90}")
print(f"  311策略 5分钟数据回测 — 精确日内卖出")
print(f"{'='*90}")
print(f"特征: {' + '.join(FEATURES)}")
print(f"样本: {n}笔, {len(all_dates)}天")

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

# 跑5个策略对比
strategies = [
    ('收盘卖', 999, 0, False, None),
    ('止损-6%', 999, 0, True, None),
    ('止损+涨停+移动止盈(+3%/-2%)_5M', 1.03, 0.02, True, '5M'),
    ('止损+涨停+移动止盈(+3%/-1%)_5M', 1.03, 0.01, True, '5M'),
    ('止损+涨停+移动止盈(+3%/-1%)_日线', 1.03, 0.01, True, 'daily'),
]

all_results = {}
all_stats = {}

# 收盘卖(不需要5M)
rd_close, _, _ = backtest_5m(samples, all_dates, daily_meta, X, y, 999, 0, False)
all_results['收盘卖'] = rd_close

# 止损-6%
rd_stop, _, st_stop = backtest_5m(samples, all_dates, daily_meta, X, y, 999, 0, True)
all_results['止损-6%'] = rd_stop
all_stats['止损-6%'] = st_stop

# 移动止盈 5M版本
for label, trg, trl, cl in [
    ('止损+涨停+移动止盈(+3%/-2%)_5M', 1.03, 0.02, True),
    ('止损+涨停+移动止盈(+3%/-1%)_5M', 1.03, 0.01, True),
]:
    print(f"\n--- {label} ---")
    rets, _, st = backtest_5m(samples, all_dates, daily_meta, X, y, trg, trl, cl)
    all_results[label] = rets
    all_stats[label] = st

# 日线版本对比(+3%/-1%)
# 需要用sell_intraday_daily而非5M
def backtest_daily_only(samples, all_dates, daily_meta, X, y, trigger_pct, trail_pct):
    ridge_daily = []; stats = defaultdict(int); consec_loss = 0
    for d1_date in all_dates:
        idxs = daily_meta[d1_date]; first_i = idxs[0]
        if first_i < 100:
            best = samples[idxs[0]]
        else:
            hist = [j for j in range(first_i)]
            Xh = X[hist]; yh = y[hist]
            mean = Xh.mean(axis=0); std = Xh.std(axis=0) + 1e-8
            Xn = (Xh - mean) / std
            try: w = solve(Xn.T @ Xn + np.eye(6) * 2.0, Xn.T @ yh)
            except: w = np.zeros(6)
            Xt = np.array([(X[i] - mean) / std for i in idxs])
            preds = Xt @ w; best = samples[idxs[int(np.argmax(preds))]]
        bp=best[3]; o=best[6]; h=best[7]; l=best[8]; c=best[4]
        actual_capital = CAPITAL
        if consec_loss >= 3:
            ridge_daily.append(0.0); stats['skip'] += 1; consec_loss = 0; continue
        elif consec_loss >= 2:
            actual_capital = CAPITAL * 0.5; stats['half'] += 1
        sp, mode = sell_intraday_daily(bp, o, h, l, c, trigger_pct, trail_pct)
        ret = fee(bp, sp, actual_capital)
        ridge_daily.append(ret); stats[mode] += 1
        if ret < -0.05: consec_loss += 1
        elif ret > 0.05: consec_loss = 0
    return ridge_daily, stats

rd_daily, st_daily = backtest_daily_only(samples, all_dates, daily_meta, X, y, 1.03, 0.01)
all_results['止损+涨停+移动止盈(+3%/-1%)_日线'] = rd_daily
all_stats['止损+涨停+移动止盈(+3%/-1%)_日线'] = st_daily

# 汇总
print(f"\n{'='*90}")
print(f"  策略对比汇总")
print(f"{'='*90}")
print(f"\n{'策略':<40} {'净值':>8} {'收益':>10} {'胜率':>7} {'回撤':>7}")
print(f"{'-'*75}")

labels_order = ['收盘卖', '止损-6%',
                '止损+涨停+移动止盈(+3%/-2%)_5M',
                '止损+涨停+移动止盈(+3%/-1%)_5M',
                '止损+涨停+移动止盈(+3%/-1%)_日线']

for label in labels_order:
    rets = all_results[label]
    c, tr, wr, dd = calc_metrics(rets)
    print(f"{label:<40} {c:>8.4f} {tr:>+9.1f}% {wr:>6.1f}% {dd:>6.1f}%")
    if label in all_stats:
        st = all_stats[label]
        mods = ', '.join(f'{k}:{v}' for k, v in sorted(st.items()))
        print(f"  {'':>38}  卖出: {mods}")


# ============================================================
# 月度/年度明细 (5M +3%/-1%)
# ============================================================
def print_monthly_annual(rets, label):
    print(f"\n{'='*90}")
    print(f'  {label} — 月度/年度明细')
    print(f"{'='*90}")
    print(f"{'月份':<8} {'天':>4} {'收益':>10} {'胜率':>7}  {'净值':>10}")
    print(f"{'-'*50}")
    
    m_rets = defaultdict(list)
    for mi, d in enumerate(all_dates):
        m_rets[d[:6]].append(rets[mi])
    
    cum = 1.0
    for m in sorted(m_rets.keys()):
        mr = 1.0
        for r in m_rets[m]:
            if r != 0: mr *= (1 + r / 100)
        cum *= mr
        days_with_trades = sum(1 for r in m_rets[m] if r != 0)
        wr = sum(1 for r in m_rets[m] if r > 0) / max(days_with_trades, 1) * 100
        print(f'{m:<8} {days_with_trades:>4} {(mr-1)*100:>+9.2f}% {wr:>6.0f}%  {cum:>10.4f}')
    
    print(f'{"合计":<8} {len(rets):>4} {(cum-1)*100:>+9.1f}%')
    
    # 年度
    print(f"\n{'年份':<8} {'收益':>12}")
    y_rets = defaultdict(list)
    for mi, d in enumerate(all_dates):
        y_rets[d[:4]].append(rets[mi])
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
    print(f'\n样本外(>={cutoff}) 累计: {(ot-1)*100:+.2f}%')


# 5M +3%/-1%
print_monthly_annual(all_results['止损+涨停+移动止盈(+3%/-1%)_5M'],
                     '5分钟数据 +3%/-1%')

# 日线 +3%/-1% (对比)
print_monthly_annual(all_results['止损+涨停+移动止盈(+3%/-1%)_日线'],
                     '日线数据 +3%/-1%')


# ============================================================
# 5M网格扫描 (trigger × trail)
# ============================================================
print(f"\n{'='*90}")
print(f'  5分钟数据 移动止盈参数网格扫描')
print(f"{'='*90}")

triggers = [1.02, 1.025, 1.03, 1.035, 1.04, 1.05]
trails = [0.005, 0.008, 0.01, 0.012, 0.015, 0.02, 0.025, 0.03]

print(f"\n{'触发':>6} {'回撤':>6} {'净值':>8} {'收益':>10} {'胜率':>6} {'回撤':>6} {'涨停':>5} {'移止':>5} {'低止':>5} {'开止':>5} {'半仓':>5} {'跳过':>5}")
print(f"{'-'*90}")

grid_5m = []
for trigger in triggers:
    for trail in trails:
        rets, _, st = backtest_5m(samples, all_dates, daily_meta, X, y, trigger, trail, True)
        cum = 1.0; peak = 1.0; max_dd = 0.0
        for r in rets:
            if r == 0: continue
            cum *= (1 + r / 100)
            if cum > peak: peak = cum
            dd = (cum - peak) / peak * 100
            if dd < max_dd: max_dd = dd
        wr = sum(1 for r in rets if r > 0) / max(len(rets), 1) * 100
        grid_5m.append((trigger, trail, cum, (cum-1)*100, wr, max_dd, st))
        
        lu = st.get('limit_up', 0); trl = st.get('trail_stop', 0)
        lo = st.get('low_stop', 0); op = st.get('open_stop', 0)
        hf = st.get('half', 0); sk = st.get('skip', 0)
        print(f'{trigger*100-100:>+5.1f}% {trail*100:>5.1f}% {cum:>8.4f} {(cum-1)*100:>+9.1f}% {wr:>5.1f}% {max_dd:>5.1f}% {lu:>5} {trl:>5} {lo:>5} {op:>5} {hf:>5} {sk:>5}')

# Top 10
grid_5m.sort(key=lambda x: -x[2])
print(f"\n{'='*60}")
print(f'  Top 10 参数组合 (5M数据)')
print(f"{'='*60}")
print(f"{'排名':<5} {'触发':<8} {'回撤':<8} {'净值':>10} {'收益':>12} {'胜率':>6} {'回撤':>6}")
print(f"{'-'*60}")
for i, (trg, trl, cum, ret, wr, dd, st) in enumerate(grid_5m[:10]):
    print(f"{i+1:<5} +{(trg-1)*100:.1f}%    -{trl*100:.1f}%     {cum:>8.4f} {ret:>+11.1f}% {wr:>5.1f}% {dd:>5.1f}%")
    mods = ', '.join(f'{k}:{v}' for k, v in sorted(st.items()))
    print(f"      卖出: {mods}")

print(f"\n完成!")
