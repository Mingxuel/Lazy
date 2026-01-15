from datetime import datetime
import time
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from Common import Common, DataType
from BLTraderCallback import BLTraderCallback
from enum import Enum, IntEnum
from Sectors import Sectors
from Trader import Trader, DEFAULT_COUNT, trade_history, TOTAL
from TraderList import TradeList, PositionList, AssertList, OrderList
from Singleton import Singleton

common = Common()
trader = Trader()
trader_list = TradeList()
position_list = PositionList()
assert_list = AssertList()
order_list = OrderList()

# 买卖队列 ###############################################################################################
class TradeStatus(IntEnum):
    process = 1
    done = 2
    keep = 3

class TradeItem:
    def __init__(self):
        self.price = 0.0
        self.volumn = 0
        self.status: TradeStatus = TradeStatus.process

@Singleton
class SellStack:
    def __init__(self):
        self.__stack: dict[str, TradeItem] = {}

    @property
    def STACK(self) -> dict[str, TradeItem]:
        return self.__stack

    def PUSH(self, stock_code, price, status: TradeStatus = TradeStatus.process):
        if stock_code not in self.__stack.keys():
            item = TradeItem()
            item.volumn = 0
            if common.TEST_MODE is True:
                data = common.GET_STOCK_REAL_DATA_FOR_1D(stock_code)
                item.price = common.GET_STOCK_DATA_ITEM(data, DataType.open)
            else:
                item.price = price
            item.status = status
            self.__stack[stock_code] = item
        else:
            self.__stack[stock_code].price = price

    def GET_STOCK_LIST(self, status: TradeStatus):
        stock_list = []
        for stock_code, item in self.__stack.items():
            if item.status == status:
                stock_list.append(stock_code)
        return stock_list

    def UPDATE_STATUS(self, stock_code, status: TradeStatus):
        if stock_code in self.__stack.keys():
            self.__stack[stock_code].status = status

    def UPDATE(self):
        for stock_code, item in self.STACK.items():
            if position_list.IS_SELLED(stock_code):
                item.status = TradeStatus.done
    
    def CLEAR(self):
        self.__stack.clear()

@Singleton
class BuyStack:
    def __init__(self):
        self.__stack: dict[str, TradeItem] = {}

    @property
    def STACK(self) -> dict[str, TradeItem]:
        return self.__stack

    def PUSH(self, stock_code, price, status: TradeStatus = TradeStatus.process):
        if assert_list.BOX_COUNT <= len(self.__stack):
            return
        if stock_code not in self.__stack.keys():
            item = TradeItem()
            item.volumn = self.__CALC_VOLUME(price)
            item.price = price
            item.status = status
            self.__stack[stock_code] = item
        else:
            if self.__stack[stock_code].price > price:
                self.__stack[stock_code].price = price

    def GET_STOCK_LIST(self, status: TradeStatus):
        stock_list = []
        for stock_code, item in self.__stack.items():
            if item.status == status:
                stock_list.append(stock_code)
        return stock_list

    def UPDATE_STATUS(self, stock_code, status: TradeStatus):
        if stock_code in self.__stack.keys():
            self.__stack[stock_code].status = status

    def __CALC_VOLUME(self, price):
        volumn = assert_list.BOX / price
        count = 0
        if volumn < 100:
            count = 1
        else:
            count = int(volumn / 100.0)
            times = (volumn / 10.0) % 10
            if times >= 5:
                count = count + 1
        return count * 100

    def UPDATE(self):
        for stock_code, item in self.STACK.items():
            if position_list.GET_VOLUME(stock_code) == item.volumn:
                item.status = TradeStatus.done

    def CLEAR(self):
        self.__stack.clear()

buy_stack = BuyStack()
sell_stack = SellStack()

