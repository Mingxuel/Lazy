#!/usr/bin/env python3
"""
311策略回测 v2 — 日线级别卖出规则修正:
  关键修正: 移动止盈优先级 > 涨停 (因为+3%总是先于涨停触发)
  卖出优先级: 止损-6% > 移动止盈 > 涨停 > 收盘
  连续亏损管理: 2连亏半仓, 3连亏跳过
"""
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

def compute_ma_golden(rows, d2i):
    """判断D-2日是否MA5上穿MA10"""
    if d2i < 10: return 0
    closes = np.array([r[4] for r in rows[:d2i+1]])
    ma5_now = np.mean(closes[-5:])
    ma10_now = np.mean(closes[-10:])
    ma5_prev = np.mean(closes[-6:-1])
    ma10_prev = np.mean(closes[-11:-1])
    if ma5_prev <= ma10_prev and ma5_now > ma10_now:
        return 1
    return 0

# 6特征版本
FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

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
            f['ma5_support'],f['ma5_bounce']=check_ma5(code,d2,r1[6])
            samples.append((f,code,d1,bp,sp_close,name,d1_open,d1_high,d1_low))

samples.sort(key=lambda x:x[2])
n=len(samples)
print(f"样本: {n}笔")

# 日线买卖
daily_meta=defaultdict(list)
for i,s in enumerate(samples): daily_meta[s[2]].append(i)
all_dates=sorted(daily_meta.keys())

# Walk-Forward 岭回归 (6特征)
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples])
y=np.array([(s[4]-s[3])/s[3]*100 for s in samples])  # 收盘收益率

def fee(buy,sell,pc=CAPITAL):
    sh=int(pc/buy/100)*100
    if sh==0: sh=100
    c=sh*buy; bf=max(c*CR,CM)+c*TF; tb=c+bf
    r=sh*sell; sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

# ============================================================
# 卖出规则 (日线级别, 修正版)
# 关键: 移动止盈优先级 > 涨停, 因为+3%总是先于涨停
# ============================================================
def sell_daily(bp, o, h, l, c, trigger_pct=1.03, trail_pct=0.01):
    """
    日线卖出模拟:
      价格路径不可知, 保守假设: 先到最高价, 可能触发移动止盈回撤, 再看涨停
    
    返回: (sell_price, mode)
    mode: 'open_stop','low_stop','trail_stop','limit_up','close'
    """
    limit_up = round(bp * 1.10, 2)
    stop_price = bp * 0.94
    
    # 1. 开盘止损
    if o <= stop_price:
        return o, 'open_stop'
    
    # 2. 盘中最低止损
    if l <= stop_price:
        return stop_price, 'low_stop'
    
    # 3. 移动止盈 (优先于涨停!)
    #    价格必须先经过 trigger 才能到涨停, 如果在到涨停前回撤>trail就触发
    if h >= bp * trigger_pct:
        # 从日内最高价计算回撤退出卖价
        trail_sell = h * (1 - trail_pct)
        
        if l <= trail_sell:
            # 盘中触发了回撤 → 移动止盈
            # 但不能低于 stop_price (止损已经覆盖)
            actual_sell = max(trail_sell, stop_price)
            return actual_sell, 'trail_stop'
        
        # 没触发回撤, 说明一路涨上去没怎么回调
        if h >= limit_up * 0.999:
            return limit_up, 'limit_up'
        else:
            # 涨了但没到涨停, 也没触发回撤 → 收盘
            return c, 'close'
    
    # 4. 没触发移动止盈但到涨停 (极少见, 涨停<3%涨幅的股票)
    if h >= limit_up * 0.999:
        return limit_up, 'limit_up'
    
    # 5. 收盘
    return c, 'close'


