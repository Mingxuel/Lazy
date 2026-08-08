"""回测: 5特征 + 买入时过滤涨停封板股"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S = r'C:\Lazy\李明学的大A\Data\Strategy'; K = r'C:\Lazy\李明学的大A\Data\1D'
FEATURES = ['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001; CM=0; SD=0.0005; TF=0.00001; CAPITAL=1_000_000

def load_kline(code):
    fp=os.path.join(K,code); rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'): continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit(): continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f: l=l.strip(); l and l.isdigit() and len(l)==8 and tds.append(l)
tds=sorted(tds); di={d:i for i,d in enumerate(tds)}

# 加载样本
samples_all=[]
daily_meta=defaultdict(list)
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
            name,code=p[0],p[1]
            rows,date_idx=load_kline(code)
            d1i_k=date_idx.get(d1); d2i_k=date_idx.get(d2)
            if d1i_k is None or d2i_k is None: continue
            r1=rows[d1i_k]; bp=r1[6]; sp_c=r1[4]
            o1,h1,l1=r1[1],r1[2],r1[3]  # D-1(sell day) OHLC
            if bp<=0: continue
            r2=rows[d2i_k]; o2,h2,l2,c2,v2,pc2=r2[1],r2[2],r2[3],r2[4],r2[5],r2[6]
            r3=rows[d2i_k-1] if d2i_k>=1 else None
            cls=np.array([r[4] for r in rows[:d2i_k+1]])
            highs=np.array([r[2] for r in rows[:d2i_k+1]]); n=len(cls)
            f={}
            f['pb_depth']=(r3[4]-c2)/r3[4]*100 if(r3 and r3[4]>0) else 0
            f['ma5_dev']=(c2-np.mean(cls[-5:]))/np.mean(cls[-5:])*100 if n>=5 else 0
            if n>=10:
                trs=[]
                for i in range(d2i_k-9,d2i_k+1):
                    h=highs[i]; l=rows[i][3]; pc=rows[i-1][4] if i>0 else rows[i][6]
                    trs.append(max(h-l,abs(h-pc),abs(l-pc)))
                atr10=np.mean(trs) if trs else 1
            else: atr10=h2-l2 if h2>l2 else 1
            f['pc_vs_low_atr']=(pc2-rows[d2i_k][3])/atr10 if atr10>0 else 0
            f['high_vs_pc_atr']=(h2-pc2)/atr10 if atr10>0 else 0
            ma_golden=0
            if d2i_k>=10:
                c_arr=[r[4] for r in rows[:d2i_k+1]]
                ma5=np.mean(c_arr[-5:]); ma10=np.mean(c_arr[-10:])
                ma5p=np.mean(c_arr[-6:-1]); ma10p=np.mean(c_arr[-11:-1])
                ma_golden=1 if(ma5p<=ma10p and ma5>ma10) else 0
            f['ma_golden']=ma_golden
            samples_all.append((f,code,d1,bp,sp_c,name,o1,h1,l1,o2,h2,l2,c2,pc2))
            daily_meta[d1].append(len(samples_all)-1)
samples_all.sort(key=lambda x:x[2])
# 重建 daily_meta (排序后索引已变)
daily_meta=defaultdict(list)
for i,s in enumerate(samples_all):
    daily_meta[s[2]].append(i)

X=np.array([[s[0].get(k,0) for k in FEATURES] for s in samples_all])
y_target=np.array([(s[4]-s[3])/s[3]*100 for s in samples_all])

all_dates=sorted(daily_meta.keys())
print(f'样本: {len(samples_all)} | 交易日: {len(all_dates)}')

def sell_daily(bp,o,h,l,c):
    limit_up=round(bp*1.10,2); stop=bp*0.94
    if o>0 and o<=stop: return o,'开盘止损'
    if l<=stop: return stop,'日内止损'
    if h>=limit_up*0.999: return limit_up,'涨停卖出'
    return c,'收盘卖出'

def fee(bp,sp,capital):
    buy_s = capital * CR + int(capital/bp/100)*100 * SD
    shares = int(capital / bp / 100) * 100
    sell_s = shares * sp * (CR + SD) + TF
    cost = shares * (sp - bp) - buy_s - sell_s
    return cost / capital * 100, shares

# ==== 回测: 无涨停过滤 vs 有涨停过滤 ====

for label, filter_limit in [("无涨停过滤(旧)", False), ("过滤涨停封板(新)", True)]:
    consec_loss=0; cum=1.0; peak=1.0; max_dd=0.0
    skip_count=0; limit_skip=0
    trades=[]; rets=[]
    m_data=defaultdict(list); annual_data=defaultdict(list)
    mode_stats=defaultdict(int)

    for d1_date in all_dates:
        idxs=daily_meta[d1_date]
        first_i=idxs[0]

        # Walk-Forward 选股
        if first_i<100:
            best=samples_all[idxs[0]]
        else:
            hist=[j for j in range(first_i)]
            Xh=X[hist]; yh=y_target[hist]
            mean=Xh.mean(axis=0); std=Xh.std(axis=0)+1e-8
            Xn=(Xh-mean)/std; d=Xn.shape[1]
            try: w=solve(Xn.T@Xn+np.eye(d)*2.0,Xn.T@yh)
            except: w=np.zeros(d)
            Xt=np.array([(X[i]-mean)/std for i in idxs]); preds=Xt@w
            # 选最高分, 但如果涨停过滤则跳过封板的
            ranked=sorted(zip(preds,idxs),key=lambda x:-x[0])
            chosen=None
            for sc,idx in ranked:
                s=samples_all[idx]
                bp=s[3]; pc2=s[13]; c2=s[12]  # pc2=D-2昨收(D-3收盘), c2=D-2收盘
                if filter_limit:
                    limit_up=round(pc2*1.10,2)
                    if c2>=limit_up*0.995:  # D-2涨停封板, 尾盘买不到!
                        limit_skip+=1
                        continue
                chosen=s
                break
            if chosen is None:
                skip_count+=1; rets.append(0.0); cum_ret=cum
                continue
            best=chosen

        bp=best[3]; o=best[6]; h=best[7]; l=best[8]; c_d=best[4]
        code=best[1]; name=best[5]

        # 仓位管理
        cap=CAPITAL
        tag=""
        if consec_loss>=3:
            ret=0.0; rets.append(ret); skip_count+=1; cum_ret=cum; consec_loss=0; continue
        elif consec_loss>=2:
            cap=CAPITAL*0.5; tag=" [半仓]"

        sp,mode=sell_daily(bp,o,h,l,c_d)
        ret,sh=fee(bp,sp,cap)
        cum*=(1+ret/100); rets.append(ret)
        if cum>peak: peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd: max_dd=dd
        if ret<-0.05: consec_loss+=1
        elif ret>0.05: consec_loss=0

        mode_stats[mode+tag]+=1
        trades.append({'date':d1_date,'code':code,'name':name,'bp':bp,'sp':sp,'ret':ret,'mode':mode+tag})
        m=d1_date[:6]; yr=d1_date[:4]
        m_data[m].append(ret); annual_data[yr].append(ret)

    nonzero=[r for r in rets if r!=0]
    wr=sum(1 for r in nonzero if r>0)/len(nonzero)*100 if nonzero else 0

    print(f'\n{"="*60}')
    print(f'{label}')
    print(f'净值: {cum:.4f} | 收益: +{(cum-1)*100:.1f}% | 胜率: {wr:.1f}% | 回撤: {max_dd:.1f}%')
    print(f'总交易: {len(trades)} | 跳过(连亏): {skip_count} | 跳过(涨停封板): {limit_skip}')
    print(f'卖出方式: {dict(mode_stats)}')

    # 年度
    print('\n年度:')
    for yk in sorted(annual_data):
        yr=1.0
        for rv in annual_data[yk]: yr*=(1+rv/100)
        wins=sum(1 for rv in annual_data[yk] if rv>0)
        all_n=len(annual_data[yk])
        print(f'  {yk}: {(yr-1)*100:+.1f}% ({wins}/{all_n})')

    # 月度
    hdr = '月份'; ret_hdr = '收益'; cnt_hdr = '笔'
    print(f'\n{hdr:<8} {ret_hdr:>8} {cnt_hdr}')
    cv=1.0
    for mk in sorted(m_data):
        mr=1.0
        for rv in m_data[mk]: mr*=(1+rv/100)
        cv*=mr
        print(f'{mk[:4]}-{mk[4:]:<3} {mr-1:>+8.2%} {len(m_data[mk]):>4}')
