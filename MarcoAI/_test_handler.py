# -*- coding: utf-8 -*-
import sys, io, urllib.parse
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

# 模拟 Handler 的参数解析
def parse_url(url):
    parsed = urllib.parse.urlparse(url)
    return dict(urllib.parse.parse_qsl(parsed.query))

print("测试1 - 数据更新:", parse_url("marcoai://run?cmd=UPDATE_DATA"))
print("测试2 - 同花顺:", parse_url("marcoai://run?cmd=UPDATE_THS&strategy=TPO31"))
print("测试3 - git:", parse_url("marcoai://run?cmd=GIT_SYNC"))

# 测试命令分发逻辑（GIT_SYNC 不涉及实盘机写入，安全）
from AICode.MarcoAPI.StrategyService import GIT_SYNC
out = GIT_SYNC()
print("\nGIT_SYNC 结果（后3行）:")
print("\n".join(out.splitlines()[-3:]))
