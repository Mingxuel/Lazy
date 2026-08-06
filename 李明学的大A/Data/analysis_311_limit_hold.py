#!/usr/bin/env python3
"""
311 5M回测 — 涨停封板持仓过夜
  涨停后检测是否开板:
    未开板(一字/K线低点=涨停价) → 持仓过夜，第二天继续卖出
    开板(后续K线低点<涨停价)   → 直接涨停价卖出
  持仓过夜当天不买新股
  手续费: 万一免五
"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S = r'C:\Lazy\李明学的大A\Data\Strategy'
K = r'C:\Lazy\李明学的大A\Data\1D'
M5DIR = r'C:\Lazy\MarcoAI\AIData\5M'
# 万一免五
CR = 0.0001; CM = 0.0; SD = 0.0005; TF = 0.00001; CAPITAL = 1_000_000

def load_td():
    ds = []
    with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
        for l in f: l = l.strip(); l and l.isdigit() and len(l) == 8 and ds.append(l)
    return sorted(ds)

def load_kline(code):
    fp = os.path.join(K, code)
    if not os.path.exists(fp): return [], []
    rows = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('\ufeff'): continue
            c = l.split()
            if len(c) < 10 or not c[0].isdigit(): continue
            rows.append((c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5]), float(c[9])))
    return rows, {r[0]: i for i, r in enumerate(rows)}

_5m_cache = {}
def load_5m_bars_scaled(code, date_str, d1_open, d1_close):
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

    m5_open = raw_bars[0][1]
    m5_close = raw_bars[-1][3]
    scale_open = d1_open / m5_open if m5_open > 0 else 1.0
    scale_close = d1_close / m5_close if m5_close > 0 else 1.0
    if abs(scale_open - 1.0) < 0.02:
        scale = scale_open
    else:
        scale = scale_close

    scaled = []
    for dt, o, h, l, c, v in raw_bars:
        scaled.append((dt, o * scale, h * scale, l * scale, c * scale, v))
    return scaled


FEATURES = ['pb_depth', 'vol_contract', 'ma5_dev', 'pc_vs_low_atr', 'high_vs_pc_atr', 'ma_golden']

def compute_ma_golden(rows, d2i):
    if d2i < 10: return 0
    closes = np.array([r[4] for r in rows[:d2i + 1]])
    ma5_now = np.mean(closes[-5:]); ma10_now = np.mean(closes[-10:])
    ma5_prev = np.mean(closes[-6:-1]); ma10_prev = np.mean(closes[-11:-1])
    return 1 if (ma5_prev <= ma10_prev and ma5_now > ma10_now) else 0

def extract_all(rows, d2i, code):
    r2 = rows[d2i]; o2, h2, l2, c2, v2, pc2 = r2[1], r2[2], r2[3], r2[4], r2[5], r2[6]
    r3 = rows[d2i - 1] if d2i >= 1 else None
    cls = np.array([r[4] for r in rows[:d2i + 1]])
    highs = np.array([r[2] for r in rows[:d2i + 1]])
    lows = np.array([r[3] for r in rows[:d2i + 1]])
    n = len(cls)
    f = {}
    f['pb_depth'] = (r3[4] - c2) / r3[4] * 100 if (r3 and r3[4] > 0) else 0
    f['vol_contract'] = 1 if (r3 and v2 < r3[5] * 0.8) else 0
    f['ma5_dev'] = (c2 - np.mean(cls[-5:])) / np.mean(cls[-5:]) * 100 if n >= 5 else 0
    if n >= 10:
        trs = []
        for i in range(d2i - 9, d2i + 1):
            h = highs[i]; l = lows[i]; pc = rows[i - 1][4] if i > 0 else rows[i][6]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        atr10 = np.mean(trs) if trs else 1
    else:
        atr10 = h2 - l2 if h2 > l2 else 1
    f['pc_vs_low_atr'] = (pc2 - l2) / atr10 if atr10 > 0 else 0
    f['high_vs_pc_atr'] = (h2 - pc2) / atr10 if atr10 > 0 else 0
    f['ma_golden'] = compute_ma_golden(rows, d2i)
    return f


# 加载样本
tds = load_td(); di = {d: i for i, d in enumerate(tds)}
samples = []
for fn in sorted(os.listdir(S)):
    if not fn.isdigit(): continue
    d1 = fn; d1i = di.get(d1)
    if d1i is None or d1i < 3: continue
    d2 = tds[d1i - 1]
    with open(os.path.join(S, fn)) as f:
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
            bp = r1[6]; sp_close = r1[4]; d1_open = r1[1]; d1_high = r1[2]; d1_low = r1[3]
            if bp <= 0: continue
            f = extract_all(rows, d2i_k, code)
            samples.append((f, code, d1, bp, sp_close, name, d1_open, d1_high, d1_low))

samples.sort(key=lambda x: x[2])
daily_meta = defaultdict(list)
for i, s in enumerate(samples): daily_meta[s[2]].append(i)
all_dates = sorted(daily_meta.keys())
X = np.array([[s[0].get(k, 0) for k in FEATURES] for s in samples])
y = np.array([(s[4] - s[3]) / s[3] * 100 for s in samples])
print(f"样本: {len(samples)}笔, {len(all_dates)}天")


def fee(buy, sell, pc=CAPITAL):
    sh = int(pc / buy / 100) * 100
    if sh == 0: sh = 100
    c = sh * buy; bf = max(c * CR, CM) + c * TF; tb = c + bf
    r = sh * sell; sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100


# ============================================================
# 5M 卖出 — 含涨停封板检测
# ============================================================
def sell_5m_hold(bars, bp):
    """
    返回 (sell_price, mode) 或 (None, 'locked_overnight') — 持仓过夜
    """
    if not bars: return bp, 'no_data'

    stop_price = bp * 0.94
    limit_up = round(bp * 1.10, 2)
    hit_limit_bar = None

    for i, (dt, o, h, l, c, v) in enumerate(bars):
        # 1. 开盘止损
        if i == 0 and o <= stop_price:
            return o, 'open_stop'
        # 2. 日内止损
        if l <= stop_price:
            return stop_price, 'low_stop'
        # 3. 涨停
        if h >= limit_up * 0.999:
            hit_limit_bar = i
            break

    if hit_limit_bar is not None:
        # 检查后续K线是否开板
        opened = False
        for j in range(hit_limit_bar + 1, len(bars)):
            _, _, _, l2, _, _ = bars[j]
            if l2 < limit_up * 0.999:
                opened = True
                break

        if opened:
            return limit_up, 'limit_up'
        else:
            # 封板不动 → 持仓过夜
            return None, 'locked_overnight'

    # 收盘卖出
    return bars[-1][3], 'close'


def sell_daily(bp, o, h, l, c):
    limit_up = round(bp * 1.10, 2); stop = bp * 0.94
    if o <= stop: return o, 'open_stop'
    if l <= stop: return stop, 'low_stop'
    if h >= limit_up * 0.999: return limit_up, 'limit_up'
    return c, 'close'


def sell_5m_next_day(bars, bp):
    """持仓过夜后第二天卖出"""
    if not bars or len(bars) < 5:
        return bars[-1][3] if bars else bp, 'forced_close'

    stop_price = bp * 0.94
    limit_up = round(bp * 1.10, 2)

    hit_limit = False
    for i, (dt, o, h, l, c, v) in enumerate(bars):
        # 开盘止损
        if i == 0 and o <= stop_price:
            return o, 'open_stop_次日'
        # 日内止损
        if l <= stop_price:
            return stop_price, 'low_stop_次日'
        # 涨停卖出
        if h >= limit_up * 0.999:
            hit_limit = True
            hit_idx = i
            break

    if hit_limit:
        # 检查是否再次封板
        opened = False
        for j in range(hit_idx + 1, len(bars)):
            _, _, _, l2, _, _ = bars[j]
            if l2 < limit_up * 0.999:
                opened = True
                break
        if opened:
            return limit_up, 'limit_up_次日'
        else:
            # 第二天也封板了 → 再拿一天? 还是卖?
            # 策略规定: 第二天必须卖，按收盘价
            return bars[-1][3], 'close_次日(再封板)'

    # 收盘卖出
    return bars[-1][3], 'close_次日'


# ============================================================
# 回测
# ============================================================
def metrics(rets):
    cum = 1.0; peak = 1.0; md = 0.0
    for r in rets:
        if r == 0: continue
        cum *= (1 + r / 100)
        if cum > peak: peak = cum
        dd = (cum - peak) / peak * 100
        if dd < md: md = dd
    nonzero = [r for r in rets if r != 0]
    wr = sum(1 for r in nonzero if r > 0) / len(nonzero) * 100 if nonzero else 0
    return cum, (cum - 1) * 100, wr, md


def backtest_hold(use_hold=True, use_consec=True):
    """
    use_hold=True: 涨停封板持仓过夜
    use_hold=False: 基准(涨停即卖)
    """
    all_rets = []
    stats = defaultdict(int)
    consec = 0
    fb = 0
    hold_bp = None; hold_code = None; hold_name = None; hold_date = None  # 持仓过夜状态
    hold_trades = []  # 记录过夜交易明细

    for d_idx, d1_date in enumerate(all_dates):
        # ================================================================
        # 第一步: 处理持仓过夜
        # ================================================================
        if hold_bp is not None:
            rows, date_idx = load_kline(hold_code)
            d1i_k = date_idx.get(d1_date)
            if d1i_k is None:
                # 数据缺失，强制按收盘价
                ret = 0.0
                all_rets.append(ret)
                stats['forced_close'] += 1
                hold_bp = None; hold_code = None; hold_name = None; hold_date = None
                continue

            r = rows[d1i_k]; o, h_d, l_d, c_d = r[1], r[2], r[3], r[4]

            bars = load_5m_bars_scaled(hold_code, d1_date, o, c_d)
            if bars and len(bars) >= 10:
                sp, mode = sell_5m_next_day(bars, hold_bp)
            else:
                fb += 1
                sp, mode = sell_daily(hold_bp, o, h_d, l_d, c_d)

            ret = fee(hold_bp, sp, CAPITAL)
            all_rets.append(ret); stats[mode] += 1
            hold_trades.append({
                'buy_date': hold_date, 'sell_date': d1_date,
                'code': hold_code, 'name': hold_name,
                'bp': hold_bp, 'sp': sp, 'ret': ret, 'mode': mode
            })

            if ret < -0.05: consec += 1
            elif ret > 0.05: consec = 0

            hold_bp = None; hold_code = None; hold_name = None; hold_date = None
            # 持仓过夜当天不买新股
            continue

        # ================================================================
        # 第二步: 选股 (Walk-Forward)
        # ================================================================
        idxs = daily_meta[d1_date]; first_i = idxs[0]
        if first_i < 100:
            best = samples[idxs[0]]
        else:
            hist = [j for j in range(first_i)]
            Xh = X[hist]; yh = y[hist]
            mean = Xh.mean(axis=0); std = Xh.std(axis=0) + 1e-8
            Xn = (Xh - mean) / std; d_dim = Xn.shape[1]
            try:
                w_s = solve(Xn.T @ Xn + np.eye(d_dim) * 2.0, Xn.T @ yh)
            except:
                w_s = np.zeros(d_dim)
            Xt = np.array([(X[i] - mean) / std for i in idxs])
            preds = Xt @ w_s; best = samples[idxs[int(np.argmax(preds))]]

        code = best[1]; name = best[5]
        bp = best[3]; o = best[6]; h_d = best[7]; l_d = best[8]; c_d = best[4]

        # 仓位管理
        cap = CAPITAL
        if use_consec:
            if consec >= 3:
                all_rets.append(0.0); stats['skip'] += 1; consec = 0; continue
            elif consec >= 2:
                cap = CAPITAL * 0.5; stats['half'] += 1

        # ================================================================
        # 第三步: 卖出
        # ================================================================
        bars = load_5m_bars_scaled(code, d1_date, o, c_d)
        if bars and len(bars) >= 10:
            if use_hold:
                sp, mode = sell_5m_hold(bars, bp)
            else:
                sp, mode = sell_daily(bp, o, h_d, l_d, c_d)
        else:
            fb += 1
            sp, mode = sell_daily(bp, o, h_d, l_d, c_d)

        if mode == 'locked_overnight':
            # 封板持仓过夜
            hold_bp = bp; hold_code = code; hold_name = name; hold_date = d1_date
            all_rets.append(0.0)
            stats['locked_overnight'] += 1
        else:
            ret = fee(bp, sp, cap)
            all_rets.append(ret); stats[mode] += 1
            if ret < -0.05: consec += 1
            elif ret > 0.05: consec = 0

    return all_rets, stats, fb, hold_trades


# ============================================================
# 运行
# ============================================================
print(f"\n{'=' * 100}")
print(f"  涨停封板持仓过夜回测 (万一免五)")
print(f"{'=' * 100}")

# 基准: 不持仓过夜
rets_base, st_base, fb_base, _ = backtest_hold(use_hold=False)
c_base, tr_base, wr_base, dd_base = metrics(rets_base)
mods_base = ', '.join(f'{k}:{v}' for k, v in sorted(st_base.items()))
fb_str = f' [回退{fb_base}]' if fb_base > 0 else ''

# 涨停封板持仓过夜
rets_hold, st_hold, fb_hold, hold_trades = backtest_hold(use_hold=True)
c_hold, tr_hold, wr_hold, dd_hold = metrics(rets_hold)
mods_hold = ', '.join(f'{k}:{v}' for k, v in sorted(st_hold.items()))
fb_str2 = f' [回退{fb_hold}]' if fb_hold > 0 else ''

print(f"\n{'策略':<50} {'净值':>8} {'收益':>10} {'胜率':>7} {'回撤':>7}  卖出分布")
print(f"{'-' * 120}")
print(f"{'基准: 涨停即卖':<50} {c_base:>8.4f} {tr_base:>+9.1f}% {wr_base:>6.1f}% {dd_base:>6.1f}%  {mods_base}{fb_str}")
print(f"{'封板持仓过夜':<50} {c_hold:>8.4f} {tr_hold:>+9.1f}% {wr_hold:>6.1f}% {dd_hold:>6.1f}%  {mods_hold}{fb_str2}")

# ============================================================
# 封板过夜交易明细
# ============================================================
if hold_trades:
    print(f"\n{'=' * 100}")
    print(f"  封板过夜交易明细 ({len(hold_trades)}笔)")
    print(f"{'=' * 100}")
    print(f"{'买入日':<12} {'卖出日':<12} {'名称':<8} {'代码':<12} {'买入':>8} {'卖出':>8} {'收益':>9} {'卖出方式':<25}")
    print('-' * 100)
    total_ret = 0.0
    for t in hold_trades:
        sign = '+' if t['ret'] > 0 else ''
        print(f"{t['buy_date']:<12} {t['sell_date']:<12} {t['name']:<8} {t['code']:<12} "
              f"{t['bp']:>8.2f} {t['sp']:>8.2f} {sign}{t['ret']:>+8.2f}% {t['mode']:<25}")
        total_ret += t['ret']
    avg_ret = total_ret / len(hold_trades)
    print(f"\n  封板过夜共{len(hold_trades)}次  平均收益{avg_ret:+.2f}%  累计{total_ret:+.1f}%")

# ============================================================
# 月度分解 (两种策略)
# ============================================================
for label, rets in [('基准: 涨停即卖', rets_base), ('封板持仓过夜', rets_hold)]:
    print(f"\n{'=' * 90}")
    print(f'  {label} — 月度盈亏')
    print(f"{'=' * 90}")

    m_rets = defaultdict(list)
    for mi, d in enumerate(all_dates):
        m_rets[d[:6]].append(rets[mi])

    cum_v = 1.0
    # 分组显示
    years = sorted(set(k[:4] for k in m_rets))
    for yr in years:
        yr_months = sorted([k for k in m_rets if k[:4] == yr])
        row1 = f"  {yr}: "
        row2 = f"       "
        for m in yr_months:
            mr = 1.0
            valid = [r for r in m_rets[m] if r != 0]
            for r in valid: mr *= (1 + r / 100)
            cum_v *= mr
            row1 += f"{m[4:]}月{((mr-1)*100):>+5.1f}%  "
            row2 += f"       "
        print(row1)

    # 汇总
    print(f"\n  净值: {cum_v:.4f}")


# ============================================================
# 年度
# ============================================================
print(f"\n{'=' * 50}")
print(f'  年度对比')
print(f"{'=' * 50}")
print(f"{'年份':<8} {'基准':>12} {'封板过夜':>12} {'差异':>10}")

y_base = defaultdict(float)
y_hold = defaultdict(float)

for mi, d in enumerate(all_dates):
    yr = d[:4]
    if rets_base[mi] != 0:
        y_base[yr] = y_base[yr] * (1 + rets_base[mi] / 100) if y_base[yr] != 0 else (1 + rets_base[mi] / 100)
    if rets_hold[mi] != 0:
        y_hold[yr] = y_hold[yr] * (1 + rets_hold[mi] / 100) if y_hold[yr] != 0 else (1 + rets_hold[mi] / 100)

for yr in sorted(set(list(y_base.keys()) + list(y_hold.keys()))):
    b = (y_base.get(yr, 1.0) - 1) * 100
    h = (y_hold.get(yr, 1.0) - 1) * 100
    diff = h - b
    print(f"{yr:<8} {b:>+11.1f}% {h:>+11.1f}% {diff:>+9.1f}pp")


# ============================================================
# 季度
# ============================================================
print(f"\n{'=' * 50}")
print(f'  季度对比')
print(f"{'=' * 50}")

q_base = defaultdict(float)
q_hold = defaultdict(float)

for mi, d in enumerate(all_dates):
    ym = d[:6]
    q_key = d[:4] + 'Q' + str((int(d[4:6]) - 1) // 3 + 1)
    if rets_base[mi] != 0:
        q_base[q_key] = q_base[q_key] * (1 + rets_base[mi] / 100) if q_base[q_key] != 0 else (1 + rets_base[mi] / 100)
    if rets_hold[mi] != 0:
        q_hold[q_key] = q_hold[q_key] * (1 + rets_hold[mi] / 100) if q_hold[q_key] != 0 else (1 + rets_hold[mi] / 100)

print(f"{'季度':<10} {'基准':>12} {'封板过夜':>12} {'差异':>10}")
for q in sorted(set(list(q_base.keys()) + list(q_hold.keys()))):
    b = (q_base.get(q, 1.0) - 1) * 100
    h = (q_hold.get(q, 1.0) - 1) * 100
    diff = h - b
    print(f"{q:<10} {b:>+11.1f}% {h:>+11.1f}% {diff:>+9.1f}pp")
