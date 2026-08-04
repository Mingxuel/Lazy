#!/usr/bin/env python3
"""
策略311 全量策略对比
- 统计分析(全量606笔)
- 规则策略回测(全量256天)
- MLP训练+回测(70/30 split)
"""
import os, random
import numpy as np
from collections import defaultdict

random.seed(42); np.random.seed(42)

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
FIVEM_DIR = os.path.join(BASE, "5M")
KLINE_DIR = os.path.join(BASE, "1D")

CR = 0.00025; CM = 5.0; SD = 0.0005; TF = 0.00001; CAPITAL = 1_000_000

def load_td():
    ds = []
    with open(os.path.join(BASE, "TRADING_DATES")) as f:
        for l in f:
            l = l.strip()
            if l: ds.append(l)
    return sorted(ds)

def load_1d(code, dt):
    fp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fp): return None
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l: continue
            if l.startswith(dt):
                p = l.split('|')
                if len(p) >= 5: return float(p[4])

def load_5m(code, dt):
    fp = os.path.join(FIVEM_DIR, code)
    if not os.path.exists(fp): return None
    df = f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}"
    bars = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) < 6: continue
            if p[0].startswith(df):
                bars.append((p[0], float(p[4]), float(p[2]), float(p[3]), float(p[1]), float(p[5])))
    return bars if bars else None

def load_sigs():
    sd = {}
    for fn in sorted(os.listdir(SIGNAL_DIR)):
        fp = os.path.join(SIGNAL_DIR, fn)
        if os.path.getsize(fp) <= 3: continue
        with open(fp, encoding='utf-8') as f:
            ls = [l.strip() for l in f if l.strip()]
        if not ls: continue
        es = []
        for l in ls:
            p = l.split('|')
            if len(p) < 8: continue
            es.append((p[0], float(p[7])))
        if es: sd[fn] = es
    return sd

def fee(buy, sell, pc):
    if buy == 0 or sell == 0: return 0.0
    sh = int(pc / buy / 100) * 100
    if sh == 0: sh = 100
    c = sh * buy
    bf = max(c * CR, CM) + c * TF
    tb = c + bf
    r = sh * sell
    sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100

def backtest(all_data, strategies, test_idx=None):
    """回测策略, 返回results dict"""
    by_d1 = defaultdict(list)
    n_tot = len(all_data)
    for i in (test_idx if test_idx else range(n_tot)):
        code, d1, d2c, bars = all_data[i]
        by_d1[d1].append((code, d2c, bars))
    
    results = {s: [] for s in strategies}
    for d1 in sorted(by_d1.keys()):
        trs = by_d1[d1]
        pc = CAPITAL / len(trs)
        dr = {s: [] for s in strategies}
        for code, d2c, bars in trs:
            for sn, sf in strategies.items():
                try:
                    sp = sf(bars, d2c)
                    dr[sn].append(fee(d2c, sp, pc))
                except:
                    dr[sn].append(0.0)
        for sn in strategies:
            rts = dr[sn]
            if rts:
                results[sn].append({'date': d1, 'ret': round(sum(rts)/len(rts), 4), 'cnt': len(rts)})
    return results

def compute_metrics(results):
    ranks = []
    for sn, data in results.items():
        if not data: continue
        cum = 1.0; peak = 1.0; max_dd = 0.0
        rets = [r['ret'] for r in data]
        for r in rets:
            cum *= (1 + r/100)
            if cum > peak: peak = cum
            dd = (cum - peak)/peak*100
            if dd < max_dd: max_dd = dd
        wr = sum(1 for r in rets if r>0)/len(rets)*100
        dly = np.array(rets)
        sh = np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
        total = (cum-1)*100
        ranks.append((cum, sn, total, wr, max_dd, sh, len(data)))
    ranks.sort(key=lambda x: x[0], reverse=True)
    return ranks

