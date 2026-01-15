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

HISTORY_1D_COUNT = 10
HISTORY_1M_COUNT = 10
STOP_COUNT = 9

common = Common()
sectors = Sectors()

def UPDATE_MAIN_STOCK_LIST():
    print(f"# UPDATE_MAIN_STOCK_LIST START #######")
    config_file = "Config/主板代码"
    count = 0
    with open(config_file, 'w') as file:
        stocks = xtdata.get_stock_list_in_sector('沪深A股')
        stocks = sorted(stocks, reverse=True)
        for stock_code in stocks:
            if stock_code.startswith('688') or stock_code.startswith('30'): #科创/创业板
                continue
            elif stock_code.startswith('8'): #北交所
                continue
            else: #主板(也包含st)
                file.write(f"{stock_code}\n")
                count += 1
    print(f"[UPDATE_MAIN_STOCK_LIST] MAIN STOCKS COUNT: {count}")
    print(f"# UPDATE_MAIN_STOCK_LIST END #######")
    print("")

def UPDATE_TRADING_DATES():
    print(f"# UPDATE_TRADING_DATES START #######")
    count = common.UPDATE_TRADING_DATES()
    print(f"[UPDATE_TRADING_DATES] TRADING DATES COUNT: {count}")
    print(f"# UPDATE_TRADING_DATES END #######")
    print("")

def UPDATE_TRADING_TIMES_1M():
    print(f"# UPDATE_TRADING_TIMES_1M START #######")
    count = common.UPDATE_TRADING_TIMES_1M()
    print(f"[UPDATE_TRADING_TIMES_1M] TRADING TIMES FOR 1M COUNT: {count}")
    print(f"# UPDATE_TRADING_TIMES_1M END #######")
    print("")

def DOWNLOAD_HISTORY_1D():
    print(f"# DOWNLOAD_HISTORY_1D START #######")
    status = True
    all_count = len(common.MAIN_STOCKS)
    while status:
        if HISTORY_1D_COUNT == -1:
            xtdata.download_history_data2(common.MAIN_STOCKS, "1d", common.TRADING_DATES[0], common.TRADING_DATES[-1])
        else:
            xtdata.download_history_data2(common.MAIN_STOCKS, "1d", common.TRADING_DATES[-HISTORY_1D_COUNT], common.TRADING_DATES[-1])
        common.RESET_MARKET_DATAS_FOR_1D()
        whole_data = common.GET_MARKET_DATAS_FOR_1D(HISTORY_1D_COUNT)
        count = 0
        for stock_code in common.MAIN_STOCKS:
            if len(whole_data[stock_code].index) == 0:
                continue
            if HISTORY_1D_COUNT == -1:
                first_date = whole_data[stock_code].index[0]
                last_date = whole_data[stock_code].index[-1]
                if first_date == common.TRADING_DATES[0] and last_date == common.TRADING_DATES[-1]:
                    count += 1
            else:
                last_date = whole_data[stock_code].index[-1]
                if last_date == common.TRADING_DATES[-1]:
                    count += 1
        if HISTORY_1D_COUNT == -1:
            count += 29
        if (count  + STOP_COUNT) >= len(common.MAIN_STOCKS):
            time.sleep(30)
            status = False
            print(f"[DOWNLOAD_HISTORY_1D] PROCESS: [{all_count}-{count}]")
            continue
        print(f"[DOWNLOAD_HISTORY_1D] PROCESS: [{all_count}-{count}]")
        time.sleep(10)
    print(f"# DOWNLOAD_HISTORY_1D END #######")
    print("")

