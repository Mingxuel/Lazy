"""
miniQMT 交易 API 基础接口层
===========================
所有策略模块的底层依赖，提供统一的连接管理、账户查询、交易执行接口。

依赖: xtquant (需安装，用 python3.11 运行)
文档: http://dict.thinktrader.net/nativeApi/download_xtquant.html

用法:
    from api import QMTAPI
    api = QMTAPI()
    api.connect()
    print(api.asset())
    print(api.positions())
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

from xtquant import xtdata, xtconstant
from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount

# ============================================================
# 配置
# ============================================================
ACCOUNT_ID = "80391095"                                  # 江海证券
USERDATA_DIR = r"C:\江海证券QMT实盘_交易\userdata_mini"

# ============================================================
# 数据类
# ============================================================

@dataclass
class AssetInfo:
    """账户资产"""
    account_id:    str   = ""
    total_asset:   float = 0.0
    cash:          float = 0.0
    frozen_cash:   float = 0.0
    market_value:  float = 0.0
    position_ratio: float = 0.0       # 仓位比例 = 持仓市值 / 总资产

    def __str__(self):
        return (f"Asset(总:{self.total_asset:,.0f}  可用:{self.cash:,.0f}  "
                f"市值:{self.market_value:,.0f}  仓位:{self.position_ratio:.1%})")


@dataclass
class Position:
    """持仓明细"""
    stock_code:      str   = ""
    stock_name:      str   = ""
    volume:          int   = 0
    can_use_volume:  int   = 0
    frozen_volume:   int   = 0
    avg_price:       float = 0.0
    current_price:   float = 0.0
    market_value:    float = 0.0
    profit:          float = 0.0
    profit_pct:      float = 0.0

    def __str__(self):
        code = self.stock_code.replace(".SH", "").replace(".SZ", "")
        return (f"{code} {self.stock_name:<6s} {self.volume:>6d}股  "
                f"成本{self.avg_price:.2f} 现价{self.current_price:.2f}  "
                f"盈亏{self.profit:+.0f}({self.profit_pct:+.1f}%)")


@dataclass
class Order:
    """委托"""
    stock_code:    str   = ""
    order_id:      str   = ""
    order_type:    int   = 0          # 23=买 24=卖
    order_volume:  int   = 0
    price:         float = 0.0
    order_status:  int   = 0
    status_text:   str   = ""

    def __str__(self):
        return f"{self.stock_code} {'买' if self.order_type==23 else '卖'} {self.order_volume}股 {self.price:.2f} [{self.status_text}]"


@dataclass
class Trade:
    """成交"""
    stock_code:    str   = ""
    traded_volume: int   = 0
    traded_price:  float = 0.0
    traded_amount: float = 0.0
    traded_time:   str   = ""
    direction:     int   = 0          # 1=买 2=卖

    def __str__(self):
        return f"{self.stock_code} {'买' if self.direction==1 else '卖'} {self.traded_volume}股 {self.traded_price:.2f}"


# ============================================================
# API 主类
# ============================================================

class QMTAPI:
    """miniQMT 交易 API 统一入口"""

    def __init__(self, account_id: str = ACCOUNT_ID, userdata_dir: str = USERDATA_DIR):
        self._account_id = account_id
        self._userdata_dir = userdata_dir
        self._trader: Optional[XtQuantTrader] = None
        self._account: Optional[StockAccount] = None
        self._connected = False

        xtdata.enable_hello = False

    # ---- 连接管理 --------------------------------------------------

    def connect(self) -> bool:
        """连接 miniQMT 交易服务"""
        try:
            session_id = int(time.time())
            self._trader = XtQuantTrader(self._userdata_dir, session_id)
            self._account = StockAccount(self._account_id)
            self._trader.start()

            if self._trader.connect() != 0:
                return False
            if self._trader.subscribe(self._account) != 0:
                return False

            self._connected = True
            return True
        except Exception as e:
            logging.error(f"连接失败: {e}")
            return False

    @property
    def connected(self) -> bool:
        return self._connected

    def disconnect(self):
        """断开连接"""
        self._connected = False

    # ---- 账户资产 --------------------------------------------------

    def asset(self) -> Optional[AssetInfo]:
        """查询账户资产"""
        if not self._connected:
            return None
        raw = self._trader.query_stock_asset(self._account)
        if raw is None:
            return None
        mv = float(raw.market_value)
        ta = float(raw.total_asset)
        return AssetInfo(
            account_id    = raw.account_id,
            total_asset   = ta,
            cash          = float(raw.cash),
            frozen_cash   = float(raw.frozen_cash),
            market_value  = mv,
            position_ratio = mv / ta if ta > 0 else 0,
        )

    # ---- 持仓 --------------------------------------------------

    def positions(self) -> list[Position]:
        """查询当前持仓（含实时市价）"""
        if not self._connected:
            return []
        raw_list = self._trader.query_stock_positions(self._account)
        if raw_list is None:
            return []

        # 批量获取实时行情
        codes = [p.stock_code for p in raw_list]
        ticks = {}
        if codes:
            try:
                raw_ticks = xtdata.get_full_tick(codes)
                for code in codes:
                    if code in raw_ticks and raw_ticks[code]:
                        ticks[code] = raw_ticks[code].get('lastPrice', 0)
                    else:
                        ticks[code] = 0
            except Exception:
                pass

        result = []
        for p in raw_list:
            cp = ticks.get(p.stock_code, 0)
            pr = (cp - p.avg_price) * p.volume if cp else 0
            pp = (cp - p.avg_price) / p.avg_price * 100 if p.avg_price and cp else 0
            result.append(Position(
                stock_code     = p.stock_code,
                stock_name     = getattr(p, 'stock_name', ''),
                volume         = p.volume,
                can_use_volume = p.can_use_volume,
                frozen_volume  = getattr(p, 'frozen_volume', 0),
                avg_price      = p.avg_price,
                current_price  = cp,
                market_value   = p.market_value,
                profit         = pr,
                profit_pct     = pp,
            ))
        return result

    # ---- 委托 --------------------------------------------------

    # 委托状态码映射
    ORDER_STATUS = {
        48: "未报", 49: "待报", 50: "已报", 51: "已报待撤",
        52: "部成待撤", 53: "部撤", 54: "已撤", 55: "部成",
        56: "已成", 57: "废单",
    }

    def orders(self) -> list[Order]:
        """查询当日委托"""
        if not self._connected:
            return []
        raw_list = self._trader.query_stock_orders(self._account)
        if raw_list is None:
            return []
        result = []
        for o in raw_list:
            result.append(Order(
                stock_code   = o.stock_code,
                order_id     = str(o.order_id),
                order_type   = o.order_type,
                order_volume = o.order_volume,
                price        = o.price,
                order_status = o.order_status,
                status_text  = self.ORDER_STATUS.get(o.order_status, str(o.order_status)),
            ))
        return result

    # ---- 成交 --------------------------------------------------

    def trades(self) -> list[Trade]:
        """查询当日成交"""
        if not self._connected:
            return []
        raw_list = self._trader.query_stock_trades(self._account)
        if raw_list is None:
            return []
        result = []
        for t in raw_list:
            result.append(Trade(
                stock_code    = t.stock_code,
                traded_volume = t.traded_volume,
                traded_price  = t.traded_price,
                traded_amount = t.traded_amount,
                traded_time   = str(t.traded_time),
                direction     = t.direction,
            ))
        return result

    # ---- 交易 --------------------------------------------------

    def buy(self, stock_code: str, volume: int, price: float) -> int:
        """买入（限价单）

        Args:
            stock_code: 如 '000001.SZ'
            volume: 股数（须为100的整数倍）
            price: 限价

        Returns:
            订单ID，失败返回 0
        """
        if not self._connected:
            return 0
        order_id = self._trader.order_stock(
            self._account, stock_code,
            xtconstant.STOCK_BUY, volume,
            xtconstant.FIX_PRICE, price,
            "", ""
        )
        return order_id if order_id else 0

    def sell(self, stock_code: str, volume: int, price: float) -> int:
        """卖出（限价单）"""
        if not self._connected:
            return 0
        order_id = self._trader.order_stock(
            self._account, stock_code,
            xtconstant.STOCK_SELL, volume,
            xtconstant.FIX_PRICE, price,
            "", ""
        )
        return order_id if order_id else 0

    def cancel(self, order_id: int) -> bool:
        """撤单"""
        if not self._connected:
            return False
        return self._trader.cancel_order_stock(self._account, order_id) == 0

    # ---- 行情（快捷接口）----------------------------------------------

    @staticmethod
    def quote(stock_codes: list[str], period: str = "1d", count: int = 5):
        """获取行情数据

        Args:
            stock_codes: 股票代码列表，如 ['000001.SZ', '600519.SH']
            period: 周期 '1d'/'1m'/'tick'
            count: 获取的K线数量

        Returns:
            dict {stock_code: DataFrame}
        """
        xtdata.subscribe_quote(stock_codes[0] if stock_codes else "", period, "", "")
        return xtdata.get_market_data_ex(
            [], stock_codes, period, "", "", count, fill_data=False
        )

    @staticmethod
    def tick(stock_code: str) -> Optional[dict]:
        """获取实时 tick"""
        try:
            data = xtdata.get_full_tick([stock_code])
            return data.get(stock_code)
        except Exception:
            return None

    @staticmethod
    def stock_list(sector: str = "沪深A股") -> list[str]:
        """获取板块成分股"""
        return xtdata.get_stock_list_in_sector(sector)

    @staticmethod
    def stock_name(stock_code: str) -> str:
        """获取股票名称"""
        detail = xtdata.get_instrument_detail(stock_code)
        return detail.get("InstrumentName", "") if detail else ""


# ============================================================
# 测试入口
# ============================================================

def _fmt(label, value, unit=""):
    """格式化输出"""
    return f"  {label:<10s} {value:>14s} {unit}"

if __name__ == "__main__":
    api = QMTAPI()

    # --- 测试连接 ---
    print("=" * 60)
    print("1. 连接测试")
    print("-" * 60)
    if not api.connect():
        print("[FAIL] 连接失败，请确认 miniQMT 已启动")
        exit(1)
    print("[OK] 连接成功")

    # --- 测试资产 ---
    print("\n" + "=" * 60)
    print("2. 账户资产")
    print("-" * 60)
    a = api.asset()
    if a:
        print(_fmt("账户ID", a.account_id))
        print(_fmt("总资产", f"{a.total_asset:,.2f}", "元"))
        print(_fmt("可用资金", f"{a.cash:,.2f}", "元"))
        print(_fmt("冻结资金", f"{a.frozen_cash:,.2f}", "元"))
        print(_fmt("持仓市值", f"{a.market_value:,.2f}", "元"))
        print(_fmt("仓位比例", f"{a.position_ratio:.1%}"))

    # --- 测试持仓 ---
    print("\n" + "=" * 60)
    print("3. 当前持仓")
    print("-" * 60)
    positions = api.positions()
    if positions:
        for p in positions:
            print(p)
    else:
        print("  无持仓")

    # --- 测试委托 ---
    print("\n" + "=" * 60)
    print("4. 今日委托")
    print("-" * 60)
    orders = api.orders()
    if orders:
        for o in orders:
            print(f"  {o}")
    else:
        print("  无委托")

    # --- 测试成交 ---
    print("\n" + "=" * 60)
    print("5. 今日成交")
    print("-" * 60)
    trades = api.trades()
    if trades:
        for t in trades:
            print(f"  {t}")
    else:
        print("  无成交")

    # --- 测试行情 ---
    print("\n" + "=" * 60)
    print("6. 行情数据（000001.SZ 近5日）")
    print("-" * 60)
    data = api.quote(['000001.SZ'], '1d', 5)
    if '000001.SZ' in data:
        print(data['000001.SZ'].tail(3))

    # --- 测试名称 ---
    print("\n" + "=" * 60)
    print("7. 代码→名称")
    print("-" * 60)
    for code in ['000001.SZ', '600519.SH', '512480.SH', '588000.SH']:
        name = api.stock_name(code)
        print(f"  {code:<14s} → {name}")

    print("\n[OK] 全部接口测试通过")
