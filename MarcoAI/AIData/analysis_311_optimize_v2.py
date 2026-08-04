#!/usr/bin/env python3
"""策略311 卖点fallback优化"""
import os, numpy as np
from collections import defaultdict

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
FIVEM_DIR = os.path.join(BASE, "5M")
KLINE_DIR = os.path.join(BASE, "1D")
CR=0.00025; CM=5.0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

def load_td():
    ds=[]
    with open(os.path.join(BASE,"TRADING_DATES")) as f:
        for l in f:
            l=l.strip()
            if l: ds.append(l)
    return sorted(ds)

def load_stock_info():
    info={}
    with open(os.path.join(BASE,"STOCK_CODES_ALL"),encoding='utf-8') as f:
        for i,l in enumerate(f):
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)>=2: info[p[0]]={'rank':i,'name':p[1]}
    return info

def load_kline_range(code,dates):
    fp=os.path.join(KLINE_DIR,code)
    if not os.path.exists(fp): return {}
    r={}
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<7: continue
            if p[0] in dates:
                r[p[0]]=(float(p[1]),float(p[2]),float(p[3]),float(p[4]),float(p[5]),float(p[6]))
    return r

def load_5m(code,dt):
    fp=os.path.join(FIVEM_DIR,code)
    if not os.path.exists(fp): return None
    df=f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}"
    bars=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<6: continue
            if p[0].startswith(df):
                bars.append((p[0],float(p[4]),float(p[2]),float(p[3]),float(p[1]),float(p[5])))
    return bars if bars else None

def load_sigs():
    sd={}
    for fn in sorted(os.listdir(SIGNAL_DIR)):
        fp=os.path.join(SIGNAL_DIR,fn)
        if os.path.getsize(fp)<=3: continue
        with open(fp,encoding='utf-8') as f:
            ls=[l.strip() for l in f if l.strip()]
        if not ls: continue
        es=[(l.split('|')[0],float(l.split('|')[7])) for l in ls if len(l.split('|'))>=8]
        if es: sd[fn]=es
    return sd

def load_sentiment():
    sent=defaultdict(dict)
    for fname,convs in [
        ("1D_PANIC_INDEX",[('panic',float)]),
        ("1D_AVG_CHANGE",[('avg_chg',float)]),
        ("1D_MOTION_COUNT",[('net_motion',int)]),
        ("1D_TOTAL_AMOUNT",[('amount',lambda x:float(x) if x!='nan' else None),
                           ('amount_ma5',lambda x:float(x) if x!='nan' else None)])
    ]:
        with open(os.path.join(BASE,fname)) as f:
            for l in f:
                l=l.strip()
                if not l: continue
                p=l.split('|')
                for i,(k,conv) in enumerate(convs):
                    if len(p)>i+1:
                        try: sent[p[0]][k]=conv(p[i+1])
                        except: pass
    return sent

def classify_sentiment(s):
    panic=s.get('panic',20)
    avg_chg=s.get('avg_chg',0)
    net=s.get('net_motion',0)
    amt=s.get('amount')
    amt_ma5=s.get('amount_ma5')
    score=0
    if panic>70: score-=3
    elif panic>50: score-=2
    elif panic>30: score-=1
    elif panic<5: score+=1
    if avg_chg<-2.0: score-=3
    elif avg_chg<-1.0: score-=2
    elif avg_chg<-0.3: score-=1
    elif avg_chg>2.0: score+=2
    elif avg_chg>1.0: score+=1
    mp=net/677*100
    if mp<-30: score-=2
    elif mp<-10: score-=1
    elif mp>30: score+=2
    elif mp>10: score+=1
    if amt and amt_ma5 and amt_ma5>0:
        if amt/amt_ma5>1.3: score+=1
        elif amt/amt_ma5<0.7: score-=1
    if score<=-4: return 0,'恐慌'
    elif score<=-1: return 1,'偏空'
    elif score<=1: return 2,'震荡'
    elif score<=4: return 3,'偏多'
    else: return 4,'过热'

def fee(buy,sell,pc):
    if buy==0 or sell==0: return 0.0
    sh=int(pc/buy/100)*100
    if sh==0: sh=100
    c=sh*buy
    bf=max(c*CR,CM)+c*TF
    tb=c+bf
    r=sh*sell
    sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