def UPDATE_HISTORY_1D():
    print(f"# UPDATE_HISTORY_1D START #######")
    count = 0
    common.RESET_MARKET_DATAS_FOR_1D()
    datas = common.GET_MARKET_DATAS_FOR_1D(HISTORY_1D_COUNT)
    if len(datas) == 0:
        print(f"ERROR:[{stock_code} 获取数据失败]")
        return None
    stocks_count = len(common.MAIN_STOCKS)
    for stock_code in common.MAIN_STOCKS:
        count += 1
        print(f"[UPDATE_HISTORY_1D] COUNT: [{stocks_count}-{count}]")
        if stock_code not in datas.keys():
            continue
        config_file = f"Config/Data/1D/{stock_code}"
        if os.path.exists(config_file):
            #获取最后一次更新的日期
            last_date = ""
            with open(config_file, 'r') as file:
                last_date = file.readlines()[-1].strip().split(" ")[0]
            data = datas[stock_code]
            #写入新数据
            with open(config_file, 'a') as file:
                for date, row in data.iterrows():
                    #判断是否有最新数据
                    if date <= last_date:
                        continue
                    #到这里了就说明有新数据
                    file.write(f"{date} ")
                    for index in data.columns[1:-1]:
                        file.write(str(common.ROUNDOFF(row[index])))
                        file.write(" ")
                    file.write("\n")
        else: #文件不存在，写入所有数据
            data = datas[stock_code]
            with open(config_file, 'a') as file:
                for index in data.columns:
                    file.write(index + " ")
                file.write("\n")
                for date, row in data.iterrows():
                    file.write(date)
                    file.write(" ")
                    for index in data.columns[1:-1]:
                        file.write(str(common.ROUNDOFF(row[index])))
                        file.write(" ")
                    file.write("\n")
    print(f"# UPDATE_HISTORY_1D END #######")
    print("")

def DOWNLOAD_HISTORY_1M():
    print(f"# DOWNLOAD_HISTORY_1M START #######")
    status = True
    all_count = len(common.MAIN_STOCKS)
    start_date = common.TRADING_DATES[-HISTORY_1M_COUNT] + "091500"
    end_date = common.TRADING_DATES[-1] + "150000"
    while status:
        xtdata.download_history_data2(common.MAIN_STOCKS, "1m", start_date, end_date)
        common.RESET_MARKET_DATAS_FOR_1M()
        # 获取最新数据
        whole_data = common.GET_MARKET_DATAS_FOR_1M(1, common.TRADING_DATES[-1], common.TRADING_DATES[-1])
        count = 0
        for stock_code in common.MAIN_STOCKS:
            if len(whole_data[stock_code].index) == 0:
                continue
            date = whole_data[stock_code].index[-1]
            if date == end_date or date == (common.TRADING_DATES[-1]+"145900"):
                count += 1
        if (count + STOP_COUNT) >= len(common.MAIN_STOCKS):
            time.sleep(10)
            status = False
            print(f"[DOWNLOAD_HISTORY_1M] PROCESS: [{all_count}-{count}]")
            continue
        print(f"[DOWNLOAD_HISTORY_1M] PROCESS: [{all_count}-{count}]")
    time.sleep(60)
    print(f"# DOWNLOAD_HISTORY_1M END #######")
    print("")

def UPDATE_HISTORY_1M():
    print(f"# UPDATE_HISTORY_1M START #######")
    count = 0
    all_count = len(common.MAIN_STOCKS)
    start_date = ""
    end_date = ""
    last_date = common.TRADING_DATES[-1]
    date_count = 0
    trading_count = len(common.TRADING_DATES)
    index = common.TRADING_DATES.index(common.TRADING_DATES[-HISTORY_1M_COUNT])
    for i in range(index, trading_count):
        trading_date = common.TRADING_DATES[i]
        if date_count == 0:
            start_date = trading_date
            date_count += 1
            continue
        if date_count == 5 or trading_date == last_date:
            end_date = trading_date
            date_count = 0
        else:
            date_count += 1
            continue
        common.RESET_MARKET_DATAS_FOR_1M()
        datas = common.GET_MARKET_DATAS_FOR_1M(-1, start_date, end_date)
        print(f"[UPDATE_HISTORY_1M] START:{start_date} END{end_date}")
        for stock_code in common.MAIN_STOCKS:
            config_folder = f"Config/Data/1M/{stock_code}"
            if not os.path.exists(config_folder):
                os.makedirs(config_folder)
            status = False
            for time, row in datas[stock_code].iterrows():
                if "093000" in time:
                    config_file = f"Config/Data/1M/{stock_code}/{time[0:8]}"
                    if os.path.exists(config_file):
                        status = True
                        continue
                    with open(config_file, 'a') as file:
                        for index in datas[stock_code].columns:
                            file.write(index + " ")
                        file.write("\n")
                    status = False
                if status is True:
                    continue
                config_file = f"Config/Data/1M/{stock_code}/{time[0:8]}"
                with open(config_file, 'a') as file:
                    file.write(time)
                    file.write(" ")
                    for index in datas[stock_code].columns[1:-1]:
                        file.write(str(common.ROUNDOFF(row[index])))
                        file.write(" ")
                    file.write("\n")
            count += 1
            print(f"[UPDATE_HISTORY_1M] COUNT: [{all_count}-{count}]")
        common.RESET_STOCK_DATAS_FOR_1M()
    print(f"# UPDATE_HISTORY_1M END #######")
    print("")

