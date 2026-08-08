"""
诊断: 逐笔比对 sell_5m vs sell_1d
找出导致5M净值远低于1D的原因
"""
import os,numpy as np
from collections import defaultdict

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D'
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

_5m={}
def lm5(code):
    if code in _5m:return _5m[code]
    fp=os.path.join(M5DIR,code)
    if not os.path.exists(fp):_5m[code]={};return{}
    bd=defaultdict(list)
    with open(fp) as f:
        for l in f:
            l=l.strip();p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','');bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    _5m[code]=dict(bd);return _5m[code]

def sell_5m(code, date, bp):
    bars=lm5(code).get(date,[])
    if not bars:return None,'no_data',''
    stop_price=bp*0.94;limit_up_price=round(bp*1.10,2)
    detail=[]
    for i,bar in enumerate(bars):
        o,h,l,c=bar
        if l<=stop_price:
            detail.append(f"bar{i}:{h}-{l} 触止损")
            return stop_price,'stop',detail[-1]
        if h>=limit_up_price*0.999:
            detail.append(f"bar{i}:{h}≈涨停")
            return limit_up_price,'limit_up',detail[-1]
    return bars[-1][3],'close',f"bar{len(bars)-1}:收盘{bars[-1][3]}"

def sell_1d(code,date,bp,o,h,l,c):
    st=bp*0.94;lu=round(bp*1.10,2)
    if o<=st:return o,'stop_1d'
    if l<=st:return bp*0.94,'stop_1d'
    if h>=lu*0.999:return lu,'limit_1d'
    return c,'close_1d'

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

print("加载候选数据...")
sa=[]
for fn in sorted(os.listdir(S)):
    if not fn.isdigit():continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    d2=tds[d1i-1];d4=tds[d1i-3]
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip();p=l.split('|')
            if len(p)<2:continue
            code=p[1];name=p[0]
            rs,dx=lk(code);d1k=dx.get(d1);d2k=dx.get(d2);d4k=dx.get(d4)
            if d1k is None or d2k is None:continue
            r1=rs[d1k];bp=r1[6]
            if bp<=0:continue
            r2=rs[d2k];r3=rs[d2k-1] if d2k>=1 else None
            if r3 is None:continue
            d2_bars=lm5(code).get(d2,[])
            if len(d2_bars)>=2:bar55=d2_bars[-2]
            else:bar55=(r2[1],r2[2],r2[3],r2[4])
            c5=bar55[3];pre_pb=r3[4]
            if r3[4]<=0:continue
            pb=(r3[4]-c5)/r3[4]*100
            o1=r1[1];h1=r1[2];l1=r1[3];c1=r1[4]
            sa.append((pb,code,d1,bp,name,o1,h1,l1,c1,c5))

print(f"{len(sa)} 条候选")

# === 逐笔对比 D策略选中后的 5M vs 1D 卖出 ===
# 假设用 D 策略选中：每天选 pb_depth>0 里最深的（简单规则，不用WF）
# 这样能快速看出两类卖出的差异

dm=defaultdict(list)
for i,s in enumerate(sa):
    dm[s[2]].append(i)
ad=sorted(dm.keys())

comparisons=[]
for d1_date in ad:
    idxs=dm[d1_date]
    # D策略选股: fall 里最深
    fall=[i for i in idxs if sa[i][0]>0]
    if fall:
        best=max(fall,key=lambda i:sa[i][0])
    else:
        best=max(idxs,key=lambda i:sa[i][0])
    
    pb,code,d1,bp,name,o1,h1,l1,c1,c5=sa[best]
    
    sp5,mode5,detail5=sell_5m(code,d1,bp)
    sp1,mode1=sell_1d(code,d1,bp,o1,h1,l1,c1)
    
    if sp5 is None:
        sp5=sp1;mode5='fallback_1d';detail5='无5M数据'
    
    ret5=(sp5-bp)/bp*100 if bp>0 else 0
    ret1=(sp1-bp)/bp*100 if bp>0 else 0
    diff=ret5-ret1
    
    comparisons.append({
        'date':d1,'code':code,'name':name,'bp':bp,
        'sp5':sp5,'sp1':sp1,'ret5':ret5,'ret1':ret1,'diff':diff,
        'mode5':mode5,'mode1':mode1,
        'o1':o1,'h1':h1,'l1':l1,'c1':c1,
        'detail5':detail5,'pb':pb
    })

print(f"\n=== 逐笔对比 (D策略选出) ===")
print(f"共 {len(comparisons)} 笔")

# 统计差异分布
diffs=[c['diff'] for c in comparisons]
print(f"\n5M - 1D 差异分布:")
print(f"  均值: {np.mean(diffs):+.2f}%")
print(f"  中位数: {np.median(diffs):+.2f}%")
print(f"  标准差: {np.std(diffs):.2f}%")
print(f"  min: {np.min(diffs):+.2f}%  max: {np.max(diffs):+.2f}%")

# 差异分段
print(f"\n差异分段:")
for lo,hi in [(-100,-5),(-5,-2),(-2,-1),(-1,0),(0,1),(1,2),(2,5),(5,100)]:
    grp=[c for c in comparisons if lo<=c['diff']<hi]
    if not grp:continue
    avg5=np.mean([c['ret5'] for c in grp])
    avg1=np.mean([c['ret1'] for c in grp])
    print(f"  差{lo:+d}~{hi:+d}%: {len(grp)}笔, 5M均{avg5:+.2f}% vs 1D均{avg1:+.2f}%")

