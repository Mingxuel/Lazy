# -*- coding: utf-8 -*-
"""311 趋势拿票回测: 买入后持有直到收盘破MA5才卖 | 10W起始"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001
CAPITAL=100_000

print('加载数据...')

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

def fee(bp,sp,cap):
    sh=int(cap/bp/100)*100
    if sh==0:return 0
    return (sp*sh*(1-CR-SD-TF)-bp*sh*(1+CR))/(bp*sh)*100

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

# --- 构建样本 (和5M 14:55版完全一致) ---
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
            r1=rs[d1k];bp=r1[6];sc=r1[4]
            if bp<=0:continue
            r2=rs[d2k];r3=rs[d2k-1] if d2k>=1 else None
            if r3 is None:continue
            bar55=get_bar(code,d2,-2)
            c2_pb=bar55[3] if bar55 else r2[4]
            pre_pb=r3[4]
            if bar55:
                bars5=lm5(code).get(d2,[])
                scale=r2[4]/bars5[-1][3] if bars5[-1][3]>0 else 1.0
                o5=bar55[0]*scale;h5=bar55[1]*scale;l5=bar55[2]*scale
                pc5=r3[4]
            else:o5=r2[1];h5=r2[2];l5=r2[3];pc5=r2[6]
            cl=np.array([r[4] for r in rs[:d2k+1]]);hi=np.array([r[2] for r in rs[:d2k+1]]);n=len(cl)
            f={}
            f['pb_depth']=(pre_pb-c2_pb)/pre_pb*100 if pre_pb>0 else 0
            f['ma5_dev']=(c2_pb-np.mean(cl[-5:]))/np.mean(cl[-5:])*100 if n>=5 else 0
            if n>=10:
                tr=[]
                for i in range(d2k-9,d2k+1):
                    hh=hi[i];l_=rs[i][3];pc=rs[i-1][4] if i>0 else rs[i][6]
                    tr.append(max(hh-l_,abs(hh-pc),abs(l_-pc)))
                atr=np.mean(tr)
            else:atr=r2[2]-r2[3] if r2[2]>r2[3] else 1
            f['pc_vs_low_atr']=(pc5-l5)/atr if atr>0 else 0
            f['high_vs_pc_atr']=(h5-pc5)/atr if atr>0 else 0
            mg=0
            if d2k>=10:
                ca=[r[4] for r in rs[:d2k+1]]
                ma5=np.mean(ca[-5:]);ma10=np.mean(ca[-10:])
                ma5p=np.mean(ca[-6:-1]);ma10p=np.mean(ca[-11:-1])
                mg=1 if(ma5p<=ma10p and ma5>ma10)else 0
            f['ma_golden']=mg
            # D-2 date = d2 (the date we would buy at)
            sa.append((f,code,d1,bp,sc,name,o5,h5,l5,c2_pb,pre_pb,d2))

print(f'样本: {len(sa)}')
sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

# --- 按买入日(D-2)重新组织数据 ---
# 每只股票的完整K线缓存
kline_cache={}
def get_stock_ohlc(code,date):
    """获取某日某股的 OHLC + preClose  + close"""
    if code not in kline_cache:
        rows,idx=lk(code)
        kline_cache[code]=(rows,idx)
    rows,idx=kline_cache[code]
    i=idx.get(date)
    if i is None:return None
    r=rows[i]
    return (r[0],r[1],r[2],r[3],r[4],r[5],r[6])  # date,o,h,l,c,vol,preClose

def get_ma5(code,upto_date):
    """MA5 at given date's close (含该日)"""
    rows,idx=kline_cache.get(code,(None,None))
    if rows is None:
        rows2,idx2=lk(code)
        kline_cache[code]=(rows2,idx2)
        rows,idx=rows2,idx2
    i=idx.get(upto_date)
    if i is None or i<4:return None
    closes=[rows[j][4] for j in range(i-4,i+1)]
    return np.mean(closes)

# 创建按买入日索引: buy_date -> [candidates]
buy_day_samples=defaultdict(list)
for i,s in enumerate(sa):
    buy_date=s[11]  # d2 = D-2 = buy day
    buy_day_samples[buy_date].append(i)

buy_dates=sorted(buy_day_samples.keys())

print(f'买入日: {len(buy_dates)}')
print('开始趋势拿票回测...')

# --- 主回测 ---
consec_loss=0;cum=1.0;peak=1.0;max_dd=0.0
mm=defaultdict(list);yy=defaultdict(list);qq=defaultdict(list)
hold_stat=defaultdict(int)   # 持有天数统计
trades_all=[];skip_count=0;half_count=0

