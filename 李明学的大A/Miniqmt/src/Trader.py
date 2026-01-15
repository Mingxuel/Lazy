from datetime import datetime
import time
import datetime
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from xtquant import xtdata, xtconstant
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from enum import Enum, IntEnum
from BLTraderCallback import BLTraderCallback
from Common import Common
from Singleton import Singleton
from TraderList import PositionList, OrderList, AssertList, TradeList

DEFAULT_COUNT = 1
DEFAULT_CASH = 50000.0

common = Common()
trade_list = TradeList()
order_list = OrderList()
position_list = PositionList()
assert_list = AssertList()

trade_history ={}
trade_log_file = None

def TOTAL():
    if common.TEST_MODE is not True:
        return
    for year in range(2024, 2026):
        for month in range(1, 13):
            month = str(year) + str(month).zfill(2)
            month_ratio = 1.0
            month_win = 1.0
            win_days = 0
            lose_days = 0
            days = 0
            chart = ""
            for date, ratio in trade_history.items():
                if month in date:
                    month_ratio = month_ratio * (1 + ratio)
                    if ratio > 0:
                        month_win = month_win * (1 + ratio)
                        chart += "+"
                        win_days += 1
                        days += 1
                    elif ratio < 0:
                        lose_days += 1
                        days += 1
                        chart += "-"
                    else:
                        chart += "."

            if abs(month_ratio - 1) > 0.001:
                print(f"{chart}")
                month_win = FORMAT_NUMBER(common.ROUNDOFF((month_win - 1) * 100))
                month_ratio = FORMAT_NUMBER(common.ROUNDOFF((month_ratio - 1) * 100))
                win_ratio = FORMAT_NUMBER(common.ROUNDOFF(win_days / days * 100))
                print(f"[{month}] [{days:<2}]    主赢比: {month_win}%    盈亏比: {month_ratio}%    胜率: {win_ratio}%")

def FORMAT_NUMBER(num):
    output = ""
    if num >= 0:
        output = "+{:06.2f}".format(num)
    else:
        output = "{:07.2f}".format(num)
    if output[1] == "0":
        lst = list(output)
        lst[1] = " "
        output = ''.join(lst)
    if output[1] == " " and output[2] == "0":
        lst = list(output)
        lst[2] = " "
        output = ''.join(lst)
    return output

def LOG(log):
    global trade_log_file
    if trade_log_file is None:
        time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        trade_log_file = f"Log/{time}_{DEFAULT_CASH}_{DEFAULT_COUNT}"
        with open(trade_log_file, "a") as file:
            file.write(f"初始资金:{DEFAULT_CASH}元 仓位:{DEFAULT_COUNT}层仓\n")
    with open(trade_log_file, "a") as file:
        file.write(f"{log}\n")
    print(log)

@Singleton
class Trader:
    def __init__(self):
        self.__userdata = "D:/江海证券QMT实盘_交易/userdata_mini" #数据保存目录
        self.__account = None
        self.__trader = None

    def INIT_TRADER(self, accountID):
        session_id = int(time.time())
        self.__trader = XtQuantTrader(self.__userdata, session_id)
        self.__account = StockAccount(accountID)
        trader_callback = BLTraderCallback()
        self.__trader.register_callback(trader_callback)
        self.__trader.start()
        trade_list.INIT(self.__account, self.__trader)
        order_list.INIT(self.__account, self.__trader)
        position_list.INIT(self.__account, self.__trader)
        assert_list.INIT(self.__account, self.__trader)
        connect_result = self.__trader.connect()
        if connect_result != 0:
            print(f"ERROR:[Connect server failed.]")
            return False
        subscribe_result = self.__trader.subscribe(self.__account)
        if subscribe_result != 0:
            print(f"ERROR:[Subscribe failed.]")
            return False
        return True

# 交易函数 ################################################################################################
    def BUY(self, stock_code, volume, price):
        if common.TEST_MODE is False:
            order = self.__trader.order_stock(self.__account, stock_code, xtconstant.STOCK_BUY, volume, xtconstant.FIX_PRICE, price, "", "")
            return order
        else:
            cash = volume * price
            assert_list.CASH -= cash
            position_list.UPDATE_B(stock_code, volume, price)
            order_list.UPDATE_B(stock_code, volume, price)
            stock_name = common.GET_STOCKNAME(stock_code)
            time = f"{common.TIME[0:4]}-{common.TIME[4:6]}-{common.TIME[6:8]} {common.TIME[8:10]}:{common.TIME[10:12]}:{common.TIME[12:14]}"
            LOG(f"[B] {time} [{common.ROUNDOFF(assert_list.CASH):<12}] {stock_code} {stock_name} {volume:<12} {price}")

    def SELL(self, stock_code, volume, price):
        if common.TEST_MODE is False:
            order = self.__trader.order_stock(self.__account, stock_code, xtconstant.STOCK_SELL, volume, xtconstant.FIX_PRICE, price, "", "")
            return order
        else:
            cash = volume * float(price)
            assert_list.CASH += cash
            position_list.UPDATE_S(stock_code, volume, price)
            order_list.UPDATE_S(stock_code, volume, price)
            stock_name = common.GET_STOCKNAME(stock_code)
            time = f"{common.TIME[0:4]}-{common.TIME[4:6]}-{common.TIME[6:8]} {common.TIME[8:10]}:{common.TIME[10:12]}:{common.TIME[12:14]}"
            LOG(f"[S] {time} [{common.ROUNDOFF(assert_list.CASH):<12}] {stock_code} {stock_name} {volume:<12} {price}")