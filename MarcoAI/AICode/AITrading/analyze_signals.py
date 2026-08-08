# -*- coding: utf-8 -*-
"""分析D-4涨停板质量 & D-3回踩深度 对次日收益的影响"""
import os, numpy as np
from collections import defaultdict

S=r'C:\Lazy\李明学的大A\Data\Strategy'
K=r'C:\Lazy\李明学的大A\Data\1D'
M5DIR=r'C:\Lazy\MarcoAI\AIData\5M'

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

_5m_cache={}
def lm5(code):
    if code in _5m_cache:return _5m_cache[code]
    fp=os.path.join(M5DIR,code)
    if not os.path.exists(fp):_5m_cache[code]={};return{}
    bd=defaultdict(list)
    with open(fp) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','')
            bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    _5m_cache[code]=dict(bd)
    return _5m_cache[code]

def get_bar(code,d,offset):
    bars=lm5(code).get(d,[])
    if len(bars)>=abs(offset):return bars[offset]
    return None

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

# ====== 收集所有样本，带更多特征 ======
samples=[]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    d2=tds[d1i-1];d3=tds[d1i-2];d4=tds[d1i-3]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip()
            if not l:continue
            p=l.split('|')
            if len(p)<2:continue
            code=p[1];name=p[0]
            rs,dx=lk(code)
            d4k=dx.get(d4)
            if d4k is None:continue
            r4=rs[d4k]  # D-4 (涨停日)
            d4_o,d4_h,d4_l,d4_c=r4[1],r4[2],r4[3],r4[4]

            # D-4 涨停价
            d4_pre=r4[6] if d4k==0 else rs[d4k-1][4]
            d4_lu=round(d4_pre*1.10,2)

            d3k=dx.get(d3)
            if d3k is None:continue
            r3=rs[d3k]  # D-3 (放量/回踩日)
            d3_o,d3_h,d3_l,d3_c,d3_v=d3k>=0 and r3[1],r3[2],r3[3],r3[4],r3[5]

            d2k=dx.get(d2)
            if d2k is None:continue
            r2=rs[d2k]  # D-2 (买入日)

            d1k=dx.get(d1)
            if d1k is None:continue
            r1=rs[d1k]  # D-1 (卖出日)
            bp=r1[6];sp_c=r1[4]
            if bp<=0:continue

            # ===== D-4 涨停板性质 =====
            # 一字板: 开≈涨停 且 收=涨停
            is_yizi = d4_o>=d4_lu*0.999 and d4_c>=d4_lu*0.999
            # 实体占比: (收-开)/涨停幅度
            d4_range=d4_lu-d4_pre
            d4_body=d4_c-d4_o
            body_pct=d4_body/d4_range*100 if d4_range>0 else 0
            # 上影线
            upper_wick=(d4_h-max(d4_o,d4_c))/d4_range*100 if d4_range>0 else 0
            # 涨停时间(用5M): D-4 第一根涨停的K线位置
            d4_bars=lm5(code).get(d4,[])
            first_lu_bar=None
            for bi,bar in enumerate(d4_bars):
                if bar[2]>=d4_lu*0.999:  # high 触及涨停
                    first_lu_bar=bi;break
            # 封板时间 (48根5M/天, 第0根=9:35)
            lu_bar_pct=first_lu_bar/48*100 if first_lu_bar is not None and len(d4_bars)>=48 else None

            # ===== D-3 回踩性质 =====
            pb_pct=(d3_c-d3_h)/d3_h*100 if d3_h>0 else 0  # 负=回踩
            # D-3放量程度 (相对于前20日均量)
            if d3k>=20:
                avg20=np.mean([rs[i][5] for i in range(d3k-19,d3k+1)])
                vol_ratio=d3_v/avg20 if avg20>0 else 1
            else:vol_ratio=None

            # ===== D-2 特征 (已有) =====
            bar55=get_bar(code,d2,-2)
            if bar55 is None:bar55=(r2[1],r2[2],r2[3],r2[4])
            c55=bar55[3]

            # ===== 标签 =====
            ret_next=(sp_c-bp)/bp*100
            # 卖出方式
            st=bp*0.94;lu=round(bp*1.10,2)
            if r1[1]<=st:mode='open_stop'
            elif r1[3]<=st:mode='low_stop'
            elif r1[2]>=lu*0.999:mode='limit_up'
            else:mode='close'

            entry={
                'date':d1,'code':code,'name':name,'ret':ret_next,'mode':mode,
                'is_yizi':is_yizi,'body_pct':body_pct,'upper_wick':upper_wick,
                'lu_bar':first_lu_bar,'lu_bar_pct':lu_bar_pct,
                'pb_pct':pb_pct,'vol_ratio':vol_ratio,
                'd4_c':d4_c,'d4_lu':d4_lu,'d4_pre':d4_pre,
                'd3_h':d3_h,'d3_l':d3_l,'d3_c':d3_c,'d3_o':d3_o,
                'c55':c55,'bp':bp,'d2_pre':r2[6],
            }
            samples.append(entry)

print(f"总样本: {len(samples)}")

# ====== 分析 ======

# 1. 一字板 vs 换手板
print("\n" + "="*60)
print("一、一字板 vs 换手板")
yizi=[s for s in samples if s['is_yizi']]
normal=[s for s in samples if not s['is_yizi']]
for label,grp in [('一字板',yizi),('换手板',normal)]:
    if not grp:continue
    avg=np.mean([s['ret'] for s in grp])
    wr=sum(1 for s in grp if s['ret']>0)/len(grp)*100
    lu_cnt=sum(1 for s in grp if s['mode']=='limit_up')
    stop_cnt=sum(1 for s in grp if s['mode'] in ('low_stop','open_stop'))
    print(f"  {label}: {len(grp)}笔, 均收益{avg:+.2f}%, 胜率{wr:.1f}%, 涨停{lu_cnt}次, 止损{stop_cnt}次")

