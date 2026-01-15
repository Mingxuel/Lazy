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
from Common import Common

class SectorType(Enum):
    S2F = 1
    S2F_ = 2
    S2S = 3
    S2S_ = 4
    S2A = 5
    S2N = 6
    S2J = 7
    SELF = 8

@Singleton
class Sectors:
    def __init__(self):
        self.__debug_func_name = False
        self.__sector_2a : list[str] = []
        self.__sector_2f : list[str] = []
        self.__sector_2n : list[str] = []

########################################## 初始化板块数据 ###################################################
    def INIT(self):
        if self.__debug_func_name:
            print("[INIT]")

########################################### 获取板块股票 ####################################################
    def GET_SECTOR_2A(self):
        if self.__debug_func_name:
            print("[GET_SECTOR_2A]")
        config_file = "Config/板块/2A"
        if len(self.__sector_2a) == 0:
            with open(config_file, 'r') as file:
                for line in file:
                    self.__sector_2a.append(line.strip())
        return self.__sector_2a

    def GET_SECTOR_2F(self):
        if self.__debug_func_name:
            print("[GET_SECTOR_2F]")
        config_file = "Config/板块/2F"
        if len(self.__sector_2f) == 0:
            with open(config_file, 'r') as file:
                for line in file:
                    self.__sector_2f.append(line.strip())
        return self.__sector_2f

    def GET_SECTOR_2N(self):
        config_file = "Config/板块/2N"
        if len(self.__sector_2n) == 0:
            with open(config_file, 'r') as file:
                for line in file:
                    self.__sector_2n.append(line.strip())
        return self.__sector_2n
# 更新同花顺数据 ###############################################################################################
    def UPDATE_TONGHUASHUN(self):
        self.__RESET_TARGET_FILE()
        target = f"Config/板块/blockstockV3.xml"
        content = ""
        with open(target, 'r', encoding='utf-8') as file:
            content = file.read()
        content = content.replace("##2A##", self.__CONVERT_TO_BLOCK(self.GET_SECTOR_2A()))
        content = content.replace("##2F##", self.__CONVERT_TO_BLOCK(self.GET_SECTOR_2F()))
        content = content.replace("##2N##", self.__CONVERT_TO_BLOCK(self.GET_SECTOR_2N()))
        stock_list = []
        stock_list.extend(self.GET_SECTOR_2A())
        stock_list.extend(self.GET_SECTOR_2N())
        content = content.replace("##ALL##", self.__CONVERT_TO_BLOCK(stock_list))
        with open(target, 'w', encoding='utf-8') as file:
            file.write(content)
        self.__RESET_TONGHUASHUN()

    def __RESET_TONGHUASHUN(self):
        origin = f"Config/板块/blockstockV3.xml"
        target = f"C:/同花顺远航版/bin/users/狗蛋儿家的金/blockstockV3.xml"
        content = ""
        with open(origin, 'r', encoding='utf-8') as file_origin:
            content = file_origin.read()
        with open(target, 'w', encoding='utf-8') as file_target:
            file_target.write(content)

    def __RESET_TARGET_FILE(self):
        origin = f"Config/板块/blockstockV3.xml_origin"
        target = f"Config/板块/blockstockV3.xml"
        content = ""
        with open(origin, 'r', encoding='utf-8') as file_origin:
            content = file_origin.read()
        with open(target, 'w', encoding='utf-8') as file_target:
            file_target.write(content)

    def __CONVERT_TO_BLOCK(self, stock_list):
        block = ""
        for stock_code in stock_list:
            block += self.__CONVERT_TO_BLOCK_ITEM(stock_code)
        block = block[:-1]
        return block

    def __CONVERT_TO_BLOCK_ITEM(self, stock_code):
        if stock_code[7:9] == "SZ":
            return f"    <security market=\"USZA\" code=\"{stock_code[0:6]}\" />\n"
        elif stock_code[7:9] == "SH":
            return f"    <security market=\"USHA\" code=\"{stock_code[0:6]}\" />\n"
        return None

if __name__ == "__main__":
    xtdata.enable_hello = False

    passed_count = 0
    failed_count = 0
    common = Common()
    sectors = Sectors()
    today = common.TODAY
    last_trading_day = common.LAST_TRADING_DATE(today)

    # GET_SECTOR_2A ############################################################################
    function_name = "GET_SECTOR_2A"
    print(f"测试{function_name}开始")
    status = True
    stock_list = sectors.GET_SECTOR_2A()
    for stock in stock_list:
        if common.IS_2A(stock, last_trading_day) is not True:
            status = False
            break
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # GET_SECTOR_2F ############################################################################
    function_name = "GET_SECTOR_2F"
    print(f"测试{function_name}开始")
    status = True
    stock_list = sectors.GET_SECTOR_2F()
    for stock in stock_list:
        if common.IS_2F(stock, last_trading_day) is not True:
            status = False
            break
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    # GET_SECTOR_2N ############################################################################
    function_name = "GET_SECTOR_2N"
    print(f"测试{function_name}开始")
    status = True
    stock_list = sectors.GET_SECTOR_2N()
    for stock in stock_list:
        if common.IS_2N(stock, last_trading_day) is not True:
            status = False
            break
    passed_count, failed_count = common.PRINT_OUTPUT(status, function_name, passed_count, failed_count)

    print(f"")
    print(f"########################")
    common.PRINT_YELLOW(f"TEST COUNT: {passed_count + failed_count}")
    common.PRINT_GREEN(f"TEST PASSED: {passed_count}")
    common.PRINT_RED(f"TEST FAILED: {failed_count}")
    print(f"########################")