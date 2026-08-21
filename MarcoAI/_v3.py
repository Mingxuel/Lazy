# -*- coding: utf-8 -*-
import re, json
html = open('AICode/MarcoAPI/UI/StrategyDashboard.html', encoding='utf-8').read()
m = re.search(r'const DATA = (\{.*?\});\n', html, re.S)
data = json.loads(m.group(1))
print('策略列表:', data['strategies'])
print('回测keys:', list(data['backtest'].keys()))
