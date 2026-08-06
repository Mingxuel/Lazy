"""
TPO3 按策略分析
框架：311结构(D-4涨停+D-3放量) → 6特征Walk-Forward岭回归评分 → D-2尾盘买
今天0805=D-2日，用0805收盘数据做6特征评估
"""
import os, numpy as np
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
            if len(c) < 10 or not c[0].isdigit(): continue
            rows.append((c[0], float(c[1]), float(c[2]), float(c[3]),
                         float(c[4]), float(c[5]), float(c[9])))
    return rows, {r[0]: i for i, r in enumerate(rows)}

def fetch_quote(code_mkt):
    try:
        resp = urllib.request.urlopen(f'http://qt.gtimg.cn/q={code_mkt}', timeout=5).read().decode('gbk')
        p = resp.split('~')
        return (p[1], float(p[3]), float(p[5]), float(p[33]),
                float(p[34]), int(p[6])*100, float(p[4]))  # name,cur,op,hi,lo,vol,pre
    except:
        return None

# === 交易日列表 ===
tds = []
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:
        l = l.strip()
        if l and l.isdigit() and len(l) == 8:
            tds.append(l)
tds = sorted(tds)
di_td = {d: i for i, d in enumerate(tds)}

# === 加载策略文件产出样本 (D-3之前的全部历史) ===
samples_all = []
for fn in sorted(os.listdir(SRC)):
    if not fn.isdigit(): continue
    d1 = fn  # D-1日(买入日次日/卖出日)
    d1i = di_td.get(d1)
    if d1i is None or d1i < 3: continue
    d2 = tds[d1i - 1]  # D-2日(买入日)

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

            r1 = rows[d1i_k]  # D-1
            bp = r1[6]         # 买入价(开盘价)
            sp_c = r1[4]       # 卖出价(收盘价)
            if bp <= 0: continue

            r2 = rows[d2i_k]   # D-2
            r3 = rows[d2i_k - 1] if d2i_k >= 1 else None  # D-3
            if r3 is None: continue

            cls = np.array([r[4] for r in rows[:d2i_k + 1]])
            highs = np.array([r[2] for r in rows[:d2i_k + 1]])
            lows = np.array([r[3] for r in rows[:d2i_k + 1]])
            n = len(cls)

            # 6特征 (基于D-2日数据)
            f = {}

            # 1. pb_depth: (D-3收盘 - D-2收盘)/D-3收盘 → 回踩深度
            f['pb_depth'] = (r3[4] - r2[4]) / r3[4] * 100 if r3[4] > 0 else 0

            # 2. vol_contract: D-2量能收缩(相对D-3缩量20%以上)
            f['vol_contract'] = 1 if r2[5] < r3[5] * 0.8 else 0

            # 3. ma5_dev: D-2收盘偏离MA5
            f['ma5_dev'] = (r2[4] - np.mean(cls[-5:])) / np.mean(cls[-5:]) * 100 if n >= 5 else 0

            # ATR10
            if n >= 10:
                trs = []
                for i in range(d2i_k - 9, d2i_k + 1):
                    h, l = highs[i], lows[i]
                    pc = rows[i-1][4] if i > 0 else rows[i][6]
                    trs.append(max(h - l, abs(h - pc), abs(l - pc)))
                atr10 = np.mean(trs) if trs else 1
            else:
                atr10 = r2[2] - r2[3] if r2[2] > r2[3] else 1

            # 4. pc_vs_low_atr: 空头砸多深 = (前收-最低)/ATR10
            f['pc_vs_low_atr'] = (r2[6] - r2[3]) / atr10 if atr10 > 0 else 0

            # 5. high_vs_pc_atr: 多头还多强 = (最高-前收)/ATR10
            f['high_vs_pc_atr'] = (r2[2] - r2[6]) / atr10 if atr10 > 0 else 0

            # 6. ma_golden: MA5当日上穿MA10
            f['ma_golden'] = 0
            if d2i_k >= 10:
                c_arr = np.array([r[4] for r in rows[:d2i_k + 1]])
                ma5 = np.mean(c_arr[-5:])
                ma10 = np.mean(c_arr[-10:])
                ma5p = np.mean(c_arr[-6:-1])
                ma10p = np.mean(c_arr[-11:-1])
                f['ma_golden'] = 1 if (ma5p <= ma10p and ma5 > ma10) else 0

            samples_all.append((f, code, d1, bp, sp_c, name))

