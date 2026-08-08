# -*- coding: utf-8 -*-
"""分仓21天 逐笔盈亏明细"""
import os, numpy as np
from collections import defaultdict
from numpy.linalg import solve

S=r'C:\Lazy\李明学的大A\Data\Strategy'; K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'
FEATURES=['pb_depth','ma5_dev','pc_vs_low_atr','high_vs_pc_atr','ma_golden']
CR=0.0001;CM=0.0;SD=0.0005;TF=0.00001
CAPITAL=100_000

def lk(code):
    fp=os.path.join(K,code);rows=[]
    with open(fp) as f:
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

def get_1455_price(code,d2_date):
    bars=lm5(code).get(d2_date,[])
    if len(bars)>=2:return bars[-2][3]
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

sa=[]
dm=defaultdict(list)
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

            # 5M 14:55价 -> pb_depth
            p1455=get_1455_price(code,d2)
            c2_for_pb=p1455 if p1455 else r2[4]
            pre_for_pb=r3[4]

            # 用5M 14:55的OHLC (如果有) 否则用1D
            if p1455:
                bars5=lm5(code).get(d2,[])
                # 从倒数第2根取5M K线的OHLC → 缩放对齐1D
                scale=r2[4]/bars5[-1][3] if bars5[-1][3]>0 else 1.0
                o5=bars5[-2][0]*scale;h5=bars5[-2][1]*scale;l5=bars5[-2][2]*scale;c5=bars5[-2][3]*scale
                pc5=r3[4]  # D-3收盘 = D-2昨收
            else:
                o5=r2[1];h5=r2[2];l5=r2[3];c5=r2[4];pc5=r2[6]

            cl=np.array([r[4] for r in rs[:d2k+1]]);hi=np.array([r[2] for r in rs[:d2k+1]]);n=len(cl)
            f={}
            f['pb_depth']=(pre_for_pb-c2_for_pb)/pre_for_pb*100 if pre_for_pb>0 else 0
            f['ma5_dev']=(c2_for_pb-np.mean(cl[-5:]))/np.mean(cl[-5:])*100 if n>=5 else 0
            if n>=10:
                tr=[]
                for i in range(d2k-9,d2k+1):
                    h=hi[i];l_=rs[i][3];pc=rs[i-1][4] if i>0 else rs[i][6]
                    tr.append(max(h-l_,abs(h-pc),abs(l_-pc)))
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
            sa.append((f,code,d1,bp,sc,name,o5,h5,l5,c5,pc5,d2,r2[1],r2[2],r2[3],r2[4],r2[6]))

sa.sort(key=lambda x:x[2])
dm2=defaultdict(list)
for i,s in enumerate(sa):dm2[s[2]].append(i)
dm=dm2;ad=sorted(dm.keys())
X=np.array([[s[0].get(k,0) for k in FEATURES] for s in sa])
yt=np.array([(s[4]-s[3])/s[3]*100 for s in sa])

consec=0;cum=1.0;peak=1.0;max_dd=0.0
split_trades=[]
no_split_trades=[]

for d1_date in ad:
    idxs=dm[d1_date];fi=idxs[0]
    if fi<100:
        best=sa[idxs[0]]
        # 手动算最简单的评分: 用全局mean/std 近似
        Xt=np.array([(X[i]-X.mean(axis=0))/(X.std(axis=0)+1e-8) for i in idxs])
        preds=Xt@np.ones(len(FEATURES))/len(FEATURES)
        ranked=np.argsort(-preds)
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

    if consec>=3:consec=0;continue

    cap_base=CAPITAL*cum
    cap=cap_base*(0.5 if consec>=2 else 1.0)

    if len(ranked)>=2 and preds[ranked[0]]-preds[ranked[1]]<0.10:
        # 分仓模式: 各一半
        s1=sa[idxs[ranked[0]]];s2=sa[idxs[ranked[1]]]
        bp1=s1[3];bp2=s2[3]
        cap1=cap*0.5;cap2=cap*0.5

        # 用1D D-1 OHLC(卖出日) — 索引: 13=1D_o, 14=1D_h, 15=1D_l, 16=1D_c
        sp1,m1=sd(bp1,s1[13],s1[14],s1[15],s1[16])
        sp2,m2=sd(bp2,s2[13],s2[14],s2[15],s2[16])
        ret1=fee(bp1,sp1,cap1)
        ret2=fee(bp2,sp2,cap2)

        # 按权重算加权收益
        sh1=int(cap1/bp1/100)*100;sh2=int(cap2/bp2/100)*100
        tcost=sh1*bp1*(1+CR)+sh2*bp2*(1+CR)
        tret=sh1*sp1*(1-CR-SD-TF)+sh2*sp2*(1-CR-SD-TF)
        combined_ret=(tret-tcost)/tcost*100

        cum*=(1+combined_ret/100)
        if cum>peak:peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd:max_dd=dd
        if combined_ret<-0.05:consec+=1
        elif combined_ret>0.05:consec=0

        split_trades.append({
            'date':d1_date,
            'c1_name':s1[5],'c1_code':s1[1],'c1_ret':ret1,'c1_bp':bp1,'c1_sp':sp1,'c1_mode':m1,
            'c2_name':s2[5],'c2_code':s2[1],'c2_ret':ret2,'c2_bp':bp2,'c2_sp':sp2,'c2_mode':m2,
            'combined':combined_ret,'gap':preds[ranked[0]]-preds[ranked[1]],
            'c1_score':preds[ranked[0]],'c2_score':preds[ranked[1]]
        })
    else:
        s1=sa[idxs[ranked[0]]]
        bp=s1[3]
        sp,mode=sd(bp,s1[13],s1[14],s1[15],s1[16])
        ret=fee(bp,sp,cap)
        cum*=(1+ret/100)
        if cum>peak:peak=cum
        dd=(cum-peak)/peak*100
        if dd<max_dd:max_dd=dd
        if ret<-0.05:consec+=1
        elif ret>0.05:consec=0
        no_split_trades.append({'date':d1_date,'name':s1[5],'code':s1[1],'ret':ret,'mode':mode,'bp':bp,'sp':sp})