def UPDATE_TOP_LIST():
    print(f"# UPDATE_TOP_LIST START #######")
    common.RESET_MARKET_DATAS_FOR_1D()
    datas = common.GET_MARKET_DATAS_FOR_1D()
    top_data = common.GET_TOP_DATA()
    count = 0
    for date in common.TRADING_DATES:
        if date in top_data:
            continue
        for stock_code in common.MAIN_STOCKS:
            #该股是否在该日期内存在数据，不存在则跳过
            data = datas[stock_code]
            if len(data) == 0:
                continue
            if date not in data["time"]:
                continue
            #获取指定日期的数据
            data = data.loc[date]
            #根据指定日期数据计算涨停价
            price_top = common.PRICE_TOP(stock_code, data)
            #获取指定日期的收盘价
            price_close = data["close"]
            #判断是否为涨停
            if abs(price_top - price_close) >= 0.001:
                continue
            config_file = f"Config/Top/{date}"
            with open(config_file, 'a') as file:
                #涨停，将代码写入到日期文件中
                file.write(f"{stock_code}\n")
                count += 1
                print(f"[UPDATE_TOP_LIST] TOP COUNT: {count}")
    print(f"# UPDATE_TOP_LIST END #######")
    print("")

def UPDATE_BOTTOM_LIST():
    print(f"# UPDATE_BOTTOM_LIST START #######")
    datas = common.GET_MARKET_DATAS_FOR_1D()
    bottom_data = common.GET_BOTTOM_DATA()
    count = 0
    for date in common.TRADING_DATES:
        if date in bottom_data:
            continue
        for stock_code in common.MAIN_STOCKS:
            #该股是否在该日期内存在数据，不存在则跳过
            data = datas[stock_code]
            if len(data) == 0:
                continue
            if date not in data["time"]:
                continue
            #获取指定日期的数据
            data = data.loc[date]
            #根据指定日期数据计算跌停价
            price_bottom = common.PRICE_BOTTOM(stock_code, data)
            #获取指定日期的收盘价
            price_close = data["close"]
            #判断是否为跌停
            if abs(price_bottom - price_close) >= 0.001:
                continue
            config_file = f"Config/Bottom/{date}"
            with open(config_file, 'a') as file:
                #跌停，将代码写入到日期文件中
                file.write(f"{stock_code}\n")
                count += 1
                print(f"[UPDATE_BOTTOM_LIST] BOTTOM COUNT: {count}")
    print(f"# UPDATE_BOTTOM_LIST END #######")
    print("")

def UPDATE_TOP_2N_LIST():
    print(f"# UPDATE_TOP_2N_LIST START #######")
    data = {}
    config_file = f"Config/TOP_TOP"
    last_date = "20240601"
    if os.path.exists(config_file):
        with open(config_file, 'r') as file:
            last_date = file.readlines()[-1].strip().split(" ")[0]
    for trading_date in common.TRADING_DATES:
        if trading_date <= last_date:
            continue
        stock_list = []
        for stock_code in common.MAIN_STOCKS:
            if common.IS_2N(stock_code, trading_date):
                stock_list.append(stock_code)
            data[trading_date] = stock_list
    with open(config_file, 'a') as file:
        for date, stock_list in data.items():
            for stock_code in stock_list:
                pre_date = common.PRE_TRADING_DATE_FOR_STOCK(stock_code, date)
                expect_price = common.MA_EXPECT_PRICE(stock_code, MAType.ma5, pre_date)
                file.write(f"{date} {stock_code} {expect_price}\n")
    print(f"# UPDATE_TOP_2N_LIST END #######")