samples_all.sort(key=lambda x: x[2])

# Walk-Forward: 只用0805之前的样本训练
X = np.array([[s[0].get(k, 0) for k in FEATURES] for s in samples_all])
y = np.array([(s[4] - s[3]) / s[3] * 100 for s in samples_all])
mask = np.array([s[2] < '20260805' for s in samples_all])
X_tr, y_tr = X[mask], y[mask]
mean, std = X_tr.mean(axis=0), X_tr.std(axis=0) + 1e-8
Xn = (X_tr - mean) / std
w = np.linalg.solve(Xn.T @ Xn + np.eye(Xn.shape[1]) * 2.0, Xn.T @ y_tr)

print('=== 6特征权重 (Walk-Forward 截止0804) ===')
nm_cn = ['回踩深度','量能收缩','MA5偏离','空头砸多深','多头还多强','均线金叉']
for nm, wt in zip(nm_cn, w):
    bar = '█' * max(0, int(abs(wt) * 10))
    print(f'  {nm}: {wt:+.4f}  {"+" if wt>0 else "-"}{bar}')

# === 计算 D3→D2→D1 的锚定框架 ===
# TPO3 的日期框架: D-4(0801)=涨停, D-3(0804)=放量, D-2(0805今天)=回踩买入, D-1(0806明天)=卖出
print()
print('=' * 70)
print('TPO3 时间框架: D-4(0731涨停) → D-3(0804放量) → D-2(0805回踩买入) → D-1(0806卖出)')
print('=' * 70)

codes_info = [
    ('601611.SH', 'sh601611'),
    ('601865.SH', 'sh601865'),
    ('603156.SH', 'sh603156'),
]

