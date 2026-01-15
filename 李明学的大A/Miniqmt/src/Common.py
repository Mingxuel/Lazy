from datetime import datetime
import time
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from xtquant import xtdata, xtconstant
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from enum import Enum, IntEnum
from BLTraderCallback import BLTraderCallback
from Singleton import Singleton
import datetime
import os, sys

class DataType(Enum):
    open = 1
    amount = 2
    askPrice = 3
    askVol = 4
    bidPrice = 5
    bidVol = 6
    close = 7
    lastPrice = 8
    low = 9
    time = 10
    preClose = 11
    high = 12

class DataTickType(Enum):
    time = 0
    lastPrice = 1
    open = 2
    high = 3
    low = 4
    lastClose = 5
    amount = 6
    volume = 7
    pvolume = 8
    tickvol = 9
    stockStatus = 10
    openInt = 11
    lastSettlementPrice = 12
    askPrice = 13
    bidPrice = 14
    askVol = 15
    bidVol = 16
    settlementPrice = 17
    transactionNum = 18
    pe = 19

class DayFieldType(Enum):
    time = 0
    open = 1
    high = 2
    low = 3
    close = 4
    volume = 5
    amount = 6
    settelementPrice = 7
    openInterest = 8
    preClose = 9
    suspendFlag = 10

class MAType(IntEnum):
    ma5 = 5
    ma10 = 10
    ma20 = 20
    ma30 = 30
    ma60 = 60

class LimitType(IntEnum):
    Top = 1
    Bottom = 2

UPDATE_COUNT = 3

@Singleton
class Common:
    def __init__(self):
        self.__test_mode = False
        self.__test_mode_today = ""
        self.__test_mode_time = ""
        self.__top_data = {}
        self.__top_top_data = {}
        self.__bottom_data = {}
        self.__trading_dates = []
        self.__trading_times = []
        self.__stock_datas_for_1d = {}
        self.__stock_datas_for_1m = {}
        self.__whole_stocks = []
        self.__main_stocks = []
        self.__market_datas_for_1d = {}
        self.__market_datas_for_1m = {}

    @property
    def TEST_MODE(self):
        return self.__test_mode
    @TEST_MODE.setter
    def TEST_MODE(self, value):
        self.__test_mode = value

