# -*- coding: utf-8 -*-
import sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
try:
    h = urllib.request.urlopen("http://127.0.0.1:8765/", timeout=10).read().decode("utf-8")
    print("HTML len:", len(h))
    print("含 syncPriceScaleWidth:", "syncPriceScaleWidth" in h)
    print("含 setCrosshairPosition:", "setCrosshairPosition" in h)
    print("含 syncCrosshair:", "syncCrosshair" in h)
    print("含 priceScale('vol'):", "priceScale('vol')" in h)
except Exception as e:
    print("ERR:", e)