# 2. 封板时间段
print("\n" + "="*60)
print("二、涨停封板时间")
early=[s for s in samples if s['lu_bar'] is not None and s['lu_bar']<=5]   # 9:35-9:55
mid=[s for s in samples if s['lu_bar'] is not None and 5<s['lu_bar']<=20]  # 10:00-11:10
late=[s for s in samples if s['lu_bar'] is not None and s['lu_bar']>20]    # 11:15+
for label,grp in [('早封(前5根)',early),('中封(6-20)',mid),('晚封(20+)',late)]:
    if not grp:continue
    avg=np.mean([s['ret'] for s in grp])
    wr=sum(1 for s in grp if s['ret']>0)/len(grp)*100
    print(f"  {label}: {len(grp)}笔, 均收益{avg:+.2f}%, 胜率{wr:.1f}%")

# 3. 回踩深度分档
print("\n" + "="*60)
print("三、回踩深度分档 (D-3: 收 vs 高)")
bins=[(-20,-5),(-5,-3),(-3,-1.5),(-1.5,0),(0,5)]
for lo,hi in bins:
    grp=[s for s in samples if lo<=s['pb_pct']<hi]
    if not grp:continue
    avg=np.mean([s['ret'] for s in grp])
    wr=sum(1 for s in grp if s['ret']>0)/len(grp)*100
    lu_cnt=sum(1 for s in grp if s['mode']=='limit_up')
    print(f"  回踩{lo}%~{hi}%: {len(grp)}笔, 均收益{avg:+.2f}%, 胜率{wr:.1f}%, 涨停{lu_cnt}次")

# 4. D-3放量比 vs 收益
print("\n" + "="*60)
print("四、D-3放量比 (vs 20日均量)")
vol_bins=[(0,1),(1,1.5),(1.5,2),(2,3),(3,999)]
for lo,hi in vol_bins:
    grp=[s for s in samples if s['vol_ratio'] is not None and lo<=s['vol_ratio']<hi]
    if not grp:continue
    avg=np.mean([s['ret'] for s in grp])
    wr=sum(1 for s in grp if s['ret']>0)/len(grp)*100
    print(f"  量比 {lo}-{hi}: {len(grp)}笔, 均收益{avg:+.2f}%, 胜率{wr:.1f}%")

# 5. D-3 开盘 vs 收盘 (低开高走 vs 高开低走)
print("\n" + "="*60)
print("五、D-3 日内形态")
d3_up=[s for s in samples if s['d3_c']>s['d3_o']]  # 收阳
d3_dn=[s for s in samples if s['d3_c']<s['d3_o']]  # 收阴
cross=[s for s in samples if abs(s['d3_c']-s['d3_o'])<0.01]  # 十字星
for label,grp in [('收阳',d3_up),('收阴',d3_dn),('十字星',cross)]:
    if not grp:continue
    avg=np.mean([s['ret'] for s in grp])
    wr=sum(1 for s in grp if s['ret']>0)/len(grp)*100
    print(f"  {label}: {len(grp)}笔, 均收益{avg:+.2f}%, 胜率{wr:.1f}%")

# 6. D-3 下影线长度
print("\n" + "="*60)
print("六、D-3 下影线长度 (低→收)")
lower_wick_bins=[(-10,-2),(-2,-1),(-1,-0.3),(-0.3,0)]
for lo,hi in lower_wick_bins:
    grp=[s for s in samples if s['d3_l']<s['d3_c'] and lo<=(s['d3_l']-s['d3_c'])/s['d3_c']*100<hi]
    if not grp:continue
    avg=np.mean([s['ret'] for s in grp])
    wr=sum(1 for s in grp if s['ret']>0)/len(grp)*100
    print(f"  下影{(s['d3_l']-s['d3_c'])/s['d3_c']*100:.f}% ~: {len(grp)}笔, 均收益{avg:+.2f}%, 胜率{wr:.1f}%")

# 7. 一字板过滤后对比
print("\n" + "="*60)
print("七、过滤一字板后整体")
no_yizi=[s for s in samples if not s['is_yizi']]
avg_all=np.mean([s['ret'] for s in samples])
avg_ny=np.mean([s['ret'] for s in no_yizi])
wr_all=sum(1 for s in samples if s['ret']>0)/len(samples)*100
wr_ny=sum(1 for s in no_yizi if s['ret']>0)/len(no_yizi)*100
print(f"  全样本: {len(samples)}笔, 均{avg_all:+.2f}%, 胜率{wr_all:.1f}%")
print(f"  去一字板: {len(no_yizi)}笔, 均{avg_ny:+.2f}%, 胜率{wr_ny:.1f}%")

# 8. 炸板分析 (D-4 最高到涨停但没收涨停)
print("\n" + "="*60)
print("八、D-4 封板情况")
sealed=[s for s in samples if s['d4_c']>=s['d4_lu']*0.99]   # 封住了
near_lu=[s for s in samples if s['d4_h']>=s['d4_lu']*0.99 and s['d4_c']<s['d4_lu']*0.99]  # 摸到没封
notouch=[s for s in samples if s['d4_h']<s['d4_lu']*0.99]  # 没摸
for label,grp in [('封涨停',sealed),('摸未封',near_lu),('未摸',notouch)]:
    if not grp:continue
    avg=np.mean([s['ret'] for s in grp])
    wr=sum(1 for s in grp if s['ret']>0)/len(grp)*100
    print(f"  {label}: {len(grp)}笔, 均收益{avg:+.2f}%, 胜率{wr:.1f}%")
