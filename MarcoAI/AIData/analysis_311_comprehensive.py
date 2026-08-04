#!/usr/bin/env python3
"""
策略311 全面卖点优化 - 统计+规则+ML全部对比
"""
import os, math, random
import numpy as np
from collections import defaultdict

random.seed(42); np.random.seed(42)

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
FIVEM_DIR = os.path.join(BASE, "5M")
KLINE_DIR = os.path.join(BASE, "1D")

CR = 0.00025; CM = 5.0; SD = 0.0005; TF = 0.00001
CAPITAL = 1_000_000

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

# ============================================================
# 数据加载
# ============================================================
print("=" * 80)
print("  策略311 全面卖点优化")
print("=" * 80)

print("\n加载数据...")
sigs = load_sigs()
tds = load_td()
di = {d: i for i, d in enumerate(tds)}

all_data = []  # [(code, d1_date, d2_close, bars)]
for d0 in sorted(sigs.keys()):
    es = sigs[d0]
    d0i = di.get(d0)
    if d0i is None or d0i < 2: continue
    d1 = tds[d0i - 1]
    d2 = tds[d0i - 2]
    for code, d1c in es:
        d2c = load_1d(code, d2)
        if d2c is None: continue
        bars = load_5m(code, d1)
        if bars is None or len(bars) < 10: continue
        all_data.append((code, d1, d2c, bars))

n = len(all_data)
print(f"样本: {n}笔, {len(set(d[1] for d in all_data))}个卖出日")
order = sorted(range(n), key=lambda i: all_data[i][1])
all_data = [all_data[i] for i in order]

# ============================================================
# Part 1: 统计分析
# ============================================================
print("\n" + "=" * 80)
print("  PART 1: 日内模式统计分析")
print("=" * 80)

peak_times = []
peak_sessions = {'morning': 0, 'afternoon': 0}
hourly_peaks = defaultdict(int)
open_gaps = []
close_vs_open = []
morning_high_retention = []  # 上午最高 vs 全天最高
intraday_range = []
vol_profile = np.zeros(48)

for code, d1, d2c, bars in all_data:
    closes = np.array([b[1] for b in bars])
    highs = np.array([b[2] for b in bars])
    volumes = np.array([b[5] for b in bars])
    
    # 峰值时间
    max_idx = np.argmax(highs)
    peak_times.append(max_idx)
    hour = int(bars[max_idx][0][11:13])
    hourly_peaks[hour] += 1
    if hour <= 11: peak_sessions['morning'] += 1
    else: peak_sessions['afternoon'] += 1
    
    # 跳空
    open_gap = (bars[0][1] - d2c) / d2c * 100
    open_gaps.append(open_gap)
    close_vs_open.append((bars[-1][1] - bars[0][1]) / bars[0][1] * 100)
    
    # 上午高点留存率
    am_bars = [b for b in bars if int(b[0][11:13]) <= 11]
    am_max = max(b[2] for b in am_bars) if am_bars else highs[0]
    day_max = np.max(highs)
    morning_high_retention.append(am_max / day_max if day_max > 0 else 1)
    
    # 日内振幅
    intraday_range.append((np.max(highs) - np.min([b[3] for b in bars])) / bars[0][4] * 100)
    
    # 成交量分布
    if len(volumes) >= 48:
        vol_profile[:48] += volumes[:48] / np.sum(volumes[:48])
    else:
        vp = np.zeros(len(volumes))
        vp[:] = volumes / np.sum(volumes)

peak_times = np.array(peak_times)
open_gaps = np.array(open_gaps)

pm = np.percentile(peak_times, [25, 50, 75])
print(f"峰值时间分布: 中位数bar#{int(pm[1])}, "
      f"上午{peak_sessions['morning']}({peak_sessions['morning']/n*100:.0f}%) "
      f"下午{peak_sessions['afternoon']}({peak_sessions['afternoon']/n*100:.0f}%)")
print(f"峰值时段: ", end="")
for h in sorted(hourly_peaks.keys()):
    print(f"{h}h:{hourly_peaks[h]} ", end="")
print()
print(f"跳空幅度: 均值{np.mean(open_gaps):.2f}%, 中位{np.median(open_gaps):.2f}%, "
      f"高开(>2%){np.sum(open_gaps>2)/n*100:.0f}%, 低开(<-2%){np.sum(open_gaps<-2)/n*100:.0f}%")
print(f"开盘→收盘: 均值{np.mean(close_vs_open):.2f}%, 中位{np.median(close_vs_open):.2f}%")
print(f"上午高/全天高: 均值{np.mean(morning_high_retention):.3f}")
print(f"日内振幅: 均值{np.mean(intraday_range):.2f}%")

