# -*- coding: utf-8 -*-
"""
311策略 自动交易 2026-08-05
  持仓: 杰克科技(603337.SH) 700股 @45.94
  卖出规则: 涨停>止损-6%>收盘
  买入: TPO3最优股 14:57集合竞价 挂单价=现价*1.01
"""
import os, sys, time, logging, numpy as np
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, r'C:\Lazy\MarcoAI\AICode\AITrading')
from api import QMTAPI

# ==================== 配置 ====================
LOG_FILE = 'auto_trade_20260805.log'
BUY_TIME = '14:57:01'          # 集合竞价挂单时间
DECISION_TIME = '14:56:30'     # 最终决策时间

# 持仓
HOLD_CODE = '603337.SH'
HOLD_VOL = 700
HOLD_COST = 45.94

# TPO3 明日买池
TPO3_CODES = ['601611.SH', '601865.SH', '603156.SH']
TPO3_NAMES = {'601611.SH': '中国核建', '601865.SH': '福莱特', '603156.SH': '养元饮品'}

# 311模型权重 (Walk-Forward最终版)
W = np.array([0.96, 0.21, 0.47, -0.45, 0.36, 0.40])
KEYS = ['pb_depth', 'vol_contract', 'ma5_dev', 'pc_vs_low_atr', 'high_vs_pc_atr', 'ma_golden']

KLINE_DIR = r'C:\Lazy\李明学的大A\Data\1D'
D3_DATE = '20260804'  # D-3=今天(放量日)
D2_DATE = '20260805'  # D-2=明天(回踩日)

CAPITAL = None  # 卖出后才能确定

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

# ==================== 特征计算 ====================
_precomputed = {}

def _load_atr_ma5(code):
    """从1D K线计算ATR(10)和MA5"""
    fp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fp):
        return None, None
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
    # 建立索引
    idx = {}
    for i, r in enumerate(all_rows):
        idx[r[0]] = i
    di_k = idx.get(D3_DATE)  # D-3
    if di_k is None or di_k < 10:
        return None, None

    closes = np.array([r[3] for r in all_rows[:di_k + 1]])
    highs_v = np.array([r[1] for r in all_rows[:di_k + 1]])
    lows_v = np.array([r[2] for r in all_rows[:di_k + 1]])

    ma5 = float(np.mean(closes[-5:]))

    trs = []
    for i in range(di_k - 9, di_k + 1):
        h = highs_v[i]
        l = lows_v[i]
        pc = all_rows[i - 1][3] if i > 0 else all_rows[i][5]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr10 = float(np.mean(trs))
    return atr10, ma5

