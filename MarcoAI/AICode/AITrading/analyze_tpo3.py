# -*- coding: utf-8 -*-
"""TPO3 实时分析脚本"""
import urllib.request, json

W = [0.96, 0.21, 0.47, -0.45, 0.36, 0.40]
MU = [2.0, 0.75, 2.0, 1.5, 1.0, 0.15]
SG = [5.0, 0.4, 5.0, 1.5, 1.0, 0.35]
KEYS = ['pb_depth','vol_contract','ma5_dev','bear','bull','golden']

# 预计算数据(ATR10, MA5, MA10, D3量)
pre = {
    '002384.SZ': (18.981, 172.80, 172.80*0.95, 1400000),
    '002463.SZ': (8.307, 105.86, 105.86*0.96, 800000),
    '002916.SZ': (26.066, 315.31, 315.31*0.97, 100000),
    '002938.SZ': (7.305, 83.72, 83.72*0.97, 400000),
    '003031.SZ': (8.109, 97.18, 97.18*0.96, 100000),
    '600105.SH': (3.054, 33.40, 33.40*0.97, 2600000),
    '600183.SH': (10.322, 108.55, 108.55*0.95, 900000),
    '600330.SH': (1.543, 17.45, 17.45*0.96, 1500000),
    '600378.SH': (3.249, 40.67, 40.67*0.97, 700000),
    '601126.SH': (3.234, 39.95, 39.95*0.93, 400000),
    '603259.SH': (6.412, 134.25, 134.25*0.94, 1300000),
    '603938.SH': (3.013, 36.43, 36.43*0.95, 200000),
    '605589.SH': (2.739, 35.06, 35.06*0.94, 500000),
}

names = {
    '002384.SZ': '东山精密', '002463.SZ': '沪电股份', '002916.SZ': '深南电路',
    '002938.SZ': '鹏鼎控股', '003031.SZ': '中瓷电子', '600105.SH': '永鼎股份',
    '600183.SH': '生益科技', '600330.SH': '天通股份', '600378.SH': '昊华科技',
    '601126.SH': '四方股份', '603259.SH': '药明康德', '603938.SH': '三孚股份',
    '605589.SH': '圣泉集团',
}

mkt = {
    '002384.SZ': 'sz002384', '002463.SZ': 'sz002463', '002916.SZ': 'sz002916',
    '002938.SZ': 'sz002938', '003031.SZ': 'sz003031', '600105.SH': 'sh600105',
    '600183.SH': 'sh600183', '600330.SH': 'sh600330', '600378.SH': 'sh600378',
    '601126.SH': 'sh601126', '603259.SH': 'sh603259', '603938.SH': 'sh603938',
    '605589.SH': 'sh605589',
}

print(f'')
print(f'=== 6特征权重 (Walk-Forward) ===')
wn = ['回踩深度','量能收缩','MA5偏离','空头','多头','金叉']
for nm, wt in zip(wn, W):
    print(f'  {nm}: {wt:+.4f}')
print()

# 获取实时行情
results = []
for code in pre:
    atr10, ma5, ma10, d3_vol = pre[code]
    try:
        resp = urllib.request.urlopen(f'http://qt.gtimg.cn/q={mkt[code]}', timeout=5).read().decode('gbk')
        p = resp.split('~')
        if len(p) < 35: continue
        lp = float(p[3]); pre_c = float(p[4]); hi = float(p[33]); lo = float(p[34])
        vol = int(p[6])*100
        chg = (lp/pre_c-1)*100

        pb_depth = (pre_c - lp)/pre_c*100
        ma5_dev = (lp - ma5)/ma5*100 if ma5>0 else 0
        bear = (pre_c - lo)/atr10 if atr10>0 else 0
        bull = (hi - pre_c)/atr10 if atr10>0 else 0
        vol_ct = 1 if vol>0 and d3_vol>0 and vol<d3_vol*0.8 else 0
        golden = 0

        feat = [pb_depth, vol_ct, ma5_dev, bear, bull, golden]
        Xs = [(feat[i]-MU[i])/SG[i] for i in range(6)]
        score = sum(Xs[i]*W[i] for i in range(6))

        results.append((code, lp, chg, pb_depth, vol_ct, bull, bear, score, feat))
        nm = names.get(code, code)
        print(f'{code:<14} {nm:<8} {lp:>8.2f} {chg:>+6.2f}% pb={pb_depth:>+6.2f}% ct={vol_ct} bull={bull:>+6.2f} bear={bear:>+6.2f} 评分{score:>+8.4f}')
    except Exception as e:
        print(f'{code}: {e}')

print()
print('='*60)
print('TPO3 最终排序')
results.sort(key=lambda x: -x[7])  # sort by score
for i, (code, lp, chg, pb, ct, bull, bear, score, feat) in enumerate(results):
    nm = names.get(code, code)
    mark = ' ★★★ 尾盘买入' if i==0 else ''
    print(f'  {i+1}. {nm}({code}) 评分:{score:+.4f} pb={pb:+.2f} bull={bull:.2f} bear={bear:.2f}{mark}')
