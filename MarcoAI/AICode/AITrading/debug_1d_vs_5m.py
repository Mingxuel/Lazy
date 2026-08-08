"""逐笔对比: 1D止损优先 vs 5M止损优先 (同seed, 同选股)"""
import os,random
from collections import defaultdict

S=r'C:\Lazy\李明学的大A\Data\Strategy';K=r'C:\Lazy\李明学的大A\Data\1D';M5=r'C:\Lazy\MarcoAI\AIData\5M'

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
    fp=os.path.join(M5,code)
    if not os.path.exists(fp):_5m[code]={};return{}
    bd=defaultdict(list)
    with open(fp) as f:
        for l in f:
            l=l.strip();p=l.split('|')
            if len(p)<6:continue
            d=p[0][:10].replace('-','');bd[d].append((float(p[1]),float(p[2]),float(p[3]),float(p[4])))
    _5m[code]=dict(bd);return _5m[code]

tds=[]
with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
    for l in f:l=l.strip();l and l.isdigit()and len(l)==8 and tds.append(l)
tds=sorted(tds);di={d:i for i,d in enumerate(tds)}

daily_cands=defaultdict(list)
for fn in sorted(os.listdir(S)):
    if not fn.isdigit() or fn<'20250101':continue
    d1=fn;d1i=di.get(d1)
    if d1i is None or d1i<4:continue
    with open(os.path.join(S,fn)) as f:
        for l in f:
            l=l.strip();p=l.split('|')
            if len(p)<2:continue
            daily_cands[d1].append((p[1],p[0]))

days=sorted(daily_cands.keys())
random.seed(0)

print('逐笔对比: 1D止损优先 vs 5M止损优先 (seed=0)')
print('='*90)

diff_count=0;total=0
stop_1d=0;stop_5m=0;limit_1d=0;limit_5m=0;close_1d=0;close_5m=0
fallback_1d=0;fallback_5m=0  # 数据集不一致回退
big_diffs=[]

for d1 in days:
    cands=daily_cands[d1]
    code,name=random.choice(cands)
    rs,dx=lk(code);d1k=dx.get(d1)
    if d1k is None:continue
    r1=rs[d1k];bp=r1[6]
    if bp<=0:continue
    o,h,l,c=r1[1],r1[2],r1[3],r1[4]
    st=bp*0.94;lu=round(bp*1.10,2)

    # 1D 止损优先
    if o<=st:sp1d=o;m1d='open_stop'
    elif l<=st:sp1d=st;m1d='low_stop'
    elif h>=lu*0.999:sp1d=lu;m1d='limit'
    else:sp1d=c;m1d='close'

    # 5M 止损优先
    bars=lm5(code).get(d1,[])
    sp5m=c;m5m='fallback_1d'  # 默认回退1D
    if bars:
        last5m=bars[-1][3]
        if last5m>0 and c>0 and abs(last5m/c-1)<0.02:
            # 5M数据一致
            for bar in bars:
                if bar[2]<=st:sp5m=st;m5m='stop_5m';break
                if bar[1]>=lu*0.999:sp5m=lu;m5m='limit_5m';break
            if m5m=='fallback_1d':sp5m=last5m;m5m='5m_close'

    diff=abs(sp1d-sp5m)/sp1d*100 if sp1d>0 else 0
    total+=1
    
    if diff>0.5:
        diff_count+=1
        ret1d=(sp1d-bp)/bp*100;ret5m=(sp5m-bp)/bp*100
        big_diffs.append((d1,name,code,bp,sp1d,sp5m,ret1d,ret5m,m1d,m5m))

    if 'stop' in m1d:stop_1d+=1
    if 'stop' in m5m:stop_5m+=1
    if 'limit' in m1d:limit_1d+=1
    if 'limit' in m5m:limit_5m+=1
    if m1d=='close':close_1d+=1
    if m5m in ('close','5m_close'):close_5m+=1
    if m5m=='fallback_1d':fallback_5m+=1
    if sp5m==c and m5m=='fallback_1d':fallback_1d+=1

print(f'总笔数: {total}')
print(f'差异>0.5%: {diff_count} ({diff_count/total*100:.1f}%)')
print(f'1D: 开盘止损{stop_1d} 涨停{limit_1d} 收盘{close_1d}')
print(f'5M: 止损{stop_5m} 涨停{limit_5m} 收盘{close_5m} 回退1D{fallback_5m}')
print()

# 分类差异原因
same_stop=sum(1 for d in big_diffs if 'stop' in d[8] and 'stop' in d[9])
stop_only_5m=sum(1 for d in big_diffs if 'stop' not in d[8] and 'stop' in d[9])
stop_only_1d=sum(1 for d in big_diffs if 'stop' in d[8] and 'stop' not in d[9])
close_diff=sum(1 for d in big_diffs if d[8]=='close' and d[9]=='5m_close')

print(f'差异分类 ({len(big_diffs)}笔):')
print(f'  双方都止损(价差): {same_stop}')
print(f'  仅5M止损: {stop_only_5m}')
print(f'  仅1D止损: {stop_only_1d}')
print(f'  双方收盘(5Mvs1D价差): {close_diff}')
print()

# 展示: 仅5M止损的例子
print('=== 仅5M止损 (1D没止损) ===')
cnt=0
for d1,name,code,bp,sp1d,sp5m,ret1d,ret5m,m1d,m5m in big_diffs:
    if 'stop' not in m1d and 'stop' in m5m:
        print(f'{d1} {name} bp={bp:.2f} 1D:{m1d}({sp1d:.2f},{ret1d:+.1f}%) 5M:{m5m}({sp5m:.2f},{ret5m:+.1f}%)')
        cnt+=1
        if cnt>=10:break

print()
print('=== 仅1D止损 (5M没止损) ===')
cnt=0
for d1,name,code,bp,sp1d,sp5m,ret1d,ret5m,m1d,m5m in big_diffs:
    if 'stop' in m1d and 'stop' not in m5m:
        print(f'{d1} {name} bp={bp:.2f} 1D:{m1d}({sp1d:.2f},{ret1d:+.1f}%) 5M:{m5m}({sp5m:.2f},{ret5m:+.1f}%)')
        cnt+=1
        if cnt>=10:break

# 汇总: 如果5M回退到1D, 差异怎么来的
print()
ret1d_all=[]
ret5m_all=[]
for d1,name,code,bp,sp1d,sp5m,ret1d,ret5m,m1d,m5m in big_diffs:
    ret1d_all.append(ret1d)
    ret5m_all.append(ret5m)
if ret1d_all:
    import numpy as np
    print(f'差异笔平均: 1D={np.mean(ret1d_all):+.2f}% vs 5M={np.mean(ret5m_all):+.2f}%')
