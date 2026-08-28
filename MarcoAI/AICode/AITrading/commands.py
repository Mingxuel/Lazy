"""
业务命令封装（第二段 API）

将买入/卖出的完整业务规则封装为清晰命令，供 callbacks.py 的 tick 回调调用。
不直接操作 xtquant 细节，统一通过 qmt_api 与 config。
"""

import os
import datetime
from types import SimpleNamespace

from AITrading import config as C
from AITrading import qmt_api as Q
from AICode.MarcoAPI.Update.Path import PATH_AIDATA_TARGET, PATH_AIDATA_TRADING_DATES
from AICode.MarcoAPI.Update.SZ2001D import GET_SZ200_1D_PREVIOUS, GET_SZ200_1D_ALL
from AICode.MarcoAPI.Update.StockCodes import GET_STOCK_INFO
from AICode.MarcoAPI.Update.TradingDates import TRADING_DATES, TRADING_DATE_AFTER
from AICode.MarcoAPI.Backtest import _limit_ratio, _limit_price


# ----------------------------------------------------------------------
# 买入池读取
# ----------------------------------------------------------------------
def latest_target_file():
    """AIData/TARGET/<STRATEGY_NAME> 下最新日期文件路径。"""
    d = PATH_AIDATA_TARGET(C.STRATEGY_NAME)
    if not os.path.isdir(d):
        C.log("buy", f"买入池目录不存在：{d}")
        return None
    dates = sorted(f for f in os.listdir(d) if f.isdigit())
    if not dates:
        C.log("buy", f"买入池为空：{d}")
        return None
    return os.path.join(d, dates[-1])


def read_target_pool(path):
    """读取买入池文件：代码|名称|市值 -> [(code, name, market_value)]"""
    out = []
    raw = open(path, "rb").read()
    text = raw.decode("gbk", errors="ignore")
    for line in text.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 3:
            continue
        try:
            out.append((parts[0], parts[1], float(parts[2])))
        except ValueError:
            continue
    return out


# ----------------------------------------------------------------------
# TPO_M5 形态 + MA5 预测判定（与回测 GENERATE_STRATEGY_TPO 一致）
# ----------------------------------------------------------------------
def pass_tpo_m5(code, buy_date, live_t1=None):
    rec1 = GET_SZ200_1D_PREVIOUS(code, buy_date, 0)  # T-1 买入确认日
    rec2 = GET_SZ200_1D_PREVIOUS(code, buy_date, 1)  # T-2 候选池日
    rec3 = GET_SZ200_1D_PREVIOUS(code, buy_date, 2)  # T-3 首板日
    rec4 = GET_SZ200_1D_PREVIOUS(code, buy_date, 3)  # T-4（用于 MA5 预测）
    if rec3 is None or rec2 is None or rec1 is None or rec4 is None:
        return False, 0.0
    # 尾盘实时判定：用实时快照覆盖 T-1 的 close/ratio/缩量/MA5（T-2/T-3/T-4 已固化）
    if live_t1 is not None:
        pre = live_t1.get("pre_close") or 0.0
        close1 = live_t1.get("close") or 0.0
        vol1 = live_t1.get("volume") or 0.0
        ratio1 = (close1 - pre) / pre if pre > 0 else 0.0
        is_vd1 = 1 if (rec2.volume > 0 and vol1 < rec2.volume) else 0
        ma5_1 = (close1 * 2 + rec2.close + rec3.close + rec4.close) / 5.0
        rec1 = SimpleNamespace(close=close1, ratio=ratio1,
                               is_volume_down=is_vd1, ma5=ma5_1)
    # T-3 首板涨停 + 放量
    if rec3.is_top != 1 or rec3.lian_ban != 1 or rec3.is_volume_up != 1:
        return False, 0.0
    # T-2 上涨 + 放量 + 未涨停
    if rec2.is_up != 1 or rec2.is_volume_up != 1 or rec2.is_top != 0:
        return False, 0.0
    # T-1 收盘涨跌幅 <= 3% 且缩量 且 close > MA5
    if rec1.ratio > C.MAX_RATIO:
        return False, 0.0
    if rec1.is_volume_down != 1:
        return False, 0.0
    if rec1.close <= rec1.ma5:
        return False, 0.0
    # 流通市值区间
    info = GET_STOCK_INFO(code)
    if info is None or info[1] <= 0:
        return False, 0.0
    market_value = float(info[1]) * rec1.close
    if market_value < C.MARKET_MIN or market_value > C.MARKET_MAX:
        return False, 0.0
    # MA5 预测必须条件：T-1.close >= 预测 T-0 MA5 = (T-1*2 + T-2 + T-3 + T-4)/5
    pred_ma5 = (rec1.close * 2 + rec2.close + rec3.close + rec4.close) / 5.0
    if rec1.close < pred_ma5:
        return False, 0.0
    return True, market_value


