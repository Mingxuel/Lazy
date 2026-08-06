# TPO31 明日买池评估 - 用今日(0805)收盘数据
import os, sys, numpy as np
import urllib.request
from collections import defaultdict

KDIR = r'C:\Lazy\李明学的大A\Data\1D'
SRC = r'C:\Lazy\李明学的大A\Data\Strategy'
FEATURES = ['pb_depth','vol_contract','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']

def load_kline(code):
    fp = os.path.join(KDIR, code)
    rows = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('\ufeff'): continue
            c = l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5]), float(c[9])))
    return rows, {r[0]: i for i, r in enumerate(rows)}

def fetch_quote(code_mkt):
    try:
        resp = urllib.request.urlopen(f'http://qt.gtimg.cn/q={code_mkt}', timeout=5).read().decode('gbk')
        p = resp.split('~')
        name, cur, op, hi, lo, vol, pre = p[1], float(p[3]), float(p[5]), float(p[33]), float(p[34]), int(p[6])*100, float(p[4])
        return name, cur, op, hi, lo, vol, pre
    except:
        return None

# === 加载交易日 ===
tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:
        l = l.strip()
        if l and l.isdigit() and len(l)==8:
            tds.append(l)
tds = sorted(tds)
di = {d: i for i, d in enumerate(tds)}

# === 加载所有训练样本 ===
samples_all = []
for fn in sorted(os.listdir(SRC)):
    if not fn.isdigit(): continue
    d1 = fn
    d1i = di.get(d1)
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
            d1i_k = date_idx.get(d1)
            d2i_k = date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1 = rows[d1i_k]
            bp = r1[6]
            sp_c = r1[4]
            if bp <= 0: continue
            r2 = rows[d2i_k]
            r3 = rows[d2i_k - 1] if d2i_k >= 1 else None
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
                    h = highs[i]; l = lows[i]
                    pc = rows[i-1][4] if i > 0 else rows[i][6]
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

samples_all.sort(key=lambda x: x[2])

X = np.array([[s[0].get(k, 0) for k in FEATURES] for s in samples_all])
y = np.array([(s[4] - s[3]) / s[3] * 100 for s in samples_all])

# walk-forward: 用 0805 之前的数据训练
mask = np.array([s[2] < '20260805' for s in samples_all])
X_tr = X[mask]; y_tr = y[mask]
mean = X_tr.mean(axis=0); std = X_tr.std(axis=0) + 1e-8
Xn = (X_tr - mean) / std
w = np.linalg.solve(Xn.T @ Xn + np.eye(Xn.shape[1]) * 2.0, Xn.T @ y_tr)

nm_cn = ['回踩深度', '量能收缩', 'MA5偏离', '空头砸多深', '多头还多强', '均线金叉']
print('=== 6特征权重 ===')
for nm, wt in zip(nm_cn, w):
    print(f'  {nm}: {wt:+.4f}')

# === TPO31 候选: 002015, 600588, 603337 ===
codes_info = [
    ('002015.SZ', 'sz002015'),
    ('600588.SH', 'sh600588'),
    ('603337.SH', 'sh603337'),
]

print()
print('=' * 70)
print('TPO31 明日买池 (D-2=20260805, D-1=20260806 尾盘买)')
print('=' * 70)