# 分跳空方向统计
hi_gap = [d for d, g in zip(all_data, open_gaps) if g > 2]
lo_gap = [d for d, g in zip(all_data, open_gaps) if g < -2]
mid_gap = [d for d, g in zip(all_data, open_gaps) if -2 <= g <= 2]
print(f"\n跳空分组: 高开(>{len(hi_gap)}笔) / 平开({len(mid_gap)}笔) / 低开({len(lo_gap)}笔)")

# ============================================================
# Part 2: 高级规则策略
# ============================================================
print("\n" + "=" * 80)
print("  PART 2: 高级规则策略")
print("=" * 80)

def strat_close(bars, bp): return bars[-1][1]

def strat_trail_1(bars, bp):
    peak = bars[0][1]
    for b in bars:
        if b[1] > peak: peak = b[1]
        elif (peak - b[1]) / peak * 100 >= 1.0: return b[1]
    return bars[-1][1]

def strat_trail_atr(bars, bp):
    """自适应止损: ATR(20)的1.5倍"""
    if len(bars) < 22: return strat_close(bars, bp)
    closes = np.array([b[1] for b in bars])
    highs = np.array([b[2] for b in bars])
    lows = np.array([b[3] for b in bars])
    tr = np.maximum(highs[1:] - lows[1:], 
                    np.abs(highs[1:] - closes[:-1]),
                    np.abs(lows[1:] - closes[:-1]))
    atr = np.mean(tr[-20:]) if len(tr) >= 20 else np.mean(tr)
    stop_pct = max(atr / closes[-1] * 100 * 1.5, 0.5)
    peak = bars[0][1]
    for b in bars:
        if b[1] > peak: peak = b[1]
        elif (peak - b[1]) / peak * 100 >= stop_pct: return b[1]
    return bars[-1][1]

def strat_vol_climax(bars, bp):
    """放量滞涨: 成交量>3x5日均量 且 涨跌幅<0.5%"""
    if len(bars) < 30: return strat_close(bars, bp)
    vols = np.array([b[5] for b in bars])
    closes = np.array([b[1] for b in bars])
    ma5_vol = np.convolve(vols, np.ones(5)/5, mode='same')
    for i in range(10, len(bars)):
        bar_ret = abs(closes[i] - closes[i-1]) / closes[i-1] * 100
        if vols[i] > 3 * ma5_vol[i] and bar_ret < 0.5:
            return bars[i][1]
    return bars[-1][1]

def strat_gap_aware(bars, bp):
    """跳空策略: 高开>2%立即卖;低开<-2%等10:30;平开等新高回落1%"""
    gap = (bars[0][1] - bp) / bp * 100
    if gap > 2:
        return bars[0][1]
    if gap < -2:
        target = bars[0][0][:10] + ' 10:30:00'
        for b in bars:
            if b[0] == target: return b[1]
        return bars[-1][1]
    return strat_trail_1(bars, bp)

def strat_time_segmented(bars, bp):
    """分时段策略: 上午用新高回落0.8%, 下午用新高回落1.5%"""
    peak = bars[0][1]
    for b in bars:
        hour = int(b[0][11:13])
        trail = 0.8 if hour <= 11 else 1.5
        if b[1] > peak: peak = b[1]
        elif (peak - b[1]) / peak * 100 >= trail: return b[1]
    return bars[-1][1]

def strat_momentum_filter(bars, bp):
    """动量过滤: 前30分钟涨>2%且放量则激进止盈(0.5%回落),否则保守(2%)"""
    first6 = bars[:6]
    mom = (first6[-1][1] - first6[0][1]) / first6[0][1] * 100
    vol_first = np.mean([b[5] for b in first6])
    vol_rest = np.mean([b[5] for b in bars[6:]]) if len(bars) > 6 else vol_first
    
    if mom > 2 and vol_first > vol_rest * 1.5:
        trail_pct = 0.5  # 强势, 紧止损
    elif mom > 0:
        trail_pct = 1.0
    else:
        trail_pct = 2.0  # 弱势, 宽止损
    
    peak = bars[0][1]
    for b in bars:
        if b[1] > peak: peak = b[1]
        elif (peak - b[1]) / peak * 100 >= trail_pct: return b[1]
    return bars[-1][1]

def strat_1130_sell(bars, bp):
    """11:30卖出 (简单但有效)"""
    for b in bars:
        if '11:30' in b[0]: return b[1]
    return bars[-1][1]