# 日期相关函数 ################################################################################################

    # 当前时间"年月日"
    @property
    def TODAY(self):
        if self.TEST_MODE == True:
            return self.__test_mode_today
        return datetime.datetime.now().strftime("%Y%m%d")
    @TODAY.setter
    def TODAY(self, value):
        if self.TEST_MODE == True:
            self.__test_mode_today = value

    # 当前时间"年月日时分秒"
    @property
    def TIME(self):
        if self.TEST_MODE == True:
            return self.__test_mode_time
        return time.strftime('%Y%m%d%H%M%S', time.localtime())
    @TIME.setter
    def TIME(self, value):
        if self.TEST_MODE == True:
            self.__test_mode_time = value

    def IS_AUCTION_TIME(self):
        if self.TIME[8:14] >= "091500" and self.TIME[8:14] <= "092500":
            return True
        return False

    # 最近一个交易日
    # 若今天是交易日，返回今日
    def LAST_TRADING_DATE(self, date):
        if self.IS_TRADING_DATE_TODAY():
            return date
        else:
            return self.TRADING_DATES[-1]

    # 上第N个交易日
    # 非交易时间使用
    def PRE_TRADING_DATE(self, date, day = 1):
        dates = self.TRADING_DATES
        if date not in dates:
            return None
        index = dates.index(date)
        if index - day < 0:
            return None
        return dates[index - day]

    # 下第N个交易日
    # 非交易时间使用
    def NEXT_TRADING_DATE(self, date, day = 1):
        dates = self.TRADING_DATES
        if date not in dates:
            return None
        index = dates.index(date)
        if index + day >= len(dates):
            return None
        return dates[index + day]

    @property
    def TRADING_DATES(self):
        if len(self.__trading_dates) == 0:
            config_file = "Config/交易日"
            with open(config_file, 'r') as file:
                for line in file:
                    self.__trading_dates.append(line.strip())
        return self.__trading_dates

    def UPDATE_TRADING_DATES(self):
        start_date = "20240601"
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        trading_dates = xtdata.get_trading_dates('SH', start_date, end_date)
        count = 0
        config_file = "Config/交易日"
        with open(config_file, 'w') as file:
            for date in trading_dates:
                date = datetime.datetime.fromtimestamp(date/1000).strftime("%Y%m%d")
                file.write(f"{date}\n")
                count += 1
        self.__trading_dates.clear()
        return count

    @property
    def TRADING_TIMES_1M(self):
        if len(self.__trading_times) == 0:
            config_file = "Config/交易时间"
            with open(config_file, 'r') as file:
                for line in file:
                    self.__trading_times.append(line.strip())
        return self.__trading_times

    def UPDATE_TRADING_TIMES_1M(self):
        trading_times = []
        hour = 9
        for trading_date in self.TRADING_DATES:
            for hour in range(9, 16):
                if hour == 9:
                    for minute in range(15, 60):
                        trading_times.append(f"{trading_date}{hour:02d}{minute:02d}00")
                elif hour == 10 or hour == 13 or hour == 14:
                    for minute in range(0, 60):
                        trading_times.append(f"{trading_date}{hour:02d}{minute:02d}00")
                elif hour == 11:
                    for minute in range(0, 31):
                        trading_times.append(f"{trading_date}{hour:02d}{minute:02d}00")
                elif hour == 15:
                    trading_times.append(f"{trading_date}{hour:02d}0000")
        config_file = "Config/交易时间"
        count = 0
        with open(config_file, 'w') as file:
            for time in trading_times:
                file.write(f"{time}\n")
                count += 1
        self.__trading_times.clear()
        return count

    # 今日是否为交易日
    def IS_TRADING_DATE_TODAY(self):
        today = self.TODAY
        trading_dates = xtdata.get_trading_dates('SH', "", today, 1)
        last_trading_date = datetime.datetime.fromtimestamp(trading_dates[0]/1000).strftime("%Y%m%d")
        if today == last_trading_date:
            return True
        return False

    # 是否为交易日
    def IS_TRADING_DATE(self, stock_code, date):
        data = self.GET_STOCK_DATAS_FOR_1D(stock_code)
        if data is None:
            return None
        if date in data.index:
            return True
        return False

    def LAST_TRADING_DAY_FOR_STOCK(self, stock_code):
        all_data = self.GET_STOCK_DATAS_FOR_1D(stock_code)
        if all_data is None:
            return None
        return all_data.index[-1]

    # 上第N个交易日
    # 非交易时间使用
    def PRE_TRADING_DATE_FOR_STOCK(self, stock_code, date, day = 1):
        index = 0
        if self.TEST_MODE is False and self.TODAY == date:
            last_trading_date = self.LAST_TRADING_DAY_FOR_STOCK(stock_code)
            data = self.GET_STOCK_DATAS_FOR_1D(stock_code)
            index = data.index.tolist().index(last_trading_date)
            day -= 1
        else:
            if self.IS_TRADING_DATE(stock_code, date) is not True:
                return None
            data = self.GET_STOCK_DATAS_FOR_1D(stock_code)
            index = data.index.tolist().index(date)
        if (index - day) < 0:
            return None
        return data.index[index - day]

    # 下第N个交易日
    # 非交易时间使用
    def NEXT_TRADING_DAY_FOR_STOCK(self, stock_code, date, day = 1):
        if self.IS_TRADING_DATE(stock_code, date) is not True:
            return None
        data = self.GET_STOCK_DATAS_FOR_1D(stock_code)
        index = data.index.tolist().index(date)
        if (index + day) >= len(data.index):
            return None
        return data.index[index + day]

    # 当前是否为交易时间
    def IS_MARKET_TIME(self):
        time = self.TIME[8:14]
        if time >= "091500" and time <= "150000":
            return True
        return False

# 获取代码函数 ################################################################################################
    @property
    def WHOLE_STOCKS(self):
        if len(self.__whole_stocks) == 0:
            self.__whole_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        return self.__whole_stocks

    @property
    def MAIN_STOCKS(self):
        if len(self.__main_stocks) == 0:
            config_file = "Config/主板代码"
            with open(config_file, 'r') as file:
                for line in file:
                    self.__main_stocks.append(line.strip())            
        return self.__main_stocks

# 获取常规函数 ################################################################################################

    # 获取代码名称
    def GET_STOCKNAME(self, stock_code):
        data = xtdata.get_instrument_detail(stock_code)
        if not data:
            return None
        return data["InstrumentName"]

    # 是否为st
    def IS_ST(self, stock_code):
        stock_name = self.GET_STOCKNAME(stock_code)
        if stock_name is None:
            return None
        if "ST" in stock_name or "*ST" in stock_name:
            return True
        return False

    # 获取全代码
    def GET_FULLCODE(self, code):
        if code.startswith("60"):
            return code + ".SH"
        if code.startswith("00"):
            return code + ".SZ"

    def CONVERT_FILE_TO_DATAFRAME(self, config_file):
        if os.path.exists(config_file) is not True:
            return None
        with open(config_file, 'r') as file:
            fields = file.readline().strip().split(" ")
            dates = []
            matrix = []
            for line in file:
                dates.append(line.split(" ")[0])
                data = line.strip(" \n").split(" ")
                while len(data) != 11:
                    data.append("0")
                matrix.append(data)
            return pd.DataFrame(matrix, index = dates, columns = fields)