# ----------------------------------------------------------------------
# 交易日历工具
# ----------------------------------------------------------------------
def ensure_trading_dates():
    """尝试刷新交易日历（依赖通达信 tq 连接，实盘机具备）。失败仅告警。"""
    try:
        from AICode.MarcoAPI.Update.TradingDates import UPDATE_TRADING_DATES
        UPDATE_TRADING_DATES()
    except Exception as e:
        C.log("warn", f"刷新交易日历失败：{e}（将使用现有日历）")


def ensure_date_in_calendar(target):
    """若 target 不在日历中，按周一~周五向后补齐（用于盘后离线验证）。"""
    dates = TRADING_DATES()
    if target in dates or not target:
        return
    from datetime import datetime as _dt
    try:
        last = _dt.strptime(dates[-1], "%Y%m%d").date()
        tgt = _dt.strptime(target, "%Y%m%d").date()
    except Exception:
        return
    extra = []
    d = last + _dt.timedelta(days=1)
    while d <= tgt:
        if d.weekday() < 5:
            extra.append(d.strftime("%Y%m%d"))
        d += _dt.timedelta(days=1)
    if extra:
        dates.extend(extra)
        try:
            with open(PATH_AIDATA_TRADING_DATES(), "a") as f:
                f.write("\n" + "\n".join(extra) + "\n")
            C.log("info", f"日历已补齐未来交易日至 {target}：{extra}")
        except Exception:
            pass


# ----------------------------------------------------------------------
# 买入：决策 + 执行
# ----------------------------------------------------------------------
def decide_buy(force=False):
    """买入决策：读取买入池 + TPO_M5 实时判定，返回 {'code','name','price'} 或 None。"""
    C.log("buy", f"开始买入判定 force={force}")
    ensure_trading_dates()
    GET_SZ200_1D_ALL()  # 预热离线日线缓存
    path = latest_target_file()
    if path is None:
        return None
    pool = read_target_pool(path)
    C.log("buy", f"买入池（{os.path.basename(path)}）候选数：{len(pool)}")

    today = datetime.date.today().strftime("%Y%m%d")
    if force:
        # 离线验证：以最新买入池日期(T-2) + 1 交易日为 T-1 基准
        pool_date = os.path.basename(path)
        buy_date = TRADING_DATE_AFTER(pool_date, 1)
        if buy_date is None:
            from datetime import datetime as _dt
            try:
                d = _dt.strptime(pool_date, "%Y%m%d").date() + _dt.timedelta(days=1)
                while d.weekday() >= 5:
                    d += _dt.timedelta(days=1)
                buy_date = d.strftime("%Y%m%d")
            except Exception:
                buy_date = None
        if buy_date:
            ensure_date_in_calendar(buy_date)
        C.log("buy", f"[force] 以买入池日期 {pool_date} 推算 T-1={buy_date} 做离线判定")
    else:
        if today not in TRADING_DATES():
            C.log("buy", "今日非交易日，跳过。")
            return None
        buy_date = today
    if buy_date is None:
        C.log("buy", "无法推算 T-1 买入确认日，跳过。")
        return None

    # —— 选出「策略最优先股」：买入池按市值倒序，取第一只满足 TPO_M5 形态的 ——
    # 市值大的优先（流动性更好、对组合影响更小）；命中即定为当日唯一买入标的。
    for code, name, mv in sorted(pool, key=lambda x: x[2], reverse=True):
        live_t1 = Q.get_live_snapshot(code)
        ok, market_value = pass_tpo_m5(code, buy_date, live_t1=live_t1)
        if not ok:
            C.log("buy", f"剔除 {code} {name}（不满足 TPO_M5 形态/MA5 预测）")
            continue
        price = Q.get_realtime_price(code)
        if price is None:
            C.log("buy", f"无法获取 {code} 实时价，放弃。")
            continue
        C.log("buy", f"策略最优先股：{code} {name} 市值≈{market_value/1e8:.1f}亿 现价≈{price:.2f}")
        return {"code": code, "name": name, "price": price}

    # 遍历完仍无一只满足 → 无策略最优先股，返回 None（上层据此跳过今日买入）
    C.log("buy", "无满足 TPO_M5 条件的股票，无策略最优先股，今日空仓。")
    return None