def strat_am_peak_pm_trail(bars, bp):
    """上午最高后, 下午用回落0.8%跟踪"""
    am_bars = [b for b in bars if int(b[0][11:13]) <= 11]
    am_peak = max(b[2] for b in am_bars) if am_bars else bars[0][2]
    in_pm = False
    peak = am_peak
    for b in bars:
        hour = int(b[0][11:13])
        if hour >= 13: in_pm = True
        if in_pm:
            if b[1] > peak: peak = b[1]
            elif (peak - b[1]) / peak * 100 >= 0.8: return b[1]
    return bars[-1][1]

def strat_near_limit(bars, bp):
    for b in bars:
        if b[1] >= bp * 1.09: return b[1]
    return bars[-1][1]

def strat_1430(bars, bp):
    for b in bars:
        if '14:30' in b[0]: return b[1]
    return bars[-1][1]

# ============================================================
# Part 3: 改进MLP
# ============================================================
print("\n" + "=" * 80)
print("  PART 3: 改进MLP神经网络")
print("=" * 80)

def extract_rich_features(bars, bp):
    """提取更丰富的特征, X(n, 20)"""
    n = len(bars)
    closes = np.array([b[1] for b in bars], dtype=np.float64)
    highs = np.array([b[2] for b in bars], dtype=np.float64)
    lows = np.array([b[3] for b in bars], dtype=np.float64)
    opens = np.array([b[4] for b in bars], dtype=np.float64)
    vols = np.array([b[5] for b in bars], dtype=np.float64)
    times_str = [b[0] for b in bars]
    
    # 价格特征
    cr = closes / bp
    br = (closes - opens) / opens * 100
    ba = (highs - lows) / opens * 100
    cumr = (closes - closes[0]) / closes[0] * 100
    
    # 成交量
    vm5 = np.convolve(vols, np.ones(5)/5, mode='same')
    vr = vols / (vm5 + 1e-10)
    
    # 日内位置
    dh = np.maximum.accumulate(highs)
    dl = np.minimum.accumulate(lows)
    dfh = (dh - closes) / dh * 100
    dfl = (closes - dl) / dl * 100
    
    # 均线
    m5 = np.convolve(closes, np.ones(5)/5, mode='same')
    m10 = np.convolve(closes, np.ones(min(10,n))/min(10,n), mode='same')
    m20 = np.convolve(closes, np.ones(min(20,n))/min(20,n), mode='same')
    mr5 = closes / (m5 + 1e-10)
    mr10 = closes / (m10 + 1e-10)
    mr20 = closes / (m20 + 1e-10)
    
    # 时间
    ti = np.arange(n) / max(n-1, 1)
    hours = np.array([int(t[11:13]) for t in times_str])
    mins = np.array([int(t[14:16]) for t in times_str])
    sess_min = np.where(hours >= 13, (hours-13)*60 + mins, (hours-9)*60 + mins - 30)
    sess_norm = sess_min / 240  # normalized session time
    
    is_am = (hours <= 11).astype(float)
    is_pm = (hours >= 13).astype(float)
    is_open = np.logical_or((hours == 9), np.logical_and((hours == 10), (mins <= 30))).astype(float)
    
    # 动量
    mom1 = np.zeros(n); mom1[1:] = (closes[1:] - closes[:-1]) / (closes[:-1] + 1e-10) * 100
    mom3 = np.zeros(n)
    if n >= 4: mom3[3:] = (closes[3:] - closes[:-3]) / (closes[:-3] + 1e-10) * 100
    
    # VWAP
    cum_vol = np.cumsum(vols)
    cum_vp = np.cumsum(vols * closes)
    vwap = cum_vp / (cum_vol + 1e-10)
    vwap_dist = (closes - vwap) / vwap * 100
    
    X = np.column_stack([
        cr, br, ba, vr, cumr, dfh, dfl, mr5, mr10, mr20,
        ti, sess_norm, is_am, is_pm, is_open, mom1, mom3, vwap_dist,
        (highs - closes) / closes * 100, (closes - lows) / lows * 100
    ])
    
    y = np.zeros(n)
    for i in range(n):
        if i < n - 1:
            y[i] = (np.max(closes[i+1:]) - closes[i]) / closes[i] * 100
    
    return X, y