# 获取1D数据 ####################################################################################################
    # 1D所有历史数据
    # 1D数据总量比较小，因此把所有数据都导入进来也不是问题
    def GET_STOCK_DATAS_FOR_1D(self, stock_code):
        if len(self.__stock_datas_for_1d) == 0:
            for stock_code in self.MAIN_STOCKS:
                self.__stock_datas_for_1d[stock_code] = self.CONVERT_FILE_TO_DATAFRAME(f"Config/Data/1D/{stock_code}")
        if stock_code not in self.__stock_datas_for_1d:
            self.__stock_datas_for_1d[stock_code] = self.CONVERT_FILE_TO_DATAFRAME(f"Config/Data/1D/{stock_code}")
        return self.__stock_datas_for_1d[stock_code]

    def RESET_STOCKS_DATAS_FOR_1D(self):
        self.__stock_datas_for_1d.clear()

    # 获取代码的单日数据
    def GET_STOCK_DATA_FOR_1D(self, stock_code, date):
        if self.IS_TRADING_DATE(stock_code, date) is False:
            return None
        data = self.GET_STOCK_DATAS_FOR_1D(stock_code)
        if data is None:
            return None
        return data.loc[date]

# 获取1M数据 ####################################################################################################
    # 所有1M数据
    # 具体数据是按需加载的
    def GET_STOCK_DATAS_FOR_1M(self):
        if len(self.__stock_datas_for_1m) == 0:
            self.UPDATE_STOCK_DATAS_FOR_1M()
        return self.__stock_datas_for_1m

    def RESET_STOCK_DATAS_FOR_1M(self):
        self.__stock_datas_for_1m.clear()

    # 1M数据实在是太大了，因此为了避免大量数据的载入，根据每次提供的stock_list进行数据切换
    # 加载新的stock_list数据，卸载旧的stock_list数据
    def UPDATE_STOCK_DATAS_FOR_1M(self, stock_list = [], date = None):
        # 首次时更新所有数据
        if len(self.__stock_datas_for_1m) == 0:
            for stock_code in self.MAIN_STOCKS:
                stock_datas = {}
                for trading_date in self.TRADING_DATES:
                    config_file = f"Config/Data/1M/{stock_code}/{trading_date}"
                    if os.path.exists(config_file) is not True:
                        stock_datas[trading_date] = None
                        continue
                    stock_datas[trading_date] = config_file
                self.__stock_datas_for_1m[stock_code] = stock_datas
        # 加载新数据
        for stock_code in stock_list:
            if stock_code not in self.__stock_datas_for_1m:
                stock_datas = {}
                for trading_date in self.TRADING_DATES:
                    config_file = f"Config/Data/1M/{stock_code}/{trading_date}"
                    if os.path.exists(config_file) is not True:
                        stock_datas[trading_date] = None
                        continue
                    stock_datas[trading_date] = config_file
                self.__stock_datas_for_1m[stock_code] = stock_datas
            self.__stock_datas_for_1m[stock_code][date] = self.CONVERT_FILE_TO_DATAFRAME(f"Config/Data/1M/{stock_code}/{date}")

# 获取实时数据 ####################################################################################################
    # 获取代码的实1M数据
    def GET_STOCK_REAL_DATA_FOR_1D(self, stock_code):
        if self.TEST_MODE == False:
            if self.IS_TRADING_DATE_TODAY() is False or self.IS_MARKET_TIME() is False:
                return None
            today = self.TODAY
            stock_list = [stock_code]
            xtdata.subscribe_quote(stock_code, "1d", "", today, 1)
            data = xtdata.get_market_data_ex([], stock_list, "1d", "", today, 1, fill_data=False)[stock_code]
            if len(data) == 0:
                return None
            return data.iloc[0]
        else:
            data = self.GET_STOCK_DATAS_FOR_1D(stock_code)
            if self.TODAY not in data.index:
                return None
            return self.GET_STOCK_DATAS_FOR_1D(stock_code).loc[self.TODAY]

    # 获取代码的实1M数据
    def GET_STOCK_REAL_DATA_FOR_1M(self, stock_code):
        if self.TEST_MODE == False:
            if self.IS_TRADING_DATE_TODAY() is False or self.IS_MARKET_TIME() is False:
                return None
            today = self.TODAY
            stock_list = [stock_code]
            xtdata.subscribe_quote(stock_code, "1m", "", today, 1)
            data = xtdata.get_market_data_ex([], stock_list, "1m", "", today, 1, fill_data=False)[stock_code]
            if len(data) == 0:
                return None
            return data.iloc[0]
        else:
            data = self.GET_STOCK_DATAS_FOR_1M()[stock_code][self.TODAY]
            if data is None:
                return None
            if self.TIME not in data.index:
                return None
            return self.GET_STOCK_DATAS_FOR_1M()[stock_code][self.TODAY].loc[self.TIME]      

    # 获取代码的实时秒数据
    # 暂时不支持测试数据的获取
    def GET_STOCK_REAL_DATA_FOR_TICK(self, stock_code):
        if self.IS_TRADING_DATE_TODAY() is False or self.IS_MARKET_TIME() is False:
            return None
        today = self.TODAY
        stock_list = [stock_code]
        xtdata.subscribe_quote(stock_code, "tick", "", today, 1)
        data = xtdata.get_market_data_ex([], stock_list, "tick", "", today, 1, fill_data=False)[stock_code]
        if len(data) == 0:
            return None
        return data.iloc[0]

