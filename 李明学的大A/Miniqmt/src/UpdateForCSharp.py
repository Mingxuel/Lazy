from decimal import ROUND_HALF_UP, Decimal
from xtquant import xtdata
import datetime
from Common import Common, DataType, MAType
import sys
from RunTime import RunTime
from Sectors import Sectors
import time
import argparse
import os, sys
import ast
import pandas as pd

HISTORY_1D_COUNT = 3
ACTIVE_COUNT = 1156

def UPDATE_TRADING_DATES():
    config_file = GET_ROOT_PATH() + "/Data/交易日.config"
    start_date = "20240101"
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    trading_dates = xtdata.get_trading_dates('SH', start_date, end_date)
    with open(config_file, 'w') as file:
        for date in trading_dates:
            date = datetime.datetime.fromtimestamp(date/1000).strftime("%Y%m%d")
            file.write(f"{date}\n")
        return True
    return False

def DOWNLOAD_HISTORY_1D():
    stock_codes = ZZ500_STOCK_CODES()
    trading_dates = TRADING_DATES()

    pre_count = 0
    while True:
        if HISTORY_1D_COUNT == -1:
            xtdata.download_history_data2(stock_codes, "1d", trading_dates[0], trading_dates[-1])
        else:
            xtdata.download_history_data2(stock_codes, "1d", trading_dates[-HISTORY_1D_COUNT], trading_dates[-1])

        xtdata.subscribe_whole_quote(stock_codes)
        data_1d = xtdata.get_market_data_ex([], stock_codes, "1d", trading_dates[-1], trading_dates[-1], 1, dividend_type="front_ratio", fill_data=False)
        count = 0

        for stock_code in stock_codes:
            if data_1d[stock_code].size != 0 and data_1d[stock_code].index[-1] == trading_dates[-1]:
                count = count + 1
        if count < ACTIVE_COUNT or count != pre_count:
            pre_count = count
        else:
            time.sleep(10)
            return True

def UPDATE_HISTORY_1D():
    stock_codes = ZZ500_STOCK_CODES()
    trading_dates = TRADING_DATES()
    config_file = ""

    xtdata.subscribe_whole_quote(stock_codes)
    data_1d = xtdata.get_market_data_ex([], stock_codes, "1d", trading_dates[0], trading_dates[-1], -1, dividend_type="front_ratio", fill_data=False)

    if len(data_1d) == 0:
        return False
    for stock_code in stock_codes:
        if stock_code not in data_1d.keys():
            continue
        config_file = GET_ROOT_PATH() + f"/Data/1D/{stock_code}"
        if os.path.exists(config_file):
            #获取最后一次更新的日期
            last_date = ""
            with open(config_file, 'r') as file:
                last_date = file.readlines()[-1].strip().split(" ")[0]
            data = data_1d[stock_code]
            #写入新数据
            with open(config_file, 'a') as file:
                for date, row in data.iterrows():
                    #判断是否有最新数据
                    if date <= last_date:
                        continue
                    #到这里了就说明有新数据
                    file.write(f"{date} ")
                    for index in data.columns[1:-1]:
                        file.write(str(ROUNDOFF(row[index])))
                        file.write(" ")
                    file.write("\n")
        else: #文件不存在，写入所有数据
            data = data_1d[stock_code]
            with open(config_file, 'a') as file:
                for index in data.columns:
                    file.write(index + " ")
                file.write("\n")
                for date, row in data.iterrows():
                    file.write(date)
                    file.write(" ")
                    for index in data.columns[1:-1]:
                        file.write(str(ROUNDOFF(row[index])))
                        file.write(" ")
                    file.write("\n")
    return True

def DOWNLOAD_HISTORY_1M():
    stock_codes = ZZ500_STOCK_CODES()
    trading_dates = TRADING_DATES()
    start_time = trading_dates[0] + "091500"
    end_time = trading_dates[-1] + "150000"
    xtdata.download_history_data2(stock_codes, "1m", start_time, end_time)
    xtdata.subscribe_whole_quote(stock_codes)
    xtdata.get_market_data_ex([], stock_codes, "1m", start_time, end_time, 1, dividend_type="front_ratio", fill_data=False)

def UPDATE_HISTORY_1M():
    stock_codes = ZZ500_STOCK_CODES()
    trading_dates = TRADING_DATES()
    start_time = trading_dates[0] + "091500"
    end_time = trading_dates[-1] + "150000"

    count_all = len(stock_codes)
    count = 0
    for stock_code in stock_codes:
        xtdata.subscribe_whole_quote([stock_code])
        data_1m = xtdata.get_market_data_ex([], [stock_code], "1m", start_time, end_time, -1, dividend_type="front_ratio", fill_data=False)
        config_file = ""

        count = count + 1
        print(f"1M数据更新进度：[{count}/{count_all}]")

        if stock_code not in data_1m.keys():
            continue
        config_file = GET_ROOT_PATH() + f"/Data/1M/{stock_code}"
        if os.path.exists(config_file):
            #获取最后一次更新的日期
            last_date = ""
            with open(config_file, 'r') as file:
                last_date = file.readlines()[-1].strip().split(" ")[0]
            data = data_1m[stock_code]
            #写入新数据
            with open(config_file, 'a') as file:
                for date, row in data.iterrows():
                    #判断是否有最新数据
                    if date <= last_date:
                        continue
                    #到这里了就说明有新数据
                    file.write(f"{date} ")
                    for index in data.columns[1:-1]:
                        file.write(str(ROUNDOFF(row[index])))
                        file.write(" ")
                    file.write("\n")
        else: #文件不存在，写入所有数据
            data = data_1m[stock_code]
            with open(config_file, 'a') as file:
                for index in data.columns:
                    file.write(index + " ")
                file.write("\n")
                for date, row in data.iterrows():
                    file.write(date)
                    file.write(" ")
                    for index in data.columns[1:-1]:
                        file.write(str(ROUNDOFF(row[index])))
                        file.write(" ")
                    file.write("\n")
    return True