# ============================================================
# 回测函数
# ============================================================
def backtest(samples, all_dates, daily_meta, X, y, trigger_pct, trail_pct, use_consec_loss=True):
    """
    回测指定参数组合
    """
    ridge_daily = []
    ridge_picks = []
    stats = defaultdict(int)
    
    consec_loss = 0  # 连续亏损计数
    
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
        
        # 连续亏损管理
        actual_capital = CAPITAL
        if use_consec_loss:
            if consec_loss >= 3:
                # 跳过当天, 重置计数器(休息一天)
                ridge_daily.append(0.0)
                ridge_picks.append(best)
                stats['skip'] += 1
                consec_loss = 0
                continue
            elif consec_loss >= 2:
                actual_capital = CAPITAL * 0.5
                stats['half'] += 1
        
        # 卖出
        sp, mode = sell_daily(bp, o, h, l, c, trigger_pct, trail_pct)
        
        # 止损价不低于买入价的94%保护
        if mode == 'trail_stop':
            sp = max(sp, bp * 0.94)
        
        ret = fee(bp, sp, actual_capital)
        ridge_daily.append(ret)
        ridge_picks.append(best)
        stats[mode] += 1
        
        # 更新连续亏损 (盈利才重置, 微利/微亏不改变计数)
        if ret < -0.05:
            consec_loss += 1
        elif ret > 0.05:
            consec_loss = 0
        # 接近0不改变计数
    
    return ridge_daily, ridge_picks, stats


# ============================================================
# 基础对比: 收盘卖 vs 卖出规则
# ============================================================
def run_comparison():
    print(f"\n{'='*90}")
    print(f"  311策略回测 v2: 日线卖出规则修正 (移动止盈 > 涨停)")
    print(f"{'='*90}")
    print(f"特征: {' + '.join(FEATURES)}")
    print(f"样本: {n}笔, {len(all_dates)}天")
    
    # 1. 收盘卖 (基准)
    rd_close, _, st_close = backtest(samples, all_dates, daily_meta, X, y, 999, 0, False)
    
    # 2. 止损-6% only
    rd_stop, _, st_stop = backtest(samples, all_dates, daily_meta, X, y, 999, 0, True)
    
    # 3. 止损+涨停 (无移动止盈)
    # 用 trigger=1.10 即只有涨停触发
    rd_lu, _, st_lu = backtest(samples, all_dates, daily_meta, X, y, 1.099, 0.001, True)
    
    # 4. 完整规则: +3%触发/-2%回撤 (旧版)
    rd_tr2, _, st_tr2 = backtest(samples, all_dates, daily_meta, X, y, 1.03, 0.02, True)
    
    # 5. 完整规则: +3%触发/-1%回撤 (新版, 最优)
    rd_tr1, _, st_tr1 = backtest(samples, all_dates, daily_meta, X, y, 1.03, 0.01, True)
    
    def calc_metrics(rets):
        cum = 1.0; peak = 1.0; max_dd = 0.0
        for r in rets:
            if r == 0: continue  # skip days
            cum *= (1 + r / 100)
            if cum > peak: peak = cum
            dd = (cum - peak) / peak * 100
            if dd < max_dd: max_dd = dd
        wr = sum(1 for r in rets if r > 0) / len(rets) * 100 if rets else 0
        return cum, (cum - 1) * 100, wr, max_dd
    
    labels = ['收盘卖', '止损-6%', '止损+涨停', '止损+涨停+移动止盈(+3%/-2%)', '止损+涨停+移动止盈(+3%/-1%)']
    results = {
        '收盘卖': rd_close,
        '止损-6%': rd_stop,
        '止损+涨停': rd_lu,
        '止损+涨停+移动止盈(+3%/-2%)': rd_tr2,
        '止损+涨停+移动止盈(+3%/-1%)': rd_tr1,
    }
    stats_all = {
        '止损-6%': st_stop,
        '止损+涨停': st_lu,
        '止损+涨停+移动止盈(+3%/-2%)': st_tr2,
        '止损+涨停+移动止盈(+3%/-1%)': st_tr1,
    }
    
    print(f"\n{'策略':<35} {'净值':>8} {'收益':>10} {'胜率':>7} {'回撤':>7}")
    print(f"{'-'*70}")
    for label in labels:
        rets = results[label]
        c, tr, wr, dd = calc_metrics(rets)
        print(f"{label:<35} {c:>8.4f} {tr:>+9.1f}% {wr:>6.1f}% {dd:>6.1f}%")
        if label in stats_all:
            st = stats_all[label]
            mods = ', '.join(f'{k}:{v}' for k, v in sorted(st.items()))
            print(f"  {'':>33}  卖出: {mods}")
    
    return rd_tr1, all_dates, results


rd_tr1, all_dates, all_results = run_comparison()


