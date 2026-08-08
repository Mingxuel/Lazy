"""回测8月逐笔交易"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
FEATURES = ['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001; CM=0.0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

def load_kline(code):
    fp=os.path.join(K,code); rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith(chr(65279)): continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}

def fee(bp,sp,cap):
    shares=int(cap/bp/100)*100; b_amt=bp*shares; s_amt=sp*shares
    comm_buy=max(b_amt*CR,CM); comm_sell=max(s_amt*CR,CM)
    stamp=s_amt*SD; tfee=s_amt*TF
    total_cost=b_amt+comm_buy; total_return=s_amt-comm_sell-stamp-tfee
    ret_pct=(total_return-total_cost)/total_cost*100
    return ret_pct, total_return/total_cost

def sell_daily(bp,o,h,l,c):
    stop_p=bp*0.94; limit_up=round(bp*1.10,2)
    if o<=stop_p: return o,'open_stop'
    if l<=stop_p: return stop_p,'low_stop'
    if h>=limit_up*0.999: return limit_up,'limit_up'
    return c,'close'

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds=sorted(tds); di={d:i for i,d in enumerate(tds)}

samples_all = []
daily_meta = defaultdict(list)
for fn in sorted(os.listdir(S)):
    if not fn.isdigit(): continue
    d1=fn; d1i=di.get(d1)
    if d1i is None or d1i<3: continue
    d2=tds[d1i-1]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l: continue
            p=l.split('|')
            if len(p)<2: continue
            name=p[0]; code=p[1]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]; bp=r1[6]; sp_c=r1[4]
            if bp<=0: continue
            r2=rows[d2i_k]; r3=rows[d2i_k-1] if d2i_k>=1 else None
            if r3 is None: continue
            cls=np.array([r[4] for r in rows[:d2i_k+1]])
            highs=np.array([r[2] for r in rows[:d2i_k+1]])
            n=len(cls)
            f={}
            f['pb_depth']=(r3[4]-r2[4])/r3[4]*100 if r3[4]>0 else 0
            f['ma5_dev']=(r2[4]-np.mean(cls[-5:]))/np.mean(cls[-5:])*100 if n>=5 else 0
            if n>=10:
                trs=[]
                for i in range(d2i_k-9,d2i_k+1):
                    h=highs[i]; l_=rows[i][3]; pc=rows[i-1][4] if i>0 else rows[i][6]
                    trs.append(max(h-l_,abs(h-pc),abs(l_-pc)))
                atr10=np.mean(trs) if trs else 1
            else: atr10=r2[2]-r2[3] if r2[2]>r2[3] else 1
            f['pc_vs_low_atr']=(r2[6]-r2[3])/atr10 if atr10>0 else 0
            f['high_vs_pc_atr']=(r2[2]-r2[6])/atr10 if atr10>0 else 0
            ma_golden=0
            if d2i_k>=10:
                c_arr=[r[4] for r in rows[:d2i_k+1]]
                ma5=np.mean(c_arr[-5:]); ma10=np.mean(c_arr[-10:])
                ma5p=np.mean(c_arr[-6:-1]); ma10p=np.mean(c_arr[-11:-1])
                ma_golden=1 if(ma5p<=ma10p and ma5>ma10) else 0
            f['ma_golden']=ma_golden
            # 存 D-1 的 OHLC (卖出日), 不是 D-2 的
            samples_all.append((f,code,d1,bp,sp_c,name,r1[1],r1[2],r1[3],r2[4]))
            daily_meta[d1].append(len(samples_all)-1)

samples_all.sort(key=lambda x:x[2])
daily_meta_new = defaultdict(list)
for i,s in enumerate(samples_all):
    daily_meta_new[s[2]].append(i)
daily_meta = daily_meta_new
all_dates=sorted(daily_meta.keys())

X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples_all])
y_target=np.array([(s[4]-s[3])/s[3]*100 for s in samples_all])

consec = 0; cum = 1.0; peak = 1.0; trades = []

for d1_date in all_dates:
    if d1_date < '20260801':
        # Pre-loop: just update state
        idxs = daily_meta[d1_date]; first_i = idxs[0]
        if first_i < 100:
            best = samples_all[idxs[0]]
        else:
            hist = [j for j in range(first_i)]
            Xh=X[hist]; yh=y_target[hist]
            mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
            Xn=(Xh-mean)/std; d=Xn.shape[1]
            try: w=solve(Xn.T@Xn+np.eye(d)*2.0,Xn.T@yh)
            except: w=np.zeros(d)
            Xt=np.array([(X[i]-mean)/std for i in idxs])
            preds=Xt@w
            best=samples_all[idxs[int(np.argmax(preds))]]
        
        bp=best[3]; o=best[6]; h=best[7]; l=best[8]; c_d=best[4]  # c_d = D-1收盘=卖出日收盘
        cap=CAPITAL
        if consec>=3:
            consec=0; continue
        elif consec>=2:
            cap=CAPITAL*0.5
        sp,mode=sell_daily(bp,o,h,l,c_d)
        ret,sh=fee(bp,sp,cap)
        cum*=(1+ret/100)
        if cum>peak: peak=cum
        if ret<-0.05: consec+=1
        elif ret>0.05: consec=0
        continue
    
    # August: record detail
    idxs = daily_meta[d1_date]; first_i = idxs[0]
    if first_i < 100:
        best = samples_all[idxs[0]]
    else:
        hist = [j for j in range(first_i)]
        Xh=X[hist]; yh=y_target[hist]
        mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
        Xn=(Xh-mean)/std; d=Xn.shape[1]
        try: w=solve(Xn.T@Xn+np.eye(d)*2.0,Xn.T@yh)
        except: w=np.zeros(d)
        Xt=np.array([(X[i]-mean)/std for i in idxs])
        preds=Xt@w
        best=samples_all[idxs[int(np.argmax(preds))]]
    
    bp=best[3]; o=best[6]; h=best[7]; l=best[8]; c_d=best[4]  # c_d = D-1收盘=卖出日收盘
    code=best[1]; name=best[5]
    
    cap=CAPITAL
    if consec>=3:
        ret=0.0; mode='skip'; consec=0; sp=0
    elif consec>=2:
        cap=CAPITAL*0.5
        sp,mode=sell_daily(bp,o,h,l,c_d)
        ret,sh=fee(bp,sp,cap)
        mode+=' [半仓]'
        if ret<-0.05: consec+=1
        elif ret>0.05: consec=0
    else:
        sp,mode=sell_daily(bp,o,h,l,c_d)
        ret,sh=fee(bp,sp,cap)
        if ret<-0.05: consec+=1
        elif ret>0.05: consec=0
    
    cum*=(1+ret/100)
    if cum>peak: peak=cum
    trades.append((d1_date,code,name,bp,sp,ret,mode,cum))

print(f'=== 2026年8月 回测 ({len(trades)}笔) ===')
print(f'5特征版 | 万一免五')
print()
print(f'{"日":<10} {"代码":<14} {"名称":<10} {"买入":>8} {"卖出":>8} {"收益":>8} {"卖出方式":<16} {"累计净值":>10}')
print('-'*90)
for t in trades:
    dt,code,name,bp,sp,ret,mode,cum = t
    if mode=='skip':
        print(f'{dt:<10} {code:<14} {name:<10} {"":>8} {"":>8} {"跳过":>8} {"":<16} {cum:>10.4f}')
    else:
        print(f'{dt:<10} {code:<14} {name:<10} {bp:>8.2f} {sp:>8.2f} {ret:>+7.2f}% {mode:<16} {cum:>10.4f}')

# Stats
non_skip = [t for t in trades if t[5]!=0]
wins = sum(1 for t in non_skip if t[5]>0)
print()
print(f'胜率: {wins}/{len(non_skip)} ({wins/len(non_skip)*100:.1f}%)')
print(f'月收益: {trades[-1][7]:.4f} ({(trades[-1][7]-1)*100:+.1f}%)')
