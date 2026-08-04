import os
from collections import defaultdict

BASE = r'C:\Lazy\MarcoAI\AIData'
KLINE_DIR = os.path.join(BASE, '1D')
DATES_FILE = os.path.join(BASE, 'TRADING_DATES')
SIGNAL_DIR = os.path.join(BASE, 'TARGET', '311')

dates = []
with open(DATES_FILE) as f:
    for l in f:
        d = l.strip()
        if d: dates.append(d)
date_idx = {d: i for i, d in enumerate(dates)}

# 读取信号
signal_days = {}
for fname in sorted(os.listdir(SIGNAL_DIR)):
    fp = os.path.join(SIGNAL_DIR, fname)
    if os.path.getsize(fp) <= 3: continue
    with open(fp) as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines: continue
    sd = fname; idx = date_idx.get(sd, -1)
    if idx < 4: continue
    entries = [l.split('|')[0] for l in lines if '|' in l]
    if entries:
        signal_days[sd] = (entries, dates[idx-2], dates[idx-3], dates[idx-4])

# 加载 K线 D-4, D-3, D-2, D-1
need_kline = defaultdict(set)
for sd, (codes, d2, d3, d4) in signal_days.items():
    d1 = dates[date_idx[sd]-1]
    for code in codes:
        for d in [d2, d3, d4, d1]:
            need_kline[code].add(d)

kline = defaultdict(dict)
for code, tds in need_kline.items():
    kp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(kp): continue
    with open(kp) as kf:
        for line in kf:
            p = line.strip().split('|')
            if len(p) < 6: continue
            if p[0] in tds:
                kline[code][p[0]] = {'close': float(p[4]), 'volume': float(p[5]), 'amount': float(p[6])}

COMM = 0.00025; COMM_MIN = 5.0; STAMP = 0.0005; TRANS = 0.00001
CAPITAL = 1_000_000

def calc_ret(buy, sell):
    shares = int(CAPITAL/2/buy/100)*100
    if shares == 0: shares = 100
    cost = shares*buy
    bf = max(cost*COMM, COMM_MIN) + cost*TRANS
    tb = cost + bf
    rev = shares*sell
    sf = max(rev*COMM, COMM_MIN) + rev*TRANS + rev*STAMP
    return (rev-sf - tb)/tb*100

trades = []
for sd, (codes, d2, d3, d4) in sorted(signal_days.items()):
    d1 = dates[date_idx[sd]-1]
    for code in codes:
        kd2 = kline.get(code,{}).get(d2,{})
        kd3 = kline.get(code,{}).get(d3,{})
        kd4 = kline.get(code,{}).get(d4,{})
        kd1 = kline.get(code,{}).get(d1,{})
        buy_p = kd2.get('close')
        sell_p = kd1.get('close')
        if not buy_p or not sell_p or buy_p==0: continue
        
        ret = calc_ret(buy_p, sell_p)
        d2c = kd2.get('close',0); d2v = kd2.get('volume',0); d2a = kd2.get('amount',0)
        d3c = kd3.get('close',0); d3v = kd3.get('volume',0)
        d4c = kd4.get('close',0)
        if d2c==0 or d3c==0 or d4c==0: continue
        
        pullback = (d3c-d2c)/d3c*100
        vol_decay = d2v/d3v if d3v>0 else 1.0
        gain_top = (d2c-d4c)/d4c*100
        
        trades.append({
            'sd': sd, 'code': code, 'ret': ret, 'buy': buy_p, 'sell': sell_p,
            'pullback': pullback, 'vol_decay': vol_decay,
            'gain_top': gain_top, 'amount': d2a
        })

print(f'总交易: {len(trades)} 笔\n')

def test_rank(name, key_func, reverse=True):
    monthly = defaultdict(lambda: {'sum':0.0,'days':0,'win':0,'lose':0})
    day_groups = defaultdict(list)
    for t in trades:
        day_groups[t['sd']].append(t)
    
    for sd, group in sorted(day_groups.items()):
        scored = [(key_func(t), t) for t in group if key_func(t) is not None]
        if not scored: continue
        scored.sort(key=lambda x:x[0], reverse=reverse)
        top = [s[1] for s in scored[:2]]
        tr = sum(t['ret'] for t in top)/len(top)
        m = sd[:6]
        monthly[m]['sum']+=tr; monthly[m]['days']+=1
        if tr>0: monthly[m]['win']+=1
        else: monthly[m]['lose']+=1
    
    cum=1.0; peak=1.0; dd=0.0; w=0; d=0
    for m in sorted(monthly):
        d+=monthly[m]['days']; w+=monthly[m]['win']
        cum*=(1+monthly[m]['sum']/100)
        if cum>peak: peak=cum
        _dd=(cum-peak)/peak*100
        if _dd<dd: dd=_dd
    wr=w/d*100 if d else 0
    return {'name':name,'nav':cum,'total':(cum-1)*100,'dd':dd,'wr':wr}

# D-2时刻已知的排名指标
tests = [
    ('回踩幅度最小(最强势)', lambda t: -t['pullback']),
    ('回踩幅度最大(超跌反弹)', lambda t: t['pullback']),
    ('缩量比最小(缩量最明显)', lambda t: -t['vol_decay']),
    ('缩量比最大(放量维持)', lambda t: t['vol_decay']),
    ('涨停以来涨幅最小(未透支)', lambda t: -t['gain_top']),
    ('涨停以来涨幅最大(强势)', lambda t: t['gain_top']),
    ('成交额最大(流动性好)', lambda t: t['amount']),
    ('成交额最小(小票弹性)', lambda t: -t['amount']),
    ('回踩最小+缩量明显', lambda t: -t['pullback']*10 - t['vol_decay']),
    ('回踩最小+成交额大', lambda t: -t['pullback']*100 + t['amount']*1e-7),
    ('随机(对照基准)', lambda t: 0.0),
]

print(f'  {"策略":<32} {"收益%":>9} {"净值":>7} {"回撤%":>7} {"胜率%":>6}')
print('  ' + '-'*68)
results = []
for name, func in tests:
    r = test_rank(name, func)
    results.append(r)
    print(f'  {r["name"]:<32} {r["total"]:>9.1f} {r["nav"]:>7.2f} {r["dd"]:>7.1f} {r["wr"]:>6.1f}')

best = max(results, key=lambda x: x['total'])
print(f'\n  最佳: {best["name"]} — 净值{best["nav"]:.1f}倍')
# 原311全量等权: 300.68%
print(f'  原311全量等权: +300.68% (净值4.01)')
