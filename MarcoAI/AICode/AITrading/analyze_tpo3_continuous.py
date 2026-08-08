# -*- coding: utf-8 -*-
"""TPO3 分析: vol_contract 改为连续值 (D-3量-D-2量)/D-3量, 不再用0.8二分"""
import os, sys, numpy as np, urllib.request

KDIR = r'C:\Lazy\李明学的大A\Data\1D'
SRC  = r'C:\Lazy\李明学的大A\Data\Strategy'
FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

# ═══════════ 交易日 ═══════════
tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds = sorted(tds); di = {d:i for i,d in enumerate(tds)}
today = '20260807'; today_i = di[today]
d4_311 = tds[today_i - 2]  # 0805
d3_311 = tds[today_i - 1]  # 0806
d2_311 = today
print(f'D-4={d4_311}(涨停) → D-3={d3_311}(放量) → D-2={d2_311}(今日)')

# ═══════════ K线 ═══════════
def load_kline(code):
    fp = os.path.join(KDIR, code)
    rows = []; idx = {}
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('\ufeff'): continue
            c = l.split()
            if len(c) < 10 or not c[0].isdigit(): continue
            idx[c[0]] = len(rows)
            rows.append((c[0], float(c[1]), float(c[2]), float(c[3]),
                        float(c[4]), float(c[5]), float(c[9])))
    return rows, idx

# ═══════════ Walk-Forward (连续vol_contract) ═══════════
print(f'\n{"="*60}')
print(f'Walk-Forward 训练 (vol_contract 连续值, 截止 {d3_311})')
print(f'{"="*60}')

samples_all = []
for fn in sorted(os.listdir(SRC)):
    if not fn.isdigit(): continue
    d1 = fn; d1i = di.get(d1)
    if d1i is None or d1i < 3: continue
    d2 = tds[d1i - 1]
    with open(os.path.join(SRC, fn)) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            p = l.split('|')
            if len(p) < 2: continue
            name, code = p[0], p[1]
            rows, date_idx = load_kline(code)
            d1i_k = date_idx.get(d1); d2i_k = date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1 = rows[d1i_k]; bp = r1[6]; sp_c = r1[4]
            if bp <= 0: continue
            r2 = rows[d2i_k]; r3 = rows[d2i_k - 1] if d2i_k >= 1 else None
            cls = np.array([r[4] for r in rows[:d2i_k + 1]])
            highs = np.array([r[2] for r in rows[:d2i_k + 1]])
            lows = np.array([r[3] for r in rows[:d2i_k + 1]])
            n = len(cls)
            f = {}
            f['pb_depth'] = (r3[4] - r2[4]) / r3[4] * 100 if (r3 and r3[4] > 0) else 0
            # ★ vol_contract 连续值: (D-3量 - D-2量) / D-3量 × 100
            # 正值=缩量(好), 负值=放量(差)
            f['vol_contract'] = (r3[5] - r2[5]) / r3[5] * 100 if (r3 and r3[5] > 0) else 0
            f['ma5_dev'] = (r2[4] - np.mean(cls[-5:])) / np.mean(cls[-5:]) * 100 if n >= 5 else 0
            if n >= 10:
                trs = []
                for i in range(d2i_k - 9, d2i_k + 1):
                    h = highs[i]; l = lows[i]; pc = rows[i - 1][4] if i > 0 else rows[i][6]
                    trs.append(max(h - l, abs(h - pc), abs(l - pc)))
                atr10 = np.mean(trs) if trs else 1
            else:
                atr10 = r2[2] - r2[3] if r2[2] > r2[3] else 1
            f['pc_vs_low_atr'] = (r2[6] - r2[3]) / atr10 if atr10 > 0 else 0
            f['high_vs_pc_atr'] = (r2[2] - r2[6]) / atr10 if atr10 > 0 else 0
            c_arr = np.array([r[4] for r in rows[:d2i_k + 1]])
            f['ma_golden'] = 0
            if d2i_k >= 10:
                ma5 = np.mean(c_arr[-5:]); ma10 = np.mean(c_arr[-10:])
                ma5p = np.mean(c_arr[-6:-1]); ma10p = np.mean(c_arr[-11:-1])
                f['ma_golden'] = 1 if (ma5p <= ma10p and ma5 > ma10) else 0
            samples_all.append((f, code, d1, bp, sp_c, name))