def print_table(ranks, title="策略对比"):
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"{'='*100}")
    print(f"  {'策略':<28} {'净值':>8} {'总收益%':>10} {'胜率%':>7} {'回撤%':>8} {'夏普':>7} {'天':>5}")
    print(f"  {'-'*80}")
    for cum, sn, tr, wr, dd, sh, td in ranks:
        print(f"  {sn:<28} {cum:>8.4f} {tr:>10.2f} {wr:>7.1f} {dd:>8.2f} {sh:>7.2f} {td:>5}")

# ============================================================
# 规则策略
# ============================================================
def s_close(bars, bp): return bars[-1][1]

def s_trail(pct):
    def f(bars, bp):
        peak = bars[0][1]
        for b in bars:
            if b[1] > peak: peak = b[1]
            elif (peak-b[1])/peak*100 >= pct: return b[1]
        return bars[-1][1]
    return f

def s_atr(bars, bp):
    """自适应ATR止损"""
    if len(bars) < 22: return bars[-1][1]
    c = np.array([b[1] for b in bars]); h = np.array([b[2] for b in bars]); l = np.array([b[3] for b in bars])
    tr = np.max(np.vstack([h[1:]-l[1:], np.abs(h[1:]-c[:-1]), np.abs(l[1:]-c[:-1])]), axis=0)
    atr = np.mean(tr[-20:]) if len(tr) >= 20 else np.mean(tr)
    stop_pct = max(atr / c[-1] * 100 * 2.0, 1.0)
    peak = bars[0][1]
    for b in bars:
        if b[1] > peak: peak = b[1]
        elif (peak-b[1])/peak*100 >= stop_pct: return b[1]
    return bars[-1][1]

def s_gap_aware(bars, bp):
    gap = (bars[0][1] - bp)/bp*100
    if gap > 2: return bars[0][1]  # 高开即卖
    if gap < -2:  # 低开等10:30
        for b in bars:
            if '10:30' in b[0]: return b[1]
        return bars[-1][1]
    # 平开: 新高回落1%
    return s_trail(1.0)(bars, bp)

def s_near_limit(bars, bp):
    for b in bars:
        if b[1] >= bp*1.09: return b[1]
    return bars[-1][1]

def s_1130(bars, bp):
    for b in bars:
        if '11:30' in b[0]: return b[1]
    return bars[-1][1]

def s_1430(bars, bp):
    for b in bars:
        if '14:30' in b[0]: return b[1]
    return bars[-1][1]

def s_morning_trail(bars, bp):
    """上午峰后下午紧追: 上午最高后,下午用1%追踪"""
    am = [b for b in bars if int(b[0][11:13]) <= 11]
    am_peak = max(b[2] for b in am) if am else bars[0][2]
    peak = am_peak
    for b in bars:
        if int(b[0][11:13]) >= 13:
            if b[1] > peak: peak = b[1]
            elif (peak-b[1])/peak*100 >= 1.0: return b[1]
    return bars[-1][1]

def s_vol_climax(bars, bp):
    """成交量尖峰卖出"""
    if len(bars) < 12: return bars[-1][1]
    v = np.array([b[5] for b in bars])
    vm5 = np.convolve(v, np.ones(5)/5, mode='same')
    for i in range(10, len(bars)):
        if v[i] > 3*vm5[i]: return bars[i][1]
    return bars[-1][1]

def s_am_strong(bars, bp):
    """上午强势则卖上午高,否则下午14:30"""
    am = [b for b in bars if int(b[0][11:13]) <= 11]
    am_ret = (am[-1][1] - bars[0][1])/bars[0][1]*100 if am else 0
    if am_ret > 1.5:  # 上午强势
        return max(b[2] for b in am)  # 卖上午最高
    return s_1430(bars, bp)

def s_best_fixed(bars, bp):
    """尾盘最佳固定时间: 14:50(比14:30好)"""
    for b in bars:
        if '14:50' in b[0]: return b[1]
    return bars[-1][1]

