# -*- coding: utf-8 -*-
import sys, json, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
req = urllib.request.Request("http://127.0.0.1:8765/api/cmd", data=json.dumps({"cmd": "GIT_SYNC"}).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
try:
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    print("ok:", resp.get("ok"))
    print(resp.get("output"))
except Exception as e:
    print("ERR:", e)
