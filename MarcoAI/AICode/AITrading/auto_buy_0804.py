"""
311策略 尾盘集合竞价自动买入
==============================
日期: 2026-08-04 (D-2回踩日，尾盘买入)
候选: 002015 协鑫能科 / 600580 卧龙电驱 / 600588 用友网络 / 600673 东阳光 / 603337 杰克科技

规则:
  1. 实时监控5只候选股，每秒计算模型评分
  2. 14:56:30 做最终决策，打印全部评分
  3. 14:57:01 集合竞价买入评分最高的股票
  4. 挂单价格 = min(最新价×1.01, 涨停价)，确保成交

⚠️ 真金白银，每条日志都会写入文件。
"""

import os, sys, time, logging, numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from api import QMTAPI
from xtquant import xtdata

# ============================================================
# 配置
# ============================================================
CODES = ['002015.SZ', '600580.SH', '600588.SH', '600673.SH', '603337.SH']
NAMES = {
    '002015.SZ': '协鑫能科', '600580.SH': '卧龙电驱',
    '600588.SH': '用友网络', '600673.SH': '东阳光',
    '603337.SH': '杰克科技',
}
KLINE_DIR = r'C:\Lazy\李明学的大A\Data\1D'
D3_DATE = '20260803'  # 昨日(0803)
PREMIUM = 1.01        # 挂高1%
LOG_FILE = os.path.join(os.path.dirname(__file__),
                        f'auto_buy_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# ============================================================
# 日志
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'),
              logging.StreamHandler()]
)
log = logging.getLogger('auto_buy')

# ============================================================
# 模型权重 (Walk-Forward 岭回归, 样本外+85.9%)
# 特征: pb_depth, vol_contract, ma5_dev, pc_vs_low_atr, high_vs_pc_atr
# ============================================================
W = np.array([0.93, 0.20, 0.45, -0.44, 0.33])

# ============================================================
# 历史数据: 从1D文件加载ATR和MA5
# ============================================================
_precomputed = {}  # 启动时算一次，不重复读文件