# ============================================================
# ML特征+模型
# ============================================================
def extract_features(bars, bp):
    n = len(bars)
    c = np.array([b[1] for b in bars], dtype=np.float64)
    h = np.array([b[2] for b in bars], dtype=np.float64)
    lo = np.array([b[3] for b in bars], dtype=np.float64)
    o = np.array([b[4] for b in bars], dtype=np.float64)
    v = np.array([b[5] for b in bars], dtype=np.float64)
    ts = [b[0] for b in bars]
    
    cr = c / bp; br = (c-o)/o*100; ba = (h-lo)/o*100
    cumr = (c - c[0])/c[0]*100
    vm5 = np.convolve(v, np.ones(5)/5, mode='same'); vr = v/(vm5+1e-10)
    dh = np.maximum.accumulate(h); dl = np.minimum.accumulate(lo)
    dfh = (dh-c)/dh*100; dfl = (c-dl)/dl*100
    k5 = min(5,n); k10 = min(10,n)
    m5 = np.convolve(c, np.ones(k5)/k5, mode='same')
    m10 = np.convolve(c, np.ones(k10)/k10, mode='same')
    mr5 = c/(m5+1e-10); mr10 = c/(m10+1e-10)
    ti = np.arange(n)/max(n-1,1)
    hr = np.array([int(t[11:13]) for t in ts])
    is_am = (hr<=11).astype(float); is_pm = (hr>=13).astype(float)
    # 累计成交量VWAP离差
    cv = np.cumsum(v); cvp = np.cumsum(v*c)
    vwap = cvp/(cv+1e-10); vw = (c-vwap)/vwap*100
    mom1 = np.zeros(n); mom1[1:] = (c[1:]-c[:-1])/(c[:-1]+1e-10)*100
    mom3 = np.zeros(n)
    if n>=4: mom3[3:] = (c[3:]-c[:-3])/(c[:-3]+1e-10)*100
    
    X = np.column_stack([cr, br, ba, vr, cumr, dfh, dfl, mr5, mr10,
                         ti, is_am, is_pm, mom1, mom3, vw,
                         (h-c)/c*100, (c-lo)/lo*100])
    y = np.zeros(n)
    for i in range(n):
        if i < n-1: y[i] = (np.max(c[i+1:])-c[i])/c[i]*100
    return X, y

class MLP:
    def __init__(self, sizes, lr=0.001, l2=1e-5):
        self.sizes = sizes; self.lr = lr; self.l2 = l2
        self.W = []; self.B = []
        for i in range(len(sizes)-1):
            f = sizes[i]
            self.W.append(np.random.randn(f, sizes[i+1])*np.sqrt(2.0/f))
            self.B.append(np.zeros(sizes[i+1]))
    def _r(self, x): return np.maximum(0, x)
    def _dr(self, x): return (x>0).astype(float)
    def predict(self, X):
        a = X
        for w,b in zip(self.W[:-1], self.B[:-1]): a = self._r(a@w+b)
        return (a@self.W[-1]+self.B[-1]).flatten()
    def fit(self, X, y, Xv, yv, ep=200, bs=128, p=25):
        bl = float('inf'); bw = None; bb = None; ni = 0
        for e in range(ep):
            idx = np.random.permutation(X.shape[0])
            for s in range(0, X.shape[0], bs):
                end = min(s+bs, X.shape[0]); bi = idx[s:end]
                Xb = X[bi]; yb = y[bi]
                acts = [Xb]; pas = []
                for w,b in zip(self.W[:-1], self.B[:-1]):
                    z = acts[-1]@w+b; pas.append(z); acts.append(self._r(z))
                z = acts[-1]@self.W[-1]+self.B[-1]; pas.append(z); acts.append(z)
                err = (acts[-1].flatten()-yb)/len(bi); delta = err.reshape(-1,1)
                for l in range(len(self.W)-1,-1,-1):
                    if l<len(self.W)-1: delta = delta@self.W[l+1].T*self._dr(pas[l])
                    dw = acts[l].T@delta + self.l2*self.W[l]
                    db = np.sum(delta, axis=0)
                    self.W[l] -= self.lr*dw; self.B[l] -= self.lr*db
            vl = np.mean((self.predict(Xv)-yv)**2) if Xv is not None else 0
            if vl < bl: bl=vl; bw=[w.copy() for w in self.W]; bb=[b.copy() for b in self.B]; ni=0
            else: ni+=1
            if ni>=p: break
        if bw: self.W=bw; self.B=bb
        return bl

