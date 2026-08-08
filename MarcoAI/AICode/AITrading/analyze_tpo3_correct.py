# -*- coding: utf-8 -*-
"""TPO3 正确分析: D-4=0804涨停, D-3=0805放量, D-2=0807今日买入
   特征计算用 D-3=0806 (交易日序列的D-2前一天)"""
import os, sys, numpy as np, urllib.request
from collections import defaultdict

KDIR = r'C:\Lazy\李明学的大A\Data\1D'
SRC  = r'C:\Lazy\李明学的大A\Data\Strategy'
FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
cn_names = ['回踩深度','量能收缩','MA5偏离','空头砸多深','多头还多强','均线金叉']

# ══════════════════ 1. 交易日 ════════════════════════════════
tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds = sorted(tds); di = {d:i for i,d in enumerate(tds)}

today = '20260807'
today_i = di[today]

d4_311 = tds[today_i - 2]  # D-4: 0805 (最近交易日前2)
d3_311 = tds[today_i - 1]  # D-3: 0806 (紧邻交易日)
d2_311 = today              # 0807
print(f'311结构: D-4={d4_311}(涨停) → D-3={d3_311}(放量) → D-2={d2_311}(今日买入)')

# ══════════════════ 2. K线读取 ════════════════════════════════
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

# ══════════════════ 3. Walk-Forward 训练 ══════════════════════
print(f'\n{"="*60}')
print(f'Walk-Forward 训练 (截止 {d3_311})')
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
            f['vol_contract'] = 1 if (r3 and r2[5] < r3[5] * 0.8) else 0
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

print(f'训练样本: {mask.sum()} 条\n')
print(f'=== 6特征权重 ===')
for cn, wt in zip(cn_names, w):
    print(f'  {cn:<10} {wt:>+8.4f}')

# ══════════════════ 4. 腾讯行情 ════════════════════════════════
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

# ══════════════════ 5. 311结构 ════════════════════════════════
print(f'\n{"="*70}')
print(f'311 结构验证: D-4={d4_311}涨停 + D-3={d3_311}放量 → TPO3买池')
print(f'{"="*70}')
for code in codes:
    rows, idx = load_kline(code)
    d4i = idx.get(d4_311); d3i = idx.get(d3_311)
    if d4i is None or d3i is None:
        print(f'  {names_cn[code]}: 数据缺失'); continue
    r4 = rows[d4i]; r3 = rows[d3i]
    lu4 = round(r4[6]*1.10, 2); is_lim = r4[4] >= lu4*0.995
    ve = r3[5] > r4[5]
    ok = '✅' if (is_lim and ve) else '❌'
    print(f'  {ok} {names_cn[code]}({code}) '
          f'D-4 C={r4[4]:.2f}(涨停{lu4:.2f}) V={r4[5]/100:.0f}手 '
          f'D-3 C={r3[4]:.2f} V={r3[5]/100:.0f}手 涨停={is_lim} 放量={ve}')

# ══════════════════ 6. 行情 ════════════════════════════════════
print(f'\n{"="*70}')
print(f'今日 D-2={d2_311} 收盘行情')
print(f'{"="*70}')
print(f'{"代码":<14} {"名称":<8} {"昨收":>8} {"今开":>8} {"最高":>8} {"最低":>8} {"收盘":>8} {"涨跌":>7} {"量(万手)":>10}')
print('-'*70)
for code in codes:
    if code not in live: continue
    nm,c,o,h,l,v,pre = live[code]; chg = (c-pre)/pre*100
    print(f'  {code:<14} {nm:<8} {pre:>8.2f} {o:>8.2f} {h:>8.2f} {l:>8.2f} {c:>8.2f} {chg:>+6.2f}% {v/1000000:>10.1f}')

# ══════════════════ 7. 特征 & 评分 ════════════════════════════
print(f'\n{"="*70}')
print(f'特征计算 (D-3={d3_311}日线K线 + 今日腾讯行情)')
print(f'{"="*70}')

