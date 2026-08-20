"""
实盘候选股票池（TARGET）计算模块

功能:
    为 TPO 系列策略生成 T-2 日候选股票池，供实盘在下个交易日根据日内情况买入。

实盘时序:
    T-3 日首板放量涨停 -> T-2 日上涨放量未涨停（选股池产生）-> T-1 日根据日内情况买入

候选池记录在 T-2 日，最新候选池 = 最新交易日，下个交易日可买入。

存储:
    MarcoAI/AIData/TARGET/{策略}/{T-2日期}，每行 股票代码|股票名称|市值

API 说明:
    UPDATE_TARGET_TPO_3()    市值统一用 T-2 日收盘价计算（>= 200 亿）
    UPDATE_TARGET_TPO_TOP()  市值统一用 T-2 日收盘价计算（>= 200 亿），按流通市值倒序排列
"""

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import partial

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)
from AICode.MarcoAPI.Update.Constants import *
from AICode.MarcoAPI.Update.StockCodes import *
from AICode.MarcoAPI.Update.TradingDates import *
from AICode.MarcoAPI.Update.Path import *
from AICode.MarcoAPI.Update.SZ2001D import GET_SZ200_1D_PREVIOUS, _rotate_dir


def UPDATE_TARGET_TPO_3():
    """实盘候选池 TPO_3：市值统一用 T-2 日收盘价计算（>= 200 亿）"""
    _UPDATE_TARGET_CANDIDATE("TPO_3", market_index=2)


def UPDATE_TARGET_TPO_TOP():
    """实盘候选池 TPO_TOP：条件同 TPO_3，按流通市值倒序排列（市值最大的排第一）"""
    _UPDATE_TARGET_CANDIDATE("TPO_TOP", market_index=2, sort_by_market=True)


def _UPDATE_TARGET_CANDIDATE(strategy_name: str, market_index: int, sort_by_market: bool = False):
    """生成 T-2 日候选股票池到 TARGET/{strategy_name}/（多进程）"""
    target_dir = PATH_AIDATA_TARGET(strategy_name)
    _rotate_dir(target_dir)
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    with ProcessPoolExecutor(max_workers=32) as pool:
        list(pool.map(partial(GENERATE_TARGET_CANDIDATE, stock_codes, target_dir, market_index, sort_by_market), trading_dates))


def GENERATE_TARGET_CANDIDATE(stock_codes: list[str], target_dir: str, market_index: int, sort_by_market: bool, trading_date: str):
    """worker: 以 trading_date 为 T-2（选股池产生日），生成 T-2 候选股票池。

    候选池条件:
        T-3 首板（lian_ban==1）放量涨停 + T-2 上涨放量未涨停
    首板用 1D 加工字段 lian_ban==1 判断，无需 T-4 数据。
    市值筛选:
        统一用 T-2 日（record_0）收盘价计算市值，>= 200 亿才保留
    候选池记录在 T-2 日（trading_date），最新候选池 = 最新交易日，下个交易日可买入。
    每行只存 股票代码|股票名称|市值。
    sort_by_market=True 时（TPO_TOP）按流通市值倒序排列（市值最大的排第一），否则按股票代码顺序。
    """
    print("UPDATE_TARGET_CANDIDATE: " + trading_date)
    t2_date = trading_date                      # T-2 选股池产生日
    rows: list[tuple[str, float]] = []
    for stock_code in stock_codes:
        stock = stock_code.split('|')
        code = stock[0]
        name = stock[1] if len(stock) > 1 else ""
        record_1 = GET_SZ200_1D_PREVIOUS(code, trading_date, 1)  # T-3（首板涨停日）
        record_0 = GET_SZ200_1D_PREVIOUS(code, trading_date, 0)  # T-2（选股池产生日）
        if record_1 is None or record_0 is None:
            continue
        # T-3 首板放量涨停（lian_ban==1 表示当天是首板）
        if record_1.is_top != 1:
            continue
        if record_1.lian_ban != 1:
            continue
        if record_1.is_volume_up != 1:
            continue
        # T-2 上涨放量未涨停
        if record_0.is_up != 1:
            continue
        if record_0.is_volume_up != 1:
            continue
        if record_0.is_top != 0:
            continue
        # 市值：统一用 T-2 日（record_0）收盘价计算，>= 200 亿才保留
        market_value = 0.0
        info = GET_STOCK_INFO(code)
        if info is None or info[1] <= 0:
            continue
        market_value = float(info[1]) * record_0.close
        if market_value < 2e10:              # 市值 >= 200 亿才保留
            continue
        rows.append((f"{code}|{name}|{market_value:.2f}", market_value))

    # TPO_TOP：按流通市值倒序排列，市值最大的排第一（TPO_3 保持股票代码顺序）
    if sort_by_market:
        rows.sort(key=lambda x: x[1], reverse=True)

    with open(f"{target_dir}/{t2_date}", "a") as file:
        if len(rows) == 0:
            file.write("\n")
        for row, _mv in rows:
            file.write(row + "\n")


if __name__ == "__main__":
    UPDATE_TARGET_TPO_3()
    UPDATE_TARGET_TPO_TOP()