def compute_factors(code,kd2,kd3,kd4,stock_info):
    if not kd2 or not kd3: return None
    o2,h2,l2,c2,v2,a2=kd2
    o3,h3,l3,c3,v3,a3=kd3
    f={}
    f['pullback_depth']=(c3-c2)/c3*100 if c3 else 0
    f['lower_shadow']=(c2-l2)/(h2-l2)*100 if h2>l2 else 50
    f['vol_ratio_d3_d2']=v3/v2 if v2 else 1
    f['cap_rank']=stock_info.get(code,{}).get('rank',338)
    f['cap_rank_norm']=f['cap_rank']/677.0
    f['is_mega_cap']=1 if f['cap_rank']<100 else 0
    f['vol_contract']=1 if v2<v3*0.8 else 0
    f['shadow_support']=1 if (f['lower_shadow']>50 and f['pullback_depth']>1) else 0
    if kd4: f['vol_ratio_d3_d4']=v3/kd4[4] if kd4[4] else 1
    else: f['vol_ratio_d3_d4']=1
    score=0
    if 0<f['pullback_depth']<8: score+=2
    elif f['pullback_depth']>15: score-=1
    if f['lower_shadow']>60: score+=2
    if f['vol_contract']: score+=2
    if f['vol_ratio_d3_d2']>1.5: score+=1
    if f['shadow_support']: score+=1
    f['quality_score']=score
    return f

def select_stock(candidates, env_name):
    if env_name=='过热': return None
    if env_name in ('恐慌','偏空','偏多'):
        scored=[]
        for code,d2c,bars,f in candidates:
            if f is None: continue
            s=f.get('is_mega_cap',0)*5+f.get('shadow_support',0)*3+f.get('vol_contract',0)*2
            scored.append((s,code,d2c,bars,f))
        scored.sort(key=lambda x:-x[0])
        return scored[0] if scored else None
    elif env_name=='震荡':
        scored=[]
        for code,d2c,bars,f in candidates:
            if f is None: continue
            s=(1-f.get('cap_rank_norm',0.5))*5
            if f.get('vol_ratio_d3_d2',1)>1.2: s+=2
            if 0<f.get('pullback_depth',0)<10: s+=1
            scored.append((s,code,d2c,bars,f))
        scored.sort(key=lambda x:-x[0])
        return scored[0] if scored else None
    return None

def make_sell_strategy(fallback_mode):
    def sell(bars, bp, env_name):
        if fallback_mode == 'pure_close':
            return bars[-1][1], bars[-1][0], 'close'
        
        if fallback_mode.startswith('pure_trail_'):
            pct = float(fallback_mode.split('_')[2])
            peak = bars[0][1]
            for b in bars:
                if b[1] > peak: peak = b[1]
                elif (peak - b[1]) / peak * 100 >= pct:
                    return b[1], b[0], f'trail_{pct}'
            return bars[-1][1], bars[-1][0], 'close'
        
        elif fallback_mode == 'trail_0.5_pure_then_compare':
            # 旧版 trail_0.5 fallback (用于对比)
            # 先检查上午(am_high future data版本)
            am_bars = [b for b in bars if int(b[0][11:13]) <= 11]
            if am_bars:
                am_ret = (am_bars[-1][1] - bars[0][1]) / bars[0][1] * 100
                if am_ret > 1.5:
                    sp = max(b[2] for b in am_bars)
                    for b in am_bars:
                        if b[2] == sp: return sp, b[0], 'am_high_FUTURE'
                    return sp, am_bars[-1][0], 'am_high_FUTURE'
            # fallback = trail_0.5
            peak = bars[0][1]
            for b in bars:
                if b[1] > peak: peak = b[1]
                elif (peak - b[1]) / peak * 100 >= 0.5:
                    return b[1], b[0], 'trail_0.5'
            return bars[-1][1], bars[-1][0], 'close'
    
    return sell

# ============================================================
print("="*100)
print("  策略311 卖点fallback优化")
print("="*100)

sigs=load_sigs()
tds=load_td()
di={d:i for i,d in enumerate(tds)}
stock_info=load_stock_info()
sentiment=load_sentiment()

all_trades=[]
for d0 in sorted(sigs.keys()):
    es=sigs[d0]
    d0i=di.get(d0)
    if d0i is None or d0i<3: continue
    d1,d2,d3=tds[d0i-1],tds[d0i-2],tds[d0i-3]
    d4=tds[d0i-4] if d0i>=4 else None
    sent_d2=sentiment.get(d2,{})
    if not sent_d2: continue
    env_code,env_name=classify_sentiment(sent_d2)
    if env_name=='过热': continue
    
    candidates=[]
    for code,d1_close in es:
        klines=load_kline_range(code,set(filter(None,[d2,d3,d4])))
        kd2=klines.get(d2)
        kd3=klines.get(d3)
        kd4=klines.get(d4) if d4 else None
        if not kd2 or not kd3: continue
        d2_close=kd2[3]
        factors=compute_factors(code,kd2,kd3,kd4,stock_info)
        if not factors: continue
        bars=load_5m(code,d1)
        if not bars or len(bars)<10: continue
        candidates.append((code,d2_close,bars,factors))
    if not candidates: continue
    
    pick=select_stock(candidates,env_name)
    if pick is None: continue
    all_trades.append((pick, env_name))

