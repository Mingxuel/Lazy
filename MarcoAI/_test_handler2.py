# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
# 直接调用 Handler 的 main，模拟协议唤起（传入 URL 参数）
from AICode.MarcoAPI import MarcoAI_Handler as H
# 用 GIT_SYNC 命令（无实盘机副作用）
H.main(["MarcoAI_Handler.py", "marcoai://run?cmd=GIT_SYNC"])
print("Handler 主流程执行完毕")
# 检查日志
log = os.path.join("AIData", "run.log")
if os.path.isfile(log):
    lines = open(log, encoding="utf-8").read().strip().splitlines()
    print("日志末行:", lines[-1] if lines else "空")
