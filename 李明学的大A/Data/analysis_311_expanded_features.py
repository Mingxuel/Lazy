"""
311策略 — 扩展特征工程选股模型
新增: 多空博弈特征(高/低/开 vs 昨收)、价格位置、成交量深度特征、均线多周期
行业过滤: 排除制造/基建(近3月大亏行业)
训练: <202604, 测试: >=202604, walk-forward
"""

import os, numpy as np
from collections import defaultdict

S = r'C:\Lazy\李明学的大A\Data\Strategy'
K = r'C:\Lazy\李明学的大A\Data\1D'
M5 = r'C:\Lazy\MarcoAI\AIData\5M'
CR = 0.00025; CM = 5.0; SD = 0.0005; TF = 0.00001
CAPITAL = 1_000_000

# ============================================================
# 数据加载
# ============================================================

def load_td():
    ds = []
    with open(r'C:\Lazy\李明学的大A\Data\交易日.config') as f:
        for l in f:
            l = l.strip()
            if l and l.isdigit() and len(l) == 8:
                ds.append(l)
    return sorted(ds)

def load_kline_full(code):
    """返回完整K线 (date, open, high, low, close, volume, preClose)"""
    fp = os.path.join(K, code)
    if not os.path.exists(fp):
        return [], {}
    rows = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('\ufeff'):
                continue
            c = l.split()
            if len(c) < 10 or not c[0].isdigit():
                continue
            rows.append((
                c[0],
                float(c[1]), float(c[2]), float(c[3]),
                float(c[4]), float(c[5]), float(c[9])
            ))
    return rows, {r[0]: i for i, r in enumerate(rows)}

def check_ma5_bounce(code, d2_date, d2_close):
    """检查D-2回踩日盘中MA5弹起"""
    fp = os.path.join(M5, code)
    if not os.path.exists(fp):
        return 0, 0
    df = f'{d2_date[:4]}-{d2_date[4:6]}-{d2_date[6:8]}'
    with open(fp, encoding='utf-8') as f:
        bars = []
        for l in f:
            l = l.strip()
            if not l:
                continue
            p = l.split('|')
            if len(p) < 6:
                continue
            if p[0].startswith(df):
                bars.append((p[0], float(p[4]), float(p[2]), float(p[3]), float(p[1]), float(p[5])))
    if not bars or len(bars) < 10:
        return 0, 0
    for b in bars:
        bl, bc = b[3], b[1]
        if d2_close > 0:
            d = (bl - d2_close) / d2_close * 100
            if -1.5 < d < 1.0:
                bounce = (bc - bl) / bl * 100
                if bounce > 1.5:
                    return 1, bounce
    return 0, 0

# ============================================================
# 行业分类 (排除制造、基建)
# ============================================================

def classify_sector(name):
    n = name
    tech = ['半导', '芯片', '电子', '通信', '软件', '计算机', '科技', '集成', '微电',
            '晶方', '华天', '华虹', '中芯', '韦尔', '紫光', '中科', '浪潮', '中兴',
            '烽火', '通富', '长电', '斯达', '瑞芯', '纳芯', '圣邦', '铖昌', '广合',
            '深科技', '凯盛', '雅克', '法拉', '东材', '长飞', '立昂微', '德明利',
            'TCL科技', '风华高科']
    consumer = ['酒', '食品', '饮料', '医药', '药', '片仔', '零售', '超市', '永辉',
                '安德利', '昭衍', '古井']
    cyclical = ['钢铁', '有色', '化工', '建材', '煤炭', '铝业', '中环', '振华',
                '中孚', '天山铝', '赤峰', '黄金', '和邦', '山金', '有研', '铜陵',
                '稀土', '洛阳钼', '驰宏', '株冶', '北方铜', '博威', '锡业', '江西铜',
                '金田', '方大', '巨化', '多氟', '恩捷', '桐昆', '平煤', '三祥',
                '杭氧', '爱旭', '福斯特']
    mfg = ['汽车', '机械', '设备', '电气', '电机', '传动', '重汽', '杰瑞', '卧龙',
           '奥士康', '麦格米特', '飞龙', '赛腾', '双环', '海亮', '鸣志', '华勤',
           '中恒', '万丰', '国机', '中航', '湘财', '科达', '欧派']
    finance = ['证券', '银行', '保险', '金融', '广发', '财通', '华林', '中信建投', '越秀']
    media = ['网络', '巨人', '广电']
    construction = ['核建', '铁塔', '杭钢', '深深房']
    other_exclude = ['东山精密', '亨通', '常山', '永鼎', '江海', '高能', '太极', '和而泰',
                     '罗曼', '东睦', '新材']
    
    for kw in tech: 
        if kw in n: return '科技', False
    for kw in consumer:
        if kw in n: return '消费', False
    for kw in cyclical:
        if kw in n: return '周期', False
    for kw in mfg:
        if kw in n: return '制造', True  # ★ 标记为排除
    for kw in finance:
        if kw in n: return '金融', False
    for kw in media:
        if kw in n: return '传媒', False
    for kw in construction:
        if kw in n: return '基建', True  # ★ 标记为排除
    for kw in other_exclude:
        if kw in n: return '其他', False
    return '其他', False

