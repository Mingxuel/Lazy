from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class DATA_1D:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float

@dataclass
class DATA_5M:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float

@dataclass
class DATA_1D_TARGET:
    stock_code: str
    stock_name: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    pre_close: float
