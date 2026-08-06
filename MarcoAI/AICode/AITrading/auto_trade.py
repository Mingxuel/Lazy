# -*- coding: utf-8 -*-
"""
311策略 自动交易（最终版 v2.0）
  仅 TPO3 选股
  卖出: 止损-6% > 涨停 > 14:55 收盘卖出  (无移动止盈)
  止损卖: 盘口卖一 - 0.01，2tick 未成交→撤单→重挂卖一-0.01
  尾盘卖: 最新价，2tick 未成交→撤单→重挂卖一-0.01
  买入: 14:57:03 挂单 @ 收盘价 × 1.01
  配置文件: auto_trade_config.json (score_now开关)
  输出: tpo3_tick.txt (实时tick) / tpo3_scores.txt (按需评分)
"""
import os, sys, time, json, logging, math, numpy as np
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api import QMTAPI

# ==================== 配置 ====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, f'auto_trade_{datetime.now().strftime("%Y%m%d")}.log')
TICK_FILE = os.path.join(SCRIPT_DIR, f'tpo3_tick_{datetime.now().strftime("%Y%m%d")}.txt')
SCORE_SNAPSHOT_FILE = os.path.join(SCRIPT_DIR, 'tpo3_scores.txt')
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'auto_trade_config.json')

# 数据路径
KLINE_DIR = r'C:\Lazy\李明学的大A\Data\1D'
TPO3_FILE = r'C:\Lazy\李明学的大A\Data\Target\TPO3'
TRADING_DAYS = r'C:\Lazy\李明学的大A\Data\交易日.config'

# 时机
FORCE_SELL_TIME  = '14:55:00'   # 强制收盘卖出
SCORE_START_TIME = '14:56:30'   # 开始循环评分(算10次, 取最后一次)
SCORE_END_TIME   = '14:56:59'   # 评分结束
BUY_TIME         = '14:57:03'   # 集合竞价挂单(晚3秒避免撮合中买入)

# 311模型参数 — 由 train_walk_forward() 每日动态计算, 严格对齐回测
KEYS = ['pb_depth', 'vol_contract', 'ma5_dev', 'pc_vs_low_atr', 'high_vs_pc_atr', 'ma_golden']
W = np.zeros(6)    # 动态更新
MU = np.zeros(6)   # 动态更新
SG = np.ones(6)    # 动态更新

# 交易参数
STOP_PCT = 0.94          # 止损线: 买入价 × 0.94
RETRY_TICKS = 2          # 2 tick 未成交则重试
TICK_INTERVAL = 3        # 每个 tick 约 3 秒 (QMT快照刷新间隔)
SELL_PRICE_DISCOUNT = 0.01  # 止损/尾盘重挂: 卖一价 - 0.01

# ==================== 日志 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('auto_trade')

# ==================== 安全类型转换 ====================
def _safe_float(val, default=0.0):
    """安全转 float，处理 QMT tick 字段可能是 list 的情况"""
    if val is None:
        return default
    if isinstance(val, (list, tuple)):
        return float(val[0]) if len(val) > 0 else default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# ==================== 配置文件热开关 ====================
def _init_config():
    """初始化配置文件"""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'score_now': False}, f)

