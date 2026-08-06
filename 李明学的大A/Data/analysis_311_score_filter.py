#!/usr/bin/env python3
"""
311回测 — 评分过滤: 最优股分数低于阈值则不买入
阈值: baseline(无过滤) / <0 / < -0.5 / < -1.0 / < -2.0 / < -3.0
"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
CR=0.00025; CM=5.0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

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

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds=sorted(tds); di={d:i for i,d in enumerate(tds)}

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
            r1=rows[d1i_k]; bp=r1[6]
            if bp<=0: continue
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
            samples.append((f,code,d1,bp,rows[d1i_k][4],name,rows[d1i_k][1],rows[d1i_k][2],rows[d1i_k][3]))

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

def run_backtest(score_threshold, label):
    """
    score_threshold: 最优股评分低于该值 → 跳过不买
    None = baseline 不过滤
    """
    trades = []
    consec = 0
    cum = 1.0; peak = 1.0; max_dd = 0.0
    skip_count = 0
    total_days = 0
    monthly = defaultdict(lambda: {'ret_sum': 0, 'w': 0, 'l': 0})

    for d1_date in all_dates:
        idxs = daily_meta[d1_date]; first_i = idxs[0]
        total_days += 1

        # WF选股 + 评分
        if first_i < 100:
            best = samples[idxs[0]]
            best_score = 0  # 前100天不过滤
        else:
            hist = [j for j in range(first_i)]
            Xh = X[hist]; yh = y[hist]
            mean = Xh.mean(axis=0); std = Xh.std(axis=0) + 1e-8
            Xn = (Xh - mean) / std; d = Xn.shape[1]
            try: w = solve(Xn.T @ Xn + np.eye(d) * 2.0, Xn.T @ yh)
            except: w = np.zeros(d)
            Xt = np.array([(X[i] - mean) / std for i in idxs])
            preds = Xt @ w
            best_i = int(np.argmax(preds))
            best_score = preds[best_i]
            best = samples[idxs[best_i]]

        # 评分过滤
        if score_threshold is not None and best_score < score_threshold:
            skip_count += 1
            # 重置连续亏损计数（避免连跳）
            continue

        code = best[1]; name = best[5]; bp = best[3]
        o = best[6]; h = best[7]; l = best[8]; c_d = best[4]

        # 连续亏损管理
        cap = CAPITAL
        if consec >= 3:
            consec = 0
            skip_count += 1
            continue
        elif consec >= 2:
            cap = CAPITAL * 0.5

        sp, mode = sell_daily(bp, o, h, l, c_d)
        ret, sh = fee(bp, sp, cap)
        cum *= (1 + ret/100)
        if cum > peak: peak = cum
        dd = (cum - peak)/peak*100
        if dd < max_dd: max_dd = dd

        # 月度统计
        m = d1_date[:6]
        monthly[m]['ret_sum'] += ret
        if ret > 0: monthly[m]['w'] += 1
        elif ret < 0: monthly[m]['l'] += 1

        if ret < -0.05: consec += 1
        else: consec = 0

    total_trade_days = total_days - skip_count
    win_count = sum(1 for t in trades if t['ret'] > 0)
    lose_count = sum(1 for t in trades if t['ret'] < 0)

    return {
        'label': label,
        'threshold': score_threshold,
        'net_value': cum,
        'total_return': (cum - 1) * 100,
        'max_dd': max_dd,
        'total_days': total_days,
        'trade_days': total_trade_days,
        'skip_days': skip_count,
        'monthly': dict(monthly),
    }

# ==================== 跑 ====================
thresholds = [
    (None, 'baseline 无过滤'),
    (0.0,  '分数<0 跳过'),
    (-0.5, '分数<-0.5 跳过'),
    (-1.0, '分数<-1.0 跳过'),
    (-2.0, '分数<-2.0 跳过'),
    (-3.0, '分数<-3.0 跳过'),
]

results = []
for th, label in thresholds:
    r = run_backtest(th, label)
    results.append(r)

# ==================== 输出 ====================
print(f"\n{'='*100}")
print(f'  311回测 — 评分过滤对比')
print(f'  止损-6% > 涨停 > 收盘卖出')
print(f"{'='*100}\n")

print(f"{'阈值':<20} {'净值':>8} {'总收益':>10} {'最大回撤':>8} {'交易日':>6} {'交易':>6} {'跳过':>6}")
print('-'*70)
for r in results:
    print(f"{r['label']:<20} {r['net_value']:>8.2f} {r['total_return']:>+9.1f}% {r['max_dd']:>+7.1f}% "
          f"{r['total_days']:>6} {r['trade_days']:>6} {r['skip_days']:>6}")

# 最优
best_r = max(results, key=lambda x: x['net_value'])
print(f"\n★ 最优: {best_r['label']}  净值 {best_r['net_value']:.2f}  跳过 {best_r['skip_days']} 天")

# 月度分解 (最优)
print(f"\n{'='*100}")
print(f'  最优策略月度盈亏: {best_r["label"]}')
print(f"{'='*100}\n")

monthly_data = best_r['monthly']
all_months = sorted(monthly_data.keys())
years = sorted(set(m[:4] for m in all_months))

# 找到每个月的交易天数
month_trade_days = defaultdict(int)
for s in samples:
    m = s[2][:6]
    month_trade_days[m] += 1

# 按行输出: 每年12个月并排
for yr in years:
    months = [m for m in all_months if m.startswith(yr)]
    if not months:
        continue
    yr_total = sum(monthly_data[m]['ret_sum'] for m in months)
    yr_w = sum(monthly_data[m]['w'] for m in months)
    yr_l = sum(monthly_data[m]['l'] for m in months)
    
    header = f"| {yr} |"
    vals = f"| {'收益':<10} |"
    for m in months:
        header += f" {m[4:]}月 |"
        d = monthly_data[m]
        vals += f" {d['ret_sum']:>+5.1f}% |"
    print(header)
    print(vals)
    wr = yr_w/(yr_w+yr_l)*100 if yr_w+yr_l>0 else 0
    print(f"  → 年度累计: {yr_total:+.1f}%  胜率: {yr_w}/{yr_w+yr_l} ({wr:.1f}%)")
    print()
