"""
miniQMT 基础 API 测试 — 获取账户信息
运行前提：miniQMT 已打开并登录
"""

import time
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount

# ============================================================
# 配置区
# ============================================================
ACCOUNT_ID = "80391095"                     # 江海证券账户
USERDATA_DIR = r"C:\江海证券QMT实盘_交易\userdata_mini"  # 数据保存目录（C盘）

# ============================================================
# 1. 连接 miniQMT
# ============================================================
def connect_trader():
    session_id = int(time.time())
    trader = XtQuantTrader(USERDATA_DIR, session_id)
    account = StockAccount(ACCOUNT_ID)

    # 启动交易服务
    trader.start()

    # 连接
    connect_result = trader.connect()
    if connect_result != 0:
        print(f"[ERROR] 连接失败, 返回码: {connect_result}")
        print("请确认 miniQMT 已启动并登录")
        return None, None

    # 订阅账户
    subscribe_result = trader.subscribe(account)
    if subscribe_result != 0:
        print(f"[ERROR] 订阅账户失败, 返回码: {subscribe_result}")
        return None, None

    print("[OK] miniQMT 连接成功")
    return trader, account

# ============================================================
# 2. 查询账户资产
# ============================================================
def query_asset(trader, account):
    """查询账户资产信息"""
    asset = trader.query_stock_asset(account)
    if asset is None:
        print("[ERROR] 查询资产失败")
        return

    print("\n" + "=" * 50)
    print("💰 账户资产")
    print("=" * 50)
    print(f"  账户ID:     {asset.account_id}")
    print(f"  总资产:     {asset.total_asset:,.2f}")
    print(f"  可用资金:   {asset.cash:,.2f}")
    print(f"  冻结资金:   {asset.frozen_cash:,.2f}")
    print(f"  持仓市值:   {asset.market_value:,.2f}")

# ============================================================
# 3. 查询持仓
# ============================================================
def query_positions(trader, account):
    """查询当前持仓"""
    positions = trader.query_stock_positions(account)
    if positions is None or len(positions) == 0:
        print("\n📭 当前无持仓")
        return

    print("\n" + "=" * 80)
    print("📦 当前持仓")
    print("=" * 80)
    print(f"{'代码':<12s} {'名称':<10s} {'持仓量':>8s} {'可用':>8s} {'成本价':>10s} {'现价':>8s} {'盈亏':>10s} {'盈亏%':>8s}")
    print("-" * 80)

    for p in positions:
        # 现价需要从行情获取
        try:
            tick = xtdata.get_full_tick([p.stock_code])
            if p.stock_code in tick:
                current_price = tick[p.stock_code]['lastPrice']
            else:
                current_price = 0
        except:
            current_price = 0

        profit = (current_price - p.avg_price) * p.volume if current_price else 0
        profit_pct = (current_price - p.avg_price) / p.avg_price * 100 if p.avg_price and current_price else 0

        code_short = p.stock_code.split('.')[0] if '.' in p.stock_code else p.stock_code
        name = getattr(p, 'stock_name', '') or code_short

        print(f"{code_short:<12s} {name:<10s} {p.volume:>8d} {p.can_use_volume:>8d} "
              f"{p.avg_price:>10.2f} {current_price:>8.2f} {profit:>10.2f} {profit_pct:>7.2f}%")

    print("-" * 80)

# ============================================================
# 4. 查询当日委托
# ============================================================
def query_orders(trader, account):
    """查询当日委托"""
    orders = trader.query_stock_orders(account)
    if orders is None or len(orders) == 0:
        print("\n📭 今日无委托")
        return

    print("\n" + "=" * 80)
    print("📋 今日委托")
    print("=" * 80)

    status_map = {
        48: "未报", 49: "待报", 50: "已报", 51: "已报待撤",
        52: "部成待撤", 53: "部撤", 54: "已撤", 55: "部成",
        56: "已成", 57: "废单"
    }

    for o in orders:
        code_short = o.stock_code.split('.')[0] if '.' in o.stock_code else o.stock_code
        status = status_map.get(o.order_status, str(o.order_status))
        side = "买" if o.order_type == 23 else "卖"
        print(f"  {code_short:<10s} {side} {o.order_volume:>6d}股  "
              f"价格:{o.price:>8.2f}  状态:{status}  编号:{o.order_id}")

# ============================================================
# 5. 查询当日成交
# ============================================================
def query_trades(trader, account):
    """查询当日成交"""
    trades = trader.query_stock_trades(account)
    if trades is None or len(trades) == 0:
        print("\n📭 今日无成交")
        return

    print("\n" + "=" * 80)
    print("✅ 今日成交")
    print("=" * 80)

    for t in trades:
        code_short = t.stock_code.split('.')[0] if '.' in t.stock_code else t.stock_code
        side = "买" if t.direction == 1 else "卖"
        print(f"  {code_short:<10s} {side} {t.traded_volume:>6d}股  "
              f"价格:{t.traded_price:>8.2f}  金额:{t.traded_amount:>12.2f}  "
              f"时间:{t.traded_time}")

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("miniQMT 账户信息查询")
    print("-" * 50)

    # 连接
    xtdata.enable_hello = False
    trader, account = connect_trader()
    if trader is None:
        exit(1)

    # 查询
    query_asset(trader, account)
    query_positions(trader, account)
    query_orders(trader, account)
    query_trades(trader, account)

    print("\n[OK] 查询完毕")
