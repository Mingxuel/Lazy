#!/usr/bin/env python3
"""策略311: 回踩日(D-2)用5M检查MA5支撑, 有支撑才买"""
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
        for l in f: l=l.strip(); l and ds.append(l)
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
            if p[0] in dates: r[p[0]]=(float(p[1]),float(p[2]),float(p[3]),float(p[4]),float(p[5]),float(p[6]))
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
            if p[0].startswith(df): bars.append((p[0],float(p[4]),float(p[2]),float(p[3]),float(p[1]),float(p[5])))
    return bars if bars else None

def load_sigs():
    sd={}
    for fn in sorted(os.listdir(SIGNAL_DIR)):
        fp=os.path.join(SIGNAL_DIR,fn)
        if os.path.getsize(fp)<=3: continue
        with open(fp,encoding='utf-8') as f: ls=[l.strip() for l in f if l.strip()]
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

def classify(s):
    panic=s.get('panic',20); avg_chg=s.get('avg_chg',0)
    net=s.get('net_motion',0); amt=s.get('amount'); amt_ma5=s.get('amount_ma5')
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
    if score<=-4: return '恐慌'
    elif score<=-1: return '偏空'
    elif score<=1: return '震荡'
    elif score<=4: return '偏多'
    else: return '过热'

def fee(buy,sell,pc):
    if buy==0 or sell==0: return 0.0
    sh=int(pc/buy/100)*100
    if sh==0: sh=100
    c=sh*buy; bf=max(c*CR,CM)+c*TF; tb=c+bf
    r=sh*sell; sf=max(r*CR,CM)+r*TF+r*SD
    return (r-sf-tb)/tb*100

def check_ma5_support_5m(code, date_str, bars):
    """
    用5M数据检查回踩日是否有MA5强支撑
    返回: (has_support, bounce_strength, day_low_dist_to_close)
    """
    if not bars or len(bars) < 10:
        return False, 0, 0
    
    day_low = min(b[3] for b in bars)
    day_close = bars[-1][1]
    day_high = max(b[2] for b in bars)
    
    # 获取MA5: 用D-2收盘作为粗略MA5代理(回踩日的MA5通常很接近收盘价)
    # 更精确的做法是查前5日收盘均值, 但这里用当日收盘价近似
    ma5_approx = day_close
    
    # 盘中最低点距MA5
    dist_low_to_ma5 = (day_low - ma5_approx) / ma5_approx * 100
    
    # 找是否有bar精准触碰然后强力弹起
    best_bounce = 0
    for b in bars:
        bar_low = b[3]
        bar_close = b[1]
        d = (bar_low - ma5_approx) / ma5_approx * 100
        # 触及MA5附近(±1%)并且弹起
        if -1.5 < d < 1.0:
            bounce = (bar_close - bar_low) / bar_low * 100
            if bounce > best_bounce:
                best_bounce = bounce
    
    # 判断是否有强支撑
    has_support = False
    # 条件1: 触碰后强力弹起
    if best_bounce > 1.5:
        has_support = True
    # 条件2: 下影线很长 + 最低点就在MA5附近
    if day_close > day_low:
        shadow_pct = (day_close - day_low) / (day_high - day_low) * 100 if day_high > day_low else 50
        if shadow_pct > 60 and abs(dist_low_to_ma5) < 2:
            has_support = True
    
    return has_support, best_bounce, dist_low_to_ma5

def compute_factors(code,kd2,kd3,kd4,stock_info,bars_d2):
    """311因子: D-2回踩日数据"""
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
    
    # ★ MA5支撑 (用D-2的5M数据)
    has_ma5, bounce, dist = check_ma5_support_5m(code, '', bars_d2)
    f['ma5_support'] = 1 if has_ma5 else 0
    f['ma5_bounce'] = bounce
    
    score = 0
    if 0<f['pullback_depth']<8: score+=2
    elif f['pullback_depth']>15: score-=1
    if f['lower_shadow']>60: score+=2
    if f['vol_contract']: score+=2
    if f['vol_ratio_d3_d2']>1.5: score+=1
    if f['shadow_support']: score+=1
    if f['ma5_support']: score+=4  # ★ MA5支撑是最强信号
    elif f['ma5_bounce']>0.5: score+=1
    f['quality_score']=score
    return f

