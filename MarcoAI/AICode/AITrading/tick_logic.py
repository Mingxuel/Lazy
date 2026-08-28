"""
on_tick 的细节实现（只编排 handle_tick，不含任何判断函数）

本文件只做一件事：在每次 tick 时，按「前提 → 判断 → 有/无 → 执行/跳过」的层次编排买卖动作。
  · 前提判断 / 触发条件判断 全部在 conditions.py（in_trading_session / hit_stop_loss / is_limit_up ...）
  · 下单执行 全部在 commands.py（stop_loss_order / take_profit_order / close_liq_order / execute_buy）

每个阶段块都严格遵循同一模板，只靠本文件即可读懂整个策略：

    if <前提：是否处于该阶段>:
        <判断：筛出满足条件的股票>
        if <无>:
            pass                     # 无目标 → 跳过
        else:
            for <每只目标股>:
                <执行：下单>          # 有目标 → 逐只执行

要改买卖节奏或触发条件，去 conditions.py；要改下单执行，去 commands.py。
"""

from AITrading import conditions as CON
from AITrading import commands as CMD


def handle_tick(xt_trader, tick):
    """每次 tick 按交易阶段执行：开盘止损 → 盘中涨停/止盈 → 收盘强平 → 尾盘买入。

    四个阶段结构一致：先判断「前提」（是否处于该阶段），
    再筛出「满足触发条件的股票」，有则逐只执行下单，无则跳过。
    """
    tick = tick or {}

    # —— 阶段一·开盘后：先同步真实持仓（处理部分成交），再监控止损 ——
    # 前提：处于盘中交易区间 [09:30,14:55)
    # 判断：哪些持仓的最低价已跌破止损线；有触发 → 逐只止损；无 → 跳过
    if CON.in_trading_session():
        CMD.sync_positions(xt_trader)                       # 同步真实持仓（处理部分成交）
        hits = [c for c in list(CMD._positions_state.keys())
                if CON.hit_stop_loss(c, tick)]
        if not hits:
            pass                                            # 无持仓触发止损 → 跳过
        else:
            for code in hits:
                CMD.stop_loss_order(xt_trader, code)        # 有 → 逐只止损

    # —— 阶段二·盘中：监控涨停 / 止盈 ——
    # 前提：处于盘中交易区间
    # 判断：哪些持仓涨停（最高价触涨停价）或盈利达止盈线；有 → 逐只卖出；无 → 跳过
    if CON.in_trading_session():
        hits = []                                           # [(code, 卖出原因)]
        for code in list(CMD._positions_state.keys()):
            if CON.is_limit_up(code, tick):
                hits.append((code, "涨停"))
            elif CON.hit_take_profit(code, tick):
                hits.append((code, "止盈"))
        if not hits:
            pass                                            # 无持仓涨停/止盈 → 跳过
        else:
            for code, reason in hits:
                CMD.take_profit_order(xt_trader, code, reason)  # 有 → 逐只卖出

    # —— 阶段三·临近收盘：仍未触板则强平 ——
    # 前提：已到达收盘强平时间点（>=14:55）
    # 判断：还有哪些持仓未卖出；有 → 逐只强平；无（已空仓）→ 跳过
    if CON.is_close_approach():
        left = list(CMD._positions_state.keys())
        if not left:
            pass                                            # 已空仓 → 跳过
        else:
            for code in left:
                CMD.close_liq_order(xt_trader, code)        # 有持仓 → 逐只强平

    # —— 阶段四·尾盘：集合竞价买入 ——
    # 前提：处于尾盘集合竞价区间 [14:57,15:00)，且今日尚未买过
    # 判断：选出「策略最优先股」；有可选股 → 按该股报价买入；无 → 跳过（空仓）
    if CON.in_tail_session():
        if CMD.buy_done_today():
            pass                                            # 今日已买过 → 跳过（避免重复下单）
        else:
            decision = CMD.decide_buy()                     # 判断：选出策略最优先股
            if decision is None:
                pass                                        # 无可选股 → 跳过（今日空仓）
            else:
                CMD.execute_buy(decision)                   # 有 → 按该股最优报价买入
