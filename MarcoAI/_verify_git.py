# -*- coding: utf-8 -*-
import sys, os, re, subprocess, json, threading, urllib.request
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

# 1. 重新生成 HTML
from AICode.MarcoAPI.StrategyUI import GENERATE_STRATEGY_UI
GENERATE_STRATEGY_UI(open_browser=False)
print("HTML regenerated")

# 2. 检查 HTML 中 git 同步按钮
html = open(r"e:\Lazy\MarcoAI\AICode\MarcoAPI\UI\StrategyDashboard.html", encoding="utf-8").read()
print("含 git同步按钮:", "git 同步" in html)
print("含 onClickGitSync:", "onClickGitSync" in html)

# 3. 验证 JS 语法
scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
os.makedirs("_js_tmp", exist_ok=True)
for i, s in enumerate(scripts):
    p = os.path.join("_js_tmp", f"inline_{i}.js")
    open(p, "w", encoding="utf-8").write(s)
    r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
    print(f"JS[{i}]:", "OK" if r.returncode == 0 else "SYNTAX ERROR\n" + r.stderr)

# 4. 测试 GIT_SYNC 接口（子线程启动服务）
from AICode.MarcoAPI.StrategyService import StrategyHandler
from http.server import ThreadingHTTPServer
srv = ThreadingHTTPServer(("127.0.0.1", 8772), StrategyHandler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
req = urllib.request.Request("http://127.0.0.1:8772/api/cmd", data=json.dumps({"cmd": "GIT_SYNC"}).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
resp = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
print("\n=== GIT_SYNC 返回 ===")
print("ok:", resp.get("ok"))
print(resp.get("output"))
srv.shutdown()

import shutil
shutil.rmtree("_js_tmp", ignore_errors=True)
