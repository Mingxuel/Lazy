from datetime import datetime
import datetime
import time
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from xtquant import xtdata, xtconstant
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from enum import Enum, IntEnum
from Common import Common
from Singleton import Singleton

common = Common()

@Singleton
class AssertList: # 资产信息
    def INIT(self, account, trader):
        self.__account = account
        self.__trader = trader
        self.__cash = 0
        self.__box = 0
        self.__box_count = 0

    #账户资产
    @property
    def __ASSERT(self):
        return self.__trader.query_stock_asset(self.__account)

    #总资产
    @property
    def TOTAL(self):
        return self.__ASSERT.total_asset

    #可用金额
    @property
    def CASH(self):
        if common.TEST_MODE:
            return self.__cash
        return self.__ASSERT.cash
    @CASH.setter
    def CASH(self, value):
        if common.TEST_MODE:
            self.__cash = value

    #可用金额
    @property
    def PRE_CASH(self):
        return self.__pre_cash
    @PRE_CASH.setter
    def PRE_CASH(self, value):
        self.__pre_cash = value

    #持仓市值
    @property
    def MARKET_VALUE(self):
        return self.__ASSERT.market_value

    #每个仓位的可买金额
    @property
    def BOX(self):
        return self.__box
    #每个仓位的可买金额
    @BOX.setter
    def BOX(self, value):
        self.__box = value

    #分仓数量
    @property
    def BOX_COUNT(self):
        return self.__box_count
    @BOX_COUNT.setter
    def BOX_COUNT(self, value):
        self.__box_count = value

# POSITION #########################################################################################
class PositionItem:
    def __init__(self):
        self.stock_code = None
        self.volume = None
        self.yesterday_volume = None
        self.can_use_volume = None
        self.frozen_volume = None
        self.market_value = None

@Singleton
class PositionList: # 持仓信息
    def INIT(self, account, trader):
        self.__account = account
        self.__trader = trader
        self.__positions: dict[str, PositionItem] = {}

    def UPDATE(self):
        if common.TEST_MODE is True:
            return
        positions = self.__trader.query_stock_positions(self.__account)
        self.__positions.clear()
        for position in positions:
            item = PositionItem()
            item.stock_code = position.stock_code
            item.volume = position.volume
            item.yesterday_volume = position.yesterday_volume
            item.can_use_volume = position.can_use_volume
            item.frozen_volume = position.frozen_volume
            item.market_value = position.market_value
            self.__positions[position.stock_code] = item

    def GET_CAN_SELL_STOCK_LIST(self):
        stock_list = []
        for stock_code, position in self.__positions.items():
            if int(position.yesterday_volume) > 0 and int(position.volume) > 0:
                stock_list.append(stock_code)
        return stock_list

    def IS_SELLED(self, stock_code):
        for pstock_code, position in self.__positions.items():
            if pstock_code == stock_code and int(position.volume) == 0:
                return True
        return False

    def GET_CAN_USE_VOLUME(self, stock_code):
        if stock_code not in self.__positions.keys():
            return 0
        return int(self.__positions[stock_code].can_use_volume)
    
    def GET_FROZEN_VOLUME(self, stock_code):
        if stock_code not in self.__positions.keys():
            return 0
        return int(self.__positions[stock_code].frozen_volume)

    def GET_VOLUME(self, stock_code):
        if stock_code not in self.__positions.keys():
            return 0
        return int(self.__positions[stock_code].volume)

    def GET_MARKET_VALUE(self, stock_code):
        if stock_code not in self.__positions.keys():
            return 0
        return self.__positions[stock_code].market_value

    def UPDATE_B(self, stock_code, volume, price):
        if common.TEST_MODE is not True:
            return
        item = PositionItem()
        item.stock_code = stock_code
        item.volume = volume
        item.yesterday_volume = 0
        item.can_use_volume = 0
        item.frozen_volume = volume
        item.market_value = volume * price
        self.__positions[stock_code] = item

    def UPDATE_S(self, stock_code, volume, price):
        if common.TEST_MODE is not True:
            return
        if stock_code not in self.__positions.keys():
            return
        position = self.__positions[stock_code]
        position.volume = position.volume - volume
        position.market_value = position.volume * price
        position.can_use_volume = position.volume

    def UPDATE_NEWDAY(self):
        if common.TEST_MODE is not True:
            return
        positions = {}
        for stock_code, position in self.__positions.items():
            if position.yesterday_volume > 0:
                continue
            else:
                position.can_use_volume = position.volume
                position.frozen_volume = 0
                position.yesterday_volume = position.volume
                positions[stock_code] = position
        self.__positions = positions

    def OUTPUT(self, termminal = False):
        config_file = f"Config/交易数据/持仓列表"
        with open(config_file, "w") as file:
            file.write(f"stock_code   volume     can_use_volume\n")
            if termminal is True:
                print(f"stock_code   volume     can_use_volume\n")
            for item in self.__positions.values():
                file.write(f"{item.stock_code:<12} {item.volume:<10} {item.can_use_volume:<10}\n")
                if termminal is True:
                    print(f"{item.stock_code:<12} {item.volume:<10} {item.can_use_volume:<10}\n")