# ============================================================
# 月度/年度明细 (最优策略: +3%/-1%)
# ============================================================
def monthly_annual(results, label='止损+涨停+移动止盈(+3%/-1%)'):
    rets = results[label]
    
    print(f"\n{'='*90}")
    print(f'  月度盈亏明细 — {label}')
    print(f"{'='*90}")
    print(f"{'月份':<8} {'天':>4} {'收益':>10} {'胜率':>7}")
    print(f"{'-'*35}")
    
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
        print(f'{m:<8} {days_with_trades:>4} {(mr-1)*100:>+9.2f}% {wr:>6.0f}%  | 净值 {cum:.4f}')
    
    print(f"{'合计':<8} {len(rets):>4} {(cum-1)*100:>+9.1f}%")
    
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
    print(f"\n{'='*60}")
    print(f'  样本外(>=202604) 逐月')
    print(f"{'='*60}")
    cutoff = '202604'
    ot = 1.0
    for m in sorted(m_rets.keys()):
        if m < cutoff: continue
        mr = 1.0
        for r in m_rets[m]:
            if r != 0: mr *= (1 + r / 100)
        ot *= mr
        days = sum(1 for r in m_rets[m] if r != 0)
        print(f'{m:<8} {(mr-1)*100:>+9.2f}% ({days}天)')
    print(f'{"合计":<8} {(ot-1)*100:>+9.2f}%')


monthly_annual(all_results, '止损+涨停+移动止盈(+3%/-1%)')

print(f"\n{'='*90}")
print(f'  vs 移动止盈(+3%/-2%) 月度/年度对比')
print(f"{'='*90}")
monthly_annual(all_results, '止损+涨停+移动止盈(+3%/-2%)')


# ============================================================
# 网格扫描: trigger × trail
# ============================================================
print(f"\n{'='*90}")
print(f'  移动止盈参数网格扫描 (日线修正版)')
print(f"{'='*90}")

triggers = [1.02, 1.025, 1.03, 1.035, 1.04, 1.05]
trails = [0.005, 0.008, 0.01, 0.012, 0.015, 0.02, 0.025, 0.03]

print(f"\n{'触发':>6} {'回撤':>6} {'净值':>8} {'收益':>10} {'胜率':>6} {'回撤':>6} {'涨停':>5} {'移止':>5} {'低止':>5} {'开止':>5} {'半仓':>5} {'跳过':>5}")
print(f"{'-'*90}")

grid_results = []
for trigger in triggers:
    for trail in trails:
        rets, _, stats = backtest(samples, all_dates, daily_meta, X, y, trigger, trail, True)
        cum = 1.0; peak = 1.0; max_dd = 0.0
        for r in rets:
            if r == 0: continue
            cum *= (1 + r / 100)
            if cum > peak: peak = cum
            dd = (cum - peak) / peak * 100
            if dd < max_dd: max_dd = dd
        wr = sum(1 for r in rets if r > 0) / max(len(rets), 1) * 100
        grid_results.append((trigger, trail, cum, (cum-1)*100, wr, max_dd, stats))
        
        lu = stats.get('limit_up', 0)
        trl = stats.get('trail_stop', 0)
        lo = stats.get('low_stop', 0)
        op = stats.get('open_stop', 0)
        hf = stats.get('half', 0)
        sk = stats.get('skip', 0)
        close_count = stats.get('close', 0) + stats.get('limit_up', 0)  # approximate close
        print(f'{trigger*100-100:>+5.1f}% {trail*100:>5.1f}% {cum:>8.4f} {(cum-1)*100:>+9.1f}% {wr:>5.1f}% {max_dd:>5.1f}% {lu:>5} {trl:>5} {lo:>5} {op:>5} {hf:>5} {sk:>5}')

# Top 10
grid_results.sort(key=lambda x: -x[2])
print(f"\n{'='*60}")
print(f'  Top 10 参数组合(按净值)')
print(f"{'='*60}")
print(f"{'排名':<5} {'触发':<8} {'回撤':<8} {'净值':>10} {'收益':>12} {'胜率':>6} {'回撤':>6}")
print(f"{'-'*60}")
for i, (trg, trl, cum, ret, wr, dd, st) in enumerate(grid_results[:10]):
    print(f"{i+1:<5} +{(trg-1)*100:.1f}%    -{trl*100:.1f}%     {cum:>8.4f} {ret:>+11.1f}% {wr:>5.1f}% {dd:>5.1f}%")
    mods = ', '.join(f'{k}:{v}' for k, v in sorted(st.items()))
    print(f"      卖出: {mods}")

print(f"\n完成!")