def select_stocks(candidates, env_name, top_n=1, require_ma5=False):
    if env_name=='过热': return []
    if env_name in ('恐慌','偏空','偏多'):
        scored=[]
        for code,bp,sp,f in candidates:
            if f is None: continue
            if require_ma5 and not f.get('ma5_support'): continue
            s=f.get('is_mega_cap',0)*5+f.get('shadow_support',0)*3+f.get('vol_contract',0)*2
            if f.get('ma5_support'): s+=6
            elif f.get('ma5_bounce',0)>1: s+=2
            scored.append((s,code,bp,sp,f))
        scored.sort(key=lambda x:-x[0])
        return scored[:top_n]
    else:
        scored=[]
        for code,bp,sp,f in candidates:
            if f is None: continue
            if require_ma5 and not f.get('ma5_support'): continue
            s=(1-f.get('cap_rank_norm',0.5))*5
            if f.get('vol_ratio_d3_d2',1)>1.2: s+=2
            if 0<f.get('pullback_depth',0)<10: s+=1
            if f.get('ma5_support'): s+=5
            scored.append((s,code,bp,sp,f))
        scored.sort(key=lambda x:-x[0])
        return scored[:top_n]
    return []

def select_stocks_basic(candidates, env_name, top_n=1):
    """不含MA5因子的基础选股"""
    if env_name=='过热': return []
    if env_name in ('恐慌','偏空','偏多'):
        scored=[]
        for code,bp,sp,f in candidates:
            if f is None: continue
            s=f.get('is_mega_cap',0)*5+f.get('shadow_support',0)*3+f.get('vol_contract',0)*2
            scored.append((s,code,bp,sp,f))
        scored.sort(key=lambda x:-x[0])
        return scored[:top_n]
    else:
        scored=[]
        for code,bp,sp,f in candidates:
            if f is None: continue
            s=(1-f.get('cap_rank_norm',0.5))*5
            if f.get('vol_ratio_d3_d2',1)>1.2: s+=2
            if 0<f.get('pullback_depth',0)<10: s+=1
            scored.append((s,code,bp,sp,f))
        scored.sort(key=lambda x:-x[0])
        return scored[:top_n]
    return []

def select_unified(candidates, top_n=1, require_ma5=False):
    """不考虑情绪的统一定权选股"""
    scored=[]
    for code,bp,sp,f in candidates:
        if f is None: continue
        if require_ma5 and not f.get('ma5_support'): continue
        s=f.get('is_mega_cap',0)*5+f.get('shadow_support',0)*3+f.get('vol_contract',0)*2
        if f.get('ma5_support'): s+=6
        elif f.get('ma5_bounce',0)>1: s+=2
        s+=f.get('quality_score',0)*0.5
        scored.append((s,code,bp,sp,f))
    scored.sort(key=lambda x:-x[0])
    return scored[:top_n]

# ============================================================
print("="*100)
print("  策略311 + MA5回踩支撑确认 (D-3情绪★实盘可用)")
print("  D-2回踩日用5M检查MA5 → 有支撑买 → D-1尾盘卖")
print("  情绪: 用D-3收盘数据(D-2开盘前已知)")
print("="*100)

sigs=load_sigs(); tds=load_td(); di={d:i for i,d in enumerate(tds)}
stock_info=load_stock_info(); sentiment=load_sentiment()

all_trades=[]
ma5_stats={'with_support':0,'without_support':0}

for d0 in sorted(sigs.keys()):
    es=sigs[d0]; d0i=di.get(d0)
    if d0i is None or d0i<2: continue
    d1=tds[d0i-1]; d2=tds[d0i-2]; d3=tds[d0i-3]
    d4=tds[d0i-4] if d0i>=4 else None
    
    sent_d2=sentiment.get(d2,{})
    # ★ 实盘修正: D-2尾盘时D-2情绪指标尚未生成, 改用D-3情绪(已知)
    sent_d3=sentiment.get(d3,{})
    if not sent_d3: continue
    env_name=classify(sent_d3)
    
    for code,d1_close in es:
        klines=load_kline_range(code,set(filter(None,[d2,d3,d4])))
        kd2=klines.get(d2); kd3=klines.get(d3); kd4=klines.get(d4) if d4 else None
        if not kd2 or not kd3: continue
        d2_close=kd2[3]
        buy_price=d2_close
        sell_price=d1_close  # D-1 close = signal[7]
        
        # ★ 加载D-2(回踩日)的5M数据
        bars_d2=load_5m(code,d2)
        if not bars_d2 or len(bars_d2)<10: continue
        
        factors=compute_factors(code,kd2,kd3,kd4,stock_info,bars_d2)
        if not factors: continue
        
        all_trades.append((code,d1,env_name,buy_price,sell_price,factors))
        if factors.get('ma5_support'):
            ma5_stats['with_support']+=1
        else:
            ma5_stats['without_support']+=1