n=len(all_trades)
print(f"交易: {n}笔")

# 测试策略: 正确版 (无未来数据)
fallback_modes = [
    'pure_close',            # 纯尾盘卖(对比基准)
    'pure_trail_0.5', 'pure_trail_1.0', 'pure_trail_2.0', 'pure_trail_3.0',
    'trail_0.5_pure_then_compare',
]

print("\n"+"="*100)
print("  各fallback对比")
print("="*100)
print(f"  {'策略':<30} {'净值':>8} {'收益%':>8} {'胜率%':>7} {'回撤%':>7} {'夏普':>7} {'卖出分布':>35}")
print(f"  {'-'*110}")

best_fb=None
best_cum=0

for fb in fallback_modes:
    sell_fn=make_sell_strategy(fb)
    results=[]
    sell_counts=defaultdict(lambda:{'count':0,'sum':0.0})
    
    for (_,code,buy_price,bars,factors),env_name in all_trades:
        sp,st,method=sell_fn(bars,buy_price,env_name)
        ret=fee(buy_price,sp,CAPITAL)
        results.append(ret)
        sell_counts[method]['count']+=1
        sell_counts[method]['sum']+=ret
    
    cum=1.0; peak=1.0; max_dd=0.0
    for r in results:
        cum*=(1+r/100)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd: max_dd=dd
    
    wr=sum(1 for r in results if r>0)/len(results)*100
    dly=np.array(results)
    sh=np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
    
    dist=", ".join(f"{k}:{v['count']}" for k,v in sorted(sell_counts.items(),key=lambda x:-x[1]['count'])[:5])
    label_map={'pure_close':'纯尾盘卖(对比基准)','trail_0.5_pure_then_compare':'旧版am_high+trail(⚠未来数据)'}
    label = label_map.get(fb, fb.replace('pure_',''))
    tag = ''
    best_marker = ' ⭐' if cum==best_cum else ''
    print(f"  {label:<34} {cum:>8.4f} {(cum-1)*100:>8.1f} {wr:>7.1f} {max_dd:>7.1f} {sh:>7.2f}  {dist:<30}{best_marker}")
    
    if cum>best_cum and 'compare' not in fb:
        best_cum=cum
        best_fb=fb
    
    # 各卖出方式明细
    for method,sc in sorted(sell_counts.items(),key=lambda x:-x[1]['count']):
        avg=sc['sum']/sc['count']
        print(f"    -> {method:<20}: {sc['count']:>3}笔 均{avg:>6.2f}%")

# 最佳方案月度
print("\n"+"="*100)
print(f"  最佳方案({best_fb}) 月度明细")
print("="*100)

sell_fn=make_sell_strategy(best_fb)
monthly=defaultdict(lambda:{'rets':[],'wins':0,'losses':0})
all_rets=[]

for (_,code,buy_price,bars,factors),env_name in all_trades:
    sp,st,method=sell_fn(bars,buy_price,env_name)
    ret=fee(buy_price,sp,CAPITAL)
    month=bars[0][0][:7].replace('-','')
    monthly[month]['rets'].append(ret)
    if ret>0: monthly[month]['wins']+=1
    else: monthly[month]['losses']+=1
    all_rets.append(ret)

cum=1.0; peak=1.0; max_dd=0.0
print(f"  {'月份':<8} {'笔':>4} {'月收益%':>8} {'净值':>8} {'回撤%':>8} {'胜率':>7}")
print(f"  {'-'*50}")
for month in sorted(monthly.keys()):
    m=monthly[month]
    n_m=len(m['rets'])
    mr=1.0
    for r in m['rets']: mr*=(1+r/100)
    mr_pct=(mr-1)*100
    cum*=mr
    if cum>peak: peak=cum
    dd=(cum-peak)/peak*100
    if dd<max_dd: max_dd=dd
    wr=m['wins']/n_m*100
    print(f"  {month:<8} {n_m:>4} {mr_pct:>8.2f}% {cum:>8.4f} {dd:>8.2f}% {wr:>6.1f}%")

total=(cum-1)*100
wr_t=sum(1 for r in all_rets if r>0)/len(all_rets)*100
dly=np.array(all_rets)
sh=np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
print(f"  {'合计':<8} {len(all_rets):>4} {total:>8.2f}% {cum:>8.4f} {max_dd:>8.2f}% {wr_t:>6.1f}%")
print(f"  夏普{sh:.2f}, 月均收益{total/len(monthly):.1f}%")

print("\n"+"="*100)
print("  完成!")
print("="*100)