# 获取最新全市场数据 ####################################################################################################
    # 获取全市场1D数据
    def GET_MARKET_DATAS_FOR_1D(self, count = -1):
        if len(self.__market_datas_for_1d) == 0:
            stock_list = self.MAIN_STOCKS
            xtdata.subscribe_whole_quote(stock_list)
            self.__market_datas_for_1d = xtdata.get_market_data_ex([], stock_list, "1d", self.TRADING_DATES[0], self.TRADING_DATES[-1], count, fill_data=False)
        return self.__market_datas_for_1d

    def RESET_MARKET_DATAS_FOR_1D(self):
        self.__market_datas_for_1d.clear()

    # 获取全市场1M数据，仅获取3天的数据量
    def GET_MARKET_DATAS_FOR_1M(self, count = -1, start_date = None, end_date = None):
        if len(self.__market_datas_for_1m) == 0:
            stock_list = self.MAIN_STOCKS
            xtdata.subscribe_whole_quote(stock_list)
            if start_date is None:
                start_date = self.TRADING_DATES[0] + "091500"
            else:
                start_date = start_date + "091500"
            if end_date is None:
                end_date = self.TRADING_DATES[-1] + "150000"
            else:
                end_date = end_date + "150000"
            self.__market_datas_for_1m = xtdata.get_market_data_ex([], stock_list, "1m", start_date, end_date, count = count, fill_data=False)
        return self.__market_datas_for_1m

    def RESET_MARKET_DATAS_FOR_1M(self):
        self.__market_datas_for_1m.clear()

    # 获取单数据
    def GET_STOCK_DATA_ITEM(self, data, type: DataType):
        return data[type.value]

