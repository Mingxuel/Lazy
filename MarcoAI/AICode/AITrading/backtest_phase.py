"""阶段感知选股回测：每天自动判断阶段 → 切换对应策略 → 模拟买入"""
import os

DATA_DIR = r'C:\Lazy\MarcoAI\AIData\1D'
MA_CROSS_FILE = r'C:\Lazy\MarcoAI\AIData\1D_MA_CROSS'
PANIC_FILE = r'C:\Lazy\MarcoAI\AIData\1D_PANIC_INDEX'

POOL = {
    '万华化学':'600309.SH','中国平安':'601318.SH','大华股份':'002236.SZ',
    '海康威视':'002415.SZ','浪潮信息':'000977.SZ','工业富联':'601138.SH',
    '中科曙光':'603019.SH','紫金矿业':'601899.SH','中兴通讯':'000063.SZ',
    '招商银行':'600036.SH','中国神华':'601088.SH','中国石油':'601857.SH',
    '长江电力':'600900.SH','五粮液':'000858.SZ','泸州老窖':'000568.SZ',
    '伊利股份':'600887.SH','恒瑞医药':'600276.SH','立讯精密':'002475.SZ',
    '洛阳钼业':'603993.SH','隆基绿能':'601012.SH',
}

def ls(fp):
    if not os.path.exists(fp): return []
    rows = []
    with open(fp, encoding='utf-8') as f:
        for line in f:
            p = line.strip().split('|')
            if len(p) < 7: continue
            try: rows.append((p[0], float(p[1]), float(p[2]), float(p[3]),
                              float(p[4]), float(p[5]), float(p[6])))
            except ValueError: continue
    return rows

def ma(vals, w):
    if len(vals) < w: return None
    return sum(vals[-w:]) / w

def s1(data, idx):
    for i in range(max(1, idx-5), idx):
        if i < 5: continue
        o, h, l, c, vol = data[i][1], data[i][2], data[i][3], data[i][4], data[i][5]
        pv = [data[j][5] for j in range(max(0, i-5), i)]
        av = sum(pv)/len(pv) if pv else vol
        body = abs(c-o); lw = min(o,c)-l; up = h-max(o,c)
        if vol > av*1.2 and lw > body and lw > up: return True
    return False

def s3(data, idx):
    if idx < 6: return False
    closes = [r[4] for r in data]
    m5t = ma(closes[:idx+1], 5); m5y = ma(closes[:idx], 5); m5d = ma(closes[:idx-1], 5)
    if None in (m5t, m5y, m5d): return False
    return m5y <= m5d and m5t > m5y

def s4(data, idx):
    if idx < 5: return False
    r0 = (data[idx][4]-data[idx-5][4])/data[idx-5][4]*100
    if idx < 6: return -2 < r0 < 5
    r1 = (data[idx-1][4]-data[idx-6][4])/data[idx-6][4]*100
    return (r0 > 0 and r1 < 0) or (-2 < r0 < 5)

def s5(data, idx):
    if idx < 4: return False
    return data[idx-4][4] < data[idx][4]

# Load
print("加载数据...")
ma_d = {}
with open(MA_CROSS_FILE, encoding='utf-8') as f:
    for line in f:
        p = line.strip().split('|')
        if len(p) < 3: continue
        try: ma_d[p[0]] = float(p[1])
        except ValueError: continue

panic_d = {}
with open(PANIC_FILE, encoding='utf-8') as f:
    for line in f:
        p = line.strip().split('|')
        if len(p) < 2: continue
        try: panic_d[p[0]] = float(p[1])
        except ValueError: continue

mdates = sorted(ma_d.keys())
pool_data = {}
for name, code in POOL.items():
    d = ls(os.path.join(DATA_DIR, code))
    if d: pool_data[name] = d

# Backtest
all_trades = []

