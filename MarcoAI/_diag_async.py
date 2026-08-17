# -*- coding: utf-8 -*-
import sys, json, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
try:
    d = json.loads(urllib.request.urlopen("http://127.0.0.1:8765/api/update_log", timeout=10).read().decode("utf-8"))
    print("running:", d.get("running"), "done:", d.get("done"))
    print("log 长度:", len(d.get("log","")))
    print("log 前800字符:")
    print(d.get("log","")[:800])
except Exception as e:
    print("ERR:", e)