class Scaler:
    def fit(self, X): self.m=np.mean(X,axis=0); self.s=np.std(X,axis=0); self.s[self.s<1e-10]=1.0; return self
    def transform(self, X): return (X-self.m)/self.s

# ============================================================
# 主流程
# ============================================================
print("="*100)
print("  策略311 全量策略对比分析")
print("="*100)

print("\n[1] 加载数据...")
sigs = load_sigs(); tds = load_td(); di = {d:i for i,d in enumerate(tds)}
all_data = []
for d0 in sorted(sigs.keys()):
    es = sigs[d0]; d0i = di.get(d0)
    if d0i is None or d0i < 2: continue
    d1, d2 = tds[d0i-1], tds[d0i-2]
    for code, d1c in es:
        d2c = load_1d(code, d2)
        if d2c is None: continue
        bars = load_5m(code, d1)
        if bars is None or len(bars)<10: continue
        all_data.append((code, d1, d2c, bars))

n = len(all_data); order = sorted(range(n), key=lambda i: all_data[i][1])
all_data = [all_data[i] for i in order]
days = len(set(d[1] for d in all_data))
print(f"  全量: {n}笔交易, {days}个卖出日")

# ============================================================
# Part 1: 统计分析
# ============================================================
print("\n"+"="*100)
print("  PART 1: 日内模式统计分析")
print("="*100)

peak_bars = []; peak_hrs = defaultdict(int); am_peak = 0; pm_peak = 0
gaps = []; close_chg = []; amplitudes = []
morning_retention = []
daily_ret = []  # 全天收益率 (D-1 close - D-2 close) / D-2 close

for _, d1, d2c, bars in all_data:
    c = np.array([b[1] for b in bars])
    h = np.array([b[2] for b in bars])
    l = np.array([b[3] for b in bars])
    peak_idx = np.argmax(h)
    peak_bars.append(peak_idx)
    hr = int(bars[peak_idx][0][11:13])
    peak_hrs[hr] += 1
    if hr <= 11: am_peak += 1
    else: pm_peak += 1
    
    gaps.append((bars[0][1]-d2c)/d2c*100)
    close_chg.append((bars[-1][1]-bars[0][1])/bars[0][1]*100)
    amplitudes.append((np.max(h)-np.min(l))/bars[0][4]*100)
    
    am_b = [b for b in bars if int(b[0][11:13])<=11]
    am_m = max(b[2] for b in am_b) if am_b else h[0]
    morning_retention.append(am_m/np.max(h) if np.max(h)>0 else 1)
    daily_ret.append((bars[-1][1]-d2c)/d2c*100)

pb = np.array(peak_bars); g = np.array(gaps); da = np.array(daily_ret)
print(f"  峰值时间: 中位bar#{int(np.median(pb))} (9:{(int(np.median(pb))-1)*5+35:02d})")
print(f"  峰值分布: 上午{am_peak}({am_peak/n*100:.0f}%) vs 下午{pm_peak}({pm_peak/n*100:.0f}%)")
print(f"  峰值时段: ", end="")
for h in sorted(peak_hrs.keys()): print(f"{h}h:{peak_hrs[h]} ", end="")
print()
print(f"  跳空: 均值{g.mean():.2f}% 中位{np.median(g):.2f}% 高开>2%:{np.sum(g>2)/n*100:.0f}% 低开<-2%:{np.sum(g<-2)/n*100:.0f}%")
print(f"  开盘→收盘: 均值{np.mean(close_chg):.2f}% 中位{np.median(close_chg):.2f}%")
print(f"  日内振幅: 均值{np.mean(amplitudes):.2f}%")
print(f"  上午高/全天高: {np.mean(morning_retention):.3f}")
print(f"  全天收益(D-1): 均值{da.mean():.2f}% 胜率{np.sum(da>0)/n*100:.0f}%")