class MLP:
    def __init__(self, sizes, lr=0.001, l2=1e-5):
        self.sizes = sizes
        self.lr = lr; self.l2 = l2
        self.W = []; self.B = []
        for i in range(len(sizes)-1):
            fan = sizes[i]
            self.W.append(np.random.randn(fan, sizes[i+1]) * np.sqrt(2.0/fan))
            self.B.append(np.zeros(sizes[i+1]))
    
    def _relu(self, x): return np.maximum(0, x)
    def _drelu(self, x): return (x > 0).astype(float)
    
    def predict(self, X):
        a = X
        for w, b in zip(self.W[:-1], self.B[:-1]):
            a = self._relu(a @ w + b)
        return (a @ self.W[-1] + self.B[-1]).flatten()
    
    def fit(self, X, y, Xv, yv, epochs=200, bs=128, pat=25):
        best_loss = float('inf'); best_W = None; best_B = None; ni = 0
        for ep in range(epochs):
            idx = np.random.permutation(X.shape[0])
            for s in range(0, X.shape[0], bs):
                e = min(s+bs, X.shape[0])
                bi = idx[s:e]; Xb = X[bi]; yb = y[bi]
                acts = [Xb]; pas = []
                for w, b in zip(self.W[:-1], self.B[:-1]):
                    z = acts[-1] @ w + b; pas.append(z)
                    acts.append(self._relu(z))
                z = acts[-1] @ self.W[-1] + self.B[-1]; pas.append(z); acts.append(z)
                err = (acts[-1].flatten() - yb) / len(bi)
                delta = err.reshape(-1, 1)
                for l in range(len(self.W)-1, -1, -1):
                    if l < len(self.W)-1:
                        delta = delta @ self.W[l+1].T * self._drelu(pas[l])
                    dw = acts[l].T @ delta + self.l2 * self.W[l]
                    db = np.sum(delta, axis=0)
                    self.W[l] -= self.lr * dw; self.B[l] -= self.lr * db
            
            if Xv is not None:
                vl = np.mean((self.predict(Xv) - yv)**2)
            else:
                vl = np.mean((self.predict(X) - y)**2)
            
            if vl < best_loss:
                best_loss = vl; best_W = [w.copy() for w in self.W]; best_B = [b.copy() for b in self.B]; ni = 0
            else: ni += 1
            if ni >= pat: break
        if best_W: self.W = best_W; self.B = best_B
        return best_loss

class Scaler:
    def fit(self, X):
        self.m = np.mean(X, axis=0); self.s = np.std(X, axis=0)
        self.s[self.s < 1e-10] = 1.0; return self
    def transform(self, X): return (X - self.m) / self.s

# 构建ML训练数据
all_X = []; all_y = []
for _, _, d2c, bars in all_data:
    X, y = extract_rich_features(bars, d2c)
    if X is not None:
        all_X.append(X); all_y.append(y)

n_tot = len(all_X)
n_feat = all_X[0].shape[1]
tr_end = int(n_tot * 0.65); vl_end = int(n_tot * 0.80)
Xt = np.vstack([all_X[i] for i in range(tr_end)])
yt = np.hstack([all_y[i] for i in range(tr_end)])
Xv = np.vstack([all_X[i] for i in range(tr_end, vl_end)])
yv = np.hstack([all_y[i] for i in range(tr_end, vl_end)])

print(f"训练: {tr_end}笔/{Xt.shape[0]}bar, 验证: {vl_end-tr_end}笔, 测试: {n_tot-vl_end}笔, 特征: {n_feat}")

sc = Scaler().fit(Xt)
Xts = sc.transform(Xt); Xvs = sc.transform(Xv)

# 训练多个架构
archs = [
    ([n_feat, 256, 128, 64, 1], 0.0005),
    ([n_feat, 512, 256, 128, 1], 0.0003),
    ([n_feat, 128, 64, 32, 1], 0.001),
    ([n_feat, 256, 128, 64, 32, 1], 0.0005),
]

best_mlp = None; best_vl = float('inf')
for arch, lr in archs:
    print(f"  训练 {arch} lr={lr}...", end=" ")
    m = MLP(arch, lr=lr)
    vl = m.fit(Xts, yt, Xvs, yv, epochs=200, pat=20)
    print(f"val_MSE={vl:.4f}")
    if vl < best_vl:
        best_vl = vl; best_mlp = m

class MLStrat:
    def __init__(self, model, scaler, th):
        self.m = model; self.s = scaler; self.th = th
    def sell(self, bars, bp):
        X, _ = extract_rich_features(bars, bp)
        if X is None or len(X) < 6: return bars[-1][1]
        Xs = self.s.transform(X)
        preds = self.m.predict(Xs)
        for i in range(5, len(preds)):
            if preds[i] < self.th: return bars[i][1]
        return bars[-1][1]

# ============================================================
# Part 4: 回测全部策略
# ============================================================
print("\n" + "=" * 80)
print("  PART 4: 全量回测")
print("=" * 80)

