from concurrent.futures import ProcessPoolExecutor
from functools import partial
import os
import sys
from typing import Callable, TextIO

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


def UPDATE_STRATEGY_TPO_M5():
    """策略 TPO_M5：基于 TPO_TOP，市值区间 200 亿~1300 亿，止损 -5%，按市值倒序首选第一只；
    额外条件：T-1 收盘价需 >= 预测 T-0 的 MA5 = (T-1*2 + T-2 + T-3 + T-4)/5，
    否则顺延至下一只，直到条件满足（都不满足则取市值最大的一只）。"""
    _UPDATE_STRATEGY_TPO(
        "TPO_M5", PATH_AIDATA_STRATEGY_TPO_M5(),
        market_index=2, max_ratio=3.0, sort_by_market=True,
        market_min=2e10, market_max=1.3e11, ma5_predict=True, stop_loss=-0.05,
    )


def _UPDATE_STRATEGY_TPO(strategy_name: str, strategy_dir: str, market_index: int, max_ratio: float = 3.0, sort_by_market: bool = False, sort_by_vol_ratio: bool = False, sort_by_vol_ratio_asc: bool = False, require_first_plate: bool = True, market_min: float = 2e10, market_max: float = float("inf"), ma5_predict: bool = False, stop_loss: float = -0.06):
    """TPO 策略通用选股：生成回测数据到 Strategy/{strategy_name}/。

    写入 T-0 日全部加工数据（29列，末列为本策略止损线），供回测使用。
    实盘候选池由 SZ200Target.py 的 UPDATE_TARGET_TPO_3/TPO_TOP/TPO_NB 生成（TARGET/ 目录）。
    市值统一用 market_index（默认 2=T-2）日收盘价计算；
    筛选条件由 max_ratio（T-1 收盘涨跌幅上限）与 TPO 形态共同决定；
    sort_by_market=True 时（TPO_TOP）结果按流通市值倒序排列（市值最大的排第一）；
    sort_by_vol_ratio=True 时（TPO_VR）结果按 T-2/T-3 量比倒序排列（量比最大的排第一）；
    sort_by_vol_ratio_asc=True 时（TPO_VR2）结果按量比升序排列（量比最小的排第一）；
    require_first_plate=False 时（TPO_NB）T-3 日只需涨停、不限首板；
    market_min/market_max 为流通市值区间（默认 200 亿~不限）；
    ma5_predict=True 时（TPO_M5）按市值倒序后，取第一只满足
      “T-1 收盘价 >= 预测 T-0 的 MA5 = (T-1*2 + T-2 + T-3 + T-4)/5” 的，否则取第一只；
    stop_loss 为本策略次日卖出止损线（默认 -6%，TPO_M5 用 -5%）。
    """
    _rotate_dir(strategy_dir)
    stock_codes = STOCK_CODES_ALL()
    trading_dates = TRADING_DATES()
    with ProcessPoolExecutor(max_workers=32) as pool:
        list(pool.map(partial(GENERATE_STRATEGY_TPO, stock_codes, strategy_dir, market_index, max_ratio, sort_by_market, sort_by_vol_ratio, sort_by_vol_ratio_asc, require_first_plate, market_min, market_max, ma5_predict, stop_loss), trading_dates))

def GENERATE_STRATEGY_TPO(stock_codes: list[str], strategy_dir: str, market_index: int, max_ratio: float, sort_by_market: bool, sort_by_vol_ratio: bool, sort_by_vol_ratio_asc: bool, require_first_plate: bool, market_min: float, market_max: float, ma5_predict: bool, stop_loss: float, trading_date: str):
    """worker（回测数据）: 以 trading_date 为 T-0，逐股按加工字段判断是否满足完整 TPO 形态。

    写入 T-0 日全部加工数据（29列，末列为止损线）到 Strategy/{strategy}/{T-0日期}，供回测使用。
    市值统一用 market_index（默认 2=T-2）日收盘价计算；
    筛选条件由 max_ratio（T-1 收盘涨跌幅上限）与 TPO 形态共同决定；
    sort_by_market=True 时（TPO_TOP）结果按流通市值倒序排列（市值最大的排第一）；
    sort_by_vol_ratio=True 时（TPO_VR）结果按 T-2/T-3 量比倒序排列（量比最大的排第一）；
    sort_by_vol_ratio_asc=True 时（TPO_VR2）结果按量比升序排列（量比最小的排第一）；
    require_first_plate=False 时（TPO_NB）T-3 日只需涨停、不限首板；
    market_min/market_max 为流通市值区间；
    ma5_predict=True 时按市值倒序后只选第一只满足 MA5 预测条件的（否则第一只）。
    """
    print("UPDATE_TARGET_TPO: " + trading_date)
    sell_date = trading_date                    # T-0
    data: list[tuple[DATA_1D, str, str, float, float]] = []  # (record_0, code, name, market_value, vol_ratio)
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
        # T-3 放量涨停（TPO_NB 不限首板）
        if record_3.is_top != 1:
            continue
        if require_first_plate and record_3.lian_ban != 1:
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
        # 市值区间 [market_min, market_max]
        info = GET_STOCK_INFO(code)
        if info is None or info[1] <= 0:
            continue
        market_record = {3: record_3, 2: record_2, 1: record_1}[market_index]
        market_value = float(info[1]) * market_record.close
        if market_value < market_min or market_value > market_max:
            continue
        # T-2 / T-3 量比
        vol_ratio = (record_2.volume / record_3.volume) if (record_3.volume and record_3.volume > 0) else 0.0
        data.append((record_0, code, name, market_value, vol_ratio))

    # 排序：TPO_TOP 按市值倒序；TPO_VR 按量比倒序；TPO_VR2 按量比升序（TPO_3 保持股票代码顺序）
    if sort_by_market:
        data.sort(key=lambda x: x[3], reverse=True)
    elif sort_by_vol_ratio:
        data.sort(key=lambda x: x[4], reverse=True)
    elif sort_by_vol_ratio_asc:
        data.sort(key=lambda x: x[4], reverse=False)

    # MA5 预测筛选：按市值倒序后，取第一只满足 “T-1 收盘 >= 预测 T-0 MA5” 的
    if ma5_predict:
        chosen: tuple[DATA_1D, str, str, float, float] | None = None
        for d, code, name, market_value, _v in data:
            rec1 = GET_SZ200_1D_PREVIOUS(code, trading_date, 1)
            rec2 = GET_SZ200_1D_PREVIOUS(code, trading_date, 2)
            rec3 = GET_SZ200_1D_PREVIOUS(code, trading_date, 3)
            rec4 = GET_SZ200_1D_PREVIOUS(code, trading_date, 4)
            if rec1 is None or rec2 is None or rec3 is None or rec4 is None:
                continue
            pred_ma5 = (rec1.close * 2 + rec2.close + rec3.close + rec4.close) / 5.0
            if rec1.close >= pred_ma5:
                chosen = (d, code, name, market_value, 0.0)
                break
        if chosen is not None:
            data = [chosen]  # 只保留选中的一只
        elif len(data) > 0:
            data = [data[0]]  # 都不满足，兜底取市值最大的一只

    with open(f"{strategy_dir}/{sell_date}", "a") as file:
        if len(data) == 0:
            file.write("\n")
        for d, code, name, market_value, _vol_ratio in data:
            _write_row(file, sell_date, code, name, market_value, d, stop_loss)


