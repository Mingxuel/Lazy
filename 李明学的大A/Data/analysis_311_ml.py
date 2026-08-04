#!/usr/bin/env python3
"""
311策略深度学习选股：用1D数据预测每只可卖股的收益，选最优
"""
import os
import numpy as np
import random
from collections import defaultdict

random.seed(42)
np.random.seed(42)

STRATEGY_DIR = r"C:\Lazy\李明学的大A\Data\Strategy"
KLINE_DIR = r"C:\Lazy\李明学的大A\Data\1D"
TRADING_DATES_FILE = r"C:\Lazy\李明学的大A\Data\交易日.config"

CR = 0.00025
CM = 5.0
SD = 0.0005
TF = 0.00001
CAPITAL = 1_000_000


# ============================================================
# 数据加载
# ============================================================
def load_trading_dates():
    dates = []
    with open(TRADING_DATES_FILE) as f:
        for line in f:
            line = line.strip()
            if line and len(line) == 8 and line.isdigit():
                dates.append(line)
    return sorted(dates)


def load_kline(code):
    """返回 [(date, open, high, low, close, volume, preClose), ...]"""
    fp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fp):
        return []
    rows = []
    with open(fp, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('\ufeff'):
                continue
            cols = line.split()
            if len(cols) < 10:
                continue
            date = cols[0]
            if not date.isdigit():
                continue
            rows.append((
                date,
                float(cols[1]),  # open
                float(cols[2]),  # high
                float(cols[3]),  # low
                float(cols[4]),  # close
                float(cols[5]),  # volume
                float(cols[9]),  # preClose
            ))
    return rows


def load_signals(date_str):
    """加载指定日期的可卖股列表"""
    fp = os.path.join(STRATEGY_DIR, date_str)
    if not os.path.exists(fp):
        return []
    stocks = []
    with open(fp) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 2:
                stocks.append((parts[0], parts[1]))  # name, code
    return stocks


# ============================================================
# 特征工程
# ============================================================
def extract_features(kline_rows, d1_date, d2_date):
    """
    从1D K线提取特征（用到D-2为止的数据）
    kline_rows: 该股的全部K线
    d1_date: D-1日期 (卖出日, 用于获取preClose=买入价)
    d2_date: D-2日期 (买入日截止)
    返回: features dict, D-1 close(实际卖出价, label用)
    """
    if len(kline_rows) < 60:
        return None, None

    # 建立日期索引
    date_idx = {r[0]: i for i, r in enumerate(kline_rows)}

    d1_idx = date_idx.get(d1_date)
    d2_idx = date_idx.get(d2_date)
    if d1_idx is None or d2_idx is None or d2_idx < 20:
        return None, None

    # D-1行: close=卖出价, preClose=D-2收盘=买入价
    d1_row = kline_rows[d1_idx]
    sell_price = d1_row[4]   # D-1 close
    buy_price = d1_row[6]    # D-1 preClose = D-2 close

    if buy_price <= 0 or sell_price <= 0:
        return None, None
        return None, None

    # D-2行
    d2_row = kline_rows[d2_idx]

    # D-3, D-4行
    d3_row = kline_rows[d2_idx - 1] if d2_idx >= 1 else None
    d4_row = kline_rows[d2_idx - 2] if d2_idx >= 2 else None
    d5_row = kline_rows[d2_idx - 3] if d2_idx >= 3 else None

    f = {}

    # === 311模式特征 ===
    # D-4涨停强度
    if d4_row and d5_row:
        f['limit_up_gain'] = (d4_row[4] - d5_row[4]) / d5_row[4] * 100
    else:
        f['limit_up_gain'] = 0

    # D-3放量倍数
    if d3_row:
        f['vol_surge_d3'] = d3_row[5] / d2_row[5] if d2_row[5] > 0 else 1
    else:
        f['vol_surge_d3'] = 1

    # D-2回踩深度
    if d3_row:
        f['pullback_depth'] = (d3_row[4] - d2_row[4]) / d3_row[4] * 100
    else:
        f['pullback_depth'] = 0

    # D-2下影线
    d2_range = d2_row[2] - d2_row[3]
    f['lower_shadow'] = (d2_row[4] - d2_row[3]) / d2_range * 100 if d2_range > 0 else 50

    # D-2缩量(相比D-3)
    f['vol_contract'] = 1 if (d3_row and d2_row[5] < d3_row[5] * 0.8) else 0

    # === 趋势特征 (截至D-2) ===
    closes = np.array([r[4] for r in kline_rows[:d2_idx + 1]])
    volumes = np.array([r[5] for r in kline_rows[:d2_idx + 1]])
    highs = np.array([r[2] for r in kline_rows[:d2_idx + 1]])
    lows = np.array([r[3] for r in kline_rows[:d2_idx + 1]])

    # MA位置
    f['ma5_ratio'] = closes[-1] / np.mean(closes[-5:]) if len(closes) >= 5 else 1
    f['ma10_ratio'] = closes[-1] / np.mean(closes[-10:]) if len(closes) >= 10 else 1
    f['ma20_ratio'] = closes[-1] / np.mean(closes[-20:]) if len(closes) >= 20 else 1
    f['ma60_ratio'] = closes[-1] / np.mean(closes[-60:]) if len(closes) >= 60 else 1

    # 近期涨跌幅
    f['ret_1d'] = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0
    f['ret_5d'] = (closes[-1] - closes[-5]) / closes[-5] * 100 if len(closes) >= 5 else 0
    f['ret_10d'] = (closes[-1] - closes[-10]) / closes[-10] * 100 if len(closes) >= 10 else 0
    f['ret_20d'] = (closes[-1] - closes[-20]) / closes[-20] * 100 if len(closes) >= 20 else 0

    # 波动率
    if len(closes) >= 10:
        daily_rets = (closes[1:] - closes[:-1]) / closes[:-1] * 100
        f['volatility_10d'] = np.std(daily_rets[-10:]) if len(daily_rets) >= 10 else 0
        f['volatility_20d'] = np.std(daily_rets[-20:]) if len(daily_rets) >= 20 else 0
    else:
        f['volatility_10d'] = 0
        f['volatility_20d'] = 0

    # 成交量特征
    if len(volumes) >= 10:
        f['vol_ratio_5d'] = volumes[-1] / np.mean(volumes[-5:])
        f['vol_ratio_10d'] = volumes[-1] / np.mean(volumes[-10:])
        f['vol_trend_5d'] = np.mean(volumes[-5:]) / np.mean(volumes[-10:-5]) if len(volumes) >= 10 else 1
    else:
        f['vol_ratio_5d'] = 1
        f['vol_ratio_10d'] = 1
        f['vol_trend_5d'] = 1

    # D-2振幅
    f['amp_d2'] = (d2_row[2] - d2_row[3]) / d2_row[1] * 100 if d2_row[1] > 0 else 0

    # D-2收盘位置
    f['close_position_d2'] = (d2_row[4] - d2_row[3]) / d2_range * 100 if d2_range > 0 else 50

    # 高低点距离
    high_20d = np.max(highs[-20:]) if len(highs) >= 20 else highs[-1]
    low_20d = np.min(lows[-20:]) if len(lows) >= 20 else lows[-1]
    f['dist_from_20d_high'] = (high_20d - closes[-1]) / high_20d * 100 if high_20d > 0 else 0
    f['dist_from_20d_low'] = (closes[-1] - low_20d) / low_20d * 100 if low_20d > 0 else 0

    # D-2是否新低（相比D-3）
    f['new_low'] = 1 if d2_row[3] < d3_row[3] else 0

    f['_buy_price'] = buy_price

    return f, sell_price


# ============================================================
# 简单MLP
# ============================================================
class SimpleMLP:
    def __init__(self, sizes, lr=0.001, l2=1e-5):
        self.W = []
        self.B = []
        for i in range(len(sizes) - 1):
            fan = sizes[i]
            self.W.append(np.random.randn(fan, sizes[i+1]) * np.sqrt(2.0 / fan))
            self.B.append(np.zeros(sizes[i+1]))

    def _relu(self, x):
        return np.maximum(0, x)

    def _drelu(self, x):
        return (x > 0).astype(float)

    def predict(self, X):
        a = X
        for w, b in zip(self.W[:-1], self.B[:-1]):
            a = self._relu(a @ w + b)
        return (a @ self.W[-1] + self.B[-1]).flatten()

    def fit(self, X, y, Xv=None, yv=None, epochs=200, bs=128, pat=25):
        best_loss = float('inf')
        best_W = None
        best_B = None
        ni = 0
        for ep in range(epochs):
            idx = np.random.permutation(X.shape[0])
            for s in range(0, X.shape[0], bs):
                e = min(s + bs, X.shape[0])
                bi = idx[s:e]
                Xb, yb = X[bi], y[bi]
                acts = [Xb]
                pas = []
                for w, b in zip(self.W[:-1], self.B[:-1]):
                    z = acts[-1] @ w + b
                    pas.append(z)
                    acts.append(self._relu(z))
                z = acts[-1] @ self.W[-1] + self.B[-1]
                pas.append(z)
                acts.append(z)
                err = (acts[-1].flatten() - yb) / len(bi)
                delta = err.reshape(-1, 1)
                for l in range(len(self.W) - 1, -1, -1):
                    if l < len(self.W) - 1:
                        delta = delta @ self.W[l+1].T * self._drelu(pas[l])
                    dw = acts[l].T @ delta + 1e-5 * self.W[l]
                    db = np.sum(delta, axis=0)
                    self.W[l] -= 0.001 * dw
                    self.B[l] -= 0.001 * db

            if Xv is not None:
                vl = np.mean((self.predict(Xv) - yv) ** 2)
            else:
                vl = np.mean((self.predict(X) - y) ** 2)

            if vl < best_loss:
                best_loss = vl
                best_W = [w.copy() for w in self.W]
                best_B = [b.copy() for b in self.B]
                ni = 0
            else:
                ni += 1
            if ni >= pat:
                break
        if best_W:
            self.W = best_W
            self.B = best_B
        return best_loss


class Scaler:
    def fit(self, X):
        self.m = np.mean(X, axis=0)
        self.s = np.std(X, axis=0)
        self.s[self.s < 1e-10] = 1.0
        return self

    def transform(self, X):
        return (X - self.m) / self.s


def fee(buy, sell, pc):
    if buy == 0 or sell == 0:
        return 0.0
    sh = int(pc / buy / 100) * 100
    if sh == 0:
        sh = 100
    c = sh * buy
    bf = max(c * CR, CM) + c * TF
    tb = c + bf
    r = sh * sell
    sf = max(r * CR, CM) + r * TF + r * SD
    return (r - sf - tb) / tb * 100


# ============================================================
# 主流程
# ============================================================
print("=" * 80)
print("  策略311 深度学习选股")
print("=" * 80)

# 加载交易日
tds = load_trading_dates()
di = {d: i for i, d in enumerate(tds)}
print(f"交易日: {len(tds)}天")

# 构建数据集
print("构建数据集...")
all_samples = []  # [(features_dict, return_pct, code, d1_date)]

for d1_date in sorted(os.listdir(STRATEGY_DIR)):
    if not d1_date.isdigit():
        continue
    d1_idx = di.get(d1_date)
    if d1_idx is None or d1_idx < 3:
        continue
    d2_date = tds[d1_idx - 1]

    stocks = load_signals(d1_date)
    if not stocks:
        continue

    for name, code in stocks:
        kline = load_kline(code)
        if not kline:
            continue
        features, sell_price = extract_features(kline, d1_date, d2_date)
        if features is None:
            continue
        buy_price = features['_buy_price']
        del features['_buy_price']
        ret_pct = (sell_price - buy_price) / buy_price * 100
        all_samples.append((features, ret_pct, code, d1_date, buy_price, sell_price))

print(f"样本: {len(all_samples)}笔")

# 特征列表
feature_keys = sorted(all_samples[0][0].keys())
n_features = len(feature_keys)
print(f"特征: {n_features}维 {feature_keys}")

# 构建X, y
X_all = np.array([[s[0][k] for k in feature_keys] for s in all_samples])
y_all = np.array([s[1] for s in all_samples])

# 按时间切分
n = len(X_all)
tr_end = int(n * 0.70)
vl_end = int(n * 0.85)

X_train, y_train = X_all[:tr_end], y_all[:tr_end]
X_val, y_val = X_all[tr_end:vl_end], y_all[tr_end:vl_end]
test_idx = list(range(vl_end, n))

print(f"训练: {tr_end}, 验证: {vl_end - tr_end}, 测试: {n - vl_end}")

# 标准化
scaler = Scaler().fit(X_train)
X_train_s = scaler.transform(X_train)
X_val_s = scaler.transform(X_val)

# 训练MLP
print("\n训练神经网络...")
n_feat = X_train.shape[1]
models = []
for hidden, lr in [
    ([n_feat, 256, 128, 64, 1], 0.001),
    ([n_feat, 512, 256, 128, 1], 0.0005),
    ([n_feat, 128, 64, 32, 1], 0.002),
]:
    print(f"  {hidden} lr={lr}...", end=" ")
    mlp = SimpleMLP(hidden, lr=lr)
    vl = mlp.fit(X_train_s, y_train, X_val_s, y_val, epochs=300, bs=128, pat=30)
    print(f"val_MSE={vl:.4f}")
    models.append((vl, mlp, hidden))

best_vl, best_model, best_arch = min(models, key=lambda x: x[0])
print(f"最佳: {best_arch}, val_MSE={best_vl:.4f}")

# 回测测试集
print("\n回测...")
# 按日期分组
by_date = defaultdict(list)
for i in test_idx:
    by_date[all_samples[i][3]].append(i)

daily_baseline = []    # 等权全买
daily_ml_top1 = []     # ML选最优1只

for d1_date in sorted(by_date.keys()):
    indices = by_date[d1_date]
    n_stocks = len(indices)

    # 获取该日所有候选股的预测和实际收益
    preds = []
    actuals = []
    buy_prices = []
    sell_prices = []

    for idx in indices:
        X_i = np.array([[all_samples[idx][0][k] for k in feature_keys]])
        X_i_s = scaler.transform(X_i)
        pred = best_model.predict(X_i_s)[0]
        actual = all_samples[idx][1]
        code = all_samples[idx][2]

        # get buy/sell from sample data
        features = all_samples[idx][0]
        # We need buy/sell prices - they were in the original extraction
        # Let's store them in the sample tuple
        buy_price = all_samples[idx][4]
        sell_price = all_samples[idx][5]

        preds.append(pred)
        buy_prices.append(buy_price)
        sell_prices.append(sell_price)

    if not preds:
        continue

    # Baseline: 等权
    pc = CAPITAL / n_stocks
    bl_ret = np.mean([fee(bp, sp, pc) for bp, sp in zip(buy_prices, sell_prices)])
    daily_baseline.append(bl_ret)

    # ML: 选预测最高的一只
    best_i = np.argmax(preds)
    ml_ret = fee(buy_prices[best_i], sell_prices[best_i], CAPITAL)
    daily_ml_top1.append(ml_ret)

# 计算指标
def compute_metrics(rets):
    cum = 1.0
    peak = 1.0
    max_dd = 0.0
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
    return cum, (cum - 1) * 100, wr, max_dd, sh

for label, rets in [("等权全买(baseline)", daily_baseline), ("ML选TOP1", daily_ml_top1)]:
    cum, tr, wr, dd, sh = compute_metrics(rets)
    print(f"  {label}: 净值{cum:.4f} 收益{tr:.1f}% 胜率{wr:.1f}% 回撤{dd:.1f}% 夏普{sh:.2f} ({len(rets)}天)")

print("\n完成!")
