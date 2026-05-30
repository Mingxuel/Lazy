import sys

sys.path.append(r"D:\new_tdx_mock\PYPlugins\user")

from tqcenter import tq

tq.initialize(__file__)

gp_val = tq.get_gpjy_value(
        stock_list=['688318.SH'],
        field_list=['GP1','GP2','GP3','GP4','GP5'],
        start_time='20250101',
        end_time='20250102')
print(gp_val)
