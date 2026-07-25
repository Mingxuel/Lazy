"""
全市场 MA5/MA10 交叉分析
基于 AIData/1D/ 目录下全部个股日线数据，计算：
  - 价格 MA10 < MA5 的股票占比（偏空信号）
  - 成交额 MA10 < MA5 的股票占比（偏空信号）
  - 双空（价格+成交额同时 MA10<MA5）占比
  - 双多（价格+成交额同时 MA10>MA5）占比

与 1D_PRICE 指数走势做对照，输出每日判断。
"""

import os
import sys
from collections import defaultdict
from typing import Optional

DATA_DIR = r"C:\Lazy\MarcoAI\AIData\1D"
PRICE_FILE = r"C:\Lazy\MarcoAI\AIData\1D_PRICE"
OUTPUT_FILE = r"C:\Lazy\MarcoAI\AIData\1D_MA_CROSS"


def load_price_index() -> dict[str, tuple[float, float]]:
    """加载价格指数: date -> (col1, col2)"""
    d = {}
    if not os.path.exists(PRICE_FILE):
        return d
    with open(PRICE_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 2:
                continue
            date = parts[0].strip()
            try:
                v1 = float(parts[1])
                v2 = float(parts[2]) if len(parts) >= 3 else v1
            except ValueError:
                continue
            d[date] = (v1, v2)
    return d


def load_all_stocks() -> dict[str, list[tuple[str, float, float]]]:
    """
    加载所有个股日线
    code -> [(date, close, amount), ...] 按日期排序
    """
    stocks: dict[str, list[tuple[str, float, float]]] = {}
    files = sorted(os.listdir(DATA_DIR))
    for fname in files:
        if not fname.endswith((".SZ", ".SH")):
            continue
        code = os.path.splitext(fname)[0]
        rows = []
        fpath = os.path.join(DATA_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) < 7:
                    continue
                try:
                    date = parts[0].strip()
                    close = float(parts[4])
                    amount = float(parts[6])  # 成交额
                except (ValueError, IndexError):
                    continue
                rows.append((date, close, amount))
        if rows:
            stocks[code] = rows
    return stocks


def compute_ma(values: list[float], window: int) -> Optional[float]:
    """计算最近 N 日移动平均"""
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def analyze():
    print("加载价格指数...")
    prices = load_price_index()
    print(f"  已加载 {len(prices)} 天价格指数")

    print("加载全市场日线...")
    stocks = load_all_stocks()
    print(f"  已加载 {len(stocks)} 只个股")

    # 找出所有日期
    all_dates_set = set()
    for rows in stocks.values():
        for d, _, _ in rows:
            all_dates_set.add(d)
    all_dates = sorted(all_dates_set)

    # 对每个日期，取有完整数据的股票
    print(f"分析日期范围: {all_dates[0]} ~ {all_dates[-1]}")
    print(f"分析天数: {len(all_dates)}")

    results = []

    for day_idx, date in enumerate(all_dates):
        if day_idx < 9:  # 需要至少 10 天历史
            continue

        price_ma10_below_ma5 = 0
        amt_ma10_below_ma5 = 0
        price_ma10_above_ma5 = 0
        amt_ma10_above_ma5 = 0
        total = 0

        for code, rows in stocks.items():
            # 找到这条股票在 date 及之前的数据
            recent = []
            for d, c, a in rows:
                if d <= date:
                    recent.append((c, a))
                else:
                    break

            if len(recent) < 10:
                continue

            closes = [c for c, _ in recent]
            amounts = [a for _, a in recent]

            ma5_p = compute_ma(closes, 5)
            ma10_p = compute_ma(closes, 10)
            ma5_a = compute_ma(amounts, 5)
            ma10_a = compute_ma(amounts, 10)

            if None in (ma5_p, ma10_p, ma5_a, ma10_a):
                continue

            total += 1

            if ma10_p < ma5_p:
                price_ma10_below_ma5 += 1
            elif ma10_p > ma5_p:
                price_ma10_above_ma5 += 1
                # ma10_p == ma5_p: 平着的不算

            if ma10_a < ma5_a:
                amt_ma10_below_ma5 += 1
            elif ma10_a > ma5_a:
                amt_ma10_above_ma5 += 1

        if total == 0:
            continue

        pb = price_ma10_below_ma5 / total * 100
        ab = amt_ma10_below_ma5 / total * 100
        pu = price_ma10_above_ma5 / total * 100
        au = amt_ma10_above_ma5 / total * 100

        dual_bear = min(pb, ab)  # 价格+成交额 双空的比例
        dual_bull = min(pu, au)  # 双多的比例

        # 价格指数
        pi = prices.get(date, (0, 0))
        idx_val = pi[1] if pi[1] else pi[0]

        prev_date = all_dates[day_idx - 1]
        prev_pi = prices.get(prev_date, (0, 0))
        prev_idx = prev_pi[1] if prev_pi[1] else prev_pi[0]

        mkt_change = (idx_val - prev_idx) / prev_idx * 100 if prev_idx else 0

        # 判断
        if dual_bear > 55:
            judgment = "🔴 强偏空"
        elif dual_bear > dual_bull + 1:
            judgment = "🟠 偏空"
        elif dual_bull > 55:
            judgment = "🟢 强偏多"
        elif dual_bull > dual_bear + 1:
            judgment = "🟢 偏多"
        else:
            judgment = "🟡 中性"

        results.append(
            {
                "date": date,
                "pb": pb,
                "ab": ab,
                "pu": pu,
                "au": au,
                "dual_bear": dual_bear,
                "dual_bull": dual_bull,
                "idx_val": idx_val,
                "mkt_change": mkt_change,
                "judgment": judgment,
                "total": total,
            }
        )

    # 输出最近 60 天
    print()
    header = f"{'日期':>10s} | {'价MA10<MA5':>8s} | {'额MA10<MA5':>8s} | {'双空':>6s} | {'双多':>6s} | {'指数':>10s} | {'市场':>7s} | 判断"
    print(header)
    print("-" * len(header))

    recent = results[-60:]
    for r in recent:
        print(
            f"{r['date']:>10s} | {r['pb']:6.1f}% | {r['ab']:6.1f}% | {r['dual_bear']:4.1f}% | {r['dual_bull']:4.1f}% | {r['idx_val']:10.4f} | {r['mkt_change']:+6.2f}% | {r['judgment']} ({r['total']}只)"
        )

    # 写输出文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in results:
            f.write(
                f"{r['date']}|{r['dual_bear']:.2f}|{r['dual_bull']:.2f}|{r['pb']:.2f}|{r['ab']:.2f}|{r['pu']:.2f}|{r['au']:.2f}|{r['judgment']}\n"
            )
    print(f"\n✅ 已写 {OUTPUT_FILE}，共 {len(results)} 天")

    # 统计：双空 > 50% 时，次日市场走势
    print("\n=== 回测：双空 > 50% 次日市场表现 ===")
    bear_next = []
    for i, r in enumerate(results):
        if r["dual_bear"] > 50 and i + 1 < len(results):
            nxt = results[i + 1]
            bear_next.append((r["date"], r["dual_bear"], nxt["mkt_change"]))

    if bear_next:
        wins = sum(1 for _, _, c in bear_next if c > 0)
        avg = sum(c for _, _, c in bear_next) / len(bear_next)
        print(f"  出现 {len(bear_next)} 次双空>50%")
        print(f"  次日上涨 {wins} 次 ({wins/len(bear_next)*100:.0f}%)")
        print(f"  次日平均: {avg:+.2f}%")
        for d, db, n in bear_next[-10:]:
            print(f"    {d} 双空={db:.1f}% → 次日 {n:+.2f}%")

    # 统计：双多 > 50% 时，次日市场走势
    print("\n=== 回测：双多 > 50% 次日市场表现 ===")
    bull_next = []
    for i, r in enumerate(results):
        if r["dual_bull"] > 50 and i + 1 < len(results):
            nxt = results[i + 1]
            bull_next.append((r["date"], r["dual_bull"], nxt["mkt_change"]))

    if bull_next:
        wins = sum(1 for _, _, c in bull_next if c > 0)
        avg = sum(c for _, _, c in bull_next) / len(bull_next)
        print(f"  出现 {len(bull_next)} 次双多>50%")
        print(f"  次日上涨 {wins} 次 ({wins/len(bull_next)*100:.0f}%)")
        print(f"  次日平均: {avg:+.2f}%")
        for d, db, n in bull_next[-10:]:
            print(f"    {d} 双多={db:.1f}% → 次日 {n:+.2f}%")


if __name__ == "__main__":
    analyze()