holding=False;hold_code=None;hold_bp=0;hold_vol=0;hold_buy_date=''
hold_name=''

for day_idx, buy_date in enumerate(buy_dates):
    # 1) 先处理持仓: 检查今天是否需要卖出
    sold_today=False;sell_ret=0.0;sell_mode='';sold_code=None

    if holding:
        ohlc=get_stock_ohlc(hold_code,buy_date)
        if ohlc is None:
            holding=False;continue

        d,o,h,l,c,v,pre=ohlc
        stop_price=hold_bp*0.94
        limit_up=round(hold_bp*1.10,2)
        ma5=get_ma5(hold_code,buy_date)

        # 止损-6%
        if o<=stop_price:
            sp=o;sell_mode='open_stop'
        elif l<=stop_price:
            sp=stop_price;sell_mode='low_stop'
        # 涨停
        elif h>=limit_up*0.999:
            sp=limit_up;sell_mode='limit_up'
        # MA5破位
        elif ma5 is not None and c<=ma5:
            sp=c;sell_mode='ma5_break'
        else:
            # 继续持有
            hold_stat[(buy_date,hold_buy_date,hold_code)]+=1
            continue

        # 卖出
        sell_ret=fee(hold_bp,sp,CAPITAL*cum*(0.5 if consec_loss>=2 else 1))
        cum*=(1+sell_ret/100)
        if cum>peak:peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd:max_dd=dd
        hold_days=(tds.index(buy_date)-tds.index(hold_buy_date)+1)
        trades_all.append((buy_date,hold_name,hold_code,hold_bp,sp,sell_ret,
                          sell_mode,f'持{hold_days}天',cum))
        m=buy_date[:6];q=buy_date[:4]+'Q'+str((int(buy_date[4:6])-1)//3+1);y=buy_date[:4]
        mm[m].append(sell_ret);yy[y].append(sell_ret);qq[q].append(sell_ret)
        if sell_ret<-0.05:consec_loss+=1
        elif sell_ret>0.05:consec_loss=0
        sold_today=True
        holding=False

    # 2) 买入 (空仓或刚卖出)
    if not holding:
        if consec_loss>=3:
            skip_count+=1;consec_loss=0;continue

        # WF 训练: 用 buy_date 之前所有 sell_day 的样本
        # sell_day = 买入日对应策略文件的日期 (即 buy_date 之后的下一个交易日)
        # 但更简单: 取 buy_date 在 buy_dates 中之前的所有样本
        # 样本是按 sell_day 排列的, 我们需要的是: 所有 sell_day < buy_date对应的后一个交易日的样本
        
        # 简化: 取样本中所有 d2 < buy_date 的作为训练集
        train_idx=[j for j,s in enumerate(sa) if s[2]<buy_date]  # s[2]=d1=sell_day
        if len(train_idx)<100:
            # 前100天: 取第一个候选
            idxs=buy_day_samples[buy_date]
            if not idxs:continue
            best=sa[idxs[0]]
        else:
            Xh=X[train_idx];yh=yt[train_idx]
            mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
            Xn=(Xh-mu)/sg
            try:w=solve(Xn.T@Xn+np.eye(5)*2.0,Xn.T@yh)
            except:w=np.zeros(5)
            idxs=buy_day_samples[buy_date]
            if not idxs:continue
            Xt=np.array([(X[i]-mu)/sg for i in idxs])
            preds=Xt@w
            best=sa[idxs[int(np.argmax(preds))]]

        bp=best[9]  # c2_pb (14:55 close)
        hold_bp=bp
        hold_code=best[1]
        hold_name=best[5]
        hold_buy_date=buy_date
        holding=True

        # 立即检查买入当天是否触发止损(开盘/最低)
        ohlc_buy=get_stock_ohlc(hold_code,buy_date)
        if ohlc_buy:
            dd_b,oo,hh,ll,cc,vv,pp=ohlc_buy
            stop_p=hold_bp*0.94
            lu_p=round(hold_bp*1.10,2)
            ma5_b=get_ma5(hold_code,buy_date)
            if oo<=stop_p:
                sell_ret=fee(hold_bp,oo,CAPITAL*cum)
                cum*=(1+sell_ret/100)
                trades_all.append((buy_date,hold_name,hold_code,hold_bp,oo,sell_ret,
                                  'open_stop_same','持1天',cum))
                if sell_ret<-0.05:consec_loss+=1
                else:consec_loss=0
                holding=False;hold_code=None
            elif ll<=stop_p:
                sell_ret=fee(hold_bp,stop_p,CAPITAL*cum)
                cum*=(1+sell_ret/100)
                trades_all.append((buy_date,hold_name,hold_code,hold_bp,stop_p,sell_ret,
                                  'low_stop_same','持1天',cum))
                if sell_ret<-0.05:consec_loss+=1
                else:consec_loss=0
                holding=False;hold_code=None

# 还剩未平仓的按最后一天收盘出
if holding:
    last_buy_date=buy_dates[-1]
    ohlc_last=get_stock_ohlc(hold_code,last_buy_date)
    if ohlc_last:
        c_last=ohlc_last[4]
        sp_last=c_last
        sell_ret=fee(hold_bp,sp_last,CAPITAL*cum)
        cum*=(1+sell_ret/100)
        trades_all.append((last_buy_date,hold_name,hold_code,hold_bp,sp_last,sell_ret,
                          'close_last','持至结束',cum))
        if sell_ret<-0.05:consec_loss+=1

# ==== 输出 ====
final=CAPITAL*cum
trades=len(trades_all)
wins=sum(1 for t in trades_all if t[5]>0)
losses=sum(1 for t in trades_all if t[5]<0)

print();print('='*80)
print(' 311 趋势拿票回测 (不破MA5就持有)')
print('='*80)
print(f'卖出规则: 止损-6% > 涨停 > 跌破MA5(<=) > 继续持有')
print(f'买入: 卖出当天立即买下一只 TPO3 最优股')
print(f'费率: 万一免五 | 起始: ¥{CAPITAL:,}')
print()
print(f'{"净值":<12} {cum:>8.4f}')
print(f'{"总收益":<12} {(cum-1)*100:>+8.1f}%')
print(f'{"最终资产":<12} ¥{final:>12,.0f}')
print(f'{"最大回撤":<12} {max_dd:>7.1f}%')
print(f'{"交易笔数":<12} {trades:>8}')
print(f'{"盈利":<12} {wins:>8} ({wins/trades*100:.1f}%)' if trades else '')
print(f'{"亏损":<12} {losses:>8}')

# 持有天数分布
print();print('=== 持有天数分布 ===')
hold_days_list=[t[8] for t in trades_all]
from collections import Counter
hd_counter=Counter()
for t in trades_all:
    d=t[8]
    if d=='持至结束':hd_counter['99+']+=1
    else:
        try:n=int(d.replace('持','').replace('天',''))
        except:n=1
        hd_counter[n]+=1
for k in sorted(hd_counter.keys(),key=lambda x:99 if x=='99+' else x):
    print(f'  持{k}天: {hd_counter[k]}笔')

# 按卖出方式统计
print();print('=== 卖出方式 ===')
mode_counter=Counter()
for t in trades_all:
    md=t[6]
    mode_counter[md]+=1
for md,cnt in mode_counter.most_common():
    print(f'  {md:<20} {cnt:>4}')

# 年度
print();print('=== 年度 ===')
cv=1.0
for y in sorted(yy.keys()):
    yr=1.0
    for rv in yy[y]:yr*=(1+rv/100)
    cv*=yr
    cnt=len(yy[y]);wr=sum(1 for rv in yy[y] if rv>0)/cnt*100
    print(f'  {y}: +{(yr-1)*100:>+8.1f}%  胜率{wr:.1f}%  {cnt}笔  净值{cv:.2f}')

# 月度
print();print('=== 月度 ===')
cv2=1.0
for m in sorted(mm.keys()):
    mr=1.0
    for rv in mm[m]:mr*=(1+rv/100)
    cv2*=mr
    cnt=len(mm[m]);wr=sum(1 for rv in mm[m] if rv>0)/cnt*100 if cnt else 0
    if m>='202601':
        print(f'  {m[:4]}-{m[4:]}  +{(mr-1)*100:>+7.2f}%  {cnt}笔  胜{wr:.0f}%')

# vs 基准
print();print(f'=== vs 基准(单日收盘卖) ===')
base_cum=8.8016
print(f'  基准净值: {base_cum:.4f}  趋势净值: {cum:.4f}')
print(f'  差: {(cum/base_cum-1)*100:+.1f}%')

# Best/Worst
print();print('=== 最佳5笔 ===')
top=sorted(trades_all,key=lambda x:-x[5])[:5]
for t in top:
    print(f'  {t[0]} {t[1]:<8} {t[2]}  买{t[3]:.2f}→卖{t[4]:.2f}  {t[5]:+.2f}% [{t[6]}] {t[8]}')
print();print('=== 最差5笔 ===')
bot=sorted(trades_all,key=lambda x:x[5])[:5]
for t in bot:
    print(f'  {t[0]} {t[1]:<8} {t[2]}  买{t[3]:.2f}→卖{t[4]:.2f}  {t[5]:+.2f}% [{t[6]}] {t[8]}')
