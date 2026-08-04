import os
from collections import defaultdict

BASE = r'C:\Lazy\MarcoAI\AIData'
SIGNAL_DIR = os.path.join(BASE, 'TARGET', '311')
KLINE_DIR = os.path.join(BASE, '1D')
DATES_FILE = os.path.join(BASE, 'TRADING_DATES')

dates = []
with open(DATES_FILE) as f:
    for l in f:
        d = l.strip()
        if d: dates.append(d)
date_idx = {d: i for i, d in enumerate(dates)}

COMM = 0.00025; COMM_MIN = 5.0; STAMP = 0.0005; TRANS = 0.00001
CAPITAL = 1_000_000

signal_days = {}
need_kline = defaultdict(set)
for fname in sorted(os.listdir(SIGNAL_DIR)):
    fp = os.path.join(SIGNAL_DIR, fname)
    if os.path.getsize(fp) <= 3: continue
    with open(fp) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines: continue
    sd = fname; idx = date_idx.get(sd, -1)
    if idx < 2: continue
    d2, d3 = dates[idx-2], dates[idx-3]
    entries = []
    for line in lines:
        p = line.split('|')
        if len(p) < 8: continue
        entries.append({'code': p[0], 'd0_close': float(p[4]), 'd0_vol': float(p[5]),
                        'd0_amt': float(p[6]), 'd1_close': float(p[7])})
        need_kline[p[0]].add((d2,'close'))
        need_kline[p[0]].add((d3,'close'))
        need_kline[p[0]].add((d3,'volume'))
    signal_days[sd] = (entries, d2, d3)

kline = defaultdict(dict)
for code, qs in need_kline.items():
    kp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(kp): continue
    dn = {q[0] for q in qs}
    with open(kp) as kf:
        for line in kf:
            p = line.strip().split('|')
            if len(p) < 6: continue
            if p[0] in dn: kline[code][p[0]] = {'close': float(p[4]), 'volume': float(p[5])}

def calc_ret(buy, sell):
    shares = int(CAPITAL/2/buy/100)*100
    if shares == 0: shares = 100
    cost = shares*buy
    bf = max(cost*COMM, COMM_MIN) + cost*TRANS
    tb = cost + bf
    rev = shares*sell
    sf = max(rev*COMM, COMM_MIN) + rev*TRANS + rev*STAMP
    return (rev-sf - tb)/tb*100

for sd, (entries, d2, d3) in signal_days.items():
    for e in entries:
        code = e['code']
        d2d = kline.get(code,{}).get(d2,{})
        d3d = kline.get(code,{}).get(d3,{})
        e['d2_close'] = d2d.get('close')
        e['d3_close'] = d3d.get('close')
        e['d3_vol'] = d3d.get('volume')
        if e.get('d2_close') and e.get('d3_close') and e['d2_close']>0:
            e['pullback'] = (e['d3_close']-e['d2_close'])/e['d3_close']*100
        else: e['pullback'] = None
        if e.get('d2_close') and e['d2_close']>0:
            e['d0vsd2'] = (e['d0_close']-e['d2_close'])/e['d2_close']*100
        else: e['d0vsd2'] = None
        if e.get('d3_vol') and e['d3_vol']>0:
            e['vol_ratio'] = e['d0_vol']/e['d3_vol']
        else: e['vol_ratio'] = None

def test(name, key_func, reverse=True):
    monthly = defaultdict(lambda: {'days':0,'sum':0.0,'win':0,'lose':0})
    for sd, (entries, d2, d3) in sorted(signal_days.items()):
        valid = [e for e in entries if e.get('d2_close') and e.get('d1_close') and e['d2_close']>0 and e['d1_close']>0]
        if not valid: continue
        scored = [(key_func(e), e) for e in valid if key_func(e) is not None]
        if not scored: continue
        scored.sort(key=lambda x:x[0], reverse=reverse)
        top = [s[1] for s in scored[:2]]
        tr = sum(calc_ret(e['d2_close'], e['d1_close']) for e in top)/len(top)
        m = sd[:6]
        monthly[m]['days']+=1; monthly[m]['sum']+=tr
        if tr>0: monthly[m]['win']+=1
        elif tr<0: monthly[m]['lose']+=1
    cum=1.0; peak=1.0; dd=0.0; wins=0; days=0
    for m in sorted(monthly):
        days+=monthly[m]['days']; wins+=monthly[m]['win']
        cum*=(1+monthly[m]['sum']/100)
        if cum>peak: peak=cum
        d=(cum-peak)/peak*100
        if d<dd: dd=d
    wr=wins/days*100 if days else 0
    return {'name':name,'nav':cum,'total':(cum-1)*100,'dd':dd,'wr':wr}

strategies = [
    ('A.D0vsD2涨幅', lambda e: e.get('d0vsd2'), True),
    ('B.量比', lambda e: e.get('vol_ratio'), True),
    ('C.回踩最小', lambda e: -e.get('pullback',999), True),
    ('D.成交额', lambda e: e['d0_amt'], True),
    ('E.D0涨幅', lambda e: (e['d0_close']-e['d1_close'])/e['d1_close']*100, True),
    ('F.D0vsD2+量比', lambda e: (e.get('d0vsd2') or 0)+(e.get('vol_ratio') or 0), True),
    ('G.D0vsD2*量比', lambda e: (e.get('d0vsd2') or 0)*(e.get('vol_ratio') or 1), True),
]

print(f"{'策略':<25} {'收益%':>10} {'净值':>8} {'回撤%':>7} {'胜率%':>7}")
print("-"*65)
results = []
for name, func, rev in strategies:
    r = test(name, func, rev)
    results.append(r)
    print(f"{r['name']:<25} {r['total']:>10.1f} {r['nav']:>8.2f} {r['dd']:>7.1f} {r['wr']:>7.1f}")

best = max(results, key=lambda x: x['total'])
print(f"\n最佳: {best['name']} — 净值{best['nav']:.1f}倍, 回撤{abs(best['dd']):.1f}%")