# ============================================================
# ★ 扩展特征工程 (35维)
# ============================================================

def extract_features(rows, d2_idx):
    """
    从D-2及之前K线提取特征
    rows: 完整K线列表
    d2_idx: D-2在rows中的索引
    
    特征分组:
    A. 多空博弈 (6维): high/preClose, preClose/low, open位置, close位置, 上影线, 下影线
    B. 量价关系 (5维): 缩量, 量比, 振幅, 实体比, 换手
    C. 均线系统 (6维): MA5/10/20位置, 偏离度, 金叉, 排列
    D. 趋势动量 (5维): 5日/10日/20日涨跌幅, 连涨连跌, 波动率
    E. 回踩质量 (4维): 回踩深度, 回踩速度, 是否新低, D-3涨停
    F. 5M盘口 (2维): MA5弹起, 弹起幅度
    G. 价格区间 (3维): 绝对价格, 近期高低位
    H. 行业标记 (4维): 科技/消费/周期/金融
    """
    f = {}
    r2 = rows[d2_idx]  # D-2
    o2, h2, l2, c2, v2, pc2 = r2[1], r2[2], r2[3], r2[4], r2[5], r2[6]
    
    # D-3
    if d2_idx >= 1:
        r3 = rows[d2_idx - 1]
        o3, h3, l3, c3, v3 = r3[1], r3[2], r3[3], r3[4], r3[5]
    else:
        r3 = None
    
    # D-4
    if d2_idx >= 2:
        r4 = rows[d2_idx - 2]
        o4, h4, l4, c4, v4 = r4[1], r4[2], r4[3], r4[4], r4[5]
    else:
        r4 = None

    # ---- A. 多空博弈特征 ----
    # A1. 最高价比昨收 (多头攻击力度)
    f['high_vs_preclose'] = (h2 - pc2) / pc2 * 100 if pc2 > 0 else 0
    # A2. 昨收比最低价 (空头打压深度)
    f['preclose_vs_low'] = (pc2 - l2) / pc2 * 100 if pc2 > 0 else 0
    # A3. 开盘相对昨收 (开盘情绪)
    f['gap_open'] = (o2 - pc2) / pc2 * 100 if pc2 > 0 else 0
    # A4. 收盘位置 (0=最低, 1=最高, 收盘在日内位置)
    f['close_position'] = (c2 - l2) / (h2 - l2) if h2 > l2 else 0.5
    # A5. 上影线比例
    f['upper_shadow'] = (h2 - max(o2, c2)) / (h2 - l2) * 100 if h2 > l2 else 0
    # A6. 下影线比例
    f['lower_shadow'] = (min(o2, c2) - l2) / (h2 - l2) * 100 if h2 > l2 else 0
    
    # ---- B. 量价关系 ----
    f['vol_contract'] = 1 if (r3 and v2 < v3 * 0.8) else 0
    f['vol_ratio_d2_d3'] = v2 / v3 if (r3 and v3 > 0) else 1.0
    f['amplitude'] = (h2 - l2) / o2 * 100 if o2 > 0 else 0
    f['body_ratio'] = abs(c2 - o2) / (h2 - l2) * 100 if h2 > l2 else 0
    f['volume_abnormal'] = 1 if (r3 and v2 > v3 * 2.0) else 0
    
    # ---- C. 均线系统 ----
    closes_all = np.array([r[4] for r in rows[:d2_idx + 1]])
    if len(closes_all) >= 5:
        ma5 = np.mean(closes_all[-5:])
        f['above_ma5'] = 1 if c2 > ma5 else 0
        f['ma5_deviation'] = (c2 - ma5) / ma5 * 100
        f['ma5_slope'] = (closes_all[-1] - closes_all[-5]) / closes_all[-5] * 100 if closes_all[-5] > 0 else 0
    else:
        f['above_ma5'] = 0
        f['ma5_deviation'] = 0
        f['ma5_slope'] = 0
    
    if len(closes_all) >= 10:
        ma10 = np.mean(closes_all[-10:])
        f['above_ma10'] = 1 if c2 > ma10 else 0
        f['ma10_deviation'] = (c2 - ma10) / ma10 * 100
    else:
        f['above_ma10'] = 0
        f['ma10_deviation'] = 0
    
    if len(closes_all) >= 20:
        ma20 = np.mean(closes_all[-20:])
        f['above_ma20'] = 1 if c2 > ma20 else 0
        f['ma20_deviation'] = (c2 - ma20) / ma20 * 100
    else:
        f['above_ma20'] = 0
        f['ma20_deviation'] = 0
    
    # MA排列: 多头排列=MA5>MA10>MA20
    if len(closes_all) >= 20:
        f['ma_bullish'] = 1 if (c2 > ma5 and ma5 > ma10 and ma10 > ma20) else 0
    else:
        f['ma_bullish'] = 0
    
    # ---- D. 趋势动量 ----
    if len(closes_all) >= 6:
        f['ret_5d'] = (closes_all[-1] - closes_all[-6]) / closes_all[-6] * 100 if closes_all[-6] > 0 else 0
    else:
        f['ret_5d'] = 0
    if len(closes_all) >= 11:
        f['ret_10d'] = (closes_all[-1] - closes_all[-11]) / closes_all[-11] * 100 if closes_all[-11] > 0 else 0
    else:
        f['ret_10d'] = 0
    if len(closes_all) >= 21:
        f['ret_20d'] = (closes_all[-1] - closes_all[-21]) / closes_all[-21] * 100 if closes_all[-21] > 0 else 0
    else:
        f['ret_20d'] = 0
    
    # 连涨连跌
    f['consecutive_up'] = 0
    if len(closes_all) >= 2:
        for i in range(d2_idx, max(0, d2_idx - 10), -1):
            if closes_all[i] > closes_all[i - 1]:
                f['consecutive_up'] += 1
            else:
                break
    
    # 近期波动率
    if len(closes_all) >= 10:
        rets = [(closes_all[i] - closes_all[i - 1]) / closes_all[i - 1] * 100
                for i in range(d2_idx - 8, d2_idx + 1) if closes_all[i - 1] > 0]
        f['volatility_10d'] = np.std(rets) if rets else 0
    else:
        f['volatility_10d'] = 0
    
    # ---- E. 回踩质量 ----
    # 回踩深度: (D-3收盘 - D-2收盘) / D-3收盘
    f['pullback_depth'] = (c3 - c2) / c3 * 100 if (r3 and c3 > 0) else 0
    # 回踩速度: 回踩深度 / 振幅
    f['pullback_speed'] = (f['pullback_depth'] / f['amplitude']) if f['amplitude'] > 0 else 0
    # D-2是否跌破D-3最低
    f['broke_d3_low'] = 1 if (r3 and l2 < l3) else 0
    # D-3是否接近涨停(>7%)
    f['d3_strong'] = 1 if (r3 and (c3 - o3) / o3 * 100 > 7) else 0
    
    # ---- F. 5M盘口 ----
    ma5_hit, bounce = 0, 0  # 外部传入
    f['ma5_support'] = 0
    f['ma5_bounce'] = 0
    
    # ---- G. 价格区间 ----
    f['price_level'] = c2  # 绝对价格
    f['price_vs_60d_high'] = 0
    if len(closes_all) >= 60:
        h60 = max(closes_all[-60:])
        f['price_vs_60d_high'] = c2 / h60 if h60 > 0 else 1.0
    f['price_vs_60d_low'] = 0
    if len(closes_all) >= 60:
        l60 = min(closes_all[-60:])
        f['price_vs_60d_low'] = c2 / l60 if l60 > 0 else 1.0
    
    return f

