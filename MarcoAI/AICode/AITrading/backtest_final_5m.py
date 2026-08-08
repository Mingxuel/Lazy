# -*- coding: utf-8 -*-
"""311策略 最终回测: 5M 14:55价 | 不分仓 | D-1 OHLC卖出 | 10W起始 | 万一免五"""
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

def fee(bp,sp,cap):
    sh=int(cap/bp/100)*100
    if sh==0:return 0
    return (sp*sh*(1-CR-SD-TF)-bp*sh*(1+CR))/(bp*sh)*100

def sd(bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o,'open_stop'
    if l<=st:return st,'low_stop'
    if h>=lu*0.999:return lu,'limit_up'
    return c,'close'

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

# Build samples with 5M 14:55 price
sa=[];dm=defaultdict(list);hit=0;miss=0
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

            bar55=get_bar(code,d2,-2)  # 14:55
            if bar55:hit+=1
            else:miss+=1
            c2_pb=bar55[3] if bar55 else r2[4]
            pre_pb=r3[4]

            if bar55:
                bars5=lm5(code).get(d2,[])
                scale=r2[4]/bars5[-1][3] if bars5[-1][3]>0 else 1.0
                o5=bar55[0]*scale;h5=bar55[1]*scale;l5=bar55[2]*scale
                pc5=r3[4]
            else:
                o5=r2[1];h5=r2[2];l5=r2[3];pc5=r2[6]

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
            sa.append((f,code,d1,bp,sc,name,o5,h5,l5,c2_pb,pre_pb,d2,
                       r1[1],r1[2],r1[3],r1[4]))  # D-1 OHLC

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

# Backtest
consec=0;cum_r=1.0;peak=1.0;max_dd=0.0
mm=defaultdict(list);yy=defaultdict(list);qq=defaultdict(list)
mode_stats=defaultdict(int);trades_all=[]
all_ret_list=[];skip_count=0;half_count=0

for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:best=sa[idxs[0]]
    else:
        hist=[j for j in range(fi)]
        Xh=X[hist];yh=yt[hist]
        mu=Xh.mean(axis=0);sg=Xh.std(axis=0)+1e-8
        Xn=(Xh-mu)/sg;d_dim=Xn.shape[1]
        try:w=solve(Xn.T@Xn+np.eye(d_dim)*2.0,Xn.T@yh)
        except:w=np.zeros(d_dim)
        Xt=np.array([(X[i]-mu)/sg for i in idxs])
        best=sa[idxs[int(np.argmax(Xt@w))]]

    if consec>=3:
        skip_count+=1;consec=0;continue

    cap_base=CAPITAL*cum_r
    is_half=consec>=2
    cap=cap_base*0.5 if is_half else cap_base
    if is_half:half_count+=1

    bp=best[3];o=best[12];h=best[13];l=best[14];c=best[15]
    sp,mode=sd(bp,o,h,l,c)
    ret=fee(bp,sp,cap)
    cum_r*=(1+ret/100)
    if cum_r>peak:peak=cum_r
    dd=(cum_r-peak)/peak*100
    if dd<max_dd:max_dd=dd
    if ret<-0.05:consec+=1
    elif ret>0.05:consec=0

    m=d1_date[:6];q=d1_date[:4]+'Q'+str((int(d1_date[4:6])-1)//3+1);y=d1_date[:4]
    mm[m].append(ret);yy[y].append(ret);qq[q].append(ret)
    md_label=mode+' [半仓]' if is_half else mode
    mode_stats[md_label]+=1
    all_ret_list.append(ret)
    trades_all.append((d1_date,best[5],best[1],bp,sp,ret,md_label,cum_r))

# ==== 输出 ====
final=CAPITAL*cum_r
trades=len(trades_all)
wins=sum(1 for t in trades_all if t[5]>0)
losses=sum(1 for t in trades_all if t[5]<0)
wr=wins/trades*100 if trades else 0

print('='*80)
print(' 311策略 最终回测')
print('='*80)
print(f'模型: 5特征 Walk-Forward 岭回归')
print(f'数据: 5M K线 14:55价 (pb_depth) + 1D日线 (其余+卖出OHLC)')
print(f'买入: D-2 14:57 TPO3最优 @ 收盘价×1.01')
print(f'卖出: 止损-6% > 涨停 > D-1收盘 | 仓位: 连亏2半仓/连亏3跳过')
print(f'费率: 万一免五 | 起始: ¥{CAPITAL:,} | 5M命中: {hit}/{hit+miss}')
print()
print(f'{"净值":<12} {cum_r:>8.4f}')
print(f'{"总收益":<12} {(cum_r-1)*100:>+8.1f}%')
print(f'{"最终资产":<12} ¥{final:>12,.0f}')
print(f'{"最大回撤":<12} {max_dd:>7.1f}%')
print(f'{"交易笔数":<12} {trades:>8}')
print(f'{"盈利":<12} {wins:>8} ({wr:.1f}%)')
print(f'{"亏损":<12} {losses:>8}')
print(f'{"跳过":<12} {skip_count:>8}')
print(f'{"半仓":<12} {half_count:>8}')

# 月度
print();print('='*70)
print('  月度盈亏')
print('='*70)
cv=1.0
for y in ['2024','2025','2026']:
    print(f'\n  {y}年:')
    for m in ['01','02','03','04','05','06','07','08','09','10','11','12']:
        kl=y+m
        if kl not in mm:continue
        mr=1.0
        for rv in mm[kl]:mr*=(1+rv/100)
        cv*=mr
        cnt=len(mm[kl])
        wr_m=sum(1 for rv in mm[kl] if rv>0)/cnt*100 if cnt else 0
        bar='█'*max(1,cnt//2)
        print(f'  {kl[:4]}-{kl[4:]}  +{(mr-1)*100:>+7.2f}%  {cnt:>3}笔  胜{wr_m:.0f}%  净值{cv:.2f}  {bar}')

# 季度
print();print('='*70)
print('  季度盈亏')
print('='*70)
for q in sorted(qq.keys()):
    qr=1.0
    for rv in qq[q]:qr*=(1+rv/100)
    cnt=len(qq[q])
    print(f'  {q}: +{(qr-1)*100:>+8.2f}%  ({cnt}笔)')

# 年度
print();print('='*70)
print('  年度盈亏')
print('='*70)
cv2=1.0
for y in sorted(yy.keys()):
    yr=1.0
    for rv in yy[y]:yr*=(1+rv/100)
    cv2*=yr
    cnt=len(yy[y])
    wr_y=sum(1 for rv in yy[y] if rv>0)/cnt*100
    print(f'  {y}: +{(yr-1)*100:>+8.1f}%  胜率{wr_y:.1f}%  {cnt}笔  净值{cv2:.2f}')

# 卖出方式
print();print('='*70)
print('  卖出方式分布')
print('='*70)
for md in sorted(mode_stats.keys()):
    cnt=mode_stats[md]
    pct=cnt/trades*100
    print(f'  {md:<20} {cnt:>4} ({pct:>5.1f}%)')

# 月度胜率热力图
print();print('='*70)
print('  月度胜率')
print('='*70)
for y in ['2024','2025','2026']:
    row=f'  {y}  '
    for m in ['01','02','03','04','05','06','07','08','09','10','11','12']:
        kl=y+m
        if kl in mm:
            wr_m=sum(1 for rv in mm[kl] if rv>0)/len(mm[kl])*100
            if wr_m>=65:row+='🟩'
            elif wr_m>=50:row+='🟨'
            else:row+='🟥'
        else:
            row+='⬜'
    print(row)

# Top/Bottom 10
print();print('='*70)
print('  最佳10笔')
print('='*70)
top=sorted([t for t in trades_all if t[5]>=0],key=lambda x:-x[5])[:10]
for t in top:
    print(f'  {t[0]} {t[1]:<8} {t[2]}  买{t[3]:.2f}→卖{t[4]:.2f}  {t[5]:+.2f}% [{t[6]}]')

print();print('  最差10笔')
print('='*70)
bot=sorted([t for t in trades_all if t[5]<0],key=lambda x:x[5])[:10]
for t in bot:
    print(f'  {t[0]} {t[1]:<8} {t[2]}  买{t[3]:.2f}→卖{t[4]:.2f}  {t[5]:+.2f}% [{t[6]}]')
