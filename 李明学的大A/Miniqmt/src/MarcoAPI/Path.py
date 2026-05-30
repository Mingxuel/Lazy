import os
from D:\new_tdx_mock\PYPlugins\user\tqcenter

def GET_ROOT_PATH():
    current_path = os.path.abspath(__file__)
    keyword = "Lazy"
    index = current_path.find(keyword)
    return current_path[:index + len(keyword)]
