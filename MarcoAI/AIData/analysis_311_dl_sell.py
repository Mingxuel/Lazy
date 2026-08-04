#!/usr/bin/env python3
"""
策略311 深度学习卖点优化 v3
- 纯numpy实现MLP神经网络, 预测5min bar剩余上涨空间
- 不依赖sklearn/scipy/torch
- time-series split: 60%train / 15%val / 25%test
"""
import os, sys, math, random
import numpy as np
from collections import defaultdict

random.seed(42)
np.random.seed(42)

BASE = r"C:\Lazy\MarcoAI\AIData"
SIGNAL_DIR = os.path.join(BASE, "TARGET", "311")
FIVEM_DIR = os.path.join(BASE, "5M")
KLINE_DIR = os.path.join(BASE, "1D")

COMMISSION_RATE = 0.00025
COMMISSION_MIN = 5.0
STAMP_DUTY = 0.0005
TRANSFER_FEE = 0.00001
CAPITAL = 1_000_000

# ============================================================
# 数据加载
# ============================================================
def load_trading_dates():
    dates = []
    with open(os.path.join(BASE, "TRADING_DATES")) as f:
        for line in f:
            line = line.strip()
            if line: dates.append(line)
    return sorted(dates)

def load_1d_close(code, date_str):
    fpath = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fpath): return None
    with open(fpath, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line.startswith(date_str):
                parts = line.split('|')
                if len(parts) >= 5: return float(parts[4])
    return None

def load_5m_bars(code, date_str):
    fpath = os.path.join(FIVEM_DIR, code)
    if not os.path.exists(fpath): return None
    date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    bars = []
    with open(fpath, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('|')
            if len(parts) < 6: continue
            dt = parts[0]
            if not dt.startswith(date_fmt): continue
            bars.append((dt, float(parts[4]), float(parts[2]),
                         float(parts[3]), float(parts[1]), float(parts[5])))
    return bars if bars else None

def load_signals():
    signal_days = {}
    for fname in sorted(os.listdir(SIGNAL_DIR)):
        fpath = os.path.join(SIGNAL_DIR, fname)
        if os.path.getsize(fpath) <= 3: continue
        with open(fpath, encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines: continue
        entries = []
        for line in lines:
            parts = line.split('|')
            if len(parts) < 8: continue
            entries.append((parts[0], float(parts[7])))
        if entries:
            signal_days[fname] = entries
    return signal_days


# ============================================================
# 特征工程
# ============================================================
def extract_features(bars, buy_price):
    """X(n_bars, 14), y(n_bars,)"""
    n = len(bars)
    if n < 5: return None, None

    closes = np.array([b[1] for b in bars], dtype=np.float64)
    highs = np.array([b[2] for b in bars], dtype=np.float64)
    lows = np.array([b[3] for b in bars], dtype=np.float64)
    opens = np.array([b[4] for b in bars], dtype=np.float64)
    volumes = np.array([b[5] for b in bars], dtype=np.float64)
    times = np.array([b[0] for b in bars])

    close_ratio = closes / buy_price
    bar_return = (closes - opens) / opens * 100
    bar_amplitude = (highs - lows) / opens * 100
    cum_return = (closes - closes[0]) / closes[0] * 100

    vol_ma5 = np.convolve(volumes, np.ones(5)/5, mode='same')
    vol_ratio = volumes / (vol_ma5 + 1e-10)

    daily_high = np.maximum.accumulate(highs)
    daily_low = np.minimum.accumulate(lows)
    dist_from_high = (daily_high - closes) / daily_high * 100
    dist_from_low = (closes - daily_low) / daily_low * 100

    ma5 = np.convolve(closes, np.ones(5)/5, mode='same')
    ma5_ratio = closes / (ma5 + 1e-10)
    k = min(10, n)
    ma10 = np.convolve(closes, np.ones(k)/k, mode='same')
    ma10_ratio = closes / (ma10 + 1e-10)

    time_idx = np.arange(n) / max(n - 1, 1)
    hour = np.array([int(t[11:13]) for t in times])
    is_am = (hour <= 11).astype(float)
    is_pm = (hour >= 13).astype(float)

    mom3 = np.zeros(n)
    if n >= 4:
        mom3[3:] = (closes[3:] - closes[:-3]) / (closes[:-3] + 1e-10) * 100

    prev_close = np.zeros(n)
    prev_close[0] = closes[0]
    prev_close[1:] = closes[:-1]
    prev_ret = (closes - prev_close) / (prev_close + 1e-10) * 100

    features = np.column_stack([
        close_ratio, bar_return, bar_amplitude, vol_ratio,
        cum_return, dist_from_high, dist_from_low,
        ma5_ratio, ma10_ratio, time_idx,
        is_am, is_pm, mom3, prev_ret,
    ])

    # 标签
    labels = np.zeros(n)
    for i in range(n):
        if i < n - 1:
            remaining_max = np.max(closes[i+1:])
            labels[i] = (remaining_max - closes[i]) / closes[i] * 100

    return features, labels


# ============================================================
# 纯numpy MLP神经网络
# ============================================================
class SimpleMLP:
    def __init__(self, layer_sizes, lr=0.001, l2=1e-5):
        self.layer_sizes = layer_sizes
        self.lr = lr
        self.l2 = l2
        self.weights = []
        self.biases = []
        # He initialization
        for i in range(len(layer_sizes) - 1):
            fan_in = layer_sizes[i]
            self.weights.append(np.random.randn(fan_in, layer_sizes[i+1]) * np.sqrt(2.0/fan_in))
            self.biases.append(np.zeros(layer_sizes[i+1]))
        self.trained = False

    def _relu(self, x):
        return np.maximum(0, x)

    def _relu_deriv(self, x):
        return (x > 0).astype(float)

    def forward(self, X):
        """前向传播, 返回每层激活值"""
        activations = [X]
        pre_activations = []
        for w, b in zip(self.weights[:-1], self.biases[:-1]):
            z = activations[-1] @ w + b
            pre_activations.append(z)
            activations.append(self._relu(z))
        # 输出层 (线性)
        z = activations[-1] @ self.weights[-1] + self.biases[-1]
        pre_activations.append(z)
        activations.append(z)
        return activations, pre_activations

    def predict(self, X):
        a, _ = self.forward(X)
        return a[-1].flatten()

    def fit(self, X, y, X_val=None, y_val=None, epochs=200, batch_size=64, patience=20):
        n_samples = X.shape[0]
        best_val_loss = float('inf')
        best_weights = None
        best_biases = None
        no_improve = 0

        for epoch in range(epochs):
            # Shuffle
            idx = np.random.permutation(n_samples)
            total_loss = 0

            for start in range(0, n_samples, batch_size):
                end = min(start + batch_size, n_samples)
                batch_idx = idx[start:end]
                Xb, yb = X[batch_idx], y[batch_idx]

                # Forward
                activations, pre_acts = self.forward(Xb)

                # Loss gradient (MSE)
                pred = activations[-1].flatten()
                error = (pred - yb) / len(batch_idx)
                delta = error.reshape(-1, 1)

                # Backward
                grads_w = []
                grads_b = []
                for l in range(len(self.weights) - 1, -1, -1):
                    if l == len(self.weights) - 1:  # Output layer
                        pass  # delta already computed
                    else:  # Hidden layers
                        delta = delta @ self.weights[l+1].T * self._relu_deriv(pre_acts[l])

                    dw = activations[l].T @ delta + self.l2 * self.weights[l]
                    db = np.sum(delta, axis=0)
                    grads_w.insert(0, dw)
                    grads_b.insert(0, db)

                # Update
                for l in range(len(self.weights)):
                    self.weights[l] -= self.lr * grads_w[l]
                    self.biases[l] -= self.lr * grads_b[l]

                total_loss += np.mean((pred - yb) ** 2)

            # Validation
            if X_val is not None and y_val is not None:
                val_pred = self.predict(X_val)
                val_loss = np.mean((val_pred - y_val) ** 2)
            else:
                val_loss = total_loss

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_weights = [w.copy() for w in self.weights]
                best_biases = [b.copy() for b in self.biases]
                no_improve = 0
            else:
                no_improve += 1

            if epoch % 30 == 0:
                print(f"    epoch {epoch}: val_loss={val_loss:.4f}")

            if no_improve >= patience:
                print(f"    early stop at epoch {epoch}, best_val_loss={best_val_loss:.4f}")
                break

        if best_weights:
            self.weights = best_weights
            self.biases = best_biases
        self.trained = True


# ============================================================
# 标准化
# ============================================================
class StandardScaler:
    def fit(self, X):
        self.mean = np.mean(X, axis=0)
        self.std = np.std(X, axis=0)
        self.std[self.std < 1e-10] = 1.0
        return self

    def transform(self, X):
        return (X - self.mean) / self.std


# ============================================================
# 规则策略(对比)
# ============================================================
def exit_close(bars, _): return bars[-1][1]

def exit_newhigh_trail1(bars, _):
    peak = bars[0][1]
    for b in bars:
        if b[1] > peak: peak = b[1]
        elif (peak - b[1]) / peak * 100 >= 1.0:
            return b[1]
    return bars[-1][1]

def exit_near_limit(bars, bp):
    for b in bars:
        if b[1] >= bp * 1.09: return b[1]
    return bars[-1][1]

def exit_1430(bars, _):
    for b in bars:
        if '14:30' in b[0]: return b[1]
    return bars[-1][1]

def exit_morning_max(bars, _):
    morning = [b for b in bars if '11:30' >= b[0][11:16] >= '09:30']
    return max(b[1] for b in morning) if morning else bars[0][1]


# ============================================================
# ML策略
# ============================================================
class MLStrategy:
    def __init__(self, model, scaler, threshold=0.3, name="MLP"):
        self.model = model
        self.scaler = scaler
        self.threshold = threshold
        self.name = name

    def decide(self, features):
        if len(features) < 6:
            return len(features) - 1
        X = self.scaler.transform(features)
        preds = self.model.predict(X)
        for i in range(5, len(preds)):
            if preds[i] < self.threshold:
                return i
        return len(features) - 1

    def sell_price(self, bars, features):
        idx = self.decide(features)
        return bars[idx][1]


def calc_return(buy_price, sell_price, per_cap):
    if buy_price == 0 or sell_price == 0: return 0.0
    shares = int(per_cap / buy_price / 100) * 100
    if shares == 0: shares = 100
    cost = shares * buy_price
    buy_fee = max(cost * COMMISSION_RATE, COMMISSION_MIN) + cost * TRANSFER_FEE
    total_buy = cost + buy_fee
    rev = shares * sell_price
    sell_fee = max(rev * COMMISSION_RATE, COMMISSION_MIN) + rev * TRANSFER_FEE + rev * STAMP_DUTY
    net_sell = rev - sell_fee
    return (net_sell - total_buy) / total_buy * 100


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 80)
    print("  策略311 — 深度学习卖点优化 (纯numpy MLP)")
    print("  D-2尾盘买 / D-1盘中ML决策卖出 / D-0信号日")
    print("=" * 80)

    # 加载数据
    print("\n[1/4] 加载+特征工程...")
    signal_days = load_signals()
    trading_dates = load_trading_dates()
    date_index = {d: i for i, d in enumerate(trading_dates)}

    all_features = []
    all_labels = []
    all_bars_raw = []
    all_meta = []

    for d0_date in sorted(signal_days.keys()):
        entries = signal_days[d0_date]
        d0_idx = date_index.get(d0_date)
        if d0_idx is None or d0_idx < 2: continue
        d1_date = trading_dates[d0_idx - 1]
        d2_date = trading_dates[d0_idx - 2]

        for code, d1_close in entries:
            d2_close = load_1d_close(code, d2_date)
            if d2_close is None: continue
            bars = load_5m_bars(code, d1_date)
            if bars is None or len(bars) < 10: continue
            X, y = extract_features(bars, d2_close)
            if X is None: continue
            all_features.append(X)
            all_labels.append(y)
            all_bars_raw.append(bars)
            all_meta.append((code, d1_date, d2_close))

    n_total = len(all_features)
    n_features = all_features[0].shape[1]
    print(f"  样本: {n_total}笔, bar总数: {sum(x.shape[0] for x in all_features)}, "
          f"特征: {n_features}维")

    # 时间排序
    order = sorted(range(n_total), key=lambda i: all_meta[i][1])
    all_meta = [all_meta[i] for i in order]
    all_features = [all_features[i] for i in order]
    all_labels = [all_labels[i] for i in order]
    all_bars_raw = [all_bars_raw[i] for i in order]

    # Split
    train_end = int(n_total * 0.60)
    val_end = int(n_total * 0.75)

    X_train = np.vstack([all_features[i] for i in range(train_end)])
    y_train = np.hstack([all_labels[i] for i in range(train_end)])
    X_val = np.vstack([all_features[i] for i in range(train_end, val_end)])
    y_val = np.hstack([all_labels[i] for i in range(train_end, val_end)])

    print(f"  训练: {train_end}笔/{X_train.shape[0]}bar, "
          f"验证: {val_end-train_end}笔/{X_val.shape[0]}bar, "
          f"测试: {n_total-val_end}笔")

    # 标准化
    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_val_s = scaler.transform(X_val)

    # 训练模型
    print("\n[2/4] 训练神经网络...")
    architectures = [
        ([n_features, 128, 64, 32, 1], 0.001),
        ([n_features, 256, 128, 64, 1], 0.0005),
        ([n_features, 64, 32, 16, 1], 0.002),
    ]

    best_model = None
    best_val_loss = float('inf')
    best_arch = None

    for arch, lr in architectures:
        print(f"\n  架构: {arch}, lr={lr}")
        mlp = SimpleMLP(arch, lr=lr, l2=1e-5)
        mlp.fit(X_train_s, y_train, X_val_s, y_val, epochs=200, batch_size=128, patience=20)
        val_loss = np.mean((mlp.predict(X_val_s) - y_val) ** 2)
        print(f"  最终val_MSE: {val_loss:.4f}")
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model = mlp
            best_arch = arch

    # 测试特征重要性 (简单方法: 逐个特征置零看loss变化)
    print(f"\n  最佳架构: {best_arch}, val_MSE={best_val_loss:.4f}")

    base_loss = np.mean((best_model.predict(X_val_s) - y_val) ** 2)
    feat_names = ['close_ratio', 'bar_return', 'bar_amp', 'vol_ratio',
                  'cum_return', 'dist_high', 'dist_low', 'ma5_ratio',
                  'ma10_ratio', 'time_idx', 'is_am', 'is_pm', 'mom3', 'prev_ret']
    print("  特征重要性(permutation):")
    imps = []
    for i in range(n_features):
        X_pert = X_val_s.copy()
        X_pert[:, i] = 0
        loss_i = np.mean((best_model.predict(X_pert) - y_val) ** 2)
        imp = loss_i - base_loss
        imps.append((feat_names[i], imp))
    for name, imp in sorted(imps, key=lambda x: -x[1])[:8]:
        print(f"    {name:<20}: {imp:.6f}")

    # 构建策略 + 回测
    print("\n[3/4] 回测...")
    base_strats = {
        "收盘(D-1)baseline": lambda b, p, f: exit_close(b, p),
        "新高后回落1%": lambda b, p, f: exit_newhigh_trail1(b, p),
        "接近涨停即卖": lambda b, p, f: exit_near_limit(b, p),
        "14:30固定卖": lambda b, p, f: exit_1430(b, p),
        "上午最高价(理论)": lambda b, p, f: exit_morning_max(b, p),
    }

    all_strats = dict(base_strats)

    # ML多阈值
    best_thresholds = {}
    for th in [0.05, 0.1, 0.15, 0.2, 0.3, 0.5]:
        ms = MLStrategy(best_model, scaler, threshold=th,
                       name=f"MLP_3layer_th={th:.2f}")
        all_strats[ms.name] = ms

    # 回测测试集
    by_d1 = defaultdict(list)
    for i in range(val_end, n_total):
        code, d1_date, d2_close = all_meta[i]
        by_d1[d1_date].append((code, d2_close, all_bars_raw[i], all_features[i]))

    print(f"  测试集: {n_total-val_end}笔, {len(by_d1)}个卖出日")

    results = {name: [] for name in all_strats}
    for d1_date in sorted(by_d1.keys()):
        trades = by_d1[d1_date]
        n = len(trades)
        per_cap = CAPITAL / n
        day_rets = {name: [] for name in all_strats}

        for code, d2_close, bars, features in trades:
            for sname, strat in all_strats.items():
                if isinstance(strat, MLStrategy):
                    sell_price = strat.sell_price(bars, features)
                else:
                    sell_price = strat(bars, d2_close, features)
                day_rets[sname].append(calc_return(d2_close, sell_price, per_cap))

        for sname in all_strats:
            rets = day_rets[sname]
            if rets:
                results[sname].append({
                    'date': d1_date,
                    'ret': round(sum(rets)/len(rets), 4),
                    'cnt': len(rets)
                })

    # 输出
    print("\n" + "=" * 90)
    print(f"  {'策略':<30} {'净值':>8} {'总收益%':>10} {'胜率%':>7} {'回撤%':>8} {'日均%':>7}")
    print("  " + "-" * 78)

    rankings = []
    for sname in all_strats:
        data = results[sname]
        if not data: continue
        cum = 1.0; peak = 1.0; max_dd = 0.0
        for r in data:
            cum *= (1 + r['ret'] / 100)
            if cum > peak: peak = cum
            dd = (cum - peak) / peak * 100
            if dd < max_dd: max_dd = dd
        total_ret = (cum - 1) * 100
        wr = sum(1 for r in data if r['ret'] > 0) / len(data) * 100
        daily_avg = sum(r['ret'] for r in data) / len(data)
        rankings.append((cum, sname, total_ret, wr, max_dd, daily_avg))

    rankings.sort(key=lambda x: x[0], reverse=True)
    for cum, sname, tr, wr, dd, da in rankings:
        tag = " <-- ML" if sname.startswith("MLP") else ""
        print(f"  {sname:<30} {cum:>8.4f} {tr:>10.2f} {wr:>7.1f} {dd:>8.2f} {da:>7.2f}{tag}")

    print("\n" + "=" * 90)
    print("  完成")
    print("=" * 90)


if __name__ == "__main__":
    main()