print(f'总交易天数: {len(split_trades)+len(no_split_trades)}')
print(f'分仓天数: {len(split_trades)}')
print(f'正常天数: {len(no_split_trades)}')
print(f'最终净值: {cum:.4f}')
print()

# 分仓明细
if split_trades:
    print('='*110)
    print('分仓交易明细 (21天)')
    print('='*110)
    tot1=0;tot2=0;tot_comb=0;win1=0;win2=0;both_win=0;both_loss=0
    for i,t in enumerate(split_trades,1):
        emoji1='🟢' if t['c1_ret']>0 else '🔴'
        emoji2='🟢' if t['c2_ret']>0 else '🔴'
        comb_emoji='✅' if t['combined']>0 else '❌'
        print(f'{i:>2}. {t["date"]} gap={t["gap"]:.3f}')
        print(f'    #1 {emoji1} {t["c1_name"]}({t["c1_code"]}) 买{t["c1_bp"]:.2f}→卖{t["c1_sp"]:.2f} {t["c1_ret"]:+.2f}% [{t["c1_mode"]}] 评分{t["c1_score"]:.3f}')
        print(f'    #2 {emoji2} {t["c2_name"]}({t["c2_code"]}) 买{t["c2_bp"]:.2f}→卖{t["c2_sp"]:.2f} {t["c2_ret"]:+.2f}% [{t["c2_mode"]}] 评分{t["c2_score"]:.3f}')
        print(f'    → 合并收益: {t["combined"]:+.2f}% {comb_emoji}')
        tot1+=t['c1_ret'];tot2+=t['c2_ret'];tot_comb+=t['combined']
        if t['c1_ret']>0:win1+=1
        if t['c2_ret']>0:win2+=1
        if t['c1_ret']>0 and t['c2_ret']>0:both_win+=1
        if t['c1_ret']<0 and t['c2_ret']<0:both_loss+=1
        print()

    print('--- 分仓统计 ---')
    print(f'#1 累计收益: {tot1:+.2f}%  胜率: {win1}/{len(split_trades)} ({win1/len(split_trades)*100:.1f}%)')
    print(f'#2 累计收益: {tot2:+.2f}%  胜率: {win2}/{len(split_trades)} ({win2/len(split_trades)*100:.1f}%)')
    print(f'合并累计: {tot_comb:+.2f}%')
    print(f'双双赢: {both_win}/{len(split_trades)}  双双亏: {both_loss}/{len(split_trades)}')
    print(f'#1>#2: {sum(1 for t in split_trades if t["c1_ret"]>t["c2_ret"])}/{len(split_trades)}')

# 对比: 如果全仓买#1
print()
print('--- 对照: 全仓#1 ---')
pure_cum=0;pure_rets=[]
for t in split_trades:
    pure_rets.append(t['c1_ret'])
    pure_cum+=t['c1_ret']
    if pure_cum<-0.05:
        pass  # 这里不模拟连亏, 只算纯额
print(f'全仓#1累计: {pure_cum:+.2f}%')
print(f'全仓#1胜率: {sum(1 for r in pure_rets if r>0)}/{len(pure_rets)} ({sum(1 for r in pure_rets if r>0)/len(pure_rets)*100:.1f}%)')
print(f'分仓优于全仓#1: {tot_comb>pure_cum}')
print(f'分仓 vs 全仓#1 差: {tot_comb-pure_cum:+.2f}%')
