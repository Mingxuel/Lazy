"""
全量回测：MA5/MA10 交叉趋势分析（覆盖全部可用数据，约1.5年）
核心理念：偏向增加的股票数量在增加 = 市场变好，反之亦然
"""

import os
from typing import Optional

DATA_DIR = r"C:\Lazy\MarcoAI\AIData\1D"
PRICE_FILE = r"C:\Lazy\MarcoAI\AIData\1D_PRICE"


def load_price_index() -> dict[str, tuple[float, float]]:
    d = {}
    with open(PRICE_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 2:
                continue
            try:
                v1 = float(parts[1])
                v2 = float(parts[2]) if len(parts) >= 3 else v1
            except ValueError:
                continue
            d[parts[0].strip()] = (v1, v2)
    return d


def load_all() -> dict[str, list[tuple[str, float, float]]]:
    stocks: dict[str, list[tuple[str, float, float]]] = {}
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith((".SZ", ".SH")):
            continue
        rows: list[tuple[str, float, float]] = []
        with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
            for line in f:
                p = line.strip().split("|")
                if len(p) < 7:
                    continue
                try:
                    rows.append((p[0].strip(), float(p[4]), float(p[6])))
                except (ValueError, IndexError):
                    continue
        if rows:
            stocks[os.path.splitext(fname)[0]] = rows
    return stocks


def ma(vals: list[float], w: int) -> Optional[float]:
    if len(vals) < w:
        return None
    return sum(vals[-w:]) / w


def analyze():
    print("加载数据...")
    prices = load_price_index()
    stocks = load_all()
    all_dates = sorted({d for rows in stocks.values() for d, _, _ in rows})
    print("{}只个股 × {}天 = {} 数据范围".format(len(stocks), len(all_dates), all_dates[0] + "~" + all_dates[-1]))

    # 逐日计算双空/双多
    results: list[dict] = []
    date_index: dict[str, int] = {}

    for di, date in enumerate(all_dates):
        if di < 9:
            continue
        pb = ab = pu = au = tot = 0
        for code, rows in stocks.items():
            recent = [(c, a) for d, c, a in rows if d <= date]
            if len(recent) < 10:
                continue
            cl = [c for c, _ in recent]
            am = [a for _, a in recent]
            m5p, m10p = ma(cl, 5), ma(cl, 10)
            m5a, m10a = ma(am, 5), ma(am, 10)
            if None in (m5p, m10p, m5a, m10a):
                continue
            tot += 1
            if m10p < m5p:
                pb += 1
            elif m10p > m5p:
                pu += 1
            if m10a < m5a:
                ab += 1
            elif m10a > m5a:
                au += 1
        if tot == 0:
            continue

        pi = prices.get(date, (0, 0))
        idx = pi[1] if pi[1] else pi[0]
        prev_date = all_dates[di - 1]
        prev_pi = prices.get(prev_date, (0, 0))
        pidx = prev_pi[1] if prev_pi[1] else prev_pi[0]
        mkt = (idx - pidx) / pidx * 100 if pidx else 0

        results.append(
            {
                "date": date,
                "idx": di,
                "dual_bear": min(pb, ab) / tot * 100,
                "dual_bull": min(pu, au) / tot * 100,
                "mkt": mkt,
                "tot": tot,
            }
        )
        date_index[date] = len(results) - 1

    n = len(results)
    print("有效交易日: {} 天".format(n))

    # 计算变化量
    for i in range(n):
        if i == 0:
            results[i]["d_bear"] = 0.0
            results[i]["d_bull"] = 0.0
        else:
            results[i]["d_bear"] = results[i]["dual_bear"] - results[i - 1]["dual_bear"]
            results[i]["d_bull"] = results[i]["dual_bull"] - results[i - 1]["dual_bull"]

    # 标记双改善/双恶化日
    for r in results:
        r["improve"] = r["d_bear"] < -0.5 and r["d_bull"] > 0.5
        r["worsen"] = r["d_bear"] > 0.5 and r["d_bull"] < -0.5

    # ====== 测试框架 ======
    def cum_return(start_idx: int, days: int) -> tuple[float, int]:
        """从 start_idx 之后，未来 days 天的累计收益和上涨天数"""
        total = 0.0
        up = 0
        for k in range(start_idx, min(start_idx + days, n)):
            total += results[k]["mkt"]
            if results[k]["mkt"] > 0:
                up += 1
        return total, up

    # ====== 多窗口测试 ======
    print()
    print("=" * 80)
    print("全量回测结果（{} ~ {}）".format(results[0]["date"], results[-1]["date"]))
    print("=" * 80)

    scenarios = [
        # (名称, 条件函数, 未来窗口)
        ("绝对值: 双空>50%", lambda i: results[i]["dual_bear"] > 50, [1, 3, 5, 10]),
        ("绝对值: 双多>50%", lambda i: results[i]["dual_bull"] > 50, [1, 3, 5, 10]),
        ("趋势: 双空↓>1%（改善）", lambda i: results[i]["d_bear"] < -1, [1, 3, 5, 10]),
        ("趋势: 双多↑>1%（改善）", lambda i: results[i]["d_bull"] > 1, [1, 3, 5, 10]),
        ("趋势: 双改善日", lambda i: results[i]["improve"], [1, 3, 5, 10]),
        ("趋势: 双恶化日", lambda i: results[i]["worsen"], [1, 3, 5, 10]),
        ("趋势: 双空↓>2%", lambda i: results[i]["d_bear"] < -2, [1, 3, 5, 10]),
        ("趋势: 双多↑>2%", lambda i: results[i]["d_bull"] > 2, [1, 3, 5, 10]),
    ]

    fmt_header = "{:35s} | {:>5s} | {:>5s} {:>7s} | {:>5s} {:>7s} | {:>5s} {:>7s} | {:>5s} {:>7s}"
    print(fmt_header.format("信号", "样本", "1日胜", "1日均", "3日胜", "3日均", "5日胜", "5日均", "10日胜", "10日均"))
    print("-" * 100)

    for name, condition, windows in scenarios:
        samples = [i for i in range(n - 10) if condition(i)]
        if not samples:
            continue

        row = "{:35s} | {:4d}".format(name, len(samples))
        for w in windows:
            returns = [cum_return(i, w) for i in samples]
            valid = [(t, u) for t, u in returns if u > 0 or t != 0]
            if not valid:
                row += " |   -       -  "
                continue
            win_rate = sum(1 for t, u in valid if t > 0) / len(valid) * 100
            avg = sum(t for t, _ in valid) / len(valid)
            row += " | {:4.0f}% {:+6.2f}%".format(win_rate, avg)
        print(row)

    # ====== 连续 N 天 ======
    print()
    print("=" * 80)
    print("连续窗口累积效应")
    print("=" * 80)

    for streak_days in [2, 3, 4, 5]:
        improve_streaks = []
        worsen_streaks = []
        for i in range(n - streak_days - 5):
            imp_count = sum(1 for j in range(i, i + streak_days) if results[j]["improve"])
            wor_count = sum(1 for j in range(i, i + streak_days) if results[j]["worsen"])
            if imp_count == streak_days:
                r3, u3 = cum_return(i + streak_days, 3)
                r5, u5 = cum_return(i + streak_days, 5)
                improve_streaks.append((r3, r5))
            if wor_count == streak_days:
                r3, u3 = cum_return(i + streak_days, 3)
                r5, u5 = cum_return(i + streak_days, 5)
                worsen_streaks.append((r3, r5))

        for label, data in [("连续{}天双改善".format(streak_days), improve_streaks),
                             ("连续{}天双恶化".format(streak_days), worsen_streaks)]:
            if not data:
                continue
            wr3 = sum(1 for r, _ in data if r > 0) / len(data) * 100
            av3 = sum(r for r, _ in data) / len(data)
            wr5 = sum(1 for _, r in data if r > 0) / len(data) * 100
            av5 = sum(r for _, r in data) / len(data)
            print("{:20s}: {:3d}次, 3日后 {:4.0f}%({:+.2f}%), 5日后 {:4.0f}%({:+.2f}%)".format(
                label, len(data), wr3, av3, wr5, av5
            ))

    # ====== 双空斜率 ======
    print()
    print("=" * 80)
    print("双空斜率（5日变化速度）vs 后续表现")
    print("=" * 80)

    for slope_range in [
        ("急升 >+8%（快速恶化）", lambda d: d > 8),
        ("缓升 +3~8%（缓慢恶化）", lambda d: 3 <= d <= 8),
        ("横盘 ±3%（中性）", lambda d: -3 < d < 3),
        ("缓降 -3~-8%（缓慢改善）", lambda d: -8 <= d <= -3),
        ("急降 <-8%（快速改善）", lambda d: d < -8),
    ]:
        samples_3 = []
        samples_10 = []
        for i in range(5, n - 10):
            slope_5d = results[i]["dual_bear"] - results[i - 5]["dual_bear"]
            if slope_range[1](slope_5d):
                r3, _ = cum_return(i, 3)
                r10, _ = cum_return(i, 10)
                samples_3.append(r3)
                samples_10.append(r10)
        if samples_3:
            wr3 = sum(1 for x in samples_3 if x > 0) / len(samples_3) * 100
            wr10 = sum(1 for x in samples_10 if x > 0) / len(samples_10) * 100
            av3 = sum(samples_3) / len(samples_3)
            av10 = sum(samples_10) / len(samples_10)
            print("{:30s}: {:3d}次, 3日 {:4.0f}%({:+.2f}%), 10日 {:4.0f}%({:+.2f}%)".format(
                slope_range[0], len(samples_3), wr3, av3, wr10, av10
            ))

    # ====== 当前趋势判断 ======
    print()
    print("=" * 80)
    print("当前趋势（截至 {}）".format(results[-1]["date"]))
    print("=" * 80)

    # 5日斜率
    if n >= 5:
        slope_5 = results[-1]["dual_bear"] - results[-5]["dual_bear"]
        slope_bull_5 = results[-1]["dual_bull"] - results[-5]["dual_bull"]
        print("双空 5日斜率: {:+.1f}% (从 {:.1f}% → {:.1f}%)".format(slope_5, results[-5]["dual_bear"], results[-1]["dual_bear"]))
        print("双多 5日斜率: {:+.1f}% (从 {:.1f}% → {:.1f}%)".format(slope_bull_5, results[-5]["dual_bull"], results[-1]["dual_bull"]))

    # 10日斜率
    if n >= 10:
        slope_10 = results[-1]["dual_bear"] - results[-10]["dual_bear"]
        print("双空 10日斜率: {:+.1f}% (从 {:.1f}% → {:.1f}%)".format(slope_10, results[-10]["dual_bear"], results[-1]["dual_bear"]))

    # 最近改善/恶化统计
    recent_n = min(10, n)
    imp = sum(1 for r in results[-recent_n:] if r["improve"])
    wor = sum(1 for r in results[-recent_n:] if r["worsen"])
    print()
    print("最近{}天: 双改善{}天, 双恶化{}天".format(recent_n, imp, wor))

    if slope_5 > 5:
        print()
        print("⚠️ 双空5日急升 +{:.1f}% — 市场结构在快速恶化".format(slope_5))
        print("   历史上类似急升出现过，后续10日平均表现往往偏弱")
    elif slope_5 > 2:
        print()
        print("🟠 双空5日缓升 +{:.1f}% — 趋势偏空但非极端".format(slope_5))
    elif slope_5 < -5:
        print()
        print("🔥 双空5日急降 — 市场结构在快速改善")
    else:
        print()
        print("🟡 双空趋势中性")

    # 年度统计
    print()
    print("=" * 80)
    print("年度分段统计")
    print("=" * 80)
    years = {}
    for r in results:
        y = r["date"][:4]
        if y not in years:
            years[y] = {"imp": 0, "wor": 0, "total": 0, "returns": []}
        years[y]["total"] += 1
        if r["improve"]:
            years[y]["imp"] += 1
        if r["worsen"]:
            years[y]["wor"] += 1
        years[y]["returns"].append(r["mkt"])

    for y in sorted(years):
        d = years[y]
        avg = sum(d["returns"]) / len(d["returns"])
        print("{}: {}天, 改善{}天, 恶化{}天, 日均{:+.2f}%".format(
            y, d["total"], d["imp"], d["wor"], avg
        ))


if __name__ == "__main__":
    analyze()