# ============================================================
# 特征名列表 (按顺序)
# ============================================================

FEATURE_KEYS = [
    # A. 多空博弈
    'high_vs_preclose', 'preclose_vs_low', 'gap_open', 'close_position',
    'upper_shadow', 'lower_shadow',
    # B. 量价关系
    'vol_contract', 'vol_ratio_d2_d3', 'amplitude', 'body_ratio', 'volume_abnormal',
    # C. 均线系统
    'above_ma5', 'ma5_deviation', 'ma5_slope',
    'above_ma10', 'ma10_deviation',
    'above_ma20', 'ma20_deviation', 'ma_bullish',
    # D. 趋势动量
    'ret_5d', 'ret_10d', 'ret_20d', 'consecutive_up', 'volatility_10d',
    # E. 回踩质量
    'pullback_depth', 'pullback_speed', 'broke_d3_low', 'd3_strong',
    # F. 5M盘口
    'ma5_support', 'ma5_bounce',
    # G. 价格区间
    'price_level', 'price_vs_60d_high', 'price_vs_60d_low',
]

print(f"特征维度: {len(FEATURE_KEYS)}")

# ============================================================
# 数据收集
# ============================================================

tds = load_td()
di = {d: i for i, d in enumerate(tds)}

all_samples = []  # (features_dict, ret_pct, code, d1_date, bp, sp, sector, exclude)

