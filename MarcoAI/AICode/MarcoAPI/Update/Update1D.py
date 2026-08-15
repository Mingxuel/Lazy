"""
统一数据更新入口

运行本脚本即可按依赖顺序更新全部数据：
    python AICode/MarcoAPI/Update/Update1D.py

更新流程（按依赖顺序）:
    1. UPDATE_TRADING_DATES    更新交易日历
    2. UPDATE_STOCK_CODES      更新股票池（SZ100.xlsx -> STOCK_CODES_ALL）
    3. UPDATE_1D_ORIGIN        拉取原始前复权日线（需通达信联网）
    4. UPDATE_1D               加工日线（1D_ORIGIN -> 1D，含 is_top/is_bottom/MA/连板等）
    5. UPDATE_TOP              生成每日涨停股列表（TOP_ORIGIN -> TOP）
    6. UPDATE_1D               加工日线（依赖涨停列表生成 is_top/lian_ban）
    7. UPDATE_STRATEGY_TPO31/32/33  三个策略选股（Strategy/ 回测数据）
    8. UPDATE_TARGET_TPO31/32/33  三个策略实盘候选池（TARGET/ 候选股）
"""

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from AICode.MarcoAPI.Update.TradingDates import UPDATE_TRADING_DATES
from AICode.MarcoAPI.Update.StockCodes import UPDATE_STOCK_CODES
from AICode.MarcoAPI.Update.SZ2001D import UPDATE_1D_ORIGIN, UPDATE_1D
from AICode.MarcoAPI.Update.SZ200Top import UPDATE_TOP
from AICode.MarcoAPI.Update.SZ200Strategy import (
    UPDATE_STRATEGY_TPO31,
    UPDATE_STRATEGY_TPO32,
    UPDATE_STRATEGY_TPO33,
)
from AICode.MarcoAPI.Update.SZ200Target import (
    UPDATE_TARGET_TPO31,
    UPDATE_TARGET_TPO32,
    UPDATE_TARGET_TPO33,
)


def UPDATE_ALL():
    """按依赖顺序更新全部数据

    顺序说明:
        UPDATE_1D 加工日线的 is_top/lian_ban 依赖 UPDATE_TOP 生成的涨停列表，
        故 UPDATE_TOP 须在 UPDATE_1D 之前执行。
    """
    steps = [
        ("UPDATE_TRADING_DATES", UPDATE_TRADING_DATES),
        ("UPDATE_STOCK_CODES", UPDATE_STOCK_CODES),
        ("UPDATE_1D_ORIGIN", UPDATE_1D_ORIGIN),
        ("UPDATE_TOP", UPDATE_TOP),
        ("UPDATE_1D", UPDATE_1D),
        ("UPDATE_STRATEGY_TPO31", UPDATE_STRATEGY_TPO31),
        ("UPDATE_STRATEGY_TPO32", UPDATE_STRATEGY_TPO32),
        ("UPDATE_STRATEGY_TPO33", UPDATE_STRATEGY_TPO33),
        ("UPDATE_TARGET_TPO31", UPDATE_TARGET_TPO31),
        ("UPDATE_TARGET_TPO32", UPDATE_TARGET_TPO32),
        ("UPDATE_TARGET_TPO33", UPDATE_TARGET_TPO33),
    ]
    for name, fn in steps:
        print(f"\n===== {name} BEGIN =====")
        try:
            fn()
            print(f"===== {name} END =====")
        except Exception as exc:
            print(f"!!!!! {name} FAILED: {exc}")
    print("\n全部数据更新完成")


if __name__ == "__main__":
    UPDATE_ALL()