def DOWNLOAD_HISTORY_5M():
    stock_codes = ZZ500_STOCK_CODES()
    trading_dates = TRADING_DATES()
    start_time = trading_dates[0] + "091500"
    end_time = trading_dates[-1] + "150000"
    xtdata.download_history_data2(stock_codes, "5m", start_time, end_time)
    xtdata.subscribe_whole_quote(stock_codes)
    xtdata.get_market_data_ex([], stock_codes, "5m", start_time, end_time, 1, dividend_type="front_ratio", fill_data=False)

def UPDATE_HISTORY_5M():
    stock_codes = ZZ500_STOCK_CODES()
    trading_dates = TRADING_DATES()
    start_time = trading_dates[0] + "091500"
    end_time = trading_dates[-1] + "150000"

    count_all = len(stock_codes)
    count = 0
    for stock_code in stock_codes:
        xtdata.subscribe_whole_quote([stock_code])
        data_5m = xtdata.get_market_data_ex([], [stock_code], "5m", start_time, end_time, -1, dividend_type="front_ratio", fill_data=False)

        count = count + 1
        print(f"5M数据更新进度：[{count}/{count_all}]")

        if stock_code not in data_5m.keys():
            continue
        config_directory = GET_ROOT_PATH() + f"\\Data\\5M\\{stock_code}"
        if not os.path.exists(config_directory):
            os.makedirs(config_directory)

        data = data_5m[stock_code]
        exists = False
        for date, row in data.iterrows():
            config_file = config_directory + "\\" + str(date)[:8]
            if date[8:] == "093500":
                if os.path.exists(config_file):
                    exists = True
                else:
                    exists = False
            if exists:
                continue
            with open(config_file, 'a') as file:
                item_time = date[8:]
                item_open = str(ROUNDOFF(row.iloc[1]))
                item_high = str(ROUNDOFF(row.iloc[2]))
                item_low = str(ROUNDOFF(row.iloc[3]))
                item_close = str(ROUNDOFF(row.iloc[4]))
                item_volume = str(ROUNDOFF(row.iloc[5]))
                item_amount = str(ROUNDOFF(row.iloc[6]))
                item_pre_close = str(ROUNDOFF(row[9]))
                file.write(f"{item_time}|{item_open}|{item_high}|{item_low}|{item_close}|{item_volume}|{item_amount}|{item_pre_close}\n")

    return True

# PRIVATE ################################################################################################
def TRADING_DATES():
    config_file_trading_dates = GET_ROOT_PATH() + "/Data/交易日.config"
    trading_dates = []
    with open(config_file_trading_dates, 'r') as file:
        for line in file:
            trading_dates.append(line.strip())
    return trading_dates

def ZZ500_STOCK_CODES():
    config_file_stock_codes = GET_ROOT_PATH() + "/Data/ZZ500/Tickets.config"
    stock_codes = []
    with open(config_file_stock_codes, 'r') as file:
        for line in file:
            stock_codes.append(line.strip())
    return stock_codes

def ROUNDOFF(data):
    price = Decimal(str(data))
    price = price.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    return float(price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

def GET_ROOT_PATH():
    current_path = os.path.abspath(__file__)
    keyword = "李明学的大A"
    index = current_path.find(keyword)
    return current_path[:index + len(keyword)]

if __name__ == "__main__":
    xtdata.enable_hello = False

    parser = argparse.ArgumentParser(description="一个带参数的示例程序")
    parser.add_argument("-utd", "--update_trading_dates", action="store_true", help="")
    parser.add_argument("-dh1d", "--download_history_1d", action="store_true", help="")
    parser.add_argument("-uh1d", "--update_history_1d", action="store_true", help="")
    parser.add_argument("-dh1m", "--download_history_1m", action="store_true", help="")
    parser.add_argument("-uh1m", "--update_history_1m", action="store_true", help="")
    parser.add_argument("-dh5m", "--download_history_5m", action="store_true", help="")
    parser.add_argument("-uh5m", "--update_history_5m", action="store_true", help="")
    parser.add_argument("-minute", "--minute", help="")
    args = parser.parse_args()

    if args.update_trading_dates:
        if UPDATE_TRADING_DATES():
            print("交易日更新成功")

    if args.download_history_1d:
        if DOWNLOAD_HISTORY_1D():
            print("1D数据下载成功")

    if args.update_history_1d:
        if UPDATE_HISTORY_1D():
            print("1D数据更新成功")

    if args.download_history_1m:
        if DOWNLOAD_HISTORY_1M():
            print("1M数据下载成功")

    if args.update_history_1m:
        if UPDATE_HISTORY_1M():
            print("1M数据更新成功")

    if args.download_history_5m:
        if DOWNLOAD_HISTORY_5M():
            print("1M数据下载成功")

    if args.update_history_5m:
        if UPDATE_HISTORY_5M():
            print("1M数据更新成功")
