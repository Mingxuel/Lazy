import os

def GET_ROOT_PATH() -> str:
    current_path: str = os.path.abspath(__file__)
    keyword = "Lazy"
    index: int = current_path.find(keyword)
    return current_path[:index + len(keyword)]

def PATH_AIDATA_ORIGIN() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/ORIGIN"

def PATH_AIDATA() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData"

def PATH_AIDATA_TRADING_DATES() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/TRADING_DATES"

def PATH_AIDATA_1D() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/1D"

def PATH_AIDATA_5M() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/5M"

def PATH_AIDATA_TOP() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/TOP"

def PATH_AIDATA_BOTTOM() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/BOTTOM"

def PATH_AIDATA_TARGET_31() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/TARGET/31"

def PATH_AIDATA_TARGET_311() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/TARGET/311"

def PATH_AIDATA_1D_MOTION_PRICE() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/1D_MOTION_PRICE"

def PATH_AIDATA_1D_MOTION_PRICE_VOLUME() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/1D_MOTION_PRICE_VOLUME"

def PATH_AIDATA_1D_WIN_COUNT() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/1D_MOTION_WIN_COUNT"

def PATH_AIDATA_5M_MOTION_PRICE() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/5M_MOTION_PRICE"

def PATH_AIDATA_5M_MOTION_PRICE_VOLUME() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/5M_MOTION_PRICE_VOLUME"

def PATH_AIDATA_5M_WIN_COUNT() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/5M_MOTION_WIN_COUNT"

def PATH_AIDATA_1D_SIGNALS() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/1D_MOTION_SIGNALS"

def PATH_AIDATA_5M_SIGNALS() -> str:
    return GET_ROOT_PATH() + "/MarcoAI/AIData/5M_MOTION_SIGNALS"

def PATH_TDX() -> str:
    return "D:/new_tdx_mock/PYPlugins/user"

def PATH_ADJUST_FACTOR() -> str:
    return PATH_AIDATA_ORIGIN() + "/ADJUST_FACTOR"

def PATH_STOCK_CODES() -> str:
    return PATH_AIDATA() + "/ORIGIN/SZ200.config"

def PATH_TRADING_DATES() -> str:
    return PATH_AIDATA() + "/TradingDates.config"