def UPDATE_SECTOR_2A():
    print(f"# UPDATE_SECTOR_2A START #######")
    common.RESET_TOP_DATA()
    stock_list = []
    last_day = common.LAST_TRADING_DATE(common.TODAY)
    for stock_code in common.MAIN_STOCKS:
        if common.IS_2A(stock_code, last_day):
            stock_list.append(stock_code)
    config_file = f"Config/板块/2A"
    with open(config_file, 'w') as file:
        for stock_code in stock_list:
            file.write(f"{stock_code}\n")
    print(f"[UPDATE_SECTOR_2A] COUNT: {len(stock_list)}")
    print(f"# UPDATE_SECTOR_2A END #######")
    print("")

def UPDATE_SECTOR_2F():
    print(f"# UPDATE_SECTOR_2F START #######")
    stock_list = []
    last_day = common.LAST_TRADING_DATE(common.TODAY)
    for stock_code in common.MAIN_STOCKS:
        if common.IS_2F(stock_code, last_day):
            stock_list.append(stock_code)
    config_file = f"Config/板块/2F"
    with open(config_file, 'w') as file:
        for stock_code in stock_list:
            file.write(f"{stock_code}\n")
    print(f"[UPDATE_SECTOR_2F] COUNT: {len(stock_list)}")
    print(f"# UPDATE_SECTOR_2F END #######")
    print("")

def UPDATE_SECTOR_2N():
    print(f"# UPDATE_SECTOR_2N START #######")
    stock_list = []
    last_day = common.LAST_TRADING_DATE(common.TODAY)
    for stock_code in common.MAIN_STOCKS:
        if common.IS_2N(stock_code, last_day):
            stock_list.append(stock_code)
    config_file = f"Config/板块/2N"
    with open(config_file, 'w') as file:
        for stock_code in stock_list:
            file.write(f"{stock_code}\n")
    print(f"[UPDATE_SECTOR_2N] COUNT: {len(stock_list)}")
    print(f"# UPDATE_SECTOR_2N END #######")
    print("")

def UPDATE_TONGHUASHUN():
    print(f"# UPDATE_TONGHUASHUN START #######")
    sectors.UPDATE_TONGHUASHUN()
    print(f"# UPDATE_TONGHUASHUN END #######")
    print("")

###############################
#一定要在收盘后更新
###############################
if __name__ == "__main__":
    if common.IS_TRADING_DATE_TODAY():
        if common.TIME >= "091500" and common.TIME <= "150000":
            print(f"当前是交易时间，是否继续<Y/N>?")
            input_text = input(["Y", "N"])
            if input_text == "N":
                sys.exit(0)

    #print(f"请输入下载1D数据的天数: ", flush=True)
    #input_text = input()
    #HISTORY_1D_COUNT = int(input_text)

    #print(f"请输入下载1M数据的天数: ", flush=True)
    #input_text = input()
    #HISTORY_1M_COUNT = int(input_text)

    print(f"请输入今日的停牌家数: ", flush=True)
    input_text = input()
    STOP_COUNT = int(input_text)

    common.TEST_MODE = True

    # 更新主板代码列表
    UPDATE_MAIN_STOCK_LIST()
    # 更新交易日期
    UPDATE_TRADING_DATES()
    # 更新交易时间1M
    UPDATE_TRADING_TIMES_1M()
    # 下载1D历史数据
    DOWNLOAD_HISTORY_1D()
    # 将1D历史数据保存至文件
    UPDATE_HISTORY_1D()
    # 下载1M历史数据
    DOWNLOAD_HISTORY_1M()
    # 将1M历史数据保存至文件
    UPDATE_HISTORY_1M()
    # 更新涨停数据
    UPDATE_TOP_LIST()
    # 更新跌停数据
    UPDATE_BOTTOM_LIST()
    # 更新2连板开板数据
    UPDATE_TOP_2N_LIST()
    # 所有2板, 包括缩量2板和放量2板
    UPDATE_SECTOR_2A()
    # 放量2板
    UPDATE_SECTOR_2F()
    # 段板2板
    UPDATE_SECTOR_2N()
    # 更新同花顺
    UPDATE_TONGHUASHUN()