# 分时段统计
am_ret = []; pm_ret = []
for _, d1, d2c, bars in all_data:
    c = np.array([b[1] for b in bars])
    am_end = None
    for i, b in enumerate(bars):
        if '11:30' in b[0]:
            am_end = i; break
    if am_end:
        am_ret.append((c[am_end]-c[0])/c[0]*100)
        pm_ret.append((c[-1]-c[am_end])/c[am_end]*100)

print(f"  上午收益率: 均值{np.mean(am_ret):.2f}% 中位{np.median(am_ret):.2f}%")
print(f"  下午收益率: 均值{np.mean(pm_ret):.2f}% 中位{np.median(pm_ret):.2f}%")

# ============================================================
# Part 2: 规则策略 (全量回测)
# ============================================================
print("\n"+"="*100)
print("  PART 2: 规则策略 (全量回测, {n}笔/{days}天)".format(n=n, days=days))
print("="*100)

rule_strats = {
    "01_baseline_收盘卖": s_close,
    "02_新高回落1%": s_trail(1.0),
    "03_新高回落0.5%": s_trail(0.5),
    "04_新高回落1.5%": s_trail(1.5),
    "05_新高回落2%": s_trail(2.0),
    "06_自适应ATR止损": s_atr,
    "07_跳空感知(高开卖/低开等/平开追)": s_gap_aware,
    "08_接近涨停(9%+)卖": s_near_limit,
    "09_11:30固定卖": s_1130,
    "10_14:30固定卖": s_1430,
    "11_上午峰下午追": s_morning_trail,
    "12_放量尖峰卖": s_vol_climax,
    "13_上午强卖高否则1430": s_am_strong,
}

rule_results = backtest(all_data, rule_strats)
rule_ranks = compute_metrics(rule_results)
print_table(rule_ranks, "规则策略 全量对比")

# ============================================================
# Part 3: MLP (70/30时间切分)
# ============================================================
print("\n"+"="*100)
print("  PART 3: MLP神经网络")
print("="*100)

# 提取特征
all_X = []; all_y = []
for _, _, d2c, bars in all_data:
    X, y = extract_features(bars, d2c)
    if X is not None: all_X.append(X); all_y.append(y)

tr_end = int(n * 0.70)
Xt = np.vstack([all_X[i] for i in range(tr_end)])
yt = np.hstack([all_y[i] for i in range(tr_end)])
Xv = np.vstack([all_X[i] for i in range(tr_end, n)])
yv = np.hstack([all_y[i] for i in range(tr_end, n)])
n_feat = all_X[0].shape[1]
print(f"  特征: {n_feat}维, 训练{tr_end}笔/{Xt.shape[0]}bar, 测试{n-tr_end}笔")

sc = Scaler().fit(Xt)
Xts = sc.transform(Xt); Xvs = sc.transform(Xv)

# 训练
archs = [
    ([n_feat, 256, 128, 64, 1], 0.0005, "MLP_256-128-64"),
    ([n_feat, 512, 256, 128, 1], 0.0003, "MLP_512-256-128"),
    ([n_feat, 128, 64, 32, 1], 0.001, "MLP_128-64-32"),
    ([n_feat, 256, 128, 64, 32, 1], 0.0005, "MLP_256-128-64-32"),
]
best_m = None; best_vl = float('inf'); best_arch = ""
for arch, lr, name in archs:
    print(f"  训练 {name}...", end=" ")
    m = MLP(arch, lr=lr)
    vl = m.fit(Xts, yt, Xvs, yv, ep=200, p=20)
    print(f"val_MSE={vl:.4f}")
    if vl < best_vl: best_vl = vl; best_m = m; best_arch = name