def _best_buy_quote(cash, vol, base_price, limit_px):
    """在 [base_price, limit_px] 区间内，找到「仍能买入 vol 手」的最高报价（单位：元）。

    尾盘集合竞价按「价格优先 + 时间优先」撮合，因此在不减少可买手数的前提下，
    应尽可能地用高价报价以确保大概率成交。手数随报价上升单调不增，
    用「以分为单位的整数二分」在 [基准价, 涨停价] 中定位仍能买满 vol 手的价格上界，
    避免浮点 round 导致的手数误差。
    """
    ratio = C.POSITION_RATIO

    def shares_at(cents):
        # cents 为「分」整数；返回按该价格可买的整百股手数
        return int(cash * ratio / ((cents / 100.0) * 100)) * 100

    base_c = int(round(base_price * 100))
    limit_c = int(round(limit_px * 100))
    # 防御：基准价本身已买不到 vol 手（理论不会发生）
    if shares_at(base_c) < vol:
        return round(base_price, 2)
    lo, hi = base_c, limit_c
    # 整数二分：找最大 cents ∈ [lo, hi] 使 shares_at(cents) >= vol
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if shares_at(mid) >= vol:
            lo = mid
        else:
            hi = mid - 1
    return lo / 100.0


def execute_buy(decision):
    """执行买入：计算股数（单股全仓），以「仍能买满手数的最高价」报价提交订单。"""
    code, name, price = decision["code"], decision["name"], decision["price"]
    try:
        xt, _ = Q.connect()
    except RuntimeError as e:
        C.log("buy", f"[模拟] {e}\n[模拟] 计划买入 {code} @ {price:.2f}（单股全仓）")
        return
    cash = Q.get_account_cash(xt)
    vol = int((cash * C.POSITION_RATIO) / (price * 100)) * 100
    if vol <= 0:
        C.log("buy", f"资金不足，无法买入 {code}")
        return
    # 报价硬上限 = 涨停价（集合竞价不可超涨跌停）
    limit_px = _limit_price(price, _limit_ratio(code))
    # 在「仍能买入 vol 手」前提下取最高报价，确保成交且不丢手数
    quote = _best_buy_quote(cash, vol, price, limit_px)
    oid = Q.submit_buy(xt, code, vol, quote)
    C.log("buy", f"已提交买入单：{code} 数量={vol} 报价={quote:.2f} "
                f"（仍能买{vol}手的最高价，涨停上限={limit_px:.2f}）订单号={oid}")
    # 打上「今日已买」标记：尾盘集合竞价区间内每个 tick 都会进来，避免重复下单
    global _buy_done_date
    _buy_done_date = datetime.date.today().strftime("%Y%m%d")


def cmd_buy(force=False):
    """顶层买入命令：先选出策略最优先股，有则按该股报价买入，无则跳过（空仓）。"""
    decision = decide_buy(force=force)   # 选出策略最优先股（或 None）
    if decision is None:
        C.log("buy", "无策略最优先股，跳过今日买入。")
        return
    execute_buy(decision)                 # 有可选股：按该股最优报价买入