def _load_atr_ma5(code):
    """从1D K线计算ATR(10)和MA5"""
    fp = os.path.join(KLINE_DIR, code)
    if not os.path.exists(fp):
        return None, None
    rows = []
    idx = {}
    with open(fp, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith('\ufeff'):
                continue
            c = l.split()
            if len(c) < 10 or not c[0].isdigit():
                continue
            idx[c[0]] = len(rows)  # ★ 用rows的长度作为索引
            rows.append((float(c[1]), float(c[2]), float(c[3]),
                         float(c[4]), float(c[5]), float(c[9])))
    di_k = idx.get(D3_DATE)
    if di_k is None or di_k < 10:
        return None, None

    closes = np.array([r[3] for r in rows[:di_k + 1]])
    highs = np.array([r[1] for r in rows[:di_k + 1]])
    lows = np.array([r[2] for r in rows[:di_k + 1]])

    ma5 = float(np.mean(closes[-5:]))

    trs = []
    for i in range(di_k - 9, di_k + 1):
        h = highs[i]
        l = lows[i]
        pc = rows[i - 1][3] if i > 0 else rows[i][5]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr10 = float(np.mean(trs))
    return atr10, ma5


def compute_features(pre_close, last_price, high, low, atr10, ma5):
    """
    计算5维特征向量

    pb_depth:       回踩深度 (昨收-现价)/昨收
    vol_contract:   缩量回踩 (盘中无法判断，固定0)
    ma5_dev:        MA5偏离 (现价-MA5)/MA5
    pc_vs_low_atr:  空头ATR (昨收-最低)/ATR10
    high_vs_pc_atr: 多头ATR (最高-昨收)/ATR10
    """
    pb = (pre_close - last_price) / pre_close * 100 if pre_close > 0 else 0
    vc = 0  # 盘中无法准确计算成交量对比
    ma5_dev = (last_price - ma5) / ma5 * 100 if ma5 > 0 else 0
    bear = (pre_close - low) / atr10 if atr10 > 0 else 0
    bull = (high - pre_close) / atr10 if atr10 > 0 else 0
    return np.array([pb, vc, ma5_dev, bear, bull])


def get_scores():
    """获取5只股票的实时评分"""
    ticks = xtdata.get_full_tick(CODES)
    scores = {}
    for code in CODES:
        t = ticks.get(code, {})
        pre = float(t.get('lastClose', 0))
        lp = float(t.get('lastPrice', 0))
        h = float(t.get('high', 0))
        l = float(t.get('low', 0))

        if pre <= 0 or lp <= 0:
            log.warning(f'{code}: tick数据异常 pre={pre} lp={lp}')
            continue

        atr10, ma5 = _precomputed.get(code, (None, None))
        if atr10 is None:
            log.warning(f'{code}: ATR/MA5预计算失败')
            continue

        feats = compute_features(pre, lp, h, l, atr10, ma5)
        score = float(feats @ W)

        scores[code] = {
            'score': score, 'last_price': lp, 'pre_close': pre,
            'high': h, 'low': l, 'pb': feats[0], 'bear': feats[3], 'bull': feats[4],
            'ma5_dev': feats[2], 'name': NAMES.get(code, code),
        }
    return scores


def print_scores(scores):
    """打印当前评分表"""
    log.info(f'{"代码":<14} {"名称":<8} {"现价":>7} {"涨幅":>7} {"回踩%":>7} {"bear":>6} {"bull":>6} {"评分":>8}')
    log.info('-' * 75)
    sorted_codes = sorted(scores.keys(), key=lambda c: -scores[c]['score'])
    for code in sorted_codes:
        s = scores[code]
        chg = (s['last_price'] / s['pre_close'] - 1) * 100 if s['pre_close'] > 0 else 0
        log.info(f'{code:<14} {s["name"]:<8} {s["last_price"]:>7.2f} {chg:>+6.2f}% {s["pb"]:>+6.2f}% {s["bear"]:>5.2f} {s["bull"]:>5.2f} {s["score"]:>+7.3f}')


# ============================================================
# 主流程
# ============================================================
def main():
    log.info('=' * 60)
    log.info('311策略 尾盘集合竞价自动买入')
    log.info(f'日期: {datetime.now().strftime("%Y-%m-%d")}')
    log.info(f'候选: {", ".join(f"{NAMES[c]}({c})" for c in CODES)}')
    log.info('=' * 60)

    # ---- 1. 预计算ATR/MA5 ----
    log.info('正在预计算ATR/MA5...')
    for code in CODES:
        atr10, ma5 = _load_atr_ma5(code)
        if atr10 is None:
            log.error(f'{code}: ATR/MA5计算失败! 退出')
            return
        _precomputed[code] = (atr10, ma5)
        log.info(f'  {NAMES.get(code, code)}: ATR10={atr10:.3f} MA5={ma5:.2f}')

    # ---- 2. 连接交易 ----
    log.info('正在连接MiniQMT交易...')
    api = QMTAPI()
    if not api.connect():
        log.error('❌ MiniQMT交易连接失败! 请确认QMT已登录交易账户')
        return

    asset = api.asset()
    if asset is None:
        log.error('❌ 无法查询账户资产!')
        api.disconnect()
        return

    cash = asset.cash
    log.info(f'✅ 交易连接OK | 可用资金: ¥{cash:,.0f} | 总资产: ¥{asset.total_asset:,.0f}')

    # ---- 3. 实时监控循环 ----
    log.info(f'开始监控，每10分钟反馈 | 目标: 14:56:30最终决策 → 14:57:01集合竞价买入')
    log.info('')

    last_print_minute = -999
    decision_made = False

    try:
        while True:
            now = datetime.now()
            now_str = now.strftime('%H:%M:%S')

            # 获取并计算评分
            scores = get_scores()
            if not scores:
                log.warning(f'[{now_str}] 无有效tick数据')
                time.sleep(5)
                continue

            # 每10分钟打印一次完整报告
            current_minute = now.minute
            if current_minute % 10 == 0 and current_minute != last_print_minute:
                last_print_minute = current_minute
                log.info('')
                log.info('=' * 70)
                log.info(f'  [{now_str}] 定期报告')
                log.info('=' * 70)

                # 账户信息
                fresh_asset = api.asset()
                if fresh_asset:
                    log.info(f'  💰 账户: 可用¥{fresh_asset.cash:,.0f} | 总资产¥{fresh_asset.total_asset:,.0f} | 市值¥{fresh_asset.market_value:,.0f}')

                # 持仓信息
                positions = api.positions()
                if positions:
                    log.info(f'  📦 当前持仓: {len(positions)}只')
                    for p in positions:
                        pnl_pct = (p.current_price/p.avg_price-1)*100 if p.avg_price>0 else 0
                        log.info(f'     {p.stock_code}: {int(p.volume)}股 成本¥{p.avg_price:.2f} 现价¥{p.current_price:.2f} 盈{pnl_pct:+.1f}%')
                else:
                    log.info(f'  📦 当前持仓: 空仓')

                # 委托信息
                orders = api.orders()
                pending = [o for o in orders if o.order_status < 50]
                if pending:
                    log.info(f'  📝 未成交委托: {len(pending)}笔')
                    for o in pending:
                        log.info(f'     {o.stock_code}: {o.order_volume}股 @ ¥{o.price:.2f} [{o.status_text}]')

                log.info('')
                log.info(f'  --- 候选股评分 ---')
                print_scores(scores)

                # 显示TOP1预测
                best_code = max(scores, key=lambda c: scores[c]['score'])
                best = scores[best_code]
                log.info(f'  → 当前TOP: {best["name"]}({best_code}) '
                         f'评分{best["score"]:+.3f} '
                         f'现价{best["last_price"]:.2f} '
                         f'pb={best["pb"]:+.1f}% '
                         f'bear={best["bear"]:.1f} bull={best["bull"]:.1f}')
                log.info('=' * 70)

            # ---- 4. 14:56:30 最终决策 ----
            if now_str >= '14:56:30' and not decision_made:
                decision_made = True
                log.info('')
                log.info('=' * 60)
                log.info('⏰ 14:56:30 最终决策')
                log.info('=' * 60)

                # 刷新最后一次评分
                time.sleep(1)
                scores = get_scores()
                print_scores(scores)

                # 选TOP1
                best_code = max(scores, key=lambda c: scores[c]['score'])
                best = scores[best_code]
                log.info('')
                log.info(f'🏆 最终选择: {best["name"]}({best_code})')
                log.info(f'   评分: {best["score"]:+.3f}')
                log.info(f'   现价: {best["last_price"]:.2f}')
                log.info(f'   昨收: {best["pre_close"]:.2f}')
                log.info(f'   最高: {best["high"]:.2f}  最低: {best["low"]:.2f}')
                log.info(f'   pb={best["pb"]:+.1f}% bear={best["bear"]:.1f} bull={best["bull"]:.1f}')

                # 计算挂单价: min(现价×1.01, 涨停价)
                limit_up = round(best['pre_close'] * 1.10, 2)
                buy_price_raw = best['last_price'] * PREMIUM
                buy_price = min(buy_price_raw, limit_up)
                buy_price = round(buy_price, 2)

                # 计算股数: 全仓买入，100股整数倍
                volume = int(cash / buy_price / 100) * 100
                if volume < 100:
                    log.error(f'❌ 资金不足! 需要¥{buy_price*100:.0f} (100股), 可用¥{cash:.0f}')
                    break

                estimated_cost = volume * buy_price
                log.info(f'')
                log.info(f'📊 下单参数:')
                log.info(f'   挂单价: ¥{buy_price:.2f} (现价{buy_price_raw:.2f} vs 涨停{limit_up:.2f})')
                log.info(f'   股数:   {volume}股')
                log.info(f'   预估金额: ¥{estimated_cost:,.0f}')
                log.info(f'   PREMIUM:  {(buy_price / best["last_price"] - 1) * 100:+.1f}%')

                # ---- 5. 等到14:57:01下单 ----
                log.info('')
                log.info('⏳ 等待 14:57:01 集合竞价开始...')

                while datetime.now().strftime('%H:%M:%S') < '14:57:01':
                    time.sleep(0.1)

                # 最后一刻再确认现价没异常变动
                final_tick = xtdata.get_full_tick([best_code])
                if best_code in final_tick and final_tick[best_code]:
                    final_lp = float(final_tick[best_code].get('lastPrice', 0))
                    if final_lp > 0:
                        price_change = abs(final_lp - best['last_price']) / best['last_price']
                        if price_change > 0.03:
                            log.warning(f'⚠️ 价格大幅变动! 14:56→14:57 现价 {best["last_price"]:.2f}→{final_lp:.2f} ({price_change*100:.1f}%)')
                            # 重新计算挂单价
                            buy_price = min(round(final_lp * PREMIUM, 2), limit_up)
                            volume = int(cash / buy_price / 100) * 100
                            log.warning(f'   调整后: 挂单价{buy_price:.2f} × {volume}股')

                # 下单
                log.info(f'🚀 正在提交买入: {best_code} {volume}股 @ {buy_price:.2f}')
                order_id = api.buy(best_code, volume, buy_price)

                if order_id:
                    log.info(f'✅ 订单已提交! ID={order_id}')
                    log.info(f'   代码: {best_code} {best["name"]}')
                    log.info(f'   价格: ¥{buy_price:.2f}')
                    log.info(f'   数量: {volume}股')
                    log.info(f'   金额: ≈¥{volume * buy_price:,.0f}')

                    # 等2秒查成交
                    time.sleep(3)
                    trades = api.trades()
                    matched = [t for t in trades if t.stock_code == best_code]
                    if matched:
                        for t in matched:
                            log.info(f'   ✅ 成交! {t.traded_volume}股 @ ¥{t.traded_price:.2f} 金额¥{t.traded_amount:,.0f}')
                    else:
                        log.info(f'   ⏳ 待成交(集合竞价15:00统一撮合)')

                        # 再等一等看委托状态
                        time.sleep(5)
                        orders = api.orders()
                        for o in orders:
                            if o.stock_code == best_code:
                                log.info(f'   委托状态: {o.status_text} ({o.order_volume}股 @ ¥{o.price:.2f})')
                else:
                    log.error(f'❌ 下单失败! 返回order_id=0')

                break

            # 收盘后退出
            if now_str >= '15:05:00':
                if not decision_made:
                    log.error('❌ 错过14:57下单窗口!')
                break

            time.sleep(5)  # 每5秒采样

    except KeyboardInterrupt:
        log.info('用户中断')
    except Exception as e:
        log.error(f'异常: {e}', exc_info=True)
    finally:
        api.disconnect()
        log.info(f'日志已保存: {LOG_FILE}')


if __name__ == '__main__':
    main()
