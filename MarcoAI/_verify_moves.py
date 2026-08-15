import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"e:/Lazy")

mods = [
    "AICode.MarcoAPI.Update.Constants",
    "AICode.MarcoAPI.Update.Path",
    "AICode.MarcoAPI.Update.Data",
    "AICode.MarcoAPI.Update.DataAligned",
    "AICode.MarcoAPI.Update.StockCodes",
    "AICode.MarcoAPI.Update.TradingDates",
    "AICode.MarcoAPI.Update.SZ2001D",
    "AICode.MarcoAPI.Update.SZ2001DMOTION",
    "AICode.MarcoAPI.Update.SZ2005M",
    "AICode.MarcoAPI.Update.SZ200Bottom",
    "AICode.MarcoAPI.Update.SZ200Motion1D",
    "AICode.MarcoAPI.Update.SZ200Motion5M",
    "AICode.MarcoAPI.Update.SZ200Target",
    "AICode.MarcoAPI.Update.SZ200Top",
    "AICode.MarcoAPI.Account",
    "AICode.MarcoAPI.KLine",
    "AICode.MarcoAPI.EntryTimingAnalysis",
]
import importlib
ok = True
for m in mods:
    try:
        importlib.import_module(m)
        print(f"OK   {m}")
    except Exception as e:
        ok = False
        print(f"FAIL {m}: {type(e).__name__}: {e}")
print("\nALL OK" if ok else "\nSOME FAILED")