# ----------------------------------------------------------------------
# 持仓状态机（处理部分卖出：以「每只股票」为粒度，而非「今天卖过」）
# ----------------------------------------------------------------------
_positions_state = {}  # code -> {"cost": 成本价, "target_vol": 目标卖出量, "ordered": 是否已挂单}


def sync_positions(xt_trader):
    """从券商同步真实持仓，更新状态机。部分成交后真实持仓减少，剩余量自动更新。"""
    if xt_trader is None:
        return
    positions = Q.get_positions(xt_trader)
    live = {p["code"]: p for p in positions}
    for code in list(_positions_state.keys()):
        if code not in live:
            _positions_state.pop(code, None)
    for code, p in live.items():
        if code not in _positions_state:
            _positions_state[code] = {"cost": p.get("cost", 0.0),
                                      "target_vol": p["volume"],
                                      "ordered": False}
        else:
            st = _positions_state[code]
            if p["volume"] != st["target_vol"]:  # 持仓变化（加仓/回补）→ 允许重新挂单
                st["target_vol"] = p["volume"]
                st["ordered"] = False


def _submit_if_pending(xt_trader, code, reason):
    """对已同步的持仓，若未挂单则按剩余量提交卖单并打印直观日志。返回是否提交。"""
    st = _positions_state.get(code)
    if not st:
        return False
    remaining = st["target_vol"]
    if remaining <= 0:
        return False
    if st["ordered"]:  # 已挂单，等成交回报（下个 tick 的 sync_positions 会更新剩余量）
        return False
    tick = Q.get_full_tick(code) or {}
    last = tick.get("lastPrice") or 0.0
    oid = Q.submit_sell(xt_trader, code, remaining, last)
    st["ordered"] = True
    C.log("sell", f"[{reason}触发] {code} 卖出数量={remaining} 价格={last:.2f} 订单号={oid}")
    return True


# ----------------------------------------------------------------------
# 卖出执行封装：只负责「下单 + 打印触发日志」，不含任何条件判断
#   （判断逻辑全部在 tick_logic.py：是否开盘、是否触止损/涨停、是否到尾盘）
# ----------------------------------------------------------------------
def stop_loss_order(xt_trader, code):
    """执行止损下单（前提判断已在 tick_logic 完成）。"""
    return _submit_if_pending(xt_trader, code, "止损")


def take_profit_order(xt_trader, code, reason):
    """执行止盈/涨停卖出下单，reason 为 '涨停' 或 '止盈'（前提判断已在 tick_logic 完成）。"""
    return _submit_if_pending(xt_trader, code, reason)


def close_liq_order(xt_trader, code):
    """执行收盘强平下单（前提判断已在 tick_logic 完成）。"""
    return _submit_if_pending(xt_trader, code, "收盘")


# ----------------------------------------------------------------------
# 买入封装：尾盘集合竞价买入（含今日去重，直观可见「到尾盘开始集合竞价买入」）
# ----------------------------------------------------------------------
_buy_done_date = None


def buy_done_today():
    """判断：今日是否已买过（买入去重，供 tick 层在尾盘区间内判断能否再买）。"""
    return _buy_done_date == datetime.date.today().strftime("%Y%m%d")


def buy_at_close(xt_trader):
    """尾盘集合竞价买入：T-1 一次性决策，今日仅触发一次。"""
    if buy_done_today():
        return
    C.log("buy", "【尾盘集合竞价】买入窗口开启，开始选股买入")
    cmd_buy(force=False)


# ----------------------------------------------------------------------
# CLI 委托入口
# ----------------------------------------------------------------------
def cmd_sell():
    """顶层卖出命令：对全部持仓股按规则监控卖出（阻塞至收盘/清仓）。规则引擎见 commands。"""
    from AITrading.Structure import callbacks as CALL
    try:
        xt, _ = Q.connect()
    except RuntimeError as e:
        C.log("sell", f"[模拟] {e}\n[sell][模拟] 仅打印卖出计划，不真实报单。")
        xt = None
    if xt is None:
        CALL.run_sell_blocking(None)
        return
    CALL.run_sell_blocking(xt)
