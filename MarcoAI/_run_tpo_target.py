import sys

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, r"e:/Lazy")
    from AICode.MarcoAPI.Update.SZ200Strategy import UPDATE_TARGET_TPO32, UPDATE_TARGET_TPO33

    UPDATE_TARGET_TPO32()
    print("DONE_TPO32")
    UPDATE_TARGET_TPO33()
    print("DONE_TPO33")
