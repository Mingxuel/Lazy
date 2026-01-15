from datetime import datetime
import sys
import os
import time
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from Common import Common, DataType, DayFieldType
from BLTraderCallback import BLTraderCallback
from enum import Enum, IntEnum
from Sectors import Sectors
from Trader import Trader, DEFAULT_COUNT, trade_history, TOTAL
from TraderList import TradeList, PositionList, AssertList, OrderList
from Singleton import Singleton

common = Common()
callback_stock_code = ""
stock_list = []

def GET_ROOT_PATH():
    current_path = os.path.abspath(__file__)
    keyword = "李明学的大A"
    index = current_path.find(keyword)
    return current_path[:index + len(keyword)]

def  CALLSTACK(data):
    if callback_stock_code in data:
        print("CALLSTACK IN")
        file_runtime = GET_ROOT_PATH() + "/Data/Runtime"
        today = datetime.now().strftime("%Y%m%d")
        for stock_code in stock_list:
            xtdata.subscribe_quote(stock_code, "1d", "", today, 1)
        datas = xtdata.get_market_data_ex([], stock_list, "1d", "", today, 1, fill_data=False)

        origin_data = []
        with open(file_runtime, 'r') as f:
            print("CALLSTACK Read file")
            origin_data = f.readlines()
            str_stock_list = ""
            for data in origin_data:
                str_stock_list += data.split(" ")[0]
            print(str_stock_list)

        with open(file_runtime, 'w') as f:
            for stock_code in stock_list:
                data = datas[stock_code].iloc[0]
                record = "{} {} {:.2f} {:.2f} {:.2f} {:.2f} {:.2f} {:.2f} {:.2f} {:.2f}".format(stock_code,
                                    data.iloc[DayFieldType.time.value],
                                    data.iloc[DayFieldType.open.value],
                                    data.iloc[DayFieldType.high.value],
                                    data.iloc[DayFieldType.low.value],
                                    data.iloc[DayFieldType.close.value],
                                    data.iloc[DayFieldType.volume.value],
                                    data.iloc[DayFieldType.amount.value],
                                    data.iloc[DayFieldType.settelementPrice.value],
                                    data.iloc[DayFieldType.openInterest.value])
                included = False
                for i, line in enumerate(origin_data):
                    if line.strip().startswith(stock_code):
                        origin_data[i] = record
                        included = True
                        break
                if not included:
                    origin_data.append(record)
            for line in origin_data:
                if len(line) > 50 and line[6:9] == ".SZ" or line[6:9] == ".SH":
                    print(line.strip() + "\n")
                    f.write(line.strip() + "\n")
        print("CALLSTACK OUT")
 
if __name__ == "__main__":
    args = sys.argv
    stock_list =  args[1].split('|')
    callback_stock_code = stock_list[0]

    xtdata.enable_hello = False
    accountID = "80391095" #江海证券
    userdata = "C:/江海证券QMT实盘_交易/userdata_mini" #数据保存目录
    session_id = int(time.time())
    account = StockAccount(accountID)

    for stock_code in stock_list:
        xtdata.subscribe_quote(stock_code, period = "tick", callback = CALLSTACK)

    xtdata.run()
