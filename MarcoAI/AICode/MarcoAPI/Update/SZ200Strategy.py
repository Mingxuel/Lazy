from concurrent.futures import ProcessPoolExecutor
from functools import partial
import os
import sys
from typing import TextIO

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)
from AICode.MarcoAPI.Update.Constants import *
from AICode.MarcoAPI.Update.StockCodes import *
from AICode.MarcoAPI.Update.TradingDates import *
from AICode.MarcoAPI.Update.Path import *
from AICode.MarcoAPI.Update.Data import DATA_1D
from AICode.MarcoAPI.Update.SZ2001D import GET_SZ200_1D_PREVIOUS, _rotate_dir

def UPDATE_STRATEGY_TPO_3():
    """策略 TPO_3：市值统一用 T-2 日收盘价计算（>= 200 亿），T-1 收盘涨跌幅 < 3%"""
    _UPDATE_STRATEGY_TPO("TPO_3", PATH_AIDATA_STRATEGY_TPO_3(), market_index=2, max_ratio=3.0)

def UPDATE_STRATEGY_TPO_TOP():
    """策略 TPO_TOP：条件同 TPO_3，但选股时按流通市值倒序排列，市值最大的排第一"""
    _UPDATE_STRATEGY_TPO("TPO_TOP", PATH_AIDATA_STRATEGY_TPO_TOP(), market_index=2, max_ratio=3.0, sort_by_market=True)

def _UPDATE_STRATEGY_TPO(strategy_name: str, strategy_dir: str, market_index: int, max_ratio: float = 3.0, sort_by_market: bool = False):
    """TPO 系列通用选股：生成回测数据到 Strategy/{strategy_name}/。

    写入 T-0 日全部加工数据（28列），供回测使用。
    实盘候选池由 SZ200Target.py 的 UPDATE_TARGET_TPO_3/TPO_TOP 生成（TARGET/ 目录）。
    市值统一用 market_index（默认 2=T-2）日收盘价计算；
    筛选条件由 max_ratio（T-1 收盘涨跌幅上限）与 TPO 形态共同决定；
    sort_by_market=True 时（TPO_TOP）结果按流通市值倒序排列（市值最大的排第一），否则按股票代码顺序。
    """
    _rotate_dir(strategy_dir)
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    with ProcessPoolExecutor(max_workers=32) as pool:
        list(pool.map(partial(GENERATE_STRATEGY_TPO, stock_codes, strategy_dir, market_index, max_ratio, sort_by_market), trading_dates))

def GENERATE_STRATEGY_TPO(stock_codes: list[str], strategy_dir: str, market_index: int, max_ratio: float, sort_by_market: bool, trading_date: str):
    """worker（回测数据）: 以 trading_date 为 T-0，逐股按加工字段判断是否满足完整 TPO 形态。

    写入 T-0 日全部加工数据（28列）到 Strategy/{strategy}/{T-0日期}，供回测使用。
    市值统一用 market_index（默认 2=T-2）日收盘价计算；
    筛选条件由 max_ratio（T-1 收盘涨跌幅上限）与 TPO 形态共同决定；
    sort_by_market=True 时（TPO_TOP）结果按流通市值倒序排列（市值最大的排第一）。
    """
    print("UPDATE_TARGET_TPO: " + trading_date)
    sell_date = trading_date                    # T-0
    data: list[tuple[DATA_1D, str, str, float]] = []
    for stock_code in stock_codes:
        stock = stock_code.split('|')
        code = stock[0]
        name = stock[1] if len(stock) > 1 else ""
        record_3 = GET_SZ200_1D_PREVIOUS(code, trading_date, 3)
        record_2 = GET_SZ200_1D_PREVIOUS(code, trading_date, 2)
        record_1 = GET_SZ200_1D_PREVIOUS(code, trading_date, 1)
        record_0 = GET_SZ200_1D_PREVIOUS(code, trading_date, 0)
        if record_3 is None or record_2 is None or record_1 is None or record_0 is None:
            continue
        # T-3 首板放量涨停
        if record_3.is_top != 1:
            continue
        if record_3.lian_ban != 1:
            continue
        if record_3.is_volume_up != 1:
            continue
        # T-2 上涨放量未涨停
        if record_2.is_up != 1:
            continue
        if record_2.is_volume_up != 1:
            continue
        if record_2.is_top != 0:
            continue
        # T-1 收盘涨跌幅 < max_ratio（按策略 3%/4%/5%）、缩量、收盘价>MA5
        if record_1.ratio >= max_ratio:
            continue
        if record_1.is_volume_down != 1:
            continue
        if record_1.close <= record_1.ma5:
            continue
        # 市值 ≥ 200 亿
        info = GET_STOCK_INFO(code)
        if info is None or info[1] <= 0:
            continue
        market_record = {3: record_3, 2: record_2, 1: record_1}[market_index]
        market_value = float(info[1]) * market_record.close
        if market_value < 2e10:
            continue
        data.append((record_0, code, name, market_value))

    # TPO_TOP：按流通市值倒序排列，市值最大的排第一（TPO_3 保持股票代码顺序）
    if sort_by_market:
        data.sort(key=lambda x: x[3], reverse=True)

    with open(f"{strategy_dir}/{sell_date}", "a") as file:
        if len(data) == 0:
            file.write("\n")
        for d, code, name, market_value in data:
            _write_row(file, sell_date, code, name, market_value, d)


def _write_row(file: TextIO, date: str, code: str, name: str, market_value: float, d: DATA_1D):
    """股票代码|股票名称|市值 放最前面，日期用 T-0 卖出日，后接该日 25 列加工数据（共28列）"""
    file.write(
        f"{code}|{name}|{market_value:.2f}"
        + f"|{date}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}"
        + f"|{d.pre_close}|{d.is_top}|{d.is_toped}|{d.ratio}"
        + f"|{d.is_up}|{d.is_down}|{d.is_red}|{d.is_green}"
        + f"|{d.is_volume_up}|{d.is_volume_down}"
        + f"|{d.ma5}|{d.ma10}|{d.ma20}|{d.ma30}|{d.ma60}|{d.ma120}|{d.lian_ban}|{d.is_bottom}\n"
    )

if __name__ == "__main__":
    #SHOW_TARGET_1D()
    UPDATE_STRATEGY_TPO_3()
    UPDATE_STRATEGY_TPO_TOP()
    #SHOW_TARGET_1D()
