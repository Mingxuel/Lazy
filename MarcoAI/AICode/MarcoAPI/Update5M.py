import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.SZ2005M import UPDATE_5M_ALL
from AICode.MarcoAPI.SZ200Motion5M import (
    CALCULATE_SZ200_MOTION_5M_PRICE,
    CALCULATE_SZ200_MOTION_5M_PRICE_VOLUME,
    CALCULATE_SZ200_MOTION_5M_WIN_COUNT,
    CALCULATE_SZ200_MOTION_5M_SIGNALS,
)
from AICode.MarcoAPI.SZ2001DMOTION import UPDATE_5M_MOTION_COUNT
from AICode.MarcoAPI.UI.UITarget import SHOW_5M_MOTION

if __name__ == "__main__":
    SHOW_ONLY = False
    #SHOW_ONLY = True
    if SHOW_ONLY:
        SHOW_5M_MOTION()
        exit(0)

    print("UPDATE_5M_ALL BEGIN")
    UPDATE_5M_ALL()
    print("UPDATE_5M_ALL END")

    print("UPDATE_5M_MOTION_COUNT BEGIN")
    UPDATE_5M_MOTION_COUNT()
    print("UPDATE_5M_MOTION_COUNT END")

    print("SHOW_5M_MOTION BEGIN")
    SHOW_5M_MOTION()
    print("SHOW_5M_MOTION END")