for di, date in enumerate(mdates):
    if date < '20250501': continue
    panic = panic_d.get(date, 50)
    db = ma_d[date]
    if di >= 5: slope5 = db - ma_d[mdates[di-5]]
    else: slope5 = 0

    # Phase
    if panic > 60 and slope5 > 3: phase, min_sig = '冰点', 99
    elif panic > 60 and slope5 < -3: phase, min_sig = '回暖(恐慌退)', 3
    elif 20 <= panic < 60 and slope5 < -3: phase, min_sig = '回暖', 3
    elif panic < 20 and slope5 < -3: phase, min_sig = '高潮', 4
    elif panic < 20 and -3 <= slope5 <= 3: phase, min_sig = '分歧', 4
    elif panic < 20 and slope5 > 3: phase, min_sig = '退潮', 99
    elif 20 <= panic < 40 and slope5 > 3: phase, min_sig = '退潮/分歧', 4
    elif 40 <= panic < 60 and slope5 > 3: phase, min_sig = '退潮/分歧(恐慌升)', 4
    elif 20 <= panic < 60 and -3 <= slope5 <= 3: phase, min_sig = '分歧', 3
    elif panic >= 40 and -3 <= slope5 <= 3: phase, min_sig = '冰点边缘', 99
    else: phase, min_sig = '未知', 99

    candidates = []
    for name, data in pool_data.items():
        idx = None
        for i, r in enumerate(data):
            if r[0] == date: idx = i; break
        if idx is None or idx < 8: continue

        sc = 0; sg = []
        if s1(data, idx): sc += 1; sg.append('1')
        if s3(data, idx): sc += 1; sg.append('3')
        if s4(data, idx): sc += 1; sg.append('4')
        if s5(data, idx): sc += 1; sg.append('5')

        has34 = '3' in sg and '4' in sg
        has345 = has34 and '5' in sg

        nret = None
        if idx+1 < len(data): nret = (data[idx+1][4]-data[idx][4])/data[idx][4]*100

        candidates.append({'n':name,'sc':sc,'sg':sg,'has34':has34,'has345':has345,'nr':nret,'close':data[idx][4]})

    buys = []
    for c in candidates:
        if phase in ('回暖','回暖(恐慌退)'):
            if c['has34']: buys.append(c)
        elif phase == '高潮':
            if c['has345']: buys.append(c)
        elif phase == '分歧':
            if c['has34']: buys.append(c)
        elif phase in ('退潮/分歧','退潮/分歧(恐慌升)'):
            if c['has345'] and c['sc'] >= 4: buys.append(c)

    buys.sort(key=lambda x: (-x['has345'], -x['sc']))
    for b in buys[:2]:
        all_trades.append({'d':date,'n':b['n'],'sc':b['sc'],'sg':','.join(b['sg']),'nr':b['nr'],'ph':phase,'close':b['close']})

# Stats
valid = [t for t in all_trades if t['nr'] is not None]
print()
print('='*95)
print('阶段感知选股回测 (2025/05 ~ 2026/07, 14个月, 20只主板大票)')
print('='*95)

wins = sum(1 for t in valid if t['nr'] > 0)
avg = sum(t['nr'] for t in valid)/len(valid) if valid else 0
print(f"\n总计: {len(valid):4d} 笔 | 胜率 {wins/len(valid)*100:3.0f}% | 均值 {avg:+.2f}%")
print(f"最佳: {max(t['nr'] for t in valid):+.2f}% | 最差: {min(t['nr'] for t in valid):+.2f}%")

# By phase
print("\n按阶段统计:")
ps = {}
for t in valid:
    ph = t['ph']
    if ph not in ps: ps[ph] = []
    ps[ph].append(t['nr'])
for ph in sorted(ps):
    vals = ps[ph]
    w = sum(1 for x in vals if x>0)
    print(f"  {ph:20s}: {len(vals):4d}笔, 胜率{w/len(vals)*100:3.0f}%, 均值{sum(vals)/len(vals):+.2f}%")

# Monthly
print("\n按月收益:")
bm = {}
for t in valid:
    m = t['d'][:6]
    if m not in bm: bm[m] = []
    bm[m].append(t['nr'])
for m in sorted(bm):
    vals = bm[m]
    cum = sum(vals)
    w = sum(1 for x in vals if x>0)
    mark = '🔥' if cum>5 else ('✅' if cum>0 else '❌')
    print(f"  {m}: {len(vals)}笔, 胜率{w/len(vals)*100:.0f}%, 累计{cum:+.2f}% {mark}")

# Recent detail
print("\n\n最近三个月逐笔:")
print('='*95)
print(f"{'日期':>8s} | {'标的':>14s} | {'信号':>8s} | {'得分':>4s} | {'阶段':>18s} | {'收盘':>8s} | {'隔日':>8s}")
print('-'*95)
for t in sorted([t for t in valid if t['d']>'20260501'], key=lambda t: t['d']):
    arrow = '✅' if t['nr']>0 else '❌'
    print(f"{t['d']:>8s} | {t['n']:>14s} | {t['sg']:>8s} | {t['sc']:>2d}/4 | {t['ph']:>18s} | {t['close']:>8.2f} | {t['nr']:>+6.2f}% {arrow}")

print("\n\n策略规则:")
print("  回暖期 → ③+④核心信号")
print("  高潮期 → ③+④+⑤完美信号")
print("  分歧期 → ③+④")
print("  退潮/分歧 → ③+④+⑤(≥4分)")
print("  冰点/退潮 → 不开仓")