# TRADE #########################################################################################
class TradeList(IntEnum):
    STOCK_BUY = 23
    STOCK_SELL = 24

class TradeItem:
    def __init__(self):
        self.stock_code = None
        self.order_type = None
        self.traded_volume = None

@Singleton
class TradeList: # 交易信息
    def INIT(self, account, trader):
        self.__account = account
        self.__trader = trader
        self.__trades = []

    def UPDATE(self):
        if common.TEST_MODE is True:
            return
        trades = self.__trader.query_stock_trades(self.__account)
        self.__trades.clear()
        for trade in trades:
            item = PositionItem()
            item.stock_code = trade.stock_code
            item.order_type = trade.order_type
            item.traded_volume = trade.traded_volume
            self.__trades.append(item)

# ORDER #########################################################################################
class OrderStatus(IntEnum):
    ORDER_UNREPORTED = 48	    # 未报
    ORDER_WAIT_REPORTING = 49   # 待报
    ORDER_REPORTED = 50	        # 已报
    ORDER_REPORTED_CANCEL = 51	# 已报待撤
    ORDER_PARTSUCC_CANCEL = 52	# 部成待撤
    ORDER_PART_CANCEL = 53	    # 部撤（已经有一部分成交，剩下的已经撤单）
    ORDER_CANCELED = 54	        # 已撤
    ORDER_PART_SUCC = 55	    # 部成（已经有一部分成交，剩下的待成交）
    ORDER_SUCCEEDED = 56	    # 已成
    ORDER_JUNK = 57             # 废单
    ORDER_UNKNOWN = 255	        # 未知

class OrderItem:
    def __init__(self):
        self.order_id = None
        self.order_time = None
        self.order_status = None
        self.stock_code = None
        self.order_volume = None
        self.traded_volume = None
        self.price = None

@Singleton
class OrderList: # 委托信息
    def INIT(self, account, trader):
        self.__account = account
        self.__trader = trader
        self.__orders = []

    def CANCEL_ORDER(self, stock_code):
        if common.TEST_MODE:
            return
        for order in self.__orders:
            if stock_code == order.stock_code:
                self.__trader.cancel_order_stock(self.__account, int(order.order_id))

    def EXIST(self, stock_code):
        for order in self.__orders:
            if stock_code == order.stock_code:
                return True
        return False

    def UPDATE(self):
        if common.TEST_MODE is True:
            return
        orders = self.__trader.query_stock_orders(self.__account)
        self.__orders.clear()
        for order in orders:
            item = OrderItem()
            item.order_id = order.order_id
            item.order_time = datetime.datetime.fromtimestamp(order.order_time).strftime("%Y%m%d%H%M%S")
            item.order_status = order.order_status
            item.stock_code = order.stock_code
            item.order_volume = order.order_volume
            item.traded_volume = order.traded_volume
            item.price = order.price
            self.__orders.append(item)

    def UPDATE_B(self, stock_code, volume, price):
        if common.TEST_MODE is not True:
            return
        item = OrderItem()
        item.order_id = 0
        item.order_time = ""
        item.order_status = 0
        item.stock_code = stock_code
        item.order_volume = volume
        item.traded_volume = volume
        item.price = price
        self.__orders.append(item)

    def UPDATE_S(self, stock_code, volume, price):
        if common.TEST_MODE is not True:
            return
        item = OrderItem()
        item.order_id = 0
        item.order_time = ""
        item.order_status = 0
        item.stock_code = stock_code
        item.order_volume = volume
        item.traded_volume = volume
        item.price = price
        self.__orders.append(item)

    def UPDATE_NEWDAY(self):
        self.__orders.clear()

    def OUTPUT(self, termminal = False):
        config_file = f"Config/交易数据/订单列表"
        with open(config_file, "w") as file:
            file.write(f"id         time           status stock_code order_volume traded_volume price\n")
            if termminal is True:
                print(f"id         time           status stock_code order_volume traded_volume price\n")
            for item in self.__orders.values():
                file.write(f"{item.order_id:<10} {item.order_time} {item.order_status:<6} {item.stock_code:<10} {item.order_volume:<12} {item.traded_volume:<13} {item.price}\n")
                if termminal is True:
                    print(f"{item.order_id:<10} {item.order_time} {item.order_status:<6} {item.stock_code:<10} {item.order_volume:<12} {item.traded_volume:<13} {item.price}\n")