# 按卖出模式分组
print(f"\n按5M卖出模式:")
for m in sorted(set(c['mode5'] for c in comparisons)):
    grp=[c for c in comparisons if c['mode5']==m]
    avg5=np.mean([c['ret5'] for c in grp])
    avg1=np.mean([c['ret1'] for c in grp])
    print(f"  {m}: {len(grp)}笔, 5M均{avg5:+.2f}% vs 1D均{avg1:+.2f}%, 差{avg5-avg1:+.2f}%")

# 重点看: 5M止损 vs 1D没止损 的情况
print(f"\n=== 5M止损 但 1D未止损 ===")
mismatch=[c for c in comparisons if 'stop' in c['mode5'] and 'stop' not in c['mode1']]
print(f"共 {len(mismatch)} 笔")
for mm in mismatch[:20]:
    print(f"  {mm['date']} {mm['name']}({mm['code']}) bp={mm['bp']:.2f} "
          f"o1={mm['o1']:.2f} h1={mm['h1']:.2f} l1={mm['l1']:.2f} c1={mm['c1']:.2f} "
          f"5M:{mm['sp5']:.2f}({mm['mode5']}) 1D:{mm['sp1']:.2f}({mm['mode1']}) "
          f"pb={mm['pb']:.1f}%  {mm['detail5']}")

# 反之: 1D止损 但 5M没止损
print(f"\n=== 1D止损 但 5M未止损 ===")
mismatch2=[c for c in comparisons if 'stop' in c['mode1'] and 'stop' not in c['mode5']]
print(f"共 {len(mismatch2)} 笔")
for mm in mismatch2[:20]:
    print(f"  {mm['date']} {mm['name']}({mm['code']}) bp={mm['bp']:.2f} "
          f"o1={mm['o1']:.2f} h1={mm['h1']:.2f} l1={mm['l1']:.2f} c1={mm['c1']:.2f} "
          f"5M:{mm['sp5']:.2f}({mm['mode5']}) 1D:{mm['sp1']:.2f}({mm['mode1']}) "
          f"  {mm['detail5']}")

# 涨停差异
print(f"\n=== 5M涨停 但 1D未涨停 ===")
mismatch3=[c for c in comparisons if 'limit' in c['mode5'] and 'limit' not in c['mode1']]
print(f"共 {len(mismatch3)} 笔")
for mm in mismatch3[:10]:
    print(f"  {mm['date']} {mm['name']}({mm['code']}) bp={mm['bp']:.2f} "
          f"h1={mm['h1']:.2f} sp5={mm['sp5']:.2f} sp1={mm['sp1']:.2f}")

print(f"\n=== 1D涨停 但 5M未涨停 ===")
mismatch4=[c for c in comparisons if 'limit' in c['mode1'] and 'limit' not in c['mode5']]
print(f"共 {len(mismatch4)} 笔")
for mm in mismatch4[:10]:
    print(f"  {mm['date']} {mm['name']}({mm['code']}) bp={mm['bp']:.2f} "
          f"h1={mm['h1']:.2f} sp5={mm['sp5']:.2f} sp1={mm['sp1']:.2f}  {mm['detail5']}")

# 检查5M数据覆盖
print(f"\n=== 5M数据检查 ===")
nodata=[c for c in comparisons if c['mode5']=='fallback_1d']
print(f"无5M数据: {len(nodata)} 笔")
nodata5=[c for c in comparisons if c['mode5']=='no_data']
print(f"no_data: {len(nodata5)} 笔")

# 检查5M bars数量
bar_counts=defaultdict(int)
for c in comparisons:
    if 'fallback' not in c['mode5'] and c['mode5']!='no_data':
        bars=lm5(c['code']).get(c['date'],[])
        bar_counts[len(bars)]+=1
print(f"\n5M bars数量分布:")
for k in sorted(bar_counts):
    print(f"  {k}根: {bar_counts[k]}笔")

# 逐月汇总
print(f"\n=== 逐月汇总: 5M净值 vs 1D净值 ===")
INIT=100_000
asset5=INIT;peak5=INIT;asset1=INIT;peak1=INIT
monthly={}
for c in comparisons:
    m=c['date'][:6]
    if m not in monthly:monthly[m]={'ret5':[],'ret1':[],'diff':0}
    ret5=(c['sp5']-c['bp'])/c['bp']*100
    ret1=(c['sp1']-c['bp'])/c['bp']*100
    monthly[m]['ret5'].append(ret5)
    monthly[m]['ret1'].append(ret1)
    monthly[m]['diff']+=(ret5-ret1)

for m in sorted(monthly):
    d=monthly[m]
    avg5=np.mean(d['ret5']);avg1=np.mean(d['ret1']);cnt=len(d['ret5'])
    print(f"  {m}: {cnt:>2}笔  5M均{avg5:>+6.2f}%  1D均{avg1:>+6.2f}%  差{d['diff']:>+7.2f}%")

print("\n诊断完成 ✓")
