"""
最终版回测: 5M 14:55价 + 分仓(gap<0.10) + 10W起始
"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D'
M5=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001
CAP_START=100_000
SPLIT_GAP=0.10

# ===== 5M缓存 =====
_5m={}
def lm5(code):
    if code in _5m:return _5m[code]
    fp=os.path.join(M5,code)
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

def get_1455(code,d2):
    bars=lm5(code).get(d2,[])
    return bars[-2][3] if bars and len(bars)>=2 else None

def lk(code):
    fp=os.path.join(K,code);rows=[]
    with open(fp) as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('\ufeff'):continue
            c=l.split()
            if len(c)<10 or not c[0].isdigit():continue
            rows.append((c[0],float(c[1]),float(c[2]),float(c[3]),
                         float(c[4]),float(c[5]),float(c[9])))
    return rows,{r[0]:i for i,r in enumerate(rows)}

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

# 构建样本: 5M有→14:55价, 无→1D收盘
sa=[];dm=defaultdict(list)
ct5m=0;ct1d=0
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
            r1=rs[d1k];bp=r1[6];sc=r1[4]
            if bp<=0:continue
            r2=rs[d2k];r3=rs[d2k-1] if d2k>=1 else None
            if r3 is None:continue
            
            c2_1455=get_1455(code,d2)
            if c2_1455 is not None:ct5m+=1;c2=c2_1455
            else:ct1d+=1;c2=r2[4]
            
            cl=np.array([r[4] for r in rs[:d2k+1]])
            hi_arr=np.array([r[2] for r in rs[:d2k+1]]);n=len(cl)
            f={}
            f['pb_depth']=(r3[4]-c2)/r3[4]*100 if r3[4]>0 else 0
            f['ma5_dev']=(c2-np.mean(cl[-5:]))/np.mean(cl[-5:])*100 if n>=5 else 0
            if n>=10:
                tr=[]
                for i in range(d2k-9,d2k+1):
                    h=hi_arr[i];l_=rs[i][3];pc=rs[i-1][4] if i>0 else rs[i][6]
                    tr.append(max(h-l_,abs(h-pc),abs(l_-pc)))
                atr=np.mean(tr)
            else:atr=r2[2]-r2[3] if r2[2]>r2[3] else 1
            f['pc_vs_low_atr']=(r2[6]-r2[3])/atr if atr>0 else 0
            f['high_vs_pc_atr']=(r2[2]-r2[6])/atr if atr>0 else 0
            mg=0
            if d2k>=10:
                ca=[r[4] for r in rs[:d2k+1]]
                ma5=np.mean(ca[-5:]);ma10=np.mean(ca[-10:])
                ma5p=np.mean(ca[-6:-1]);ma10p=np.mean(ca[-11:-1])
                mg=1 if(ma5p<=ma10p and ma5>ma10)else 0
            f['ma_golden']=mg
            sa.append((f,code,d1,bp,sc,name,r1[1],r1[2],r1[3],r2[4],d2))

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

print(f'样本: {len(sa)} (5M:{ct5m}, 1D回退:{ct1d})')
print(f'10W起始 | gap<{SPLIT_GAP}分仓 | 万一免五')
print()

# ===== 回测主循环 =====
consec=0
total_value=CAP_START  # 当前总资产(元)
peak_value=CAP_START
max_dd=0.0
trades_log=[]
split_days=0;total_trade_days=0
m_value=defaultdict(list)  # 每月资产变化
m_ret=defaultdict(list)
y_ret=defaultdict(list)
daily_values=[]  # 每日资产

for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:best=sa[idxs[0]];picks=[best];fracs=[1.0]
    else:
        hist=[j for j in range(fi)]
        Xh=X[hist];yh=yt[hist]
        mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
        Xn=(Xh-mu)/sg;d_dim=Xn.shape[1]
        try:w=solve(Xn.T@Xn+np.eye(d_dim)*2.0,Xn.T@yh)
        except:w=np.zeros(d_dim)
        Xt=np.array([(X[i]-mu)/sg for i in idxs]);preds=Xt@w
        ranked=np.argsort(-preds)
        
        if len(ranked)>=2 and (preds[ranked[0]]-preds[ranked[1]])<SPLIT_GAP:
            picks=[sa[idxs[ranked[0]]],sa[idxs[ranked[1]]]]
            fracs=[0.5,0.5];split_days+=1
        else:
            picks=[sa[idxs[ranked[0]]]];fracs=[1.0]
    
    if consec>=3:consec=0;daily_values.append(total_value);continue
    total_trade_days+=1
    
    day_capital_before=total_value
    day_ret_sum=0.0
    
    for pk,cf in zip(picks,fracs):
        bp=pk[3];o=pk[6];h=pk[7];l=pk[8];c=pk[4];code=pk[1];name=pk[5]
        
        # 卖出逻辑
        st=bp*0.94;lu=round(bp*1.10,2)
        if o<=st:sp=o;mode='open_stop'
        elif l<=st:sp=st;mode='low_stop'
        elif h>=lu*0.999:sp=lu;mode='limit_up'
        else:sp=c;mode='close'
        
        # 资金
        cap_for_this=total_value*cf
        if consec>=2:cap_for_this*=0.5
        
        shares=int(cap_for_this/bp/100)*100
        if shares<100:continue
        
        cost=shares*bp*(1+CR)
        revenue=shares*sp*(1-CR-SD-TF)
        profit=revenue-cost
        
        ret_pct=(sp/bp-1)*100 if bp>0 else 0
        
        total_value=total_value-cost+revenue
        
        day_ret_sum+=profit
        
        trades_log.append({
            'date':d1_date,'code':code,'name':name,
            'bp':bp,'sp':sp,'shares':shares,
            'profit':profit,'mode':mode,'cf':cf
        })
    
    if total_value>peak_value:peak_value=total_value
    dd=(total_value-peak_value)/peak_value*100
    if dd<max_dd:max_dd=dd
    
    m=d1_date[:6];y=d1_date[:4]
    daily_values.append(total_value)
    
    day_ret=(total_value/day_capital_before-1)*100
    m_ret[m].append(day_ret);y_ret[y].append(day_ret)
    
    if day_ret<-0.05:consec+=1
    elif day_ret>0.05:consec=0

# ===== 输出 =====
total_ret=(total_value/CAP_START-1)*100
net_value=total_value/CAP_START

print('='*70)
print(f'  最终净值: {net_value:.4f}  总收益: {total_ret:+.1f}%  最大回撤: {max_dd:.1f}%')
print(f'  最终资产: ¥{total_value:,.0f}')
print(f'  交易日: {total_trade_days} | 分仓天数: {split_days} | 胜率: {sum(1 for t in trades_log if t["profit"]>0)/len(trades_log)*100:.1f}%')
print()

print('=== 年度 ===')
cv=CAP_START
for yk in ['2024','2025','2026']:
    if yk not in y_ret:continue
    yr=1.0;rets=[]
    for rv in y_ret[yk]:yr*=(1+rv/100);rets.append(rv)
    cv*=yr
    wins=sum(1 for r in rets if r>0)
    avg_r=np.mean(rets) if rets else 0
    print(f'  {yk}: +{(yr-1)*100:.1f}%  ¥{CAP_START*yr:,.0f}  胜率{wins}/{len(rets)}({wins/len(rets)*100:.0f}%)  日均{avg_r:+.2f}%')

print()
print('=== 月度 ===')
print(f'{"月":<8} {"收益":>8} {"笔数":>5} {"月末资产":>12}')
cv_m=CAP_START
for mm in sorted(m_ret.keys()):
    mr=1.0
    for rv in m_ret[mm]:mr*=(1+rv/100)
    cv_m*=mr
    print(f'{mm[:4]}-{mm[4:]:<3} {(mr-1)*100:>+7.2f}% {len(m_ret[mm]):>5} ¥{cv_m:>11,.0f}')

print()
print('=== 2026月度明细 ===')
cv_m=CAP_START
# Find 2025 year-end value
for mm in sorted(m_ret.keys()):
    if mm<'202601':cv_m*=(np.prod([1+rv/100 for rv in m_ret[mm]]) if m_ret[mm] else 1)
for mm in sorted(m_ret.keys()):
    if mm<'202601':continue
    mr=1.0
    for rv in m_ret[mm]:mr*=(1+rv/100)
    cv_m*=mr
    wins=sum(1 for r in m_ret[mm] if r>0)
    total_n=len(m_ret[mm])
    print(f'{mm[:4]}-{mm[4:]:<3} {(mr-1)*100:>+7.2f}% {total_n:>4}笔 胜{wins}/{total_n} ¥{cv_m:>11,.0f}')

# 卖出方式
modes=defaultdict(lambda:{'count':0,'total':0.0})
for t in trades_log:
    modes[t['mode']]['count']+=1
    modes[t['mode']]['total']+=t['profit']
print()
print('=== 卖出方式 ===')
for md in ['close','limit_up','low_stop','open_stop']:
    if md in modes:
        c=modes[md]['count'];tot=modes[md]['total']
        print(f'  {md:<12} {c:>4}笔  盈亏¥{tot:>+12,.0f}')

# 分仓效果
split_trades=[t for t in trades_log if t['cf']==0.5]
single_trades=[t for t in trades_log if t['cf']==1.0]
if split_trades and single_trades:
    sw=sum(1 for t in split_trades if t['profit']>0)/len(split_trades)*100
    iw=sum(1 for t in single_trades if t['profit']>0)/len(single_trades)*100
    sp=sum(t['profit'] for t in split_trades)
    ip=sum(t['profit'] for t in single_trades)
    print(f'\n分仓({len(split_trades)}笔): 胜率{sw:.0f}% 盈亏¥{sp:+.0f}  单仓({len(single_trades)}笔): 胜率{iw:.0f}% 盈亏¥{ip:+.0f}')
