from Path import GET_ROOT_PATH

def TRADING_DATES():
    config_file_trading_dates = GET_ROOT_PATH() + "/AI/AIData/TradingDates.config"
    trading_dates = []
    with open(config_file_trading_dates, 'r') as file:
        for line in file:
            trading_dates.append(line.strip())
    return trading_dates