candidates_raw = []
for code in codes:
    if code not in live: continue
    rows, idx = load_kline(code)
    d3i = idx.get(d3_311)
    if d3i is None: continue

    nm,c,o,h,l,v,pre = live[code]
    r3 = rows[d3i]    # D-3 日线

    # ── pb_depth ──
    pb = (r3[4] - c) / r3[4] * 100

    # ── vol_contract: today(0807, 腾讯API) vs D-3(0806, 1D文件 ×100→股) ──
    d3v = r3[5] * 100
    vc = 1 if v > 0 and d3v > 0 and v < d3v * 0.8 else 0
    vr = v / d3v if d3v > 0 else 0

    # ── MA5 ──
    all_c = np.array([r[4] for r in rows[:d3i + 1]])
    n = len(all_c)
    ma5 = np.mean(all_c[-5:]) if n >= 5 else 0
    m5d = (c - ma5) / ma5 * 100 if ma5 > 0 else 0

    # ── ATR10 ──
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

    # ── bear / bull ──
    be = (pre - l) / atr10 if atr10 > 0 else 0
    bu = (h - pre) / atr10 if atr10 > 0 else 0

    # ── golden ──
    gd = 0
    if n >= 10:
        m5n = np.mean(all_c[-5:]); m10n = np.mean(all_c[-10:])
        m5p = np.mean(all_c[-6:-1]); m10p = np.mean(all_c[-11:-1])
        gd = 1 if (m5p <= m10p and m5n > m10n) else 0

    feat = np.array([pb, vc, m5d, be, bu, gd])

    print(f'\n── {nm}({code}) ──')
    print(f'  D-3({d3_311}): C={r3[4]:.2f} V={r3[5]/100:.0f}手')
    print(f'  今日({d2_311}): C={c:.2f} V={v/100:.0f}手')
    print(f'  ATR10={atr10:.3f}  MA5={ma5:.2f}')
    print(f'  pb=({r3[4]:.2f}-{c:.2f})/{r3[4]:.2f} = {pb:+.2f}%')
    print(f'  vol_ct: {v/100:.0f}手 vs {d3v/100:.0f}手×0.8={d3v*0.8/100:.0f}手 → {"缩量" if vc else "放量"}({vr:.2f}x)')
    print(f'  ma5_dev=({c:.2f}-{ma5:.2f})/{ma5:.2f} = {m5d:+.2f}%')
    print(f'  bear=({pre:.2f}-{l:.2f})/{atr10:.3f} = {be:.2f}')
    print(f'  bull=({h:.2f}-{pre:.2f})/{atr10:.3f} = {bu:.2f}')
    print(f'  golden={gd}')

    candidates_raw.append((code, nm, feat, atr10, ma5, c))

# ══════════════════ 8. 评分贡献 ════════════════════════════════
print(f'\n{"="*80}')
print('特征得分贡献 (标准化 × 权重)')
print(f'{"="*80}')

scored = []
for code, nm, feat, atr10, ma5, c in candidates_raw:
    Xs = (feat - mean) / (std + 1e-8)
    score = float(Xs @ w)
    contribs = Xs * w

    print(f'\n── {nm}({code}) ──')
    print(f'  {"特征":<14} {"原始值":>8} {"标准化":>8} {"权重":>8} {"贡献":>8}')
    feat_short = ['pb_depth','vol_contract','ma5_dev','bear','bull','golden']
    for i, (fn, fv, wt) in enumerate(zip(feat_short, feat, w)):
        z = (fv - mean[i]) / std[i]
        cn = contribs[i]
        print(f'  {fn:<14} {fv:>+8.3f} {z:>+8.3f} {wt:>+8.4f} {cn:>+8.4f}')
    print(f'  {"总分→":<14} {score:>+8.4f}')

    scored.append((code, nm, score, feat[0], feat[1], feat[4], feat[3], feat[5], feat[2], c, atr10, ma5))

# ══════════════════ 9. 最终排名 ════════════════════════════════
scored.sort(key=lambda x: -x[2])
print(f'\n{"="*70}')
print(f'TPO3 最终排序 (D-2={d2_311}, 14:57尾盘买入)')
print(f'{"="*70}')
for i, (code, nm, sc, pb, vc, bull, bear, gld, m5d, c, atr, ma5) in enumerate(scored):
    mark = ' ★★★ 尾盘买入' if i == 0 else ''
    print(f'  {i+1}. {nm}({code})  总分:{sc:+.4f}  '
          f'pb={pb:+.2f} vol_ct={vc} bull={bull:.2f} bear={bear:.2f} '
          f'golden={gld} C={c:.2f}{mark}')
