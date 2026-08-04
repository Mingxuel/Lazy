#!/usr/bin/env python3
"""策略31 MA5支撑因子测试"""
import os, numpy as np
from collections import defaultdict

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "31")
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
        es=[(l.split('|')[0],float(l.split('|')[4]),float(l.split('|')[7])) for l in ls if len(l.split('|'))>=8]
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

def compute_factors(code,kd1,kd2,kd3,stock_info,bars):
    if not kd1 or not kd2: return None
    o1,h1,l1,c1,v1,a1=kd1
    o2,h2,l2,c2,v2,a2=kd2
    f={}
    f['pullback_depth']=(c2-c1)/c2*100 if c2 else 0
    f['lower_shadow']=(c1-l1)/(h1-l1)*100 if h1>l1 else 50
    f['vol_ratio_d2_d1']=v2/v1 if v1 else 1
    f['cap_rank']=stock_info.get(code,{}).get('rank',338)
    f['cap_rank_norm']=f['cap_rank']/677.0
    f['is_mega_cap']=1 if f['cap_rank']<100 else 0
    f['vol_contract']=1 if v1<v2*0.8 else 0
    f['shadow_support']=1 if (f['lower_shadow']>50 and f['pullback_depth']>1) else 0
    if kd3: f['vol_ratio_d2_d3']=v2/kd3[4] if kd3[4] else 1
    else: f['vol_ratio_d2_d3']=1
    
    f['ma5_bounce']=0
    if bars and c1>0:
        for b in bars:
            bar_low,bar_close=b[3],b[1]
            d_ma5=(bar_low-c1)/c1*100
            if -1.0<d_ma5<1.0:
                bounce=(bar_close-bar_low)/bar_low*100
                if bounce>1.5:
                    f['ma5_bounce']=bounce
                    break
    
    score=0
    if 0<f['pullback_depth']<8: score+=2
    elif f['pullback_depth']>15: score-=1
    if f['lower_shadow']>60: score+=2
    if f['vol_contract']: score+=2
    if f['vol_ratio_d2_d1']>1.5: score+=1
    if f['shadow_support']: score+=1
    if f['ma5_bounce']>2: score+=3
    f['quality_score']=score
    return f

def select_old(candidates,env_name,top_n=1):
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
            if f.get('vol_ratio_d2_d1',1)>1.2: s+=2
            if 0<f.get('pullback_depth',0)<10: s+=1
            scored.append((s,code,bp,sp,f))
        scored.sort(key=lambda x:-x[0])
        return scored[:top_n]
    return []

def select_new(candidates,env_name,top_n=1):
    if env_name=='过热': return []
    if env_name in ('恐慌','偏空','偏多'):
        scored=[]
        for code,bp,sp,f in candidates:
            if f is None: continue
            s=f.get('is_mega_cap',0)*5+f.get('shadow_support',0)*3+f.get('vol_contract',0)*2
            if f.get('ma5_bounce',0)>2: s+=4
            scored.append((s,code,bp,sp,f))
        scored.sort(key=lambda x:-x[0])
        return scored[:top_n]
    else:
        scored=[]
        for code,bp,sp,f in candidates:
            if f is None: continue
            s=(1-f.get('cap_rank_norm',0.5))*5
            if f.get('vol_ratio_d2_d1',1)>1.2: s+=2
            if 0<f.get('pullback_depth',0)<10: s+=1
            if f.get('ma5_bounce',0)>2: s+=3
            scored.append((s,code,bp,sp,f))
        scored.sort(key=lambda x:-x[0])
        return scored[:top_n]
    return []

# Main
print("策略31 + MA5支撑因子测试")
tds=load_td(); di={d:i for i,d in enumerate(tds)}
stock_info=load_stock_info(); sentiment=load_sentiment(); sigs=load_sigs()

all_trades=[]
for d0 in sorted(sigs.keys()):
    es=sigs[d0]; d0i=di.get(d0)
    if d0i is None or d0i<1: continue
    d1=tds[d0i-1]; d2=tds[d0i-2]; d3=tds[d0i-3] if d0i>=3 else None
    sent_d1=sentiment.get(d1,{})
    if not sent_d1: continue
    env_name=classify(sent_d1)
    if env_name=='过热': continue
    for code,d0_close,d1_close in es:
        klines=load_kline_range(code,set(filter(None,[d1,d2,d3])))
        kd1=klines.get(d1); kd2=klines.get(d2); kd3=klines.get(d3) if d3 else None
        if not kd1 or not kd2: continue
        bars=load_5m(code,d1)
        factors=compute_factors(code,kd1,kd2,kd3,stock_info,bars)
        if not factors: continue
        all_trades.append((code,d0,env_name,d1_close,d0_close,factors))

by_d0=defaultdict(list)
for t in all_trades: by_d0[t[1]].append(t)

for label, select_fn in [("旧版(无MA5因子)", select_old), ("新版(+MA5弹起因子)", select_new)]:
    daily_rets=[]
    for d0 in sorted(by_d0.keys()):
        trades=by_d0[d0]; env_name=trades[0][2]
        candidates=[(t[0],t[3],t[4],t[5]) for t in trades]
        picks=select_fn(candidates,env_name,1)
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
    print(f"{label}: 净值{cum:.4f} 收益{(cum-1)*100:.1f}% 胜率{wr:.1f}% 回撤{max_dd:.1f}% 夏普{sh:.2f}")