# MA系列函数 ################################################################################################
    # 获取历史实际的MA数据
    def MA_ACTUAL(self, stock_code, date, count: MAType, is_roundoff = True):
        all_data = self.GET_STOCK_DATAS_FOR_1D(stock_code)
        if all_data is None:
            return None
        if date not in all_data.index:
            return None
        date_index = 0
        for i, i_date in enumerate(all_data.index):
            if i_date == date:
                date_index = i
                break
        total_price = 0.0
        for i in range(date_index - count + 1, date_index + 1):
            total_price += float(all_data.iloc[i]["close"])
        if is_roundoff is True:
            return self.ROUNDOFF(total_price / count)
        return total_price / count

    # 实时的当日MA价
    def MA_REAL_FOR_1M(self, stock_code, count: MAType):
        if self.IS_TRADING_DATE_TODAY() is False or self.IS_MARKET_TIME() is False: #确保是交易时间段
            return None
        if self.TEST_MODE is False:
            stock_list = [stock_code]
            xtdata.subscribe_quote(stock_code, "1d", "", self.TODAY)
            data = xtdata.get_market_data_ex(["close"], stock_list, "1d", "", self.TODAY, count, fill_data = False)[stock_code]
            if len(data) != count:
                return None
            return data["close"].mean()
        else:
            # 当日的最新价
            data = self.GET_STOCK_REAL_DATA_FOR_1M(stock_code)
            if data is None:
                return None
            total_price = float(data["close"])
            # (count-1)天的总价
            for i in range(1, count):
                history_date = self.PRE_TRADING_DATE_FOR_STOCK(stock_code, self.TODAY, i)
                if history_date is None:
                    return None
                total_price += float(self.GET_STOCK_DATAS_FOR_1D(stock_code).loc[history_date]["close"])
            return self.ROUNDOFF(total_price / count)

    def MA_REAL_EXPECT_FOR_1M(self, stock_code, count: MAType):
        if self.IS_TRADING_DATE_TODAY() is False or self.IS_MARKET_TIME() is False: #确保是交易时间段
            return None
        # 最新价
        data = self.GET_STOCK_REAL_DATA_FOR_1M(stock_code)
        if data is None:
            return None
        total_price = float(data["close"])
        # 明日涨停价
        total_price += float(self.LIMIT_PRICE(stock_code, LimitType.Top, total_price))
        # (count-2)天的总价
        for i in range(1, count - 1):
            history_date = self.PRE_TRADING_DATE_FOR_STOCK(stock_code, self.TODAY, i)
            if history_date is None:
                return None
            total_price += float(self.GET_STOCK_DATAS_FOR_1D(stock_code).loc[history_date]["close"])
        return self.ROUNDOFF(total_price / count)

    def MA_REAL_EXPECT_FOR_1M_2(self, stock_code):
        if self.IS_TRADING_DATE_TODAY() is False or self.IS_MARKET_TIME() is False: #确保是交易时间段
            return None
        # 最新价
        data = self.GET_STOCK_REAL_DATA_FOR_1M(stock_code)
        if data is None:
            return None
        pre_date = self.PRE_TRADING_DATE_FOR_STOCK(stock_code, self.TODAY)
        return self.GET_TOP_TOP_PRICE(stock_code, pre_date)

    def MA_EXPECT_PRICE(self, stock_code, count: MAType, date):
        if self.IS_TRADING_DATE(stock_code, date) is not True:
            return None
        total_price = 0.0
        # (count - 2)日的总价
        for i in range(0, count - 2):
            history_date = self.PRE_TRADING_DATE_FOR_STOCK(stock_code, date, i)
            if history_date is None:
                return None
            total_price += float(self.GET_STOCK_DATAS_FOR_1D(stock_code).loc[history_date]["close"])
        # 获取最高价和最低价
        price = float(self.GET_STOCK_DATAS_FOR_1D(stock_code).loc[date]["close"])
        price_top = self.LIMIT_PRICE(stock_code, LimitType.Top, price)
        price_bottom = self.LIMIT_PRICE(stock_code, LimitType.Bottom, price)
        price_temp = price_top
        while price_temp >= price_bottom:
            price_top_temp = self.LIMIT_PRICE(stock_code, LimitType.Top, price_temp)
            ma = self.ROUNDOFF((total_price + price_temp + price_top_temp) / count)
            if price_temp <= ma:
                return self.ROUNDOFF(price_temp)
            price_temp = self.ROUNDOFF(price_temp - 0.01)
        return None