for fn in sorted(os.listdir(S)):
    if not fn.isdigit():
        continue
    d1 = fn
    d1i = di.get(d1)
    if d1i is None or d1i < 3:
        continue
    d2 = tds[d1i - 1]
    
    with open(os.path.join(S, fn)) as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            p = l.split('|')
            if len(p) < 2:
                continue
            code = p[1]
            name = p[0]
            
            rows, date_idx = load_kline_full(code)
            d1i_k = date_idx.get(d1)
            d2i_k = date_idx.get(d2)
            if d1i_k is None or d2i_k is None:
                continue
            
            r1 = rows[d1i_k]
            bp = r1[6]  # preClose = D-2 close
            sp = r1[4]  # D-1 close
            if bp <= 0:
                continue
            ret = (sp - bp) / bp * 100
            
            # 特征
            features = extract_features(rows, d2i_k)
            
            # MA5弹起 (5M数据)
            ma5_hit, bounce = check_ma5_bounce(code, d2, features.get('close_position', 0) * 100)
            # Actually need d2_close for MA5 check
            r2_row = rows[d2i_k]
            d2_close = r2_row[4]
            ma5_hit, bounce = check_ma5_bounce(code, d2, d2_close)
            features['ma5_support'] = ma5_hit
            features['ma5_bounce'] = bounce
            
            # 行业
            sector, exclude = classify_sector(name)
            
            all_samples.append((features, ret, code, d1, bp, sp, sector, exclude, name))

print(f"总样本: {len(all_samples)}笔")

excluded = [s for s in all_samples if s[7]]
print(f"排除(制造+基建): {len(excluded)}笔 均收益{np.mean([s[1] for s in excluded]):+.2f}%")
kept = [s for s in all_samples if not s[7]]
print(f"保留: {len(kept)}笔 均收益{np.mean([s[1] for s in kept]):+.2f}%")

# ============================================================
# Walk-forward 岭回归
# ============================================================

# 按日期排序
all_samples.sort(key=lambda x: x[3])

# 转为numpy
X = np.array([[s[0][k] for k in FEATURE_KEYS] for s in all_samples])
y = np.array([s[1] for s in all_samples])

# 标准化 (walk-forward, 每次用历史数据fit)
from numpy.linalg import solve

cutoff_date = '202604'
train_cutoff = sum(1 for s in all_samples if s[3] < cutoff_date)
print(f"\n训练集(<{cutoff_date}): {train_cutoff}笔")
print(f"测试集(>={cutoff_date}): {len(all_samples) - train_cutoff}笔")

# 三种策略对比
results = {
    '等权全买': [],
    '等权_排除制造基建': [],
    '岭回归_无排除': [],
    '岭回归_排除制造基建': [],
}

daily_meta = defaultdict(list)
for i, s in enumerate(all_samples):
    daily_meta[s[3]].append(i)

