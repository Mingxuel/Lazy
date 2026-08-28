"""
miniQMT 基础 API 封装（第一段 API）

仅封装 xtquant 的连接、行情获取、持仓/资金查询、下单/撤单。
不含任何策略或业务规则，供 commands.py / callbacks.py 调用。
未安装/未配置 xtquant 时，相关函数会在调用处抛异常，由上层走“模拟”分支。
"""

from AITrading import config as C

_xt_trader = None
_xt_session = None


def connect():
    """建立 miniQMT 连接，返回 (xt_trader, session_id)。已连接则复用。"""
    global _xt_trader, _xt_session
    if _xt_trader is not None:
        return _xt_trader, _xt_session
    if not C.QMT_USERDATA_PATH or not C.ACCOUNT_ID:
        raise RuntimeError(
            "QMT 未配置：请在 config.json / config.py 填写 "
            "QMT_USERDATA_PATH 与 ACCOUNT_ID 后重试。"
        )
    from xtquant import xtdata, xttrader, xtconstant
    from xtquant.xttrader import XtTrader
    try:
        xtdata.connect(config_path=C.QMT_USERDATA_PATH)
    except Exception:
        pass
    t = XtTrader()
    sess = t.start()
    if sess == 0:
        raise RuntimeError("QMT 连接失败（session=0），请确认 QMT 客户端已登录并处于 miniQMT 模式。")
    if not t.connect(C.QMT_USERDATA_PATH):
        raise RuntimeError("QMT connect 失败，请检查 userdata 路径。")
    t.subscribe(C.ACCOUNT_ID)
    _xt_trader, _xt_session = t, sess
    return t, sess


def get_account_cash(xt_trader):
    """返回可用资金（元）。无连接时返回 INIT_CAPITAL。"""
    if xt_trader is None:
        return C.INIT_CAPITAL
    try:
        asset = xt_trader.query_stock_asset(C.ACCOUNT_ID)
        return asset.cash if asset else C.INIT_CAPITAL
    except Exception:
        return C.INIT_CAPITAL


def get_positions(xt_trader):
    """返回持仓列表 [{'code', 'volume', 'cost'}]。无连接时返回空。cost 为持仓成本价。"""
    if xt_trader is None:
        return []
    try:
        poss = xt_trader.query_stock_positions(C.ACCOUNT_ID)
        return [{"code": p.stock_code, "volume": int(p.volume),
                 "cost": float(getattr(p, "open_price", 0.0) or 0.0)} for p in poss if p.volume > 0]
    except Exception as e:
        C.log("qmt", f"查询持仓失败：{e}")
        return []


def get_full_tick(code):
    """返回 {open, high, low, lastPrice} 或 None。"""
    try:
        from xtquant import xtdata
        tick = xtdata.get_full_tick([code])
        if tick and code in tick:
            t = tick[code]
            return {"open": t.get("open"), "high": t.get("high"),
                    "low": t.get("low"), "lastPrice": t.get("lastPrice")}
    except Exception:
        pass
    return None


def get_live_snapshot(code):
    """实时快照 {close, volume, pre_close}，用于尾盘 T-1 形态判定。失败返回 None。"""
    try:
        from xtquant import xtdata
        vd = xtdata.get_market_data_ex([code], ["volume"], period="1d")
        vol = float(vd[code]["volume"].iloc[-1]) if (vd and code in vd and vd[code] is not None and len(vd[code]) > 0) else 0.0
        pd = xtdata.get_market_data_ex([code], ["preClose"], period="1d")
        pre = float(pd[code]["preClose"].iloc[-1]) if (pd and code in pd and pd[code] is not None and len(pd[code]) > 0) else 0.0
        tick = xtdata.get_full_tick([code])
        close = tick[code]["lastPrice"] if (tick and code in tick and "lastPrice" in tick[code]) else 0.0
        if close <= 0 or pre <= 0:
            return None
        return {"close": float(close), "volume": vol, "pre_close": pre}
    except Exception as e:
        C.log("buy", f"获取 {code} 实时 T-1 数据失败：{e}")
        return None


def get_realtime_price(code):
    """最新价；失败返回 None。"""
    try:
        from xtquant import xtdata
        tick = xtdata.get_full_tick([code])
        if tick and code in tick and "lastPrice" in tick[code]:
            return float(tick[code]["lastPrice"])
    except Exception:
        pass
    return None


def get_pre_close(code):
    """前收盘价；失败返回 None。"""
    try:
        from xtquant import xtdata
        d = xtdata.get_market_data_ex([code], ["preClose"], period="1d")
        if d and code in d and d[code] is not None and len(d[code]) > 0:
            return float(d[code]["preClose"].iloc[-1])
    except Exception:
        pass
    return None


def submit_buy(xt_trader, code, vol, price):
    """提交买入单，返回订单号。"""
    from xtquant import xtconstant
    return xt_trader.open_buy(
        stock_code=code, volume=vol, price=price,
        account_id=C.ACCOUNT_ID, order_type=xtconstant.FIX_PRICE,
        strategy_name=C.STRATEGY_NAME,
    )


def submit_sell(xt_trader, code, vol, price):
    """提交卖出单，返回订单号。price<=0 时调用方应已处理为限价兜底。"""
    from xtquant import xtconstant
    return xt_trader.open_sell(
        stock_code=code, volume=vol, price=price,
        account_id=C.ACCOUNT_ID, order_type=xtconstant.FIX_PRICE,
        strategy_name=C.STRATEGY_NAME,
    )