strategies = {
    "01_baseline收盘": strat_close,
    "02_新高回落1%": strat_trail_1,
    "03_自适应ATR止损": strat_trail_atr,
    "04_放量滞涨卖": strat_vol_climax,
    "05_跳空感知": strat_gap_aware,
    "06_分时段追踪": strat_time_segmented,
    "07_动量过滤": strat_momentum_filter,
    "08_11:30固定卖": strat_1130_sell,
    "09_上午峰下午追": strat_am_peak_pm_trail,
    "10_接近涨停卖": strat_near_limit,
    "11_14:30固定卖": strat_1430,
}

# 添加ML策略
ml_ths = [0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 1.0]
for th in ml_ths:
    ms = MLStrat(best_mlp, sc, th)
    strategies[f"ML_v2_th={th:.2f}"] = ms.sell

# 回测
by_d1 = defaultdict(list)
for i in range(vl_end, n_tot):
    code, d1, d2c, bars = all_data[i]
    by_d1[d1].append((code, d2c, bars))

results = {s: [] for s in strategies}
for d1 in sorted(by_d1.keys()):
    trs = by_d1[d1]
    n_tr = len(trs)
    pc = CAPITAL / n_tr
    dr = {s: [] for s in strategies}
    for code, d2c, bars in trs:
        for sn, sf in strategies.items():
            if isinstance(sf, type(strat_close)):
                sp = sf(bars, d2c)
            else:
                sp = sf(bars, d2c)
            dr[sn].append(fee(d2c, sp, pc))
    for sn in strategies:
        rts = dr[sn]
        if rts:
            results[sn].append({'date': d1, 'ret': round(sum(rts)/len(rts), 4), 'cnt': len(rts)})

# ============================================================
# Part 5: 输出
# ============================================================
print("\n" + "=" * 95)
print(f"  全策略对比 ({len(next(iter(results.values())))}卖出日)")
print("=" * 95)
print(f"  {'策略':<30} {'净值':>8} {'总收益%':>10} {'胜率%':>7} {'回撤%':>8} {'夏普':>7}")
print("  " + "-" * 78)

ranks = []
for sn in strategies:
    data = results[sn]
    if not data: continue
    cum = 1.0; peak = 1.0; max_dd = 0.0; rets = []
    for r in data:
        rets.append(r['ret'])
        cum *= (1 + r['ret']/100)
        if cum > peak: peak = cum
        dd = (cum - peak)/peak*100
        if dd < max_dd: max_dd = dd
    wr = sum(1 for r in data if r['ret']>0)/len(data)*100
    daily = np.array(rets)
    sharpe = np.mean(daily)/np.std(daily)*np.sqrt(252) if np.std(daily)>0 else 0
    total = (cum-1)*100
    ranks.append((cum, sn, total, wr, max_dd, sharpe))

ranks.sort(key=lambda x: x[0], reverse=True)
for cum, sn, tr, wr, dd, sh in ranks:
    tag = " <-- ML" if sn.startswith("ML") else ""
    print(f"  {sn:<30} {cum:>8.4f} {tr:>10.2f} {wr:>7.1f} {dd:>8.2f} {sh:>7.2f}{tag}")

# 月度明细 (前5)
print("\n" + "=" * 95)
print("  前5策略 月度收益(简单求和)")
print("=" * 95)
top5_names = [x[1] for x in ranks[:5]]
months = sorted(set(r['date'][:6] for sn, data in results.items() for r in data))

header = f"  {'月':<8}"
for sn in top5_names:
    header += f" {sn[:14]:>14}"
print(header)
print("  " + "-" * (8 + 15*len(top5_names)))

for m in months:
    row = f"  {m:<8}"
    for sn in top5_names:
        ms = sum(r['ret'] for r in results[sn] if r['date'].startswith(m))
        row += f" {ms:>14.2f}%"
    print(row)

# 策略相关性矩阵 (前8)
print("\n" + "=" * 95)
print("  策略日收益相关性 (前8)")
print("=" * 95)
top8 = [x[1] for x in ranks[:8]]
top8_daily = {}
for sn in top8:
    top8_daily[sn] = np.array([r['ret'] for r in results[sn]])

corr_m = np.zeros((8, 8))
for i, s1 in enumerate(top8):
    for j, s2 in enumerate(top8):
        corr_m[i, j] = np.corrcoef(top8_daily[s1], top8_daily[s2])[0, 1]

print("  " + " ".join(f"{s[:8]:>8}" for s in top8))
for i, s in enumerate(top8):
    print(f"  {s[:8]:>8} " + " ".join(f"{corr_m[i,j]:>8.3f}" for j in range(8)))

print("\n" + "=" * 95)
print("  分析完成!")
print("=" * 95)