def read_config():
    """读取配置，返回 dict"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'score_now': False}

def write_config_key(key, value):
    """写入配置项（保留其他项不变）"""
    cfg = read_config()
    cfg[key] = value
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f)

# ==================== 交易日判断 ====================
def load_trading_days():
    days = []
    with open(TRADING_DAYS) as f:
        for l in f:
            l = l.strip()
            if l and l.isdigit() and len(l) == 8:
                days.append(l)
    return sorted(days)

# ==================== TPO3 加载 ====================
def load_tpo3():
    """加载TPO3买池，返回 [(name, code), ...]
    兼容两种格式: name|code 或 纯code (自动从xtdata查名称)
    """
    if not os.path.exists(TPO3_FILE):
        log.warning(f"TPO3文件不存在: {TPO3_FILE}")
        return []
    codes = []
    with open(TPO3_FILE, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l: continue
            if '|' in l:
                p = l.split('|')
                codes.append((p[0], p[1]))
            else:
                # 纯代码格式: 用 xtdata 查名称
                code = l
                try:
                    from xtquant import xtdata
                    detail = xtdata.get_instrument_detail(code)
                    name = detail.get('InstrumentName', code) if detail else code
                except:
                    name = code
                codes.append((name, code))
    return codes

# ==================== K线特征预计算 ====================
_precomputed = {}

def _load_precomputed(code, d3_date):
    """从1D K线预计算 ATR10, MA5, MA10, 前日MA5/MA10, D-3成交量
    截止到D-3日"""
    fp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fp):
        return None

    all_rows = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('\ufeff'):
                continue
            c = l.split()
            if len(c) < 10 or not c[0].isdigit():
                continue
            all_rows.append((c[0], float(c[1]), float(c[2]), float(c[3]),
                             float(c[4]), float(c[5]), float(c[9])))

    idx = {r[0]: i for i, r in enumerate(all_rows)}
    di_k = idx.get(d3_date)
    if di_k is None or di_k < 10:
        return None

    closes = np.array([r[4] for r in all_rows[:di_k + 1]])
    highs = np.array([r[2] for r in all_rows[:di_k + 1]])

    # MA5 & MA10 at D-3
    ma5 = float(np.mean(closes[-5:]))
    ma10 = float(np.mean(closes[-10:]))
    # Previous day's MA5 & MA10 (D-4)
    last_ma5 = float(np.mean(closes[-6:-1]))
    last_ma10 = float(np.mean(closes[-11:-1]))
    # 被滚动丢弃的收盘价
    # MA5 at D-3 = avg(closes[-5:]) = avg(D-7_c ... D-3_c), 最老是 closes[-5]=D-7_c
    # MA10 at D-3 = avg(closes[-10:]) = avg(D-12_c ... D-3_c), 最老是 closes[-10]=D-12_c
    oldest_ma5_close = closes[-5]
    oldest_ma10_close = closes[-10]

    # ATR10
    trs = []
    for i in range(di_k - 9, di_k + 1):
        h = highs[i]
        l = all_rows[i][3]
        pc = all_rows[i - 1][4] if i > 0 else all_rows[i][6]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr10 = float(np.mean(trs))

    d3_vol = all_rows[di_k][5]  # D-3 全天成交量

    return {
        'atr10': atr10, 'ma5': ma5, 'ma10': ma10,
        'last_ma5': last_ma5, 'last_ma10': last_ma10,
        'd3_vol': d3_vol,
        'oldest_ma5_close': oldest_ma5_close,
        'oldest_ma10_close': oldest_ma10_close,
    }

def precompute_tpo3(tpo3_codes, d3_date):
    """预计算TPO3所有候选股的各项基础数据"""
    for name, code in tpo3_codes:
        data = _load_precomputed(code, d3_date)
        if data is not None:
            _precomputed[code] = data
            log.info(f"  {name}({code}): ATR10={data['atr10']:.3f} "
                     f"MA5={data['ma5']:.2f} D3量={data['d3_vol']/1e6:.1f}M")

# ==================== Walk-Forward 训练 ====================
# 严格对齐 analysis_311_1d_detail.py 的特征提取和岭回归逻辑

def _load_kline_backtest(code):
    """加载K线 -> 回测兼容格式: (date, o, h, l, c, v, preClose)"""
    fp = os.path.join(KLINE_DIR, code)
    rows = []
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('\ufeff'): continue
            c = l.split()
            if len(c) < 10 or not c[0].isdigit(): continue
            rows.append((c[0], float(c[1]), float(c[2]), float(c[3]),
                         float(c[4]), float(c[5]), float(c[9])))
    return rows, {r[0]: i for i, r in enumerate(rows)}


def train_walk_forward(tds, di):
    """
    严格对齐回测 Walk-Forward:
    加载所有历史Strategy样本 → 提取6特征 → 标准化 → 岭回归(λ=2.0)
    返回 (W, MU, SG)
    """
    from numpy.linalg import solve

    SRC = r'C:\Lazy\李明学的大A\Data\Strategy'
    FEATURES = KEYS
    samples = []

    for fn in sorted(os.listdir(SRC)):
        if not fn.isdigit():
            continue
        d1 = fn  # D-1 (卖出日)
        d1i = di.get(d1)
        if d1i is None or d1i < 3:
            continue
        d2 = tds[d1i - 1]  # D-2 (买入日)

        with open(os.path.join(SRC, fn), encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if not l:
                    continue
                p = l.split('|')
                if len(p) < 2:
                    continue
                code = p[1]
                rows, date_idx = _load_kline_backtest(code)
                d1i_k = date_idx.get(d1)
                d2i_k = date_idx.get(d2)
                if d1i_k is None or d2i_k is None:
                    continue
                r1 = rows[d1i_k]
                bp = r1[6]  # preClose = D-2收盘
                sp_close = r1[4]
                if bp <= 0:
                    continue

                # ---- 特征提取: 完全复制 backtest L57-76 ----
                r2 = rows[d2i_k]
                o2, h2, l2, c2, v2, pc2 = r2[1], r2[2], r2[3], r2[4], r2[5], r2[6]
                r3 = rows[d2i_k - 1] if d2i_k >= 1 else None

                cls = np.array([r[4] for r in rows[:d2i_k + 1]])
                highs = np.array([r[2] for r in rows[:d2i_k + 1]])
                n = len(cls)

                f = {}
                f['pb_depth'] = (r3[4] - c2) / r3[4] * 100 if (r3 and r3[4] > 0) else 0
                f['vol_contract'] = 1 if (r3 and v2 < r3[5] * 0.8) else 0
                f['ma5_dev'] = (c2 - np.mean(cls[-5:])) / np.mean(cls[-5:]) * 100 if n >= 5 else 0

                if n >= 10:
                    trs = []
                    for i in range(d2i_k - 9, d2i_k + 1):
                        h = highs[i]
                        l = rows[i][3]
                        pc = rows[i - 1][4] if i > 0 else rows[i][6]
                        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
                    atr10 = np.mean(trs) if trs else 1
                else:
                    atr10 = h2 - l2 if h2 > l2 else 1

                f['pc_vs_low_atr'] = (pc2 - rows[d2i_k][3]) / atr10 if atr10 > 0 else 0
                f['high_vs_pc_atr'] = (h2 - pc2) / atr10 if atr10 > 0 else 0

                ma_golden = 0
                if d2i_k >= 10:
                    c_arr = np.array([r[4] for r in rows[:d2i_k + 1]])
                    ma5 = np.mean(c_arr[-5:])
                    ma10 = np.mean(c_arr[-10:])
                    ma5p = np.mean(c_arr[-6:-1])
                    ma10p = np.mean(c_arr[-11:-1])
                    ma_golden = 1 if (ma5p <= ma10p and ma5 > ma10) else 0
                f['ma_golden'] = ma_golden

                samples.append((f, sp_close, bp))

    if len(samples) < 100:
        log.warning(f"Walk-Forward 训练样本不足 ({len(samples)}), 使用默认权重")
        return (np.array([0.96, 0.21, 0.47, -0.45, 0.36, 0.40]),
                np.array([2.0, 0.75, 2.0, 1.5, 1.0, 0.15]),
                np.array([5.0, 0.4, 5.0, 1.5, 1.0, 0.35]))

    X = np.array([[s[0].get(k, 0) for k in FEATURES] for s in samples])
    y = np.array([(s[1] - s[2]) / s[2] * 100 for s in samples])

    mu = X.mean(axis=0)
    sg = X.std(axis=0) + 1e-8
    Xn = (X - mu) / sg

    d = Xn.shape[1]
    try:
        w = solve(Xn.T @ Xn + np.eye(d) * 2.0, Xn.T @ y)
    except Exception:
        w = np.zeros(d)

    log.info(f"Walk-Forward 训练完成: {len(samples)}个样本, "
             f"W={np.array2string(w, precision=3, suppress_small=True)}")
    return w, mu, sg


# ==================== 实时特征计算 (对齐回测) ====================
def compute_features(code, tick):
    """
    用QMT tick数据 + 预计算的ATR/MA5/量 → 6特征
    tick: QMT get_full_tick 返回的单股dict
    """
    p = _precomputed.get(code)
    if p is None: return None
    atr10 = p['atr10']
    ma5_base = p['ma5']
    ma10_base = p['ma10']
    last_ma5 = p['last_ma5']
    last_ma10 = p['last_ma10']
    d3_vol = p['d3_vol']
    oldest_5 = p['oldest_ma5_close']
    oldest_10 = p['oldest_ma10_close']

    pre_close = _safe_float(tick.get('lastClose', 0))
    last_price = _safe_float(tick.get('lastPrice', 0))
    high = _safe_float(tick.get('high', 0))
    low = _safe_float(tick.get('low', 0))
    today_vol = _safe_float(tick.get('volume', 0))

    if pre_close <= 0 or last_price <= 0:
        return None

    pb_depth = (pre_close - last_price) / pre_close * 100
    pc_vs_low_atr = (pre_close - low) / atr10 if atr10 > 0 else 0
    high_vs_pc_atr = (high - pre_close) / atr10 if atr10 > 0 else 0

    # vol_contract: D-2累计量(盘中) < D-3全天量 × 0.8
    # 注意QMT的volume是累计成交量(手), d3_vol也是手
    vol_contract = 1 if today_vol > 0 and d3_vol > 0 and today_vol < d3_vol * 0.8 else 0

    # ⚠️ MA滚动: 先算D-2的MA5/MA10, 再算ma5_dev和ma_golden
    # 严格对齐回测: ma5_dev 用 D-2_MA5 而非 D-3_MA5
    # D-2 MA5 = (D-3_MA5 × 5 - D-7_c + D-2_c) / 5   (丢最老的, 加今天的)
    # D-2 MA10 = (D-3_MA10 × 10 - D-12_c + D-2_c) / 10
    ma5_today = (ma5_base * 5 - oldest_5 + last_price) / 5 if ma5_base > 0 else 0
    ma10_today = (ma10_base * 10 - oldest_10 + last_price) / 10 if ma10_base > 0 else 0
    ma5_dev = (last_price - ma5_today) / ma5_today * 100 if ma5_today > 0 else 0
    ma_golden = 1 if (last_ma5 <= last_ma10 and ma5_today > ma10_today) else 0

    return {
        'pb_depth': pb_depth,
        'vol_contract': vol_contract,
        'ma5_dev': ma5_dev,
        'pc_vs_low_atr': pc_vs_low_atr,
        'high_vs_pc_atr': high_vs_pc_atr,
        'ma_golden': ma_golden,
    }

def score_stock(code, tick):
    """单股评分"""
    f = compute_features(code, tick)
    if f is None: return None, None
    Xs = np.array([f[k] for k in KEYS])
    score = float(((Xs - MU) / SG) @ W)
    return score, f

# ==================== Tick输出 & 按需评分 ====================
def write_tick_snapshot(now_str, ticks, tpo3_codes, hold_code=None, hold_cost=0):
    """将当前tick数据写入文件（每次循环覆盖）"""
    lines = [f"# {now_str}", ""]
    names = {c: n for n, c in tpo3_codes}

    # 持仓
    if hold_code and hold_cost:
        ht = ticks.get(hold_code, {})
        lp = _safe_float(ht.get('lastPrice', 0))
        pre = _safe_float(ht.get('lastClose', 0))
        hi = _safe_float(ht.get('high', 0))
        lo = _safe_float(ht.get('low', 0))
        chg = (lp / pre - 1) * 100 if pre > 0 else 0
        pnl = (lp - hold_cost)
        lines.append(f"持仓 {hold_code}: {lp:.2f} 涨{chg:+.2f}% H{hi:.2f} L{lo:.2f}"
                     f"  止损{calc_stop_price(hold_cost):.2f}")
        lines.append("")

    # TPO3 候选
    lines.append(f"{'代码':<14} {'名称':<8} {'现价':>7} {'涨跌':>7} {'卖一':>7} {'H':>7} {'L':>7} {'pb%':>7}")
    lines.append("-" * 70)
    for _, code in tpo3_codes:
        t = ticks.get(code, {})
        lp = _safe_float(t.get('lastPrice', 0))
        pre = _safe_float(t.get('lastClose', 0))
        hi = _safe_float(t.get('high', 0))
        lo = _safe_float(t.get('low', 0))
        ask1 = _safe_float(t.get('askPrice', 0) or t.get('sellPrice', 0) or 0)
        chg = (lp / pre - 1) * 100 if pre > 0 else 0
        pb = (pre - lp) / pre * 100 if pre > 0 else 0
        nm = names.get(code, code)
        lines.append(f"{code:<14} {nm:<8} {lp:>7.2f} {chg:>+6.2f}% {ask1:>7.2f} {hi:>7.2f} {lo:>7.2f} {pb:>+6.2f}%")

    with open(TICK_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def write_scores_snapshot(now_str, ticks, tpo3_codes, tpo3_scores):
    """按需评分：计算完整评分并写入文件"""
    names = {c: n for n, c in tpo3_codes}
    lines = [f"# TPO3 评分快照 — {now_str}", ""]

    # 权重
    wn = ['pb_depth', 'vol_contract', 'ma5_dev', 'bear', 'bull', 'golden']
    lines.append("=== 当前权重 ===")
    for nm, wt in zip(wn, W):
        lines.append(f"  {nm}: {wt:+.4f}")
    lines.append("")

    # 原始特征
    lines.append("=== 原始特征 ===")
    header = f"{'代码':<14} {'名称':<8} " + " ".join(f"{k:>8}" for k in ['pb_depth','vol_ct','ma5_dev','bear','bull','golden'])
    lines.append(header)
    for _, code in tpo3_codes:
        t = ticks.get(code, {})
        sc, fv = score_stock(code, t)
        if fv is None: continue
        vals = " ".join(f"{fv.get(k,0):>+7.2f}" if isinstance(fv.get(k,0), float) else f"{fv.get(k,0):>8}" for k in KEYS)
        lines.append(f"{code:<14} {names.get(code,code):<8} {vals}  → 评分{sc:+.4f}")

    lines.append("")

    # 排名
    lines.append("=== 最终排名 ===")
    ranked = sorted(tpo3_scores.items(), key=lambda x: -x[1])
    for i, (code, sc) in enumerate(ranked):
        mark = " ← 买入" if i == 0 else ""
        lines.append(f"  {i+1}. {names.get(code,code)}({code})  评分:{sc:+.4f}{mark}")

    with open(SCORE_SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    log.info(f"  ✅ 按需评分已输出 → {SCORE_SNAPSHOT_FILE}")

# ==================== 卖出逻辑 ====================
def calc_limit_up(pre_close):
    """A股涨停价: 两次四舍五入 (先到3位, 再到2位)"""
    raw = pre_close * 1.10
    v3 = math.floor(raw * 1000 + 0.5) / 1000   # 第一次: 四舍五入到3位
    v2 = math.floor(v3 * 100 + 0.5) / 100       # 第二次: 四舍五入到2位
    return round(v2, 2)

def calc_stop_price(buy_price):
    """止损价 = 买入价 × 0.94 (普通四舍五入即可)"""
    return round(buy_price * STOP_PCT, 2)

def check_sell_signal(tick, hold_cost):
    """
    检查止损信号 (仅止损, 涨停由开盘预挂单处理)
    优先级: 开盘止损 > 日内止损
    返回: (should_sell, sell_price, reason)
    """
    pre_close = _safe_float(tick.get('lastClose', 0))
    last_price = _safe_float(tick.get('lastPrice', 0))
    low = _safe_float(tick.get('low', 0))
    open_price = _safe_float(tick.get('open', 0))
    # 卖一价: QMT返回 askPrice (优先) 或 sellPrice (兼容)
    ask1 = _safe_float(tick.get('askPrice', 0) or tick.get('sellPrice', 0) or 0)

    stop_price = calc_stop_price(hold_cost)

    # 1. 开盘止损
    if open_price > 0 and open_price <= stop_price:
        return True, open_price, 'open_stop'

    # 2. 日内止损: 卖一 - 0.01, 如果无卖一则用最新价 - 0.01 (绝不用bp×0.94!)
    if low > 0 and low <= stop_price:
        if ask1 > 0:
            sp = ask1 - SELL_PRICE_DISCOUNT
        elif last_price > 0:
            sp = last_price - SELL_PRICE_DISCOUNT
        else:
            sp = stop_price  # 最后兜底, 但几乎不会走到这里
        return True, sp, 'low_stop'

    return False, None, None

# ==================== 智能卖出(带重试) ====================
def smart_sell(api, code, volume, sell_price, reason, max_retries=5):
    """
    智能卖出: 挂单 → 等2tick → 查成交 → 未成则撤单重挂
    - 止损/尾盘: 卖一 - 0.01 → 2tick未成 → 重挂卖一 - 0.01
    - 涨停: 涨停价挂单
    """
    from xtquant import xtdata

    # 卖出前: 清理所有未成交委托
    pending = api.orders()
    for o in pending:
        if o.order_status in (48, 49, 50):  # 未报/待报/已报
            log.info(f"  卖出前撤旧委托: {o.stock_code} {o.order_volume}股")
            if o.order_id and o.order_id.isdigit():
                api.cancel(int(o.order_id))
    time.sleep(0.5)

    current_price = sell_price
    for attempt in range(max_retries):
        # 如果是重试，拉最新 tick 更新卖一价
        if attempt > 0 and reason in ('low_stop', 'close', 'open_stop'):
            ticks = xtdata.get_full_tick([code])
            t = ticks.get(code, {})
            ask1 = _safe_float(t.get('askPrice', 0) or t.get('sellPrice', 0) or 0)
            last_px = _safe_float(t.get('lastPrice', 0))
            if reason in ('low_stop', 'open_stop'):
                if ask1 > 0: current_price = ask1 - SELL_PRICE_DISCOUNT
                elif last_px > 0: current_price = last_px - SELL_PRICE_DISCOUNT
            elif reason == 'close':
                if ask1 > 0: current_price = ask1 - SELL_PRICE_DISCOUNT
                elif last_px > 0: current_price = last_px

        log.info(f"  卖出尝试 {attempt+1}/{max_retries}: {code} {volume}股 @{current_price:.2f} [{reason}]")

        # 下单前: 记录该代码已成交量
        trades_before = sum(t.traded_volume for t in api.trades()
                            if t.stock_code == code and t.direction == 2)

        order_id = api.sell(code, volume, current_price)
        log.info(f"  下单ID: {order_id}")

        # 等 2 tick (2 × 3秒)
        wait_time = RETRY_TICKS * TICK_INTERVAL
        log.info(f"  等 {wait_time}s (2 tick)...")
        time.sleep(wait_time)

        # 检查成交: 对比下单前后该代码的卖出成交量增量
        trades_after = sum(t.traded_volume for t in api.trades()
                           if t.stock_code == code and t.direction == 2)
        sold_vol = trades_after - trades_before

        if sold_vol >= volume:
            log.info(f"  ✅ 全部成交! 卖出 {sold_vol}股 @~{current_price:.2f}")
            return current_price
        elif sold_vol > 0:
            log.info(f"  ⚠️ 部分成交 {sold_vol}/{volume}股")
            volume -= sold_vol
            if volume <= 0:
                return current_price
            time.sleep(1)
            continue

        # 检查订单状态
        orders_now = api.orders()
        for o in orders_now:
            if str(o.order_id) == str(order_id):
                if o.order_status == 56:  # 已成
                    log.info(f"  ✅ 订单状态已成!")
                    return current_price
                elif o.order_status in (54, 57):  # 已撤/废单
                    log.warning(f"  订单 {o.status_text}, 重试")
                    break
                elif o.order_status in (52, 55):  # 部分成交
                    log.info(f"  部分成交, 继续...")
                    time.sleep(1)
                    continue

        # 未成交 → 撤单重来
        log.info(f"  未成交, 撤单 #{order_id}...")
        if order_id > 0:
            api.cancel(order_id)
            log.info(f"  已撤单")

        time.sleep(1)

    log.warning(f"  ❌ {max_retries}次尝试后仍未成交")
    return None

# ==================== 买入 ====================
def execute_buy(api, code, name, close_price, capital):
    """14:57集合竞价买入"""
    limit_up = calc_limit_up(close_price)
    # 集合竞价阶段不溢价，直接用最新价; 连续交易阶段 ×1.01 确保成交
    buy_price = round(close_price, 2)
    volume = int(capital / buy_price / 100) * 100
    if volume < 100:
        log.error(f"  资金不足: ¥{capital:,.0f} 不够买100股 @{buy_price:.2f}")
        return None

    # ============================================================
    # 买入前: 撤掉所有未成交委托, 释放资金
    # ============================================================
    log.info(f"")
    log.info(f"🔍 买入前检查未成交委托...")
    pending = api.orders()
    cancelled = 0
    for o in pending:
        if o.order_status in (48, 49, 50):  # 未报/待报/已报
            log.info(f"  撤单: {o.stock_code} {o.order_type} {o.order_volume}股 @{o.price:.2f}")
            if o.order_id and o.order_id.isdigit():
                api.cancel(int(o.order_id))
            cancelled += 1
    if cancelled:
        log.info(f"  已撤 {cancelled} 笔, 等待1秒释放资金...")
        time.sleep(1)
    else:
        log.info(f"  无未成交委托")

    # 重新拉取可用资金 (撤单后资金可能变化)
    asset_now = api.asset()
    actual_cash = asset_now.cash if asset_now else capital
    log.info(f"  实际可用资金: ¥{actual_cash:,.0f}")
    volume = int(actual_cash / buy_price / 100) * 100
    if volume < 100:
        log.error(f"  实际资金不足: ¥{actual_cash:,.0f} < 100股 @{buy_price:.2f}")
        return None

    log.info(f"")
    log.info(f"🏆 买入: {name}({code})")
    log.info(f"   收盘价: {close_price:.2f}  涨停价: {limit_up:.2f}")
    log.info(f"   挂单价: ¥{buy_price:.2f}  数量: {volume}股")

    # 下单前记录已成交量
    buys_before = sum(t.traded_volume for t in api.trades()
                      if t.stock_code == code and t.direction == 1)

    order_id = api.buy(code, volume, buy_price)
    log.info(f"   下单ID: {order_id}")

    if order_id <= 0:
        log.error(f"   ❌ 下单失败!")
        return None

    # 等 2 tick 检查成交
    time.sleep(RETRY_TICKS * TICK_INTERVAL)

    buys_after = sum(t.traded_volume for t in api.trades()
                     if t.stock_code == code and t.direction == 1)
    bought_vol = buys_after - buys_before

    if bought_vol >= volume:
        log.info(f"   ✅ 全部成交! {bought_vol}股")
        return order_id
    elif bought_vol > 0:
        log.warning(f"   ⚠️ 部分成交 {bought_vol}/{volume}股")
        return order_id

    # 查订单状态
    for o in api.orders():
        if str(o.order_id) == str(order_id):
            log.warning(f"   订单状态: {o.status_text}({o.order_status})")
            if o.order_status == 48:  # 未报
                log.error(f"   ❌ 订单未报到! 可能已过交易时间或集合竞价未接受")
            elif o.order_status == 57:  # 废单
                log.error(f"   ❌ 废单! 检查价格/数量")
            elif o.order_status == 56:  # 已成
                log.info(f"   ✅ 成交!")
            break

    return order_id

# ==================== 主流程 ====================
def main():
    global W, MU, SG  # 整个函数内使用全局权重, 只声明一次

    log.info("=" * 60)
    log.info("  311策略 自动交易 v2.0 (基准版)")
    log.info("  卖出: 止损-6% > 涨停 > 14:55收盘卖")
    log.info("  买入: 14:57 TPO3最优 @ 集合竞价最新价")
    log.info("=" * 60)

    # 0. 交易日检查
    today = datetime.now().strftime('%Y%m%d')
    tds = load_trading_days()
    if today not in tds:
        log.info(f"今日 {today} 非交易日，跳过")
        return
    today_idx = tds.index(today)
    if today_idx < 3:
        log.error("交易日不足3天，跳过")
        return
    d3_date = tds[today_idx - 1]  # D-3 (昨天, 放量日)
    d2_date = today               # D-2 (今天, 回踩买入日)
    log.info(f"D-3={d3_date} D-2={d2_date}")

    # 1. 加载 TPO3
    tpo3 = load_tpo3()
    if not tpo3:
        log.error("TPO3为空，退出")
        return
    log.info(f"TPO3买池: {len(tpo3)}只")
    for name, code in tpo3:
        log.info(f"  {name}({code})")

    # 2. 连接QMT
    log.info("连接MiniQMT...")
    api = QMTAPI()
    if not api.connect():
        log.error("❌ MiniQMT连接失败")
        return

    asset = api.asset()
    if asset:
        log.info(f"账户: 总资产 ¥{asset.total_asset:,.0f}  可用 ¥{asset.cash:,.0f}")
    else:
        log.warning("无法获取账户资产信息")

    # 3. 获取持仓
    positions = api.positions()
    hold_code = None
    hold_vol = 0
    hold_cost = 0
    for p in positions:
        if p.volume > 0:
            hold_code = p.stock_code
            hold_vol = p.volume
            hold_cost = p.avg_price
            log.info(f"持仓: {hold_code} {hold_vol}股 @{hold_cost:.2f} "
                     f"(浮盈{(float(p.last_price)/hold_cost-1)*100:+.2f}%)")
            break

    if not hold_code:
        log.info("无持仓，等待买入")

    # 4. 预计算 TPO3 所有候选的 ATR/MA5
    log.info("预计算ATR/MA5...")
    precompute_tpo3(tpo3, d3_date)

    # 4.5. Walk-Forward 训练 (严格对齐回测)
    log.info("Walk-Forward 训练...")
    di = {d: i for i, d in enumerate(tds)}
    W, MU, SG = train_walk_forward(tds, di)
    log.info(f"  W: {np.array2string(W, precision=3, suppress_small=True)}")

    # 4.6. 开盘预挂涨停卖单 (让交易所全天盯着, 不需要逐tick监控)
    limit_up_order_id = 0
    limit_up = 0.0
    if hold_code:
        limit_up = calc_limit_up(hold_cost)
        log.info(f"\n🔔 开盘预挂涨停卖单: {hold_code} {hold_vol}股 @{limit_up:.2f}")
        limit_up_order_id = api.sell(hold_code, hold_vol, limit_up)
        if limit_up_order_id > 0:
            log.info(f"  涨停卖单已挂, 订单ID: {limit_up_order_id}")
        else:
            log.warning(f"  涨停卖单挂单失败! 退回到tick监控涨停")

    # 5. 连接行情
    from xtquant import xtdata
    xtdata.enable_hello = False
    xtdata.connect()
    time.sleep(2)

    all_codes = [c for _, c in tpo3]
    if hold_code:
        all_codes = [hold_code] + all_codes

    log.info("")
    log.info("开始盘中监控 (每2秒轮询)...")
    log.info(f"  涨停: 开盘预挂单, 成交即走, 不额外监控")
    log.info(f"  止损: -6%触发 → smart_sell(自动撤涨停单)")
    log.info(f"  尾盘: 14:55 撤涨停单 → 收盘卖出")
    log.info(f"  买入: 14:57:03 挂单 @ 集合竞价最新价")
    log.info(f"  止损/尾盘卖: 卖一-0.01, 2tick未成→撤单重挂")
    log.info(f"  热开关: 改 {CONFIG_FILE} score_now=true 即可触发按需评分")
    log.info("")

    # 初始化配置文件
    _init_config()

    sold = False
    bought = False
    already_trained_1456 = False
    sell_price_realized = None
    last_score_report = -1
    last_score_run = -1
    last_tick_write = ""
    tpo3_scores = {}

    try:
        while True:
            now = datetime.now()
            now_str = now.strftime('%H:%M:%S')

            # ---- 获取最新 tick ----
            ticks = xtdata.get_full_tick(all_codes)

            # ---- 每次tick: 输出实时数据到文件 ----
            if now_str != last_tick_write:
                last_tick_write = now_str
                write_tick_snapshot(now_str, ticks, tpo3, hold_code, hold_cost)

            # ---- 检查配置文件热开关: score_now=true → 按需评分 ----
            cfg = read_config()
            if cfg.get('score_now', False):
                log.info(f"\n🔔 [{now_str}] 检测到 score_now=true, 执行按需评分...")
                # 实时 Walk-Forward 重训
                W, MU, SG = train_walk_forward(tds, di)
                tpo3_scores_live = {}
                for _, code in tpo3:
                    t = ticks.get(code, {})
                    sc, _ = score_stock(code, t)
                    if sc is not None:
                        tpo3_scores_live[code] = sc
                write_scores_snapshot(now_str, ticks, tpo3, tpo3_scores_live)
                write_config_key('score_now', False)  # 自动关闭
                log.info(f"  score_now 已自动重置为 false")

            # ========================================================
            #  卖出监控
            # ========================================================
            if not sold and hold_code:
                ht = ticks.get(hold_code, {})

                # 14:55 强制收盘卖出 (窗口1分钟, smart_sell最多~40s)
                if now_str >= FORCE_SELL_TIME and now_str < '14:56:00':
                    ask1 = _safe_float(ht.get('askPrice', 0) or ht.get('sellPrice', 0) or 0)
                    last_px = _safe_float(ht.get('lastPrice', 0))
                    sell_px = (ask1 - SELL_PRICE_DISCOUNT) if ask1 > 0 else (last_px if last_px > 0 else 0)
                    if sell_px > 0:
                        log.info(f"\n⏰ 14:55 强制收盘卖出 @{sell_px:.2f}")
                        actual_px = smart_sell(api, hold_code, hold_vol, sell_px, 'close')
                        if actual_px:
                            sell_price_realized = actual_px
                            sold = True
                            time.sleep(2)
                        else:
                            log.error("❌ 收盘卖出失败! 紧急重试 lastPrice-0.02...")
                            ht2 = xtdata.get_full_tick([hold_code]).get(hold_code, {})
                            emergency_px = _safe_float(ht2.get('lastPrice', 0)) - 0.02
                            if emergency_px > 0:
                                actual_px2 = smart_sell(api, hold_code, hold_vol, emergency_px, 'close', max_retries=8)
                                if actual_px2:
                                    sell_price_realized = actual_px2
                                    sold = True
                                else:
                                    log.error("❌ 紧急重试也失败! 持仓将过夜")
                    else:
                        log.error("❌ 14:55 tick数据异常(ask1和lastPrice均为0)! 无法卖出!")

                # 14:56:00 检查涨停预挂单是否已成交 (持仓清零→标记已卖)
                if not sold and hold_code and limit_up_order_id > 0 and now_str >= '14:56:00':
                    pos = api.positions()
                    still_hold = any(p.stock_code == hold_code and p.volume > 0 for p in pos)
                    if not still_hold:
                        log.info(f"\n✅ 涨停预挂单已成交 (持仓已清零)")
                        sold = True
                        sell_price_realized = limit_up

                # 盘中信号检查 (09:25开盘后 ~ 14:55前)
                if not sold and '09:25:00' <= now_str < FORCE_SELL_TIME:
                    should_sell, sp, reason = check_sell_signal(ht, hold_cost)
                    if should_sell:
                        log.info(f"\n⚠️ 触发卖出: {reason} → 初始价 ¥{sp:.2f}")
                        actual_px = smart_sell(api, hold_code, hold_vol, sp, reason)
                        if actual_px:
                            sell_price_realized = actual_px
                            sold = True
                            time.sleep(2)
                            asset = api.asset()
                            log.info(f"  卖出后可用: ¥{asset.cash:,.0f}")
                        else:
                            log.error("❌ 止损卖出失败! 立即重试...")
                            # 紧急重试: 直接用 lastPrice - 0.02
                            ht2 = xtdata.get_full_tick([hold_code]).get(hold_code, {})
                            emergency_px = _safe_float(ht2.get('lastPrice', 0)) - 0.02
                            if emergency_px > 0:
                                actual_px2 = smart_sell(api, hold_code, hold_vol, emergency_px, 'close', max_retries=8)
                                if actual_px2:
                                    sell_price_realized = actual_px2
                                    sold = True

            # ========================================================
            #  14:56:30→14:56:59 循环评分（10次, 以最后一次为准）
            # ========================================================
            if SCORE_START_TIME <= now_str <= SCORE_END_TIME and (sold or not hold_code):
                # 评分前 Walk-Forward 重训（确保权重实时对齐回测）
                if not already_trained_1456:
                    already_trained_1456 = True
                    W, MU, SG = train_walk_forward(tds, di)
                    log.info(f"  [{now_str}] Walk-Forward 重训完成")

                tpo3_scores = {}  # 每轮重新算
                for _, code in tpo3:
                    t = ticks.get(code, {})
                    sc, fv = score_stock(code, t)
                    if sc is not None:
                        tpo3_scores[code] = sc

                if tpo3_scores and now.second != last_score_run:
                    last_score_run = now.second
                    ranked = sorted(tpo3_scores.items(), key=lambda x: -x[1])
                    names = {c: n for n, c in tpo3}
                    best = names.get(ranked[0][0], ranked[0][0])
                    log.info(f"  [{now_str}] {best} 第1 {ranked[0][1]:+.3f}  "
                             f"({len(tpo3_scores)}只)")

            # ========================================================
            #  14:57 买入（用最后一次评分结果）
            # ========================================================
            if now_str >= BUY_TIME and not bought:
                if sold or not hold_code:
                    if tpo3_scores:
                        best_code = max(tpo3_scores, key=lambda c: tpo3_scores[c])
                        names = {c: n for n, c in tpo3}
                        best_name = names.get(best_code, best_code)

                        # 确定资金
                        if sold and sell_price_realized:
                            capital = sell_price_realized * hold_vol
                        else:
                            asset_buy = api.asset()
                            capital = asset_buy.cash if asset_buy else 0

                        # 收盘价 = 最新tick的lastPrice
                        bt = ticks.get(best_code, {})
                        close_price = _safe_float(bt.get('lastPrice', 0))
                        if close_price <= 0:
                            log.error(f"❌ {best_code} 收盘价异常")
                        else:
                            execute_buy(api, best_code, best_name, close_price, capital)
                    else:
                        log.error("❌ TPO3评分未计算")
                else:
                    log.warning(f"  未卖出持仓，不买入")
                bought = True
                log.info(f"\n✅ 交易完成")
                log.info(f"   日志: {LOG_FILE}")
                break

            # ========================================================
            #  状态报告 (14:00前仅写tick文件, 14:00后每分钟日志+TPO3排名)
            # ========================================================
            if now_str >= '14:00:00' and now_str < FORCE_SELL_TIME:
                # 14:00后每分钟报告
                current_min = now.minute
                if current_min != last_score_report:
                    last_score_report = current_min
                    log.info(f"\n--- [{now_str}] ---")

                    if not sold and hold_code:
                        ht = ticks.get(hold_code, {})
                        lp = _safe_float(ht.get('lastPrice', 0))
                        pre = _safe_float(ht.get('lastClose', 0))
                        chg = (lp / pre - 1) * 100 if pre > 0 else 0
                        pnl = (lp - hold_cost) * hold_vol
                        log.info(f"持仓 {hold_code}: {lp:.2f} 涨{chg:+.1f}%  浮¥{pnl:+.0f}")

                    # TPO3 盘中排名
                    if now_str >= '14:30:00':
                        live_scores = {}
                        for _, code in tpo3:
                            t = ticks.get(code, {})
                            sc, _ = score_stock(code, t)
                            if sc is not None:
                                live_scores[code] = sc
                        if live_scores:
                            ranked = sorted(live_scores.items(), key=lambda x: -x[1])
                            names = {c: n for n, c in tpo3}
                            for i, (code, sc) in enumerate(ranked[:3]):
                                t = ticks.get(code, {})
                                lp = _safe_float(t.get('lastPrice', 0))
                                pre = _safe_float(t.get('lastClose', 0))
                                chg = (lp / pre - 1) * 100 if pre > 0 else 0
                                log.info(f"  TPO3 {i+1}. {names.get(code,code)}({code}) {lp:.2f} 涨{chg:+.1f}%  评分{sc:+.3f}")

            # ---- 退出条件 ----
            if now_str >= '15:01:00':
                log.info("收盘，程序退出")
                break

            time.sleep(2)

    except KeyboardInterrupt:
        log.info("手动中断")
    except Exception as e:
        log.error(f"异常: {e}", exc_info=True)


if __name__ == '__main__':
    main()