candidates = []
for code, code_mkt in codes_info:
    rows, date_idx = load_kline(code)
    if not rows:
        continue

    q = fetch_quote(code_mkt)
    if not q:
        print(f'{code}: 获取行情失败')
        continue
    name, cur, op, hi, lo, vol, pre = q

    # D-3 = 0804, D-2 = 0805(today)
    d3_i = date_idx.get('20260804')
    if d3_i is None:
        print(f'{code}: 无0804数据')
        continue

    r3 = rows[d3_i]
    hist_rows = rows[:d3_i + 1]

    # pb_depth = (D-3收盘 - D-2收盘) / D-3收盘
    pb_depth = (r3[4] - cur) / r3[4] * 100

    # vol_contract
    vol_contract = 1 if vol < r3[5] * 0.8 else 0

    # ma5_dev
    closes = [r[4] for r in hist_rows[-4:]] + [cur]
    ma5 = np.mean(closes)
    ma5_dev = (cur - ma5) / ma5 * 100

    # ATR10
    trs = []
    for i in range(max(0, len(hist_rows) - 9), len(hist_rows)):
        h = hist_rows[i][2]; l = hist_rows[i][3]
        pc_adj = hist_rows[i-1][4] if i > 0 else hist_rows[i][6]
        trs.append(max(h - l, abs(h - pc_adj), abs(l - pc_adj)))
    trs.append(max(hi - lo, abs(hi - pre), abs(lo - pre)))
    atr10 = np.mean(trs) if trs else 1

    pc_vs_low_atr = (pre - lo) / atr10
    high_vs_pc_atr = (hi - pre) / atr10

    # ma_golden
    ma_golden = 0
    if len(hist_rows) >= 10:
        c_all = [r[4] for r in hist_rows[-9:]] + [cur]
        ma5_arr = np.mean(c_all[-5:]); ma10_arr = np.mean(c_all[-10:])
        c_prev = [r[4] for r in hist_rows[-10:-1]] + [pre]
        ma5p = np.mean(c_prev[-5:]); ma10p = np.mean(c_prev[-10:])
        ma_golden = 1 if (ma5p <= ma10p and ma5_arr > ma10_arr) else 0

    f = {
        'pb_depth': pb_depth, 'vol_contract': vol_contract, 'ma5_dev': ma5_dev,
        'pc_vs_low_atr': pc_vs_low_atr, 'high_vs_pc_atr': high_vs_pc_atr,
        'ma_golden': ma_golden
    }

    Xt = np.array([[f.get(k, 0) for k in FEATURES]])
    Xt = (Xt - mean) / std
    pred = Xt @ w

    # 最近走势
    recent = []
    for j in range(max(0, len(hist_rows) - 4), len(hist_rows)):
        rr = hist_rows[j]; rchg = (rr[4] - rr[6]) / rr[6] * 100
        recent.append(f"{rr[0][4:]}: C{rr[4]:.2f}({rchg:+.2f}%)")

    print(f'\n--- {name}({code}) ---')
    print(f'  今日(0805): O={op:.2f} H={hi:.2f} L={lo:.2f} C={cur:.2f} 涨跌:{(cur-pre)/pre*100:+.2f}% V={vol}')
    r4 = rows[date_idx.get('20260803')] if '20260803' in date_idx else None
    print(f'  311链: D-4(0803)={r4[4] if r4 else "?"} → D-3(0804) C={r3[4]:.2f} V={r3[5]:.0f} → D-2(0805) C={cur:.2f}')
    print(f'  pb={pb_depth:+.2f} vol_ct={vol_contract} ma5_dev={ma5_dev:+.2f} bear={pc_vs_low_atr:.2f} bull={high_vs_pc_atr:.2f} golden={ma_golden}')
    print(f'  ★ 评分: {pred[0]:+.2f}')
    print(f'  {" | ".join(recent)} | 0805: C{cur:.2f}({(cur-pre)/pre*100:+.2f}%)')

    candidates.append({
        'code': code, 'name': name, 'pred': pred[0],
        'pb': pb_depth, 'bull': high_vs_pc_atr, 'bear': pc_vs_low_atr,
        'cur': cur, 'chg': (cur-pre)/pre*100
    })

print()
print('=' * 60)
print('TPO31 明日(0806)尾盘买入排序')
candidates.sort(key=lambda x: x['pred'], reverse=True)
for i, c in enumerate(candidates):
    tag = ' ★★★ 最强' if i == 0 else ''
    print(f'  {i+1}. {c["name"]}({c["code"]}) 评分:{c["pred"]:+.2f} pb={c["pb"]:+.2f} bull={c["bull"]:.2f} 今日{c["chg"]:+.2f}%{tag}')
