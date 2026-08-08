# -*- coding: utf-8 -*-
"""311 最终完整回测: 5M 14:55价 + 5特征 + 单仓 + 真实股数 + 手续费"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001; CM=0.0; SD=0.0005; TF=0.00001
INIT_CAPITAL=100_000

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

def trade(bp,sp,capital):
    """实际买入卖出, 返回(收益%, 盈亏金额, 买入金额, 卖出金额, 股数)"""
    shares=int(capital/bp/100)*100
    if shares<100:return None
    buy_amt=bp*shares
    comm_buy=buy_amt*CR
    sell_amt=sp*shares
    comm_sell=sell_amt*CR
    stamp=sell_amt*SD
    tfee=sell_amt*TF
    total_cost=buy_amt+comm_buy
    total_return=sell_amt-comm_sell-stamp-tfee
    profit=total_return-total_cost
    ret_pct=profit/total_cost*100
    return ret_pct, profit, total_cost, total_return, shares

def sell_decision(bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o,'open_stop'
    if l<=st:return bp*0.94,'low_stop'
    if h>=lu*0.999:return lu,'limit_up'
    return c,'close'

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

# ====== 构建样本 ======
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
            sa.append((f,code,d1,bp,sp_c,name,o5,h5,l5,c5,pre_pb,d2,
                       r1[1],r1[2],r1[3],r1[4]))

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

# ====== Walk-Forward 回测 ======
consec=0
asset=INIT_CAPITAL
peak=INIT_CAPITAL
max_dd=0.0
trades=[]       # 每笔交易明细
monthly={}      # 月度
quarterly={}    # 季度
annual={}       # 年度
mode_stats=defaultdict(int)
skip_count=0

for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:
        best=sa[idxs[0]]
    else:
        hist=[j for j in range(fi)]
        Xh=X[hist];yh=yt[hist]
        mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
        Xn=(Xh-mu)/sg;d_dim=Xn.shape[1]
        try:w=solve(Xn.T@Xn+np.eye(d_dim)*2.0,Xn.T@yh)
        except:w=np.zeros(d_dim)
        Xt=np.array([(X[i]-mu)/sg for i in idxs])
        preds=Xt@w
        best=sa[idxs[int(np.argmax(preds))]]

    code=best[1];name=best[5];bp=best[3]
    o=best[12];h=best[13];l=best[14];c=best[15]

    # 仓位管理
    if consec>=3:
        trades.append({'date':d1_date,'name':name,'code':code,'bp':bp,'sp':0,'ret':0,
                       'shares':0,'cost':0,'profit':0,'asset':asset,'mode':'skip','consec':consec})
        consec=0;skip_count+=1;continue

    factor=0.5 if consec>=2 else 1.0
    capital_use=asset*factor

    # 卖出
    sp,mode=sell_decision(bp,o,h,l,c)
    result=trade(bp,sp,capital_use)
    if result is None:
        trades.append({'date':d1_date,'name':name,'code':code,'bp':bp,'sp':sp,'ret':0,
                       'shares':0,'cost':0,'profit':0,'asset':asset,'mode':'funds_insufficient','consec':consec})
        skip_count+=1;continue

    ret_pct,profit,buy_amt,sell_amt,shares=result
    asset+=profit
    if asset>peak:peak=asset
    dd=(asset-peak)/peak*100
    if dd<max_dd:max_dd=dd

    if ret_pct<-0.05:consec+=1
    elif ret_pct>0.05:consec=0

    trades.append({'date':d1_date,'name':name,'code':code,'bp':bp,'sp':sp,'ret':ret_pct,
                   'shares':shares,'cost':buy_amt,'profit':profit,'asset':asset,
                   'mode':mode,'consec':consec})
    mode_stats[mode]+=1

# ====== 统计 ======
trade_records=[t for t in trades if t['mode']!='skip']
wr=sum(1 for t in trade_records if t['ret']>0)/len(trade_records)*100

# 月/季/年
for t in trade_records:
    m=t['date'][:6];q=t['date'][:4]+'Q'+str((int(t['date'][4:6])-1)//3+1);y=t['date'][:4]
    if m not in monthly:monthly[m]={'rets':[],'assets':[]}
    if q not in quarterly:quarterly[q]={'rets':[],'assets':[]}
    if y not in annual:annual[y]={'rets':[],'assets':[]}
    monthly[m]['rets'].append(t['ret']);monthly[m]['assets'].append(t['asset'])
    quarterly[q]['rets'].append(t['ret']);quarterly[q]['assets'].append(t['asset'])
    annual[y]['rets'].append(t['ret']);annual[y]['assets'].append(t['asset'])

# ====== 输出 ======
net_v=asset/INIT_CAPITAL
print(f'{"="*70}')
print(f'  311 策略 最终回测报告')
print(f'{"="*70}')
print(f'  版本: 5特征 WF岭回归 | 5M 14:55价格 | 单仓 | 实际股数+手续费')
print(f'  费率: 万一免五(佣金0.01%,印花0.05%,过户0.001%)')
print(f'  起始资金: ¥{INIT_CAPITAL:,.0f}')
print(f'  最终资产: ¥{asset:,.0f}')
print(f'  净值: {net_v:.4f}')
print(f'  总收益: +{(net_v-1)*100:.1f}%')
print(f'  最大回撤: {max_dd:.1f}%')
wins_count=sum(1 for t in trade_records if t['ret']>0)
loss_count=sum(1 for t in trade_records if t['ret']<0)
print(f'  交易笔数: {len(trade_records)} | 胜{wins_count}负{loss_count} | 胜率{wr:.1f}%')
print(f'  跳过天数: {skip_count}')
print()

print('一、年度收益')
print(f'  {"年份":<6} {"收益":>10} {"胜率":>8} {"笔数":>6} {"年末资产":>14}')
print(f'  {"-"*50}')
cv=INIT_CAPITAL
for yk in sorted(annual.keys()):
    mr=1.0
    for rv in annual[yk]['rets']:mr*=(1+rv/100)
    cv*=(1+mr-1) if len(annual[yk]['rets'])>0 else 1
    wins=sum(1 for rv in annual[yk]['rets'] if rv>0)
    nall=len(annual[yk]['rets'])
    wr_y=wins/nall*100 if nall else 0
    last_a=annual[yk]['assets'][-1] if annual[yk]['assets'] else 0
    print(f'  {yk:<6} {(mr-1)*100:>+9.1f}% {wr_y:>7.1f}% {nall:>6} ¥{last_a:>12,.0f}')

print()
print('二、季度收益')
print(f'  {"季度":<8} {"收益":>10} {"笔数":>6} {"季末资产":>14}')
print(f'  {"-"*50}')
for qk in sorted(quarterly.keys()):
    qr=1.0
    for rv in quarterly[qk]['rets']:qr*=(1+rv/100)
    nall=len(quarterly[qk]['rets'])
    last_a=quarterly[qk]['assets'][-1] if quarterly[qk]['assets'] else 0
    print(f'  {qk:<8} {(qr-1)*100:>+9.2f}% {nall:>6} ¥{last_a:>12,.0f}')

print()
print('三、月度收益')
print(f'  {"月份":<8} {"收益":>10} {"笔数":>6} {"胜率":>8} {"月末资产":>14}')
print(f'  {"-"*60}')
last_asset=INIT_CAPITAL
for mk in sorted(monthly.keys()):
    mr=1.0
    for rv in monthly[mk]['rets']:mr*=(1+rv/100)
    wins=sum(1 for rv in monthly[mk]['rets'] if rv>0)
    nall=len(monthly[mk]['rets'])
    wr_m=wins/nall*100 if nall else 0
    a_end=monthly[mk]['assets'][-1] if monthly[mk]['assets'] else 0
    flag=' ⚡'if (mr-1)*100>20 else(' 🔴'if (mr-1)*100<0 else'')
    print(f'  {mk[:4]}-{mk[4:]:<3} {(mr-1)*100:>+9.2f}% {nall:>6} {wr_m:>7.1f}% ¥{a_end:>12,.0f}{flag}')

print()
print('四、卖出方式统计')
for m,cnt in sorted(mode_stats.items(),key=lambda x:-x[1]):
    print(f'  {m}: {cnt}次 ({cnt/len(trade_records)*100:.1f}%)')

print()
print('五、最佳/最差单笔')
sorted_trades=sorted(trade_records,key=lambda x:-x['ret'])
print('  Top 5:')
for t in sorted_trades[:5]:
    print(f'    {t["date"]} {t["name"]}({t["code"]}) 买¥{t["bp"]:.2f}→卖¥{t["sp"]:.2f}  {t["ret"]:+.2f}% [{t["mode"]}]')
print('  Bottom 5:')
for t in sorted_trades[-5:]:
    print(f'    {t["date"]} {t["name"]}({t["code"]}) 买¥{t["bp"]:.2f}→卖¥{t["sp"]:.2f}  {t["ret"]:+.2f}% [{t["mode"]}]')

print()
print('六、全部交易明细 (前30笔)')
print(f'  {"日期":<10} {"名称":<10} {"代码":<12} {"买入":>8} {"卖出":>8} {"收益":>7} {"盈亏":>10} {"资产":>12} {"方式":>12}')
print(f'  {"-"*85}')
for t in trades[:30]:
    if t['mode']=='skip':
        print(f'  {t["date"]:<10} {"跳过(连亏3次)":<22} {"—":>15} {"—":>12} {"skip":>12}')
    elif t['mode']=='funds_insufficient':
        print(f'  {t["date"]:<10} {t["name"]:<10} {t["code"]:<12} {"资金不足":>8} {"":>8} {"":>7} {"":>10} {"":>12} {"funds_insufficient":>12}')
    else:
        print(f'  {t["date"]:<10} {t["name"]:<10} {t["code"]:<12} {t["bp"]:>8.2f} {t["sp"]:>8.2f} {t["ret"]:>+6.2f}% ¥{t["profit"]:>8,.0f} ¥{t["asset"]:>10,.0f} {t["mode"]:>12}')

if len(trades)>30:
    print(f'  ... 共{len(trades)}笔, 完整明细见脚本输出')