for d1_date in sorted(daily_meta.keys()):
    idxs = daily_meta[d1_date]
    n_st = len(idxs)
    
    # === 1. 等权全买 ===
    pc = CAPITAL / n_st
    bl_rets = []
    for i in idxs:
        bp, sp = all_samples[i][4], all_samples[i][5]
        sh = int(pc / bp / 100) * 100
        if sh == 0: sh = 100
        cost = sh * bp
        bf = max(cost * CR, CM) + cost * TF
        tb = cost + bf
        rev = sh * sp
        sf = max(rev * CR, CM) + rev * TF + rev * SD
        bl_rets.append((rev - sf - tb) / tb * 100)
    results['等权全买'].append(np.mean(bl_rets))
    
    # === 2. 等权_排除制造基建 ===
    kept_idxs = [i for i in idxs if not all_samples[i][7]]
    if kept_idxs:
        pc2 = CAPITAL / len(kept_idxs)
        kept_rets = []
        for i in kept_idxs:
            bp, sp = all_samples[i][4], all_samples[i][5]
            sh = int(pc2 / bp / 100) * 100
            if sh == 0: sh = 100
            cost = sh * bp
            bf = max(cost * CR, CM) + cost * TF
            tb = cost + bf
            rev = sh * sp
            sf = max(rev * CR, CM) + rev * TF + rev * SD
            kept_rets.append((rev - sf - tb) / tb * 100)
        results['等权_排除制造基建'].append(np.mean(kept_rets))
    
    # === 3&4. 岭回归选TOP1 ===
    first_i = idxs[0]
    
    # 训练数据: 只用到今天之前的
    # 用前300笔后的数据开始预测
    if first_i >= 200:
        # 无排除
        hist_idx_all = [j for j in range(first_i) if all_samples[j][3] < d1_date]
        hist_idx_excl = [j for j in hist_idx_all if not all_samples[j][7]]
        
        for label, hist_idx, use_excl in [
            ('岭回归_无排除', hist_idx_all, False),
            ('岭回归_排除制造基建', hist_idx_excl, True),
        ]:
            if len(hist_idx) < 100:
                continue
            
            X_train = X[hist_idx]
            y_train = y[hist_idx]
            n_features = X_train.shape[1]
            
            # 岭回归: w = (X^T X + λI)^(-1) X^T y
            lam = 5.0
            XtX = X_train.T @ X_train
            try:
                w = solve(XtX + np.eye(n_features) * lam, X_train.T @ y_train)
            except:
                w = np.zeros(n_features)
            
            # 预测今天
            pred_idxs = [i for i in idxs if (not use_excl) or (not all_samples[i][7])]
            if not pred_idxs:
                continue
            
            preds = [X[i] @ w for i in pred_idxs]
            best_i = pred_idxs[int(np.argmax(preds))]
            bp, sp = all_samples[best_i][4], all_samples[best_i][5]
            sh = int(CAPITAL / bp / 100) * 100
            if sh == 0: sh = 100
            cost = sh * bp
            bf = max(cost * CR, CM) + cost * TF
            tb = cost + bf
            rev = sh * sp
            sf = max(rev * CR, CM) + rev * TF + rev * SD
            results[label].append((rev - sf - tb) / tb * 100)

# ============================================================
# 结果
# ============================================================

def metrics(rets, label):
    if not rets:
        return
    cum = 1.0
    peak = 1.0
    max_dd = 0.0
    monthly = defaultdict(list)
    for r in rets:
        cum *= (1 + r / 100)
        if cum > peak:
            peak = cum
        dd = (cum - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    wr = sum(1 for r in rets if r > 0) / len(rets) * 100
    dly = np.array(rets)
    sh = np.mean(dly) / np.std(dly) * np.sqrt(252) if np.std(dly) > 0 else 0
    
    # 按月份
    train_rets = [r for i, r in enumerate(rets) if sorted(daily_meta.keys())[i] < cutoff_date]
    test_rets = [r for i, r in enumerate(rets) if sorted(daily_meta.keys())[i] >= cutoff_date]
    
    tc = 1.0
    for r in test_rets: tc *= (1 + r / 100)
    
    print(f'{label}:')
    print(f'  全量: 净值{cum:.4f} 收益{(cum-1)*100:.1f}% 胜率{wr:.1f}% 回撤{max_dd:.1f}% 夏普{sh:.2f} ({len(rets)}天)')
    print(f'  样本外(≥202604): 净值{tc:.4f} 收益{(tc-1)*100:.1f}% ({len(test_rets)}天)')

# 按cutoff分月度
monthly_data = defaultdict(lambda: defaultdict(list))
for i, d1_date in enumerate(sorted(daily_meta.keys())):
    for label in results:
        if i < len(results[label]):
            monthly_data[d1_date[:6]][label].append(results[label][i])

print(f"\n{'='*90}")
print(f"  策略对比 (特征: {len(FEATURE_KEYS)}维)")
print(f"{'='*90}")
print()
for label in ['等权全买', '等权_排除制造基建', '岭回归_无排除', '岭回归_排除制造基建']:
    metrics(results[label], label)

# 月度对比 (样本外)
print(f"\n{'='*70}")
print(f"  样本外(≥202604) 月度对比")
print(f"{'='*70}")
print(f"  {'月份':<8} {'等权全买':>10} {'排除制造':>10} {'岭回归':>10} {'岭回归+排除':>12}")
print(f"  {'-'*56}")
for m in sorted(monthly_data.keys()):
    if m < '202604':
        continue
    vals = []
    for label in ['等权全买', '等权_排除制造基建', '岭回归_无排除', '岭回归_排除制造基建']:
        if label in monthly_data[m]:
            mr = 1.0
            for r in monthly_data[m][label]:
                mr *= (1 + r / 100)
            vals.append(f'{(mr-1)*100:>+7.2f}%')
        else:
            vals.append(f'{"N/A":>7}')
    print(f"  {m:<8} {vals[0]:>10} {vals[1]:>10} {vals[2]:>10} {vals[3]:>12}")