def compute_features(code, ticks):
    """
    D-2=0805盘中特征（需要当天实时OHLC + 历史ATR/MA5）
    ticks: QMT get_full_tick 返回的该股票数据
    """
    atr10, ma5 = _precomputed.get(code, (None, None))
    if atr10 is None:
        return None

    pre_close = float(ticks.get('lastClose', 0))
    last_price = float(ticks.get('lastPrice', 0))
    high = float(ticks.get('high', 0))
    low = float(ticks.get('low', 0))

    if pre_close <= 0 or last_price <= 0:
        return None

    # pb_depth: (D-3收盘 - D-2收盘) / D-3收盘
    # D-3收盘 = preClose (QMT的lastClose = 昨收 = D-3收盘)
    pb_depth = (pre_close - last_price) / pre_close * 100

    # vol_contract: 盘中无法判断成交量对比，暂用0
    vol_contract = 0

    # ma5_dev
    ma5_dev = (last_price - ma5) / ma5 * 100 if ma5 > 0 else 0

    # pc_vs_low_atr: (昨收 - 今日最低) / ATR
    pc_vs_low_atr = (pre_close - low) / atr10 if atr10 > 0 else 0

    # high_vs_pc_atr: (今日最高 - 昨收) / ATR
    high_vs_pc_atr = (high - pre_close) / atr10 if atr10 > 0 else 0

    # ma_golden: 需要历史数据，从K线判断
    # 简化：用1D文件算
    fp = os.path.join(KLINE_DIR, code)
    ma_golden = 0
    if os.path.exists(fp):
        rows = []
        with open(fp, encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if not l or l.startswith('\ufeff'):
                    continue
                c = l.split()
                if len(c) >= 10 and c[0].isdigit():
                    rows.append(float(c[4]))
        idx_d3 = None
        all_dates = []
        with open(fp, encoding='utf-8') as f:
            for i, l in enumerate(f):
                l = l.strip()
                if not l or l.startswith('\ufeff'):
                    continue
                c = l.split()
                if len(c) >= 10 and c[0].isdigit():
                    if c[0] == D3_DATE:
                        idx_d3 = i
                    if idx_d3 is None:
                        rows.append(float(c[4]))
        if idx_d3 is not None and len(rows) >= 11:
            m5n = np.mean(rows[-5:])
            m5p = np.mean(rows[-6:-1])
            m10n = np.mean(rows[-10:])
            m10p = np.mean(rows[-11:-1])
            if m5p <= m10p and m5n > m10n:
                ma_golden = 1

    return {
        'pb_depth': pb_depth,
        'vol_contract': vol_contract,
        'ma5_dev': ma5_dev,
        'pc_vs_low_atr': pc_vs_low_atr,
        'high_vs_pc_atr': high_vs_pc_atr,
        'ma_golden': ma_golden,
        'pre_close': pre_close,
        'last_price': last_price,
        'high': high,
        'low': low,
    }

# ==================== 评分 ====================
# 近似均值和标准差（来自全量训练数据）
MU = np.array([2.0, 0.75, 2.0, 1.5, 1.0, 0.15])
SG = np.array([5.0, 0.4, 5.0, 1.5, 1.0, 0.35])

def get_scores():
    """获取TPO3每只股票的实时评分"""
    from xtquant import xtdata
    ticks = xtdata.get_full_tick(TPO3_CODES)

    scores = {}
    for code in TPO3_CODES:
        t = ticks.get(code, {})
        f = compute_features(code, t)
        if f is None:
            continue
        Xs = np.array([f.get(k, 0) for k in KEYS])
        score = float(((Xs - MU) / SG) @ W)
        scores[code] = {**f, 'score': score, 'name': TPO3_NAMES.get(code, code)}
    return scores

def print_scores(scores):
    log.info(f"  {'排名':<4} {'代码':<14} {'名称':<8} {'现价':>7} {'涨%':>7} {'回踩%':>7} {'bear':>6} {'bull':>6} {'MA5%':>7} {'金叉':>4} {'评分':>8}")
    log.info("  " + "-" * 90)
    ranked = sorted(scores.items(), key=lambda x: -x[1]['score'])
    for i, (code, s) in enumerate(ranked):
        lp = s['last_price']
        pre = s['pre_close']
        chg = (lp / pre - 1) * 100 if pre > 0 else 0
        log.info(f"  {i+1:<4} {code:<14} {s['name']:<8} {lp:>7.2f} {chg:>+6.2f}% {s['pb_depth']:>+6.2f}% {s['pc_vs_low_atr']:>5.2f} {s['high_vs_pc_atr']:>5.2f} {s['ma5_dev']:>+6.2f}% {s['ma_golden']:>4.0f} {s['score']:>+7.3f}")


# ==================== 卖出逻辑 ====================
day_peak = HOLD_COST  # 追踪日内最高价

def check_sell_signal(api, ticks):
    """
    检查持仓股是否需要卖出。
    返回: (should_sell, sell_price, reason)
    """
    global day_peak
    t = ticks.get(HOLD_CODE, {})
    pre_close = float(t.get('lastClose', 0))
    last_price = float(t.get('lastPrice', 0))
    high = float(t.get('high', 0))
    low = float(t.get('low', 0))

    # 更新日内峰值
    if high > day_peak:
        day_peak = high

    limit_up = round(HOLD_COST * 1.10, 2)

    # 1. 涨停
    if high >= limit_up * 0.999:
        return True, limit_up, 'limit_up'

    # 2. 开盘≤-6%
    if pre_close > 0 and t.get('open', 0) > 0:
        open_price = float(t.get('open', 0))
        if open_price <= HOLD_COST * 0.94:
            return True, open_price, 'open_stop'

    # 3. 盘中最低≤-6%
    if low <= HOLD_COST * 0.94:
        return True, HOLD_COST * 0.94, 'low_stop'

    # 4. 移动止盈: 涨>3%后, 从日内峰值回落>1%即卖 (回测最优)
    if day_peak >= HOLD_COST * 1.03:
        trail_price = day_peak * 0.99
        if last_price <= trail_price:
            return True, trail_price, 'trail_stop'

    # 5. 未触发，等收盘
    return False, None, None


# ==================== 智能卖出 ====================
def smart_sell(api, code, price, volume, reason, max_retries=5):
    """
    智能卖出: 挂单 → 查成交 → 未成则撤单提价重挂
    price_step: 每次提价幅度(分)
    """
    from xtquant import xtdata

    if reason == 'limit_up':
        # 涨停卖: 直接挂涨停价, 通常即刻成交
        price_step = 0
        check_interval = 2
    elif reason in ('open_stop', 'low_stop'):
        # 止损: 需要快速卖出, 每次降0.5%
        price_step = -round(price * 0.005, 2)
        check_interval = 3
    else:
        # 收盘卖: 有几分钟可以调整
        price_step = round(price * 0.003, 2)  # 每次提0.3%
        check_interval = 5

    current_price = price
    for attempt in range(max_retries):
        log.info(f"  卖出尝试 {attempt+1}/{max_retries}: {code} {volume}股 @{current_price:.2f}")

        order_id = api.sell(code, current_price, volume)
        log.info(f"  下单ID: {order_id}")

        # 等待查看是否成交
        time.sleep(check_interval)

        # 检查持仓
        pos = api.positions()
        still_hold = False
        for p in pos:
            if p.stock_code == code and p.volume > 0:
                still_hold = True
                break

        if not still_hold:
            log.info(f"  ✅ 成交! 价格 ¥{current_price:.2f}")
            return current_price

        # 未成交 → 撤单
        log.info(f"  未成交, 撤单...")
        if order_id > 0:
            api.cancel(order_id)
            log.info(f"  已撤单 #{order_id}")

        time.sleep(1)

        # 提价重挂
        if reason == 'limit_up':
            pass  # 涨停价不变
        elif reason in ('open_stop', 'low_stop'):
            current_price = round(current_price - 0.02, 2)  # 止损降价2分
            if current_price <= price * 0.90:
                log.warning(f"  ⚠️ 价格过低, 底线价 ¥{price*0.90:.2f}")
                current_price = round(price * 0.90, 2)
        else:
            # 收盘卖: 参考实时买一价
            ticks = xtdata.get_full_tick([code])
            t = ticks.get(code, {})
            bid1 = float(t.get('bidPrice', 0)) if t.get('bidPrice') else 0
            if bid1 > 0 and bid1 > current_price * 0.98:
                current_price = bid1
            else:
                current_price = round(current_price - 0.01, 2)  # 降价1分

        time.sleep(1)

    log.warning(f"  ❌ {max_retries}次尝试后仍未成交, 最后挂单价 ¥{current_price:.2f}")
    return None


# ==================== 主流程 ====================
def main():
    log.info("=" * 60)
    log.info("  311策略 自动交易 2026-08-05")
    log.info("=" * 60)

    # 1. 连接QMT
    log.info("连接MiniQMT...")
    api = QMTAPI()
    if not api.connect():
        log.error("❌ MiniQMT连接失败")
        return

    asset = api.asset()
    log.info(f"账户: 总资产 ¥{asset.total_asset:,.0f}  可用 ¥{asset.cash:,.0f}")
    log.info(f"持仓: {HOLD_CODE} {HOLD_VOL}股 @{HOLD_COST}")

    # 2. 预计算ATR/MA5
    log.info("预计算ATR/MA5...")
    for code in TPO3_CODES:
        atr10, ma5 = _load_atr_ma5(code)
        if atr10 is not None:
            _precomputed[code] = (atr10, ma5)
            log.info(f"  {TPO3_NAMES[code]}: ATR10={atr10:.3f} MA5={ma5:.2f}")

    # 3. 连接行情
    from xtquant import xtdata
    xtdata.enable_hello = False
    xtdata.connect()
    time.sleep(2)

    log.info("")
    log.info("开始盘中监控...")
    log.info(f"  卖出: 涨停>{chr(39)}止损-6%{chr(39)}>收盘")
    log.info(f"  买入: 14:56:30最终评分 → 14:57:01挂单")
    log.info("")

    sold = False
    sell_price = None
    last_report_minute = -1

    try:
        while True:
            now = datetime.now()
            now_str = now.strftime('%H:%M:%S')

            # 获取实时行情
            all_codes = [HOLD_CODE] + TPO3_CODES
            ticks = xtdata.get_full_tick(all_codes)

            # ---- 检查卖出信号 ----
            if not sold:
                should_sell, sp, reason = check_sell_signal(api, ticks)
                if should_sell:
                    log.info(f"")
                    log.info(f"⚠️ 触发卖出: {reason} → 初始价 ¥{sp:.2f}")
                    actual_px = smart_sell(api, HOLD_CODE, sp, HOLD_VOL, reason)
                    if actual_px:
                        sell_price = actual_px
                        sold = True
                        time.sleep(2)
                        asset = api.asset()
                        CAPITAL = asset.cash
                        log.info(f"  卖出后可用: ¥{asset.cash:,.0f}")
                    else:
                        log.error(f"  ❌ 卖出失败! 继续尝试...")

                # 14:55 还未触发信号 → 主动卖出(留时间重试)
                if not sold and now_str >= '14:55:00' and now_str < '14:56:00':
                    last_px = float(ticks.get(HOLD_CODE, {}).get('lastPrice', 0))
                    if last_px > 0:
                        log.info(f"\n⏰ 14:55 未触发信号, 主动收盘卖出 @{last_px:.2f}")
                        actual_px = smart_sell(api, HOLD_CODE, last_px, HOLD_VOL, 'close')
                        if actual_px:
                            sell_price = actual_px
                            sold = True
                            time.sleep(2)
                            asset = api.asset()
                            log.info(f"  卖出后可用: ¥{asset.cash:,.0f}")

            # ---- 14:56:30 最终决策 ----
            if now_str >= DECISION_TIME and not now_str.startswith('14:57'):
                log.info(f"\n--- [{now_str}] 最终决策 ---")
                scores = get_scores()
                if scores:
                    print_scores(scores)
                    best_code = max(scores, key=lambda c: scores[c]['score'])
                    best = scores[best_code]

                    # 确定资金
                    if sold and sell_price:
                        CAPITAL = sell_price * HOLD_VOL  # 卖出所得
                    else:
                        asset = api.asset()
                        CAPITAL = asset.cash

                    limit_up = round(best['pre_close'] * 1.10, 2)
                    buy_price = round(min(best['last_price'] * 1.01, limit_up), 2)
                    volume = int(CAPITAL / buy_price / 100) * 100

                    log.info(f"")
                    log.info(f"🏆 选中: {best['name']}({best_code})")
                    log.info(f"   评分: {best['score']:+.3f}")
                    log.info(f"   现价: {best['last_price']:.2f}  涨停价: {limit_up:.2f}")
                    log.info(f"   挂单: ¥{buy_price:.2f} (现价×1.01)")
                    log.info(f"   资金: ¥{CAPITAL:,.0f}  买入: {volume}股")

                    # 等到14:57:01
                    while datetime.now().strftime('%H:%M:%S') < BUY_TIME:
                        time.sleep(0.05)

                    # 下单
                    result = api.buy(best_code, buy_price, volume)
                    log.info(f"")
                    log.info(f"✅ 下单: {best_code} {volume}股 @{buy_price:.2f}")
                    log.info(f"   订单: {result}")
                    log.info(f"   日志: {LOG_FILE}")
                    break

            # ---- 每10分钟报告 ----
            current_10min = now.minute // 10
            if current_10min != last_report_minute:
                last_report_minute = current_10min
                log.info(f"\n--- [{now_str}] ---")

                # 持仓状态
                if not sold:
                    ht = ticks.get(HOLD_CODE, {})
                    h_lp = float(ht.get('lastPrice', 0))
                    h_pre = float(ht.get('lastClose', 0))
                    h_chg = (h_lp / h_pre - 1) * 100 if h_pre > 0 else 0
                    h_pnl = (h_lp - HOLD_COST) * HOLD_VOL
                    log.info(f"持仓 {HOLD_CODE}: {h_lp:.2f} 涨{h_chg:+.1f}%  浮¥{h_pnl:+.0f}")

                # TPO3评分
                scores = get_scores()
                if scores:
                    ranked = sorted(scores.items(), key=lambda x: -x[1]['score'])
                    for i, (code, s) in enumerate(ranked):
                        lp = s['last_price']
                        pre = s['pre_close']
                        chg = (lp / pre - 1) * 100 if pre > 0 else 0
                        log.info(f"  TPO3 {i+1}. {s['name']}({code})  {lp:.2f} 涨{chg:+.1f}%  pb={s['pb_depth']:+.1f}%  评分{s['score']:+.3f}")

            time.sleep(5)

    except KeyboardInterrupt:
        log.info("手动中断")
    except Exception as e:
        log.error(f"异常: {e}", exc_info=True)


if __name__ == '__main__':
    main()