# 涨跌停系列函数 ################################################################################################
    def IS_2A(self, stock_code, date):
        if self.IS_TRADING_DATE(stock_code, date) is not True:
            return False
        date_1 = self.PRE_TRADING_DATE_FOR_STOCK(stock_code, date, 2)
        if date_1 is None:
            return False
        date_2 = self.PRE_TRADING_DATE_FOR_STOCK(stock_code, date, 1)
        if date_2 is None:
            return False
        if self.IS_TOP(stock_code, date_1) == False and self.IS_TOP(stock_code, date_2) == True and self.IS_TOP(stock_code, date) == True:
            return True
        return False

    def IS_2F(self, stock_code, date):
        if self.IS_2A(stock_code, date) is not True:
            return False
        date_1 = self.PRE_TRADING_DATE_FOR_STOCK(stock_code, date, 1)
        if date_1 is None:
            return False
        data = self.GET_STOCK_DATA_FOR_1D(stock_code, date_1)
        if data is None:
            return False
        vol_1 = data["volume"]
        data = self.GET_STOCK_DATA_FOR_1D(stock_code, date)
        if data is None:
            return False
        vol_0 = data["volume"]
        if float(vol_1) < float(vol_0):
            return True
        return False

    def IS_2N(self, stock_code, date):
        if self.IS_TRADING_DATE(stock_code, date) is not True:
            return False
        #DAY-0开板
        data = self.GET_STOCK_DATA_FOR_1D(stock_code, date)
        if data is None:
            return False
        price_low = self.GET_STOCK_DATA_ITEM(data, DataType.low)
        price_high = self.GET_STOCK_DATA_ITEM(data, DataType.high)
        if price_low == price_high:
            return False
        #2连板
        pre_date = self.PRE_TRADING_DATE_FOR_STOCK(stock_code, date, 1)
        if self.IS_2A(stock_code, pre_date) is not True:
            return False
        return True

    def LAST_TOP_DATE(self, stock_code):
        last_trading_day = self.LAST_TRADING_DAY_FOR_STOCK(stock_code)
        for i in range(0, 7):
            pre_date = self.PRE_TRADING_DATE_FOR_STOCK(stock_code, last_trading_day, i)
            if pre_date is None:
                return None
            if self.IS_TOP(stock_code, pre_date) is True:
                return pre_date
        return None

    def GET_TOP_DATA(self):
        if len(self.__top_data) == 0:
            top_files = os.listdir('Config/Top')
            for top_file in top_files:
                file_list = []
                file_name = f"Config/Top/{top_file}"
                with open(file_name, "r") as file:
                    for line in file:
                        file_list.append(line.strip())
                self.__top_data[top_file] = file_list
        return self.__top_data

    def RESET_TOP_DATA(self):
        self.__top_data.clear()

    def GET_BOTTOM_DATA(self):
        if len(self.__bottom_data) == 0:
            bottom_files = os.listdir('Config/Bottom')
            for bottom_file in bottom_files:
                file_list = []
                file_name = f"Config/Bottom/{bottom_file}"
                with open(file_name, "r") as file:
                    for line in file:
                        file_list.append(line.strip())
                self.__bottom_data[bottom_file] = file_list
        return self.__bottom_data

    def RESET_BOTTOM_DATA(self):
        self.__bottom_data.clear()

    def GET_TOP_TOP_DATA(self):
        if len(self.__top_top_data) == 0:
            self.__top_top_data = {}
            config_file = f"Config/TOP_TOP"
            with open(config_file, 'r') as file:
                for line in file:
                    date = line.strip().split(" ")[0]
                    stock_code = line.strip().split(" ")[1]
                    price = line.strip().split(" ")[2]
                    if date not in self.__top_top_data.keys():
                        data = {}
                        self.__top_top_data[date] = data
                    self.__top_top_data[date][stock_code] = price
        return self.__top_top_data

    def RESET_TOP_TOP_DATA(self):
        self.__top_top_data.clear()

    def GET_TOP_TOP_PRICE(self, stock_code, date):
        if date not in self.__top_top_data.keys():
            return None
        if stock_code not in self.__top_top_data[date].keys():
            return None
        return self.__top_top_data[date][stock_code]

    def IS_TOP(self, stock_code, date = None):
        if date is None: #默认None表示今日，
            data = self.GET_STOCK_REAL_DATA_FOR_TICK(stock_code)
            if data is None:
                print(f"Common::IS_TOP")
                print(f"ERROR:[Get data failed.]")
                return None
            price = data["close"].iloc[-1]
            price_top = self.PRICE_TOP(stock_code, data)
            return abs(price - price_top) < 0.001
        else: #历史
            if date in self.GET_TOP_DATA() and stock_code in self.GET_TOP_DATA()[date]:
                return True
            return False

    def IS_BOTTOM(self, stock_code, date = None):
        if date is None: #默认None表示今日，
            data = self.GET_STOCK_REAL_DATA_FOR_TICK(stock_code)
            if data is None:
                print(f"Common::IS_BOTTOM")
                print(f"ERROR:[Get data failed.]")
                return None
            price = data["close"].iloc[-1]
            price_top = self.PRICE_BOTTOM(stock_code, data)
            return abs(price - price_top) < 0.001
        else: #历史
            if date in self.GET_BOTTOM_DATA() and stock_code in self.GET_BOTTOM_DATA()[date]:
                return True
            return False

    """
    HOW TO USE?
    涨停价
    """
    def PRICE_TOP(self, stock_code, data):
        return self.__PRICE_LIMIT(stock_code, LimitType.Top, data)

    """
    HOW TO USE?
    跌停价
    """
    def PRICE_BOTTOM(self, stock_code, data):
        return self.__PRICE_LIMIT(stock_code, LimitType.Bottom, data)

    """
    HOW TO USE?
    计算涨跌停
    """
    def __PRICE_LIMIT(self, stock_code, type: LimitType, data):
        limit_rate = 0.0
        if stock_code.startswith('688') or stock_code.startswith('30'): #科创/创业板
            limit_rate = 0.20
        elif stock_code.startswith('8'): #北交所
            limit_rate = 0.30
        else: #主板
            limit_rate = 0.10
        # 根据前一日的收盘价进行计算
        if type == LimitType.Top:
            # 根据前一日数据计算出涨停价，并四舍五入
            pre_close = self.ROUNDOFF(data["preClose"])
            return self.ROUNDOFF(pre_close * (1 + limit_rate))
        elif type == LimitType.Bottom:
            # 根据前一日数据计算出跌停价，并四舍五入
            return self.ROUNDOFF(float(data["preClose"]) * (1 - limit_rate))
        
    def LIMIT_PRICE(self, stock_code, type: LimitType, price):
        limit_rate = 0.0
        if stock_code.startswith('688') or stock_code.startswith('30'): #科创/创业板
            limit_rate = 0.20
        elif stock_code.startswith('8'): #北交所
            limit_rate = 0.30
        else: #主板
            limit_rate = 0.10
        # 根据前一日的收盘价进行计算
        if type == LimitType.Top:
            # 根据前一日数据计算出涨停价，并四舍五入
            pre_close = self.ROUNDOFF(price)
            return self.ROUNDOFF(pre_close * (1 + limit_rate))
        elif type == LimitType.Bottom:
            # 根据前一日数据计算出跌停价，并四舍五入
            return self.ROUNDOFF(float(price) * (1 - limit_rate))

    def ROUNDOFF(self, data):
        price = Decimal(str(data))
        price = price.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        return float(price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


    def PRINT_GREEN(self, data):
        GREEN = '\033[32m'
        RESET = '\033[0m'
        print(GREEN + data + RESET)

    def PRINT_RED(self, data):
        RED = '\033[31m'
        RESET = '\033[0m'
        print(RED + data + RESET)

    def PRINT_YELLOW(self, data):
        YELLOW = '\033[33m'
        RESET = '\033[0m'
        print(YELLOW + data + RESET)

    def PRINT_OUTPUT(self, status, function_name, passed_count, failed_count):
        if status is True:
            passed_count += 1
            self.PRINT_GREEN(f"[{function_name}] PASSED")
        else:
            failed_count += 1
            self.PRINT_RED(f"[{function_name}] FAILED")
        print(f"测试{function_name}结束")
        return passed_count, failed_count

class TestData:
    def __init__(self, stock_code, date, price_top, price_bottom):
        self.stock_code = stock_code
        self.date = date
        self.price_top = price_top
        self.price_bottom = price_bottom

if __name__ == "__main__":
    xtdata.enable_hello = False

    passed_count = 0
    failed_count = 0
    common = Common()
    stocks = [
        TestData("600644.SH", "20250416", 9.34, 7.64),
        TestData("603696.SH", "20250417", 11.29, 9.23),
        TestData("603271.SH", "20250418", 38.68, 31.64)
        ]

    # PRICE_TOP ############################################################################
    function_name = "PRICE_TOP"
    print(f"测试{function_name}开始")
    status = True
    for stock in stocks:
        data = common.GET_STOCK_DATA_FOR_1D(stock.stock_code, stock.date)
        price_top = common.PRICE_TOP(stock.stock_code, data)
        if abs(price_top - stock.price_top) >= 0.001:
            status = False
            print(f"{function_name}测试失败, expect:{stock.price_top} actual:{price_top}")
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # PRICE_BOTTOM ############################################################################
    function_name = "PRICE_BOTTOM"
    print(f"测试{function_name}开始")
    status = True
    for stock in stocks:
        data = common.GET_STOCK_DATA_FOR_1D(stock.stock_code, stock.date)
        price_bottom = common.PRICE_BOTTOM(stock.stock_code, data)
        if abs(price_bottom - stock.price_bottom) >= 0.001:
            status = False
            print(f"{function_name}测试失败, expect:{stock.price_bottom} actual:{price_bottom}")
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # PRE_TRADING_DATE ############################################################################
    function_name = "PRE_TRADING_DATE"
    print(f"测试{function_name}开始")
    status = True
    date = "20250416"
    day_1 = common.PRE_TRADING_DATE(date, 2)
    day_2 = common.PRE_TRADING_DATE(date, 1)
    if day_1 != "20250414" or day_2 != "20250415":
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # NEXT_TRADING_DATE ############################################################################
    function_name = "NEXT_TRADING_DATE"
    print(f"测试{function_name}开始")
    status = True
    date = "20250416"
    day_1 = common.NEXT_TRADING_DATE(date, 1)
    day_2 = common.NEXT_TRADING_DATE(date, 2)
    if day_1 != "20250417" or day_2 != "20250418":
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # IS_TRADING_DATE ############################################################################
    function_name = "IS_TRADING_DATE"
    print(f"测试{function_name}开始")
    status = True
    if common.IS_TRADING_DATE("600644.SH", "20250416") is not True:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # WHOLE_STOCKS ############################################################################
    function_name = "WHOLE_STOCKS"
    print(f"测试{function_name}开始")
    status = True
    stocks = common.WHOLE_STOCKS
    if len(stocks) == 0:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # MAIN_STOCKS ############################################################################
    function_name = "MAIN_STOCKS"
    print(f"测试{function_name}开始")
    status = True
    stocks = common.MAIN_STOCKS
    if len(stocks) == 0:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # GET_STOCKNAME ############################################################################
    function_name = "GET_STOCKNAME"
    print(f"测试{function_name}开始")
    status = True
    stock_name = common.GET_STOCKNAME("002031.SZ")
    if stock_name != "巨轮智能":
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # GET_FULLCODE ############################################################################
    function_name = "GET_FULLCODE"
    print(f"测试{function_name}开始")
    status = True
    full_code = common.GET_FULLCODE("002031")
    if full_code != "002031.SZ":
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # GET_STOCK_DATAS_FOR_1D() ############################################################################
    function_name = "GET_STOCK_DATAS_FOR_1D"
    print(f"测试{function_name}开始")
    status = True
    stock_data = common.GET_STOCK_DATAS_FOR_1D("002031.SZ")
    if stock_data is None:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # GET_STOCK_DATA_FOR_1D ############################################################################
    function_name = "GET_STOCK_DATA_FOR_1D"
    print(f"测试{function_name}开始")
    status = True
    stock_data = common.GET_STOCK_DATA_FOR_1D("002031.SZ", "20250422")
    if stock_data is None:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # GET_MARKET_DATAS_FOR_1D ############################################################################
    function_name = "GET_MARKET_DATAS_FOR_1D"
    print(f"测试{function_name}开始")
    status = True
    all_data = common.GET_MARKET_DATAS_FOR_1D(1)
    if len(all_data) == 0:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # GET_STOCK_DATA_ITEM ############################################################################
    function_name = "GET_STOCK_DATA_ITEM"
    print(f"测试{function_name}开始")
    status = True
    stock_data = common.GET_STOCK_DATA_FOR_1D("002031.SZ", "20250422")
    close_price = common.GET_STOCK_DATA_ITEM(stock_data, DataType.close)
    if close_price != "8.47":
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # MA_ACTUAL ############################################################################
    function_name = "MA_ACTUAL"
    print(f"测试{function_name}开始")
    status = True
    ma5 = common.MA_ACTUAL("002031.SZ", "20250422", 5)
    ma10 = common.MA_ACTUAL("002031.SZ", "20250422", 10)
    ma20 = common.MA_ACTUAL("002031.SZ", "20250422", 20)
    if str(ma5) != "8.7" or str(ma10) != "8.49" or str(ma20) != "8.55":
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # MA_EXPECT ############################################################################
    function_name = "MA_EXPECT"
    print(f"测试{function_name}开始")
    status = True
    ma5 = common.MA_EXPECT("600644.SH", "20250416", 5)
    ma10 = common.MA_EXPECT("600644.SH", "20250416", 10)
    ma20 = common.MA_EXPECT("600644.SH", "20250416", 20)
    if str(ma5) != "7.97" or str(ma10) != "7.45" or str(ma20) != "7.16":
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # PRE_TRADING_DATE_FOR_STOCK ############################################################################
    function_name = "PRE_TRADING_DATE_FOR_STOCK"
    print(f"测试{function_name}开始")
    status = True
    day_1 = common.PRE_TRADING_DATE_FOR_STOCK("600644.SH", "20250416", 1)
    day_2 = common.PRE_TRADING_DATE_FOR_STOCK("600644.SH", "20250416", 2)
    if day_1 != "20250415" or day_2 != "20250414":
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # PRE_TRADING_DATE_FOR_STOCK ############################################################################
    function_name = "NEXT_TRADING_DAY_FOR_STOCK"
    print(f"测试{function_name}开始")
    status = True
    day_1 = common.NEXT_TRADING_DAY_FOR_STOCK("600644.SH", "20250416", 1)
    day_2 = common.NEXT_TRADING_DAY_FOR_STOCK("600644.SH", "20250416", 2)
    if day_1 != "20250417" or day_2 != "20250418":
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # IS_TOP ############################################################################
    function_name = "IS_TOP"
    print(f"测试{function_name}开始")
    status = True
    if common.IS_TOP("600678.SH", "20250220") is not True:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # IS_BOTTOM ############################################################################
    function_name = "IS_BOTTOM"
    print(f"测试{function_name}开始")
    status = True
    if common.IS_BOTTOM("002122.SZ", "20250121") is not True:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # IS_2F ############################################################################
    function_name = "IS_2F"
    print(f"测试{function_name}开始")
    status = True
    if common.IS_2F("000601.SZ", "20250425") is not True:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # IS_2A ############################################################################
    function_name = "IS_2A"
    print(f"测试{function_name}开始")
    status = True
    if common.IS_2A("000601.SZ", "20250425") is not True:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # IS_2N ############################################################################
    function_name = "IS_2N"
    print(f"测试{function_name}开始")
    status = True
    if common.IS_2N("000668.SZ", "20250418") is not True:
        status = False
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # LAST_TOP_DATE ############################################################################
    #function_name = "LAST_TOP_DATE"
    #print(f"测试{function_name}开始")
    #status = True
    #if common.LAST_TOP_DATE("000668.SZ") != "20250417":
    #    status = False
    #passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    print(f"")
    print(f"########################")
    common.PRINT_YELLOW(f"TEST COUNT: {passed_count + failed_count}")
    common.PRINT_GREEN(f"TEST PASSED: {passed_count}")
    common.PRINT_RED(f"TEST FAILED: {failed_count}")
    print(f"########################")