# RUNTIME ###############################################################################################
@Singleton
class RunTime:
############################################ 初始函数 #####################################################
    def INIT(self, accountID):
        self.__b_stock_list = []
        self.__s_stock_list = []
        self.b_callback_tick = None
        self.b_callback_1m = None
        self.b_callback_auction = None
        self.s_callback_1m = None
        self.s_callback_tick = None
        self.s_callback_auction = None
        self.__1m = None
        if common.TEST_MODE:
            xtdata.enable_hello = False
        if trader.INIT_TRADER(accountID) is False:
            return False
        return True

    @property
    def B_STOCK_LIST(self):
        return self.__b_stock_list

    @property
    def S_STOCK_LIST(self):
        return self.__s_stock_list

    def B_RIGISTER(self, stock_list, callback_tick, callback_1m, callback_auction):
        self.__b_stock_list = stock_list
        self.b_callback_tick = callback_tick
        self.b_callback_1m = callback_1m
        self.b_callback_auction = callback_auction
        if common.TEST_MODE is False:
            for stock_code in stock_list:
                xtdata.subscribe_quote(stock_code, period = "tick")

    def S_RIGISTER(self, stock_list, callback_tick, callback_1m, callback_auction):
        self.__s_stock_list = stock_list
        self.s_callback_tick = callback_tick
        self.s_callback_1m = callback_1m
        self.s_callback_auction = callback_auction
        if common.TEST_MODE is False:
            for stock_code in stock_list:
                xtdata.subscribe_quote(stock_code, period = "tick")

    def RUN(self):
        if common.TEST_MODE is False:
            xtdata.subscribe_quote("601998.SH", period = "tick", callback=self.RUN_CALLSTACK)
            xtdata.run()
        else:
            common.TEST_MODE = True
            common.TODAY = common.TRADING_DATES[0]
            print(f"# TODAY is {common.TODAY[0:4]}-{common.TODAY[4:6]}-{common.TODAY[6:8]} ##########################")
            for trading_time in common.TRADING_TIMES_1M:
                common.TIME = trading_time
                # 新的一天，调用newday回调函数
                if common.TODAY != trading_time[0:8]:
                    common.TODAY = trading_time[0:8]
                    print("")
                    print(f"# TODAY is {common.TODAY[0:4]}-{common.TODAY[4:6]}-{common.TODAY[6:8]} ##########################")
                    order_list.UPDATE_NEWDAY()
                    position_list.UPDATE_NEWDAY()
                    buy_stack.CLEAR()
                    sell_stack.CLEAR()
                    top_top_data = common.GET_TOP_TOP_DATA()
                    if common.TODAY in top_top_data.keys():
                        self.__b_stock_list = top_top_data[common.TODAY].keys()
                    pre_date = common.PRE_TRADING_DATE(common.TODAY)
                    if pre_date in top_top_data.keys():
                        self.__s_stock_list = top_top_data[pre_date].keys()
                    common.UPDATE_STOCK_DATAS_FOR_1M(self.__b_stock_list, common.TODAY)
                    common.UPDATE_STOCK_DATAS_FOR_1M(self.__s_stock_list, common.TODAY)
                self.RUN_CALLSTACK(None)
            TOTAL()

    def RUN_CALLSTACK(self, stock_code = "601998.SH"):
        call_1m = self.__CALL_1M()
        self.SELL_BEGIN()
        if self.s_callback_tick is not None:
            self.s_callback_tick()
        if call_1m and self.s_callback_1m is not None:
            self.s_callback_1m()
        self.SELL_END()
        self.BUY_BEGIN()
        if self.b_callback_tick is not None:
            self.b_callback_tick()
        if call_1m and self.b_callback_1m is not None:
            self.b_callback_1m()
        self.BUY_END()
        if common.TIME[8:12] == "0925":
            if common.TEST_MODE is not True:
                time.sleep(5)
            if self.s_callback_auction is not None:
                self.s_callback_auction()
            if self.b_callback_auction is not None:
                self.b_callback_auction()
            if common.TEST_MODE is True:
                trade_history[common.TODAY] = (assert_list.CASH - assert_list.PRE_CASH) / assert_list.PRE_CASH                    
                assert_list.PRE_CASH = assert_list.CASH
                assert_list.BOX = assert_list.PRE_CASH / assert_list.BOX_COUNT
                print(f"总金额: {assert_list.CASH}")

    def SELL_BEGIN(self):
        # 更新数据
        position_list.UPDATE()
        order_list.UPDATE()
        trader_list.UPDATE()
        stock_list = sell_stack.GET_STOCK_LIST(TradeStatus.process)
        for stock_code in stock_list:
            if position_list.GET_VOLUME(stock_code) == 0:
                sell_stack.STACK[stock_code].status = TradeStatus.done

    def SELL_END(self):
        if common.IS_AUCTION_TIME(): # 竞价阶段出售
            stock_list = sell_stack.GET_STOCK_LIST(TradeStatus.process)
            for stock_code in stock_list:
                if stock_code in stock_list:
                    can_use_volume = position_list.GET_CAN_USE_VOLUME(stock_code)
                    if can_use_volume > 0: #如果有可卖量就卖
                        trader.SELL(stock_code, can_use_volume, sell_stack.STACK[stock_code].price)
        else:
            stock_list = sell_stack.GET_STOCK_LIST(TradeStatus.process)
            for stock_code in stock_list:
                order_list.CANCEL_ORDER(stock_code)
                position_list.UPDATE()
                can_use_volume = position_list.GET_CAN_USE_VOLUME(stock_code)
                if can_use_volume > 0:
                    trader.SELL(stock_code, can_use_volume, sell_stack.STACK[stock_code].price)

    def BUY_BEGIN(self):
        position_list.UPDATE()
        order_list.UPDATE()
        trader_list.UPDATE()
        stock_list = buy_stack.GET_STOCK_LIST(TradeStatus.process)
        for stock_code in stock_list:
            if position_list.GET_VOLUME(stock_code) == buy_stack.STACK[stock_code].volumn:
                buy_stack.STACK[stock_code].status = TradeStatus.done

    def BUY_END(self):
        stock_list = buy_stack.GET_STOCK_LIST(TradeStatus.process)
        for stock_code in stock_list:
            order_list.CANCEL_ORDER(stock_code)
            position_list.UPDATE()
            volume = position_list.GET_VOLUME(stock_code)
            target_volume = buy_stack.STACK[stock_code].volumn
            if volume < target_volume:
                volume = target_volume - volume
                price = buy_stack.STACK[stock_code].price
                while volume > 0:
                    if assert_list.CASH < (volume * price):
                        volume -= 100
                    else:
                        trader.BUY(stock_code, volume, price)
                        break

    def __CALL_1M(self):
        if self.__1m != common.TIME[10:12]:
            self.__1m = common.TIME[10:12]
            return True
        return False
