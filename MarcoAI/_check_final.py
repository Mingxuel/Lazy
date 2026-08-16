# -*- coding: utf-8 -*-
import sys, re, subprocess, os, shutil
sys.stdout.reconfigure(encoding="utf-8")
html = open(r"e:\Lazy\MarcoAI\AICode\MarcoAPI\UI\StrategyDashboard.html", encoding="utf-8").read()
scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
os.makedirs("_js_tmp", exist_ok=True)
ok = True
for i, s in enumerate(scripts):
    p = os.path.join("_js_tmp", f"inline_{i}.js")
    open(p, "w", encoding="utf-8").write(s)
    r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"JS[{i}]: OK")
    else:
        ok = False
        print(f"JS[{i}]: SYNTAX ERROR\n{r.stderr[:600]}")
# 检查关键结构
for kw in ["kline-main", "kline-ind", "calcMACD", "calcKDJ", "calcBOLL", "calcVWAP", "aggregateMonthly", "initKlineControls", "kline-ma-btn"]:
    print(f"含 {kw}:", kw in html)
shutil.rmtree("_js_tmp", ignore_errors=True)
