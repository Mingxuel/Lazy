

from Path import GET_ROOT_PATH

def SZ200_STOCK_CODES():
    config_file_stock_codes = GET_ROOT_PATH() + "/AI/AIData/ORIGIN/SZ200.config"
    stock_codes = []
    with open(config_file_stock_codes, 'r') as file:
        for line in file:
            stock_codes.append(line.strip())
    # return stock_codes