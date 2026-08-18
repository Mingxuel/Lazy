# -*- coding: utf-8 -*-
import sys, json, re
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from AICode.MarcoAPI.StrategyUI import _build_strategy_payload

p = _build_strategy_payload("TPO_3")
# 看 UI 显示的收益统计（month/summary 等）
for k in ["dates", "modes", "month", "quarter", "year"]:
    if k in p:
        v = p[k]
        if isinstance(v, dict):
            print(f"{k}: keys={list(v.keys())[:5]}")
            # 取 last 值
            lastk = list(v.keys())[-1]
            print(f"   {k}[{lastk}] = {v[lastk]}")
        else:
            print(f"{k}: {str(v)[:100]}")