X = np.array([[s[0].get(k, 0) for k in FEATURES] for s in samples_all])
y = np.array([(s[4] - s[3]) / s[3] * 100 for s in samples_all])
mask = np.array([s[2] <= d3_311 for s in samples_all])
X_tr = X[mask]; y_tr = y[mask]
mean = X_tr.mean(axis=0); std = X_tr.std(axis=0) + 1e-8
Xn = (X_tr - mean) / std
w = np.linalg.solve(Xn.T @ Xn + np.eye(Xn.shape[1]) * 2.0, Xn.T @ y_tr)

print(f'训练样本: {mask.sum()} 条')
cn_names = ['回踩深度','量能收缩','MA5偏离','空头深度','多头力度','均线金叉']
print(f'\n=== 6特征权重 (vol_contract已改为连续值) ===')
for cn, wt in zip(cn_names, w):
    print(f'  {cn:<10} {wt:>+8.4f}')
print(f'\n  MU: {np.array2string(mean, precision=3, suppress_small=True)}')
print(f'  SG: {np.array2string(std,  precision=3, suppress_small=True)}')
print(f'\n  vol_contract 分布: min={X[:,1].min():.1f}  max={X[:,1].max():.1f}  avg={X[:,1].mean():.1f}')

# ═══════════ 腾讯行情 ═══════════
codes = ['000657.SZ','002636.SZ','601869.SH','603268.SH']
names_cn = {'000657.SZ':'中钨高新','002636.SZ':'金安国纪',
            '601869.SH':'长飞光纤','603268.SH':'松发股份'}
mkt_map = {'000657.SZ':'sz000657','002636.SZ':'sz002636',
           '601869.SH':'sh601869','603268.SH':'sh603268'}

live = {}
for code in codes:
    try:
        resp = urllib.request.urlopen(f'http://qt.gtimg.cn/q={mkt_map[code]}', timeout=5).read().decode('gbk')
        p = resp.split('~')
        live[code] = (p[1], float(p[3]), float(p[5]), float(p[33]), float(p[34]), int(p[6])*100, float(p[4]))
    except Exception as e:
        print(f'{code} 行情异常: {e}')

# ═══════════ 311结构 ═══════════
print(f'\n{"="*70}')
print(f'311 结构验证: D-4={d4_311}涨停 + D-3={d3_311}放量')
print(f'{"="*70}')
for code in codes:
    rows, idx = load_kline(code)
    d4i = idx.get(d4_311); d3i = idx.get(d3_311)
    r4 = rows[d4i]; r3 = rows[d3i]
    lu4 = round(r4[6]*1.10, 2); is_lim = r4[4] >= lu4*0.995
    ve = r3[5] > r4[5]
    ok = '✅' if (is_lim and ve) else '❌'
    print(f'  {ok} {names_cn[code]}({code}) '
          f'D-4 C={r4[4]:.2f}(涨停{lu4:.2f}) V={r4[5]/100:.0f}手 '
          f'D-3 C={r3[4]:.2f} V={r3[5]/100:.0f}手')

# ═══════════ 行情 ═══════════
print(f'\n{"="*70}')
print(f'今日 D-2={d2_311} 收盘行情')
print(f'{"="*70}')
print(f'{"代码":<14} {"名称":<8} {"昨收":>8} {"今开":>8} {"最高":>8} {"最低":>8} {"收盘":>8} {"涨跌":>7} {"量(万手)":>10}')
for code in codes:
    if code not in live: continue
    nm,c,o,h,l,v,pre = live[code]; chg = (c-pre)/pre*100
    print(f'  {code:<14} {nm:<8} {pre:>8.2f} {o:>8.2f} {h:>8.2f} {l:>8.2f} {c:>8.2f} {chg:>+6.2f}% {v/1000000:>10.1f}')

# ═══════════ 特征 ═══════════
print(f'\n{"="*80}')
print('特征计算 (D-3={d3_311}日线 + 今日腾讯行情, vol_contract 连续值)')
print(f'{"="*80}')