print(f"  最佳: {best_arch}, val_MSE={best_vl:.4f}")

# ML策略
ml_strats = {
    "01_baseline_收盘卖": s_close,
    "02_新高回落1%": s_trail(1.0),
    "08_接近涨停卖": s_near_limit,
}
for th in [0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]:
    th_cap = th
    ml_strats[f"ML_{best_arch}_th={th:.2f}"] = lambda bars, bp, m=best_m, s=sc, t=th_cap: mlt_sell(bars, bp, m, s, t)

def mlt_sell(bars, bp, model, scaler, th):
    X, _ = extract_features(bars, bp)
    if X is None or len(X) < 6: return bars[-1][1]
    Xs = scaler.transform(X)
    preds = model.predict(Xs)
    for i in range(5, len(preds)):
        if preds[i] < th: return bars[i][1]
    return bars[-1][1]

# 测试集回测
ml_results = backtest(all_data, ml_strats, test_idx=list(range(tr_end, n)))
ml_ranks = compute_metrics(ml_results)
print_table(ml_ranks, f"MLP策略 测试集回测({n-tr_end}笔/{len(set(d[1] for i,d in enumerate(all_data) if i>=tr_end))}天)")

# 月度明细(前8)
print("\n"+"="*100)
print("  前8策略 月度收益")
print("="*100)
top8 = [x[1] for x in ml_ranks[:8]]
months = sorted(set(r['date'][:6] for sn,data in ml_results.items() for r in data))
hdr = f"  {'月':<8}"
for sn in top8: hdr += f" {sn[:16]:>16}"
print(hdr)
print("  "+"-"*(8+17*len(top8)))
for mo in months:
    row = f"  {mo:<8}"
    for sn in top8:
        ms = sum(r['ret'] for r in ml_results[sn] if r['date'].startswith(mo))
        row += f" {ms:>16.2f}%"
    print(row)

# 全部策略(规则+ML)合并排名
print("\n"+"="*100)
print("  全局排名 (规则全量baseline + ML测试集)")
print("="*100)
print(f"  {'策略':<35} {'净值':>8} {'总收益%':>10} {'胜率%':>7} {'回撤%':>8} {'夏普':>7}")

all_ranks = []
# Rule strategies on full data
for sn in rule_strats:
    if sn in rule_results and rule_results[sn]:
        cum = 1.0; peak = 1.0; max_dd = 0.0
        rets = [r['ret'] for r in rule_results[sn]]
        for r in rets:
            cum *= (1+r/100)
            if cum > peak: peak = cum
            dd = (cum-peak)/peak*100
            if dd < max_dd: max_dd = dd
        wr = sum(1 for r in rets if r>0)/len(rets)*100
        dly = np.array(rets)
        sh = np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
        all_ranks.append((cum, sn, (cum-1)*100, wr, max_dd, sh, '全量'))

# ML strategies on test set
for sn in ml_strats:
    if sn.startswith("ML_") and sn in ml_results and ml_results[sn]:
        cum = 1.0; peak = 1.0; max_dd = 0.0
        rets = [r['ret'] for r in ml_results[sn]]
        for r in rets:
            cum *= (1+r/100)
            if cum > peak: peak = cum
            dd = (cum-peak)/peak*100
            if dd < max_dd: max_dd = dd
        wr = sum(1 for r in rets if r>0)/len(rets)*100
        dly = np.array(rets)
        sh = np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
        all_ranks.append((cum, sn, (cum-1)*100, wr, max_dd, sh, f'测试{len(rets)}天'))

all_ranks.sort(key=lambda x: x[0], reverse=True)
for cum, sn, tr, wr, dd, sh, scope in all_ranks:
    print(f"  {sn:<35} {cum:>8.4f} {tr:>10.2f} {wr:>7.1f} {dd:>8.2f} {sh:>7.2f}  [{scope}]")

print("\n"+"="*100)
print("  分析完成!")
print("="*100)