def _write_row(file: TextIO, date: str, code: str, name: str, market_value: float, d: DATA_1D, stop_loss: float = -0.06):
    """股票代码|股票名称|市值 放最前面，日期用 T-0 卖出日，后接该日 25 列加工数据 + 本策略止损线（共29列）"""
    file.write(
        f"{code}|{name}|{market_value:.2f}"
        + f"|{date}|{d.open}|{d.high}|{d.low}|{d.close}|{d.volume}|{d.amount}"
        + f"|{d.pre_close}|{d.is_top}|{d.is_toped}|{d.ratio}"
        + f"|{d.is_up}|{d.is_down}|{d.is_red}|{d.is_green}"
        + f"|{d.is_volume_up}|{d.is_volume_down}"
        + f"|{d.ma5}|{d.ma10}|{d.ma20}|{d.ma30}|{d.ma60}|{d.ma120}|{d.lian_ban}|{d.is_bottom}"
        + f"|{stop_loss:.2f}\n"
    )

def _update_condition_strategy(strategy_dir: str, condition: Callable[[DATA_1D, DATA_1D, DATA_1D], bool]) -> None:
    """通用：遍历 TPO_3 候选池，每只按 condition(rec3, rec2, rec1) 判断，选第一只满足的，兜底第一只。"""
    _rotate_dir(strategy_dir)
    target_dir = PATH_AIDATA_TARGET("TPO_3")  # TPO_3 实盘候选池（T-2 产生）
    if not os.path.isdir(target_dir):
        return
    for t2_date in sorted(os.listdir(target_dir)):
        if not t2_date.isdigit():
            continue
        _write_condition_day(strategy_dir, target_dir, t2_date, condition)


def _write_condition_day(strategy_dir: str, target_dir: str, t2_date: str, condition: Callable[[DATA_1D, DATA_1D, DATA_1D], bool]):
    """对单个 T-2 候选池日：按顺序选第一只满足 condition 的，写入 T-0 回测数据。"""
    t3_date = TRADING_DATE_PREVIOUS(t2_date, 1)
    t1_date = TRADING_DATE_AFTER(t2_date, 1)
    t0_date = TRADING_DATE_AFTER(t2_date, 2)
    if not t3_date or not t1_date or not t0_date:
        return
    candidates = []
    with open(os.path.join(target_dir, t2_date), "r", encoding="gbk", errors="ignore") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 3:
                continue
            candidates.append((parts[0], parts[1], float(parts[2])))
    if not candidates:
        with open(os.path.join(strategy_dir, t0_date), "a") as file:
            file.write("\n")
        return
    selected = None
    for code, name, market_value in candidates:
        rec3 = GET_SZ200_1D_PREVIOUS(code, t2_date, 1)   # T-3（首板日）
        rec2 = GET_SZ200_1D_PREVIOUS(code, t2_date, 0)   # T-2（候选池日）
        rec1 = GET_SZ200_1D_PREVIOUS(code, t1_date, 0)   # T-1（买入确认日）
        rec0 = GET_SZ200_1D_PREVIOUS(code, t0_date, 0)   # T-0（卖出日）
        if rec3 is None or rec2 is None or rec1 is None or rec0 is None:
            continue
        if condition(rec3, rec2, rec1):
            selected = (rec0, code, name, market_value)
            break
    # 全部不满足 -> 选第一只
    if selected is None:
        code, name, market_value = candidates[0]
        rec0 = GET_SZ200_1D_PREVIOUS(code, t0_date, 0)
        if rec0 is not None:
            selected = (rec0, code, name, market_value)
    with open(os.path.join(strategy_dir, t0_date), "a") as file:
        if selected is None:
            file.write("\n")
        else:
            d, code, name, market_value = selected
            _write_row(file, t0_date, code, name, market_value, d)


if __name__ == "__main__":
    #SHOW_TARGET_1D()
    UPDATE_STRATEGY_TPO_3()
    UPDATE_STRATEGY_TPO_TOP()
    UPDATE_STRATEGY_TPO_M5()
    #SHOW_TARGET_1D()