candidates_raw = []
for code in codes:
    if code not in live: continue
    rows, idx = load_kline(code)
    d3i = idx.get(d3_311)
    nm,c,o,h,l,v,pre = live[code]
    r3 = rows[d3i]

    pb = (r3[4] - c) / r3[4] * 100

    # ★ vol_contract 连续值: (D-3量 - 今日量) / D-3量 × 100
    d3v = r3[5] * 100
    vc = (d3v - v) / d3v * 100 if d3v > 0 else 0
    vr = v / d3v if d3v > 0 else 0

    all_c = np.array([r[4] for r in rows[:d3i + 1]])
    n = len(all_c)
    ma5 = np.mean(all_c[-5:]) if n >= 5 else 0
    m5d = (c - ma5) / ma5 * 100 if ma5 > 0 else 0

    all_h = np.array([r[2] for r in rows[:d3i + 1]])
    all_l = np.array([r[3] for r in rows[:d3i + 1]])
    if d3i >= 10:
        trs = []
        for i in range(d3i - 9, d3i + 1):
            hh = all_h[i]; ll = all_l[i]; pc = rows[i-1][4] if i>0 else rows[i][6]
            trs.append(max(hh-ll, abs(hh-pc), abs(ll-pc)))
        atr10 = np.mean(trs)
    else:
        atr10 = h - l if h > l else 1

    be = (pre - l) / atr10 if atr10 > 0 else 0
    bu = (h - pre) / atr10 if atr10 > 0 else 0
    gd = 0
    if n >= 10:
        m5n = np.mean(all_c[-5:]); m10n = np.mean(all_c[-10:])
        m5p = np.mean(all_c[-6:-1]); m10p = np.mean(all_c[-11:-1])
        gd = 1 if (m5p <= m10p and m5n > m10n) else 0

    feat = np.array([pb, vc, m5d, be, bu, gd])

    print(f'\n── {nm}({code}) ──')
    print(f'  D-3({d3_311}): C={r3[4]:.2f} V={r3[5]/100:.0f}手= {d3v/1000000:.1f}万手')
    print(f'  今日({d2_311}): C={c:.2f} V={v/1000000:.1f}万手')
    print(f'  ATR10={atr10:.3f}  MA5={ma5:.2f}')
    print(f'  pb = ({r3[4]:.2f}-{c:.2f})/{r3[4]:.2f} = {pb:+.2f}%')
    print(f'  ★ vol_contract = ({d3v/10000:.0f}万-{v/10000:.0f}万)/{d3v/10000:.0f}万 = {vc:+.1f}%  {"(缩量)" if vc>0 else "(放量)"}')
    print(f'  ma5_dev = ({c:.2f}-{ma5:.2f})/{ma5:.2f} = {m5d:+.2f}%')
    print(f'  bear = ({pre:.2f}-{l:.2f})/{atr10:.3f} = {be:.2f}')
    print(f'  bull = ({h:.2f}-{pre:.2f})/{atr10:.3f} = {bu:.2f}')
    print(f'  golden = {gd}')

    candidates_raw.append((code, nm, feat, atr10, ma5, c, pb, vc))

# ═══════════ 评分 ═══════════
print(f'\n{"="*85}')
print(f'特征得分贡献 (标准化 × 权重)')
print(f'{"="*85}')

scored = []
for code, nm, feat, atr10, ma5, c, pb, vc in candidates_raw:
    Xs = (feat - mean) / (std + 1e-8)
    score = float(Xs @ w)
    contribs = Xs * w

    print(f'\n── {nm}({code}) ──')
    print(f'  {"特征":<14} {"原始值":>10} {"标准化":>10} {"权重":>10} {"贡献":>10}')
    print(f'  {"-"*54}')
    feat_short = ['pb_depth','vol_contract','ma5_dev','bear','bull','golden']
    for i, (fn, fv, wt) in enumerate(zip(feat_short, feat, w)):
        z = (fv - mean[i]) / std[i]
        cn = contribs[i]
        print(f'  {fn:<14} {fv:>+10.2f} {z:>+10.3f} {wt:>+10.4f} {cn:>+10.4f}')
    print(f'  {"总分→":<14} {score:>+10.4f}')

    scored.append((code, nm, score, pb, vc, feat[4], feat[5], feat[3], c, 0))

# ═══════════ 排名 ═══════════
scored.sort(key=lambda x: -x[2])
print(f'\n{"="*70}')
print(f'TPO3 最终排序 ({d2_311} 14:57尾盘买入)')
print(f'{"="*70}')
for i, (code, nm, sc, pb, vc, bull, gld, bear, c, _) in enumerate(scored):
    mark = ' ★★★ 尾盘买入' if i == 0 else ''
    print(f'  {i+1}. {nm}({code})  总分:{sc:+.4f}  '
          f'pb={pb:+.2f}% vol_ct={vc:+.1f}% bull={bull:.2f} bear={bear:.2f} golden={gld} C={c:.2f}{mark}')
