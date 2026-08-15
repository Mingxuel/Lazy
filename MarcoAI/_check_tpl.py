# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
raw = open(r"e:\Lazy\MarcoAI\AIData\THS\blockstockV3.xml", encoding="utf-8").read()
print("=== 模板 repr ===")
print(repr(raw))
print("\n=== 模板显示 ===")
print(raw)
