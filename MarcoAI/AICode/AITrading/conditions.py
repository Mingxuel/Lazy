"""
交易触发条件判断（独立文件）

集中存放所有「前提判断」与「触发条件判断」：
  · 前提判断：当前处于哪个交易阶段（是否已开盘 / 是否到尾盘 / 是否临近收盘）
  · 触发条件判断：某持仓是否满足卖出信号（止损 / 涨停 / 止盈）

设计约定：
  · 这些函数只做判断、返回 bool，绝不调用下单逻辑（下单在 commands.py）。
  · tick 推送的行情快照为 dict，至少含 low/high/lastPrice 字段（见 qmt_api.get_full_tick）。
  · 前提判断基于当前时间；触发条件判断基于「某只股票 code + 当前 tick 快照」。
  · tick_logic.py 在 handle_tick 中调用本模块，按「前提 → 触发条件 → 执行」编排买卖动作。
"""

import datetime

from AITrading import config as C
from AITrading import commands as CMD
from AITrading import qmt_api as Q
from AICode.MarcoAPI.Backtest import _limit_ratio, _limit_price


def _parse_time(s):
    """把 'HH:MM:SS' 字符串解析为 datetime.time，供时间比较使用。"""
    h, m, sec = (int(x) for x in s.split(":"))
    return datetime.time(h, m, sec)


def _now():
    """返回当前时间（本地时区），所有「前提判断」都以此为基准。"""
    return datetime.datetime.now().time()


# ----------------------------------------------------------------------
# 前提判断：当前处于哪个交易阶段（均以「时间区间」表达，而非单点阈值）
#   区间形式可避免「14:57 之后永远为 True」这类边界模糊问题。
# ----------------------------------------------------------------------
def in_trading_session():
    """前提判断：当前是否处于「盘中交易区间」。

    区间：[SELL_STOP_TIME, SELL_CLOSE_TIME) 即 [09:30, 14:55)。
    开盘后进入可交易时段，止损监控、涨停/止盈监控都以此为前提；
    到达 SELL_CLOSE_TIME(14:55) 即切出本区间、进入收盘强平阶段。
    """
    start = _parse_time(C.SELL_STOP_TIME)
    end = _parse_time(C.SELL_CLOSE_TIME)
    now = _now()
    return start <= now < end


def in_tail_session():
    """前提判断：当前是否处于「尾盘集合竞价区间」。

    区间：[BUY_TIME, 15:00:00) 即 [14:57, 15:00)。
    此时触发尾盘买入，对应 T-1 选股后在收盘集合竞价阶段挂单；
    用上界 15:00 收口，避免 15:00 之后仍误判为尾盘。
    """
    start = _parse_time(C.BUY_TIME)
    end = _parse_time("15:00:00")
    now = _now()
    return start <= now < end


def is_close_approach():
    """前提判断：当前是否已到达「收盘强平时间点」。

    单点触发：now >= SELL_CLOSE_TIME（默认 14:55）。
    与 in_trading_session 的上界衔接——盘中区间一结束即进入强平，
    此时若持仓仍未触发涨停/止损，则不再等待，直接市价清仓，避免隔夜风险。
    """
    return _now() >= _parse_time(C.SELL_CLOSE_TIME)


# ----------------------------------------------------------------------
# 触发条件判断：持仓是否满足某卖出信号
#   参数 code：股票代码（用于取前收、算涨停价）
#   参数 tick：当前行情快照 dict，含 low/high/lastPrice
#   返回：是否满足该卖出信号（bool）
# ----------------------------------------------------------------------
def hit_stop_loss(code, tick):
    """触发条件：该持仓是否已触发止损。

    逻辑：当天最低价相对前收价的跌幅超过 config.STOP_LOSS（默认 -5%）即止损。
    用「最低价」而非「最新价」判断，确保盘中下探即触发，不等到收盘。
    取不到前收或最低价时返回 False（保守，不误杀）。
    """
    pre_close = Q.get_pre_close(code)
    low = tick.get("low")
    if pre_close is None or low is None:
        return False
    return (low - pre_close) / pre_close < C.STOP_LOSS


def is_limit_up(code, tick):
    """触发条件：该持仓是否涨停（止盈的极端情形）。

    逻辑：当天最高价 >= 涨停价即视为涨停。涨停价由前收 × 涨跌幅限制算出
    （_limit_price(pre_close, _limit_ratio(code))，主板 10% / 创业板 20%）。
    涨停意味着当日盈利已锁定在最高位，按涨停价卖出。
    """
    pre_close = Q.get_pre_close(code)
    high = tick.get("high")
    if pre_close is None or high is None:
        return False
    limit_px = _limit_price(pre_close, _limit_ratio(code))
    return high >= limit_px


def hit_take_profit(code, tick):
    """触发条件：该持仓是否达到普通止盈线。

    逻辑：当前最新价相对持仓成本价盈利 >= config.TAKE_PROFIT 即止盈。
    config.TAKE_PROFIT 为 None 时本函数恒返回 False（关闭普通止盈，仅靠涨停卖）。
    成本价来自 commands 的持仓状态机（sync_positions 同步的真实持仓成本）。
    """
    if not C.TAKE_PROFIT:
        return False
    st = CMD._positions_state.get(code)
    last = tick.get("lastPrice")
    if not st or st["cost"] <= 0 or last is None:
        return False
    return (last - st["cost"]) / st["cost"] >= C.TAKE_PROFIT