candidates = []
for code, code_mkt in codes_info:
    rows, date_idx = load_kline(code)
    if not rows:
        print(f'{code}: 无日线数据'); continue

    q = fetch_quote(code_mkt)
    if not q:
        print(f'{code}: 获取行情失败'); continue
    name, cur, op, hi, lo, vol, pre = q

    # 验证311链: D-4(0803)涨停 D-3(0804)放量 D-2(0805)=今天
    d4_i = date_idx.get('20260803')
    d3_i = date_idx.get('20260804')
    if d4_i is None or d3_i is None:
        print(f'{code}: 缺少0803/0804数据'); continue

    r4 = rows[d4_i]  # D-4
    r3 = rows[d3_i]  # D-3
    d4_chg = (r4[4] - r4[6]) / r4[6] * 100  # D-4涨幅

    # === D-2(今天) 6特征 ===
    # pb_depth: (D-3收盘 - D-2收盘)/D-3收盘
    pb_depth = (r3[4] - cur) / r3[4] * 100

    # vol_contract: D-2量 vs D-3量
    vol_contract = 1 if vol < r3[5] * 0.8 else 0

    # D-2之前的历史数据
    hist = rows[:d3_i + 1]
    closes_hist = [r[4] for r in hist]

    # ma5_dev: (D-2收盘 - MA5)/MA5, MA5用hist最后4天+今天
    closes_5 = closes_hist[-4:] + [cur]
    ma5 = np.mean(closes_5)
    ma5_dev = (cur - ma5) / ma5 * 100

    # ATR10: hist最后9天 + 今天
    highs_hist = [r[2] for r in hist]
    lows_hist = [r[3] for r in hist]
    trs = []
    for i in range(max(0, len(hist) - 9), len(hist)):
        h, l = highs_hist[i], lows_hist[i]
        pc = hist[i-1][4] if i > 0 else hist[i][6]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    trs.append(max(hi - lo, abs(hi - pre), abs(lo - pre)))
    atr10 = np.mean(trs) if trs else 1

    pc_vs_low_atr = (pre - lo) / atr10
    high_vs_pc_atr = (hi - pre) / atr10

    # ma_golden: 今天MA5上穿MA10
    ma_golden = 0
    if len(hist) >= 10:
        c_all = [r[4] for r in hist[-9:]] + [cur]
        ma5_arr = np.mean(c_all[-5:])
        ma10_arr = np.mean(c_all[-10:])
        c_prev = [r[4] for r in hist[-10:-1]] + [pre]
        ma5p = np.mean(c_prev[-5:])
        ma10p = np.mean(c_prev[-10:])
        ma_golden = 1 if (ma5p <= ma10p and ma5_arr > ma10_arr) else 0

    f = {
        'pb_depth': pb_depth, 'vol_contract': vol_contract,
        'ma5_dev': ma5_dev, 'pc_vs_low_atr': pc_vs_low_atr,
        'high_vs_pc_atr': high_vs_pc_atr, 'ma_golden': ma_golden
    }

    Xt = np.array([[f.get(k, 0) for k in FEATURES]])
    Xt_norm = (Xt - mean) / std
    score = float((Xt_norm @ w)[0])

    # 最近K线
    recent = []
    for j in range(max(0, len(hist) - 4), len(hist)):
        rr = hist[j]
        rchg = (rr[4] - rr[6]) / rr[6] * 100
        recent.append(f"{rr[0][4:]}:C{rr[4]:.2f}({rchg:+.2f}%)")

    print(f'\n{"─" * 60}')
    print(f'{name}({code})')
    print(f'  D-4(0803): C={r4[4]:.2f} 涨跌={d4_chg:+.2f}% {"✓涨停" if d4_chg > 9.5 else ""}')
    print(f'  D-3(0804): C={r3[4]:.2f} V={r3[5]:.0f} {"✓放量" if r3[5] > 100000 else ""}')
    print(f'  D-2(0805): O={op:.2f} H={hi:.2f} L={lo:.2f} C={cur:.2f} 涨跌={(cur-pre)/pre*100:+.2f}% V={vol}')
    print(f'  6特征: pb={pb_depth:+.2f} vol_ct={vol_contract} ma5_dev={ma5_dev:+.2f} bear={pc_vs_low_atr:.2f} bull={high_vs_pc_atr:.2f} golden={ma_golden}')
    print(f'  ★ 加权得分: {score:+.4f}')

    # 分解贡献
    contribs = []
    for k, v, wt in zip(FEATURES, list(Xt_norm[0]), list(w)):
        contribs.append(f'{k}={v*wt:+.4f}')
    print(f'  贡献分解: {" | ".join(contribs)}')

    print(f'  走势: {" → ".join(recent)} → 0805:C{cur:.2f}({(cur-pre)/pre*100:+.2f}%)')

    candidates.append({
        'code': code, 'name': name, 'score': score,
        'pb': pb_depth, 'bull': high_vs_pc_atr, 'bear': pc_vs_low_atr,
        'cur': cur, 'chg': (cur-pre)/pre*100, 'vol_ct': vol_contract,
        'ma5_dev': ma5_dev, 'golden': ma_golden
    })

print()
print('=' * 60)
print('TPO3 最终排序 — D-2(0805)尾盘买入决策')
candidates.sort(key=lambda x: x['score'], reverse=True)
for i, c in enumerate(candidates):
    tag = ' ★★★ 今日尾盘买入' if i == 0 else (' ◇ 次优选' if i == 1 else '  不推荐')
    print(f'  {i+1}. {c["name"]}({c["code"]}) 得分:{c["score"]:+.4f} pb={c["pb"]:+.2f} bull={c["bull"]:.2f} 今日:{c["chg"]:+.2f}%{tag}')

print(f'\n{"★" * 40}')
print(f'买入决策: {candidates[0]["name"]}({candidates[0]["code"]})')
print(f'买入价参考: {candidates[0]["cur"]:.2f}')
print(f'止损价: {candidates[0]["cur"]*0.94:.2f}')
print(f'移动止盈触发: {candidates[0]["cur"]*1.03:.2f}')
print(f'{"★" * 40}')
