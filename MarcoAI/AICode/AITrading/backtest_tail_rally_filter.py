# -*- coding: utf-8 -*-
"""尾盘急拉过滤: D-2 14:30→14:55涨幅超阈值→跳过#1, 买#2"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001
CAPITAL=100_000

def lk(code):
    fp=os.path.join(K,code);rows=[]
    with open(fp,encoding='utf-8') as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'):continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit():continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}

_5m={}
def lm5(code):
    if code in _5m:return _5m[code]
    fp=os.path.join(M5DIR,code)
    if not os.path.exists(fp):_5m[code]={};return{}
    bd=defaultdict(list)
    with open(fp) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','')
            bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    _5m[code]=dict(bd)
    return _5m[code]

def get_bar(code,d2_date,offset):
    bars=lm5(code).get(d2_date,[])
    if len(bars)>=abs(offset):return bars[offset]
    return None

def get_tail_rally(code,d2_date):
    """14:30→14:55 涨幅%"""
    b7=get_bar(code,d2_date,-7)  # 14:30
    b2=get_bar(code,d2_date,-2)  # 14:55
    if b7 is None or b2 is None:return None
    c7=b7[3];c2=b2[3]
    if c7<=0:return None
    return (c2-c7)/c7*100

def sd(bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o,'open_stop'
    if l<=st:return st,'low_stop'
    if h>=lu*0.999:return lu,'limit_up'
    return c,'close'

def trade(bp,sp,cap):
    shares=int(cap/bp/100)*100
    if shares<100:return None
    ba=bp*shares;sa_amt=sp*shares
    cost=ba*(1+CR);ret_amt=sa_amt*(1-CR-SD-TF)
    profit=ret_amt-cost
    return profit/cost*100,profit,cost,ret_amt,shares

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

sa=[];dm=defaultdict(list)
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<3:continue
    d2=tds[d1i-1]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<2:continue
            code=p[1];name=p[0]
            rs,dx=lk(code);d1k=dx.get(d1);d2k=dx.get(d2)
            if d1k is None or d2k is None:continue
            r1=rs[d1k];bp=r1[6];sp_c=r1[4]
            if bp<=0:continue
            r2=rs[d2k];r3=rs[d2k-1] if d2k>=1 else None
            if r3 is None:continue
            bar55=get_bar(code,d2,-2)
            if bar55 is None:bar55=(r2[1],r2[2],r2[3],r2[4])
            o5,h5,l5,c5=bar55
            pre_pb=r3[4]
            cl=np.array([r[4] for r in rs[:d2k+1]])
            hi=np.array([r[2] for r in rs[:d2k+1]]);n=len(cl)
            f={}
            f['pb_depth']=(r3[4]-c5)/r3[4]*100 if r3[4]>0 else 0
            f['ma5_dev']=(c5-np.mean(cl[-5:]))/np.mean(cl[-5:])*100 if n>=5 else 0
            if n>=10:
                tr=[]
                for i in range(d2k-9,d2k+1):
                    hh=hi[i];l_=rs[i][3];pc=rs[i-1][4] if i>0 else rs[i][6]
                    tr.append(max(hh-l_,abs(hh-pc),abs(l_-pc)))
                atr=np.mean(tr)
            else:atr=r2[2]-r2[3] if r2[2]>r2[3] else 1
            f['pc_vs_low_atr']=(pre_pb-l5)/atr if atr>0 else 0
            f['high_vs_pc_atr']=(h5-pre_pb)/atr if atr>0 else 0
            mg=0
            if d2k>=10:
                ca=[r[4] for r in rs[:d2k+1]]
                ma5=np.mean(ca[-5:]);ma10=np.mean(ca[-10:])
                ma5p=np.mean(ca[-6:-1]);ma10p=np.mean(ca[-11:-1])
                mg=1 if(ma5p<=ma10p and ma5>ma10)else 0
            f['ma_golden']=mg
            tail=get_tail_rally(code,d2)
            sa.append((f,code,d1,bp,sp_c,name,o5,h5,l5,c5,pre_pb,d2,
                       r1[1],r1[2],r1[3],r1[4],tail))

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

def run_backtest(thresh,label):
    consec=0;asset=CAPITAL;peak=CAPITAL;max_dd=0.0
    trades_count=0;skip_count=0;skip_tail_count=0;skip_tail_saved=0
    tail_skip_details=[]

    for d1_date in ad:
        idxs=dm[d1_date];fi=idxs[0]
        if fi<100:
            preds=np.zeros(len(idxs))
        else:
            hist=[j for j in range(fi)]
            Xh=X[hist];yh=yt[hist]
            mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
            Xn=(Xh-mu)/sg;d_dim=Xn.shape[1]
            try:w=solve(Xn.T@Xn+np.eye(d_dim)*2.0,Xn.T@yh)
            except:w=np.zeros(d_dim)
            Xt=np.array([(X[i]-mu)/sg for i in idxs])
            preds=Xt@w
        ranked=np.argsort(-preds)

        if consec>=3:consec=0;skip_count+=1;continue

        # 尾盘急拉过滤
        pick_idx=0
        if thresh is not None and len(ranked)>=2:
            s1=sa[idxs[ranked[0]]]
            tail1=s1[16]  # tail_rally
            if tail1 is not None and tail1>thresh:
                pick_idx=1  # 跳过#1, 选#2
                skip_tail_count+=1
                # Record what #1 would have done
                s1_bp=s1[3];s1_o=s1[12];s1_h=s1[13];s1_l=s1[14];s1_c=s1[15]
                s1_sp,s1_mode=sd(s1_bp,s1_o,s1_h,s1_l,s1_c)
                r1=trade(s1_bp,s1_sp,CAPITAL)
                if r1:
                    tail_skip_details.append({
                        'date':d1_date,'name1':s1[5],'tail':tail1,
                        'ret1':r1[0],'name2':sa[idxs[ranked[1]]][5]
                    })

        s=sa[idxs[ranked[pick_idx]]]
        code=s[1];name=s[5];bp=s[3];o=s[12];h=s[13];l=s[14];c=s[15]

        factor=0.5 if consec>=2 else 1.0
        cap_use=asset*factor
        sp,mode=sd(bp,o,h,l,c)
        result=trade(bp,sp,cap_use)
        if result is None:skip_count+=1;continue

        ret_pct,profit,cost,ret_amt,shares=result
        asset+=profit
        if asset>peak:peak=asset
        dd=(asset-peak)/peak*100
        if dd<max_dd:max_dd=dd
        if ret_pct<-0.05:consec+=1
        elif ret_pct>0.05:consec=0
        trades_count+=1

    # Sum up saved/avoided losses
    total_saved=0.0
    for d in tail_skip_details:
        r2_ret=d.get('ret2',0)
        if d['ret1']<0:total_saved+=d['ret1']  # #1 would have lost
    
    return {
        'label':label,'net':asset/CAPITAL,'return':(asset/CAPITAL-1)*100,
        'max_dd':max_dd,'trades':trades_count,'skip':skip_count,
        'tail_skip':skip_tail_count,'tail_details':tail_skip_details[:20]
    }

# ====== 跑全部阈值 ======
all_results=[]
# 基线
all_results.append(run_backtest(None,'基线(不过滤)'))
# 扫阈值
for th in [0.1,0.2,0.3,0.5,0.8,1.0,1.5,2.0,3.0]:
    all_results.append(run_backtest(th,f'跳过尾盘拉>{th}%'))

print('尾盘急拉过滤回测')
print('='*70)
print(f'{"策略":<25} {"净值":>7} {"回撤":>7} {"跳过":>5} {"vs基线"}')
print('-'*60)
baseline=all_results[0]['net']
for r in all_results:
    diff=(r['net']-baseline)/baseline*100
    flag='✅'if diff>0 else('➖'if diff==0 else'❌')
    print(f'{r["label"]:<25} {r["net"]:>7.4f} {r["max_dd"]:>+6.1f}% {r["tail_skip"]:>5} {diff:>+6.1f}% {flag}')

# 最佳方案的明细
best=max(all_results[1:],key=lambda x:x['net'])
if best['tail_details']:
    print(f'\n最佳过滤方案: {best["label"]} ({best["tail_skip"]}次触发)')
    print(f'{"日期":<10} {"#1(跳过)":<10} {"尾盘拉":>7} {"#1收益":>7} {"#2(买入)":<10}')
    print('-'*55)
    for d in best['tail_details'][:15]:
        print(f'{d["date"]:<10} {d["name1"]:<10} {d["tail"]:>+6.2f}% {d["ret1"]:>+6.2f}% {d["name2"]:<10}')

# 尾盘拉分布
print(f'\n尾盘拉幅分布(D-2 14:30→14:55):')
all_tails=[s[16] for s in sa if s[16] is not None]
tails=np.array(all_tails)
for p in [10,25,50,75,90,95]:
    v=np.percentile(tails,p)
    print(f'  P{p}: {v:+.2f}%')
print(f'  >0.5%占比: {(tails>0.5).sum()}/{len(tails)} ({(tails>0.5).sum()/len(tails)*100:.1f}%)')
print(f'  >1.0%占比: {(tails>1.0).sum()}/{len(tails)} ({(tails>1.0).sum()/len(tails)*100:.1f}%)')
print(f'  >2.0%占比: {(tails>2.0).sum()}/{len(tails)} ({(tails>2.0).sum()/len(tails)*100:.1f}%)')
