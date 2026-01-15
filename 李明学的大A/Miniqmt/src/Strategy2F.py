from xtquant import xtdata, xtconstant
from datetime import datetime
import datetime
import time
from Common import Common, DataType, MAType, LimitType
import sys
from RunTime import RunTime, BuyStack, SellStack, TradeStatus
from Trader import Trader, DEFAULT_CASH
from Sectors import Sectors
from TraderList import OrderList, PositionList, TradeList, AssertList

common = Common()
runtime = RunTime()
sectors = Sectors()
order_list = OrderList()
position_list = PositionList()
trade_list = TradeList()
assert_list = AssertList()
buy_stack = BuyStack()
sell_stack = SellStack()
trader = Trader()
MA_RATE = 0.97
CAN_BUY = False

# 回调函数 ################################################################################################
def INIT():
    if common.TEST_MODE:
        assert_list.CASH = 1000000.0
        assert_list.PRE_CASH = 1000000.0
    #assert_list.BOX = 17000
    assert_list.BOX = 1000000
    assert_list.BOX_COUNT = 4

def S_CALLBACK_TICK():
    if common.IS_AUCTION_TIME():
        if common.TEST_MODE is not True:
            print(f"[S_CALLBACK_TICK] {common.TIME}")
        if len(sell_stack.STACK) > 0: # 说明已经完成委托，委托只进行一次
            return
        stock_list = position_list.GET_CAN_SELL_STOCK_LIST()
        for stock_code in stock_list:
            if stock_code == "510500.SH":
                sell_stack.PUSH(stock_code, 0, status = TradeStatus.keep)
                continue
            data = common.GET_STOCK_REAL_DATA_FOR_1D(stock_code)
            price_preclose = common.GET_STOCK_DATA_ITEM(data, DataType.preClose)
            price_bottom = common.LIMIT_PRICE(stock_code, LimitType.Bottom, price_preclose)
            sell_stack.PUSH(stock_code, price_bottom, status = TradeStatus.process)
    else: # 集合竞价阶段没卖出去那么，连续竞价阶段进行不断卖出
        stock_list = position_list.GET_CAN_SELL_STOCK_LIST()
        for stock_code in stock_list:
            if stock_code == "510500.SH":
                continue
            if stock_code not in sell_stack.GET_STOCK_LIST(TradeStatus.process):
                continue
            data = common.GET_STOCK_REAL_DATA_FOR_TICK(stock_code)
            price_close = common.GET_STOCK_DATA_ITEM(data, DataType.close)
            sell_stack.PUSH(stock_code, price_close)

def B_CALLBACK_1M():
    global CAN_BUY
    if CAN_BUY is False:
        return None

    if common.TEST_MODE is not True:
        print(f"[{common.TIME[8:10]}:{common.TIME[10:12]}:{common.TIME[12:14]}][B][1M]")
    stock_list = runtime.B_STOCK_LIST
    for stock_code in stock_list:
        data = common.GET_STOCK_REAL_DATA_FOR_1D(stock_code)
        price_open = float(data["open"]) # 当日开盘价
        price_preClose = float(data["preClose"])
        price_top = common.PRICE_TOP(stock_code, data)
        price_bottom = common.PRICE_BOTTOM(stock_code, data)
        ratio = float(price_open / price_preClose)
        if ratio >= 1.02 and ratio <= 0.93:
            return None
        if abs(price_top - price_open) < 0.01 or abs(price_open - price_bottom) < 0.01:
            return None
        pre_date = common.PRE_TRADING_DATE_FOR_STOCK(stock_code, common.TODAY, 1)
        if common.IS_2F(stock_code, pre_date) is not True:
            return None
        limit_price = common.MA_REAL_EXPECT_FOR_1M(stock_code, MAType.ma5)
        if limit_price is None:
            continue
        limit_price = common.ROUNDOFF(limit_price * MA_RATE)
        data = common.GET_STOCK_REAL_DATA_FOR_1M(stock_code)
        price_close = common.ROUNDOFF(float(data["close"]))
        if price_close >= limit_price:
            buy_stack.PUSH(stock_code, price_close)

def B_AUCTION(): # 集合竞价结束后调用(09:25:03)
    pass
    global CAN_BUY
    CAN_BUY = False
    stock_list = runtime.B_STOCK_LIST
    count_win = 0
    count_lose = 0
    ratio = 0.0
    for stock_code in stock_list:
        data = common.GET_STOCK_REAL_DATA_FOR_1D(stock_code)
        price_open = float(data["open"]) # 当日开盘价
        price_preClose = float(data["preClose"]) # 当日开盘价
        ratio = ratio + (price_open - price_preClose) / price_preClose
        #price_top = common.PRICE_TOP(stock_code, data)
        #price_bottom = common.PRICE_BOTTOM(stock_code, data)
        #if abs(price_open - price_bottom) <= 0.01:
        #    CAN_BUY = False
        #    break
        if price_open > price_preClose:
            count_win = count_win + 1
        else:
            count_lose = count_lose + 1
    if count_win > count_lose and ratio > 0.1:
        CAN_BUY = True
#        if abs(price_open - price_top) <= 0.01:
#            count = count + 1
#            if count >=2:
#                CAN_BUY = True
    # if common.TEST_MODE is not True:
    #     print(f"[B_AUCTION] {common.TIME}")
    # stock_list = runtime.B_STOCK_LIST
    # for stock_code in stock_list:
    #     limit_price = LIMIT_PRICE(stock_code)
    #     if limit_price is None:
    #         continue
    #     data = common.GET_STOCK_REAL_DATA_FOR_1D(stock_code)
    #     price_open = float(data["open"]) # 当日开盘价
    #     buy_stack.PUSH(stock_code, price_open)

def S_AUCTION(): # 集合竞价结束后调用(09:25:03)
    if common.TEST_MODE is not True:
        print(f"[S_AUCTION] {common.TIME}")
    position_list.UPDATE()
    order_list.UPDATE()
    trade_list.UPDATE()
    stock_list = sell_stack.GET_STOCK_LIST(TradeStatus.process)
    for stock_code in stock_list:
        volume = position_list.GET_VOLUME(stock_code)
        if volume > 0: #如果还有未出售量，则重新挂单
            order_list.CANCEL_ORDER(stock_code)

# MAIN ################################################################################################

if __name__ == "__main__":
    print(f"TEST MODE [Y/N]", flush = True)
    text = input()
    if text == "Y" or text == "y":
        common.TEST_MODE = True
    else:
        common.TEST_MODE = False
    # 初始化 #####################################################################
    accountID = "80391095" #江海证券
    if runtime.INIT(accountID) is False:
        sys.exit(-1)

    # RUN #######################################################################
    runtime.B_RIGISTER(sectors.GET_SECTOR_2F(), None, B_CALLBACK_1M, B_AUCTION)
    runtime.S_RIGISTER(sectors.GET_SECTOR_2N(), S_CALLBACK_TICK, None, S_AUCTION)
    print(f"启动《2板策略》，祝你好运")
    INIT()
    runtime.RUN()