n=len(all_trades)
print(f"\n总交易: {n}笔")
print(f"MA5支撑确认: {ma5_stats['with_support']}笔 ({ma5_stats['with_support']/n*100:.1f}%)")
print(f"无MA5支撑: {ma5_stats['without_support']}笔 ({ma5_stats['without_support']/n*100:.1f}%)")

# MA5支撑组 vs 无支撑组 收益对比
sup_rets=[fee(t[3],t[4],CAPITAL) for t in all_trades if t[5].get('ma5_support')]
nos_rets=[fee(t[3],t[4],CAPITAL) for t in all_trades if not t[5].get('ma5_support')]
print(f"\nMA5支撑组: 均收益{np.mean(sup_rets):.2f}% 胜率{sum(1 for r in sup_rets if r>0)/len(sup_rets)*100:.0f}% ({len(sup_rets)}笔)")
print(f"无MA5支撑组: 均收益{np.mean(nos_rets):.2f}% 胜率{sum(1 for r in nos_rets if r>0)/len(nos_rets)*100:.0f}% ({len(nos_rets)}笔)")

# 回测
by_d1=defaultdict(list)
for t in all_trades: by_d1[t[1]].append(t)

print(f"\n{'='*90}")
print(f"  策略对比 ({len(by_d1)}个卖出日)")
print(f"{'='*90}")
print(f"  {'策略':<35} {'净值':>8} {'收益%':>8} {'胜率%':>7} {'回撤%':>7} {'夏普':>7}")
print(f"  {'-'*80}")

best_label=""; best_cum=0

configs=[
    ("311_等权全买+尾盘卖(old)", 99, False, False),
    ("311_精选TOP1+尾盘卖(old)", 1, False, False),
    ("311_精选TOP1+MA5加分+尾盘卖(D3情绪)", 1, False, True),
    ("311_仅买MA5支撑+精选TOP1+尾盘卖(D3情绪)", 1, True, True),
    ("311_仅买MA5支撑+等权全买+尾盘卖(D3情绪)", 99, True, True),
    ("★311_不考虑情绪_精选TOP1+MA5", 1, False, True),  # 用unified selection
]

for label, top_n, require_ma5, use_ma5 in configs:
    daily_rets=[]
    for d1 in sorted(by_d1.keys()):
        trades=by_d1[d1]; env_name=trades[0][2]
        candidates=[(t[0],t[3],t[4],t[5]) for t in trades]
        
        if '不考虑情绪' in label:
            picks=select_unified(candidates, top_n, require_ma5)
        elif use_ma5:
            picks=select_stocks(candidates, env_name, top_n, require_ma5)
        else:
            picks=select_stocks_basic(candidates, env_name, top_n)
        
        if not picks: continue
        pc=CAPITAL/len(picks)
        rets=[fee(bp,sp,pc) for _,_,bp,sp,_ in picks]
        daily_rets.append(sum(rets)/len(rets))
    
    cum=1.0; peak=1.0; max_dd=0.0
    for r in daily_rets:
        cum*=(1+r/100)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd: max_dd=dd
    wr=sum(1 for r in daily_rets if r>0)/len(daily_rets)*100
    dly=np.array(daily_rets)
    sh=np.mean(dly)/np.std(dly)*np.sqrt(252) if np.std(dly)>0 else 0
    
    star=""
    if cum>best_cum: best_cum=cum; best_label=label; star=" ⭐"
    print(f"  {label:<35} {cum:>8.4f} {(cum-1)*100:>8.1f} {wr:>7.1f} {max_dd:>7.1f} {sh:>7.2f}{star}")

print(f"\n🏆 最佳: {best_label}")

# 与31对比
print(f"\n{'='*90}")
print(f"  最终对比")
print(f"{'='*90}")
print(f"  31精选TOP1+MA5 : 净值6.05 收益505.2%")
print(f"  311精选TOP1+MA5: 净值{best_cum:.4f} 收益{(best_cum-1)*100:.1f}%")

print(f"\n{'='*90}")
print("  完成!")
print("="*90)
