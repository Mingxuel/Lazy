"""
验证：双空/双多的「变化方向」是否比「绝对值」更能预测市场
核心假设：偏向增加的股票数量在增加 = 市场变好，反之亦然
"""

import os, sys
from typing import Optional

DATA_DIR = r"C:\Lazy\MarcoAI\AIData\1D"
PRICE_FILE = r"C:\Lazy\MarcoAI\AIData\1D_PRICE"


def load_price_index():
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


def load_all():
    stocks = {}
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith((".SZ", ".SH")):
            continue
        rows = []
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


def main():
    print("加载数据...")
    prices = load_price_index()
    stocks = load_all()
    print("{} 只个股, {} 天价格指数".format(len(stocks), len(prices)))

    all_dates = sorted(set(d for s in stocks.values() for d, _, _ in s))
    results = []

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

        dual_bear = min(pb, ab) / tot * 100
        dual_bull = min(pu, au) / tot * 100

        pi = prices.get(date, (0, 0))
        idx = pi[1] if pi[1] else pi[0]
        prev = prices.get(all_dates[di - 1], (0, 0))
        pidx = prev[1] if prev[1] else prev[0]
        mkt = (idx - pidx) / pidx * 100 if pidx else 0

        results.append(
            {
                "date": date,
                "dual_bear": dual_bear,
                "dual_bull": dual_bull,
                "mkt": mkt,
                "tot": tot,
            }
        )

    # 计算逐日变化
    for i, r in enumerate(results):
        if i == 0:
            r["d_bear"] = 0.0
            r["d_bull"] = 0.0
        else:
            r["d_bear"] = r["dual_bear"] - results[i - 1]["dual_bear"]
            r["d_bull"] = r["dual_bull"] - results[i - 1]["dual_bull"]

    # ===== 验证1: 变化方向 =====
    print()
    print("=" * 60)
    print("验证1: 双空方向 vs 次日")
    print("=" * 60)

    improving = []
    worsening = []
    flat = []
    for i, r in enumerate(results):
        if i + 1 >= len(results):
            continue
        if r["d_bear"] < -1:
            improving.append(results[i + 1]["mkt"])
        elif r["d_bear"] > 1:
            worsening.append(results[i + 1]["mkt"])
        else:
            flat.append(results[i + 1]["mkt"])

    for label, vals in [
        ("双空下降(变好) >1%", improving),
        ("双空上升(变差) >1%", worsening),
        ("双空变化 <1% (中性)", flat),
    ]:
        if vals:
            up = sum(1 for x in vals if x > 0)
            print(
                "{}: {}次, 胜率{:.0f}%, 均值{:+.2f}%".format(
                    label, len(vals), up / len(vals) * 100, sum(vals) / len(vals)
                )
            )

    # ===== 验证2: 双多方向 =====
    print()
    print("=" * 60)
    print("验证2: 双多方向 vs 次日")
    print("=" * 60)

    improving2 = []
    worsening2 = []
    flat2 = []
    for i, r in enumerate(results):
        if i + 1 >= len(results):
            continue
        if r["d_bull"] > 1:
            improving2.append(results[i + 1]["mkt"])
        elif r["d_bull"] < -1:
            worsening2.append(results[i + 1]["mkt"])
        else:
            flat2.append(results[i + 1]["mkt"])

    for label, vals in [
        ("双多上升(变好) >1%", improving2),
        ("双多下降(变差) >1%", worsening2),
        ("双多变化 <1% (中性)", flat2),
    ]:
        if vals:
            up = sum(1 for x in vals if x > 0)
            print(
                "{}: {}次, 胜率{:.0f}%, 均值{:+.2f}%".format(
                    label, len(vals), up / len(vals) * 100, sum(vals) / len(vals)
                )
            )

    # ===== 验证3: 双信号叠加 =====
    print()
    print("=" * 60)
    print("验证3: 双空↓ + 双多↑ 同时发生 = 最强改善信号")
    print("=" * 60)

    both_good = []
    both_bad = []
    for i, r in enumerate(results):
        if i + 1 >= len(results):
            continue
        if r["d_bear"] < -1 and r["d_bull"] > 1:
            both_good.append(results[i + 1]["mkt"])
        if r["d_bear"] > 1 and r["d_bull"] < -1:
            both_bad.append(results[i + 1]["mkt"])

    for label, vals in [("双改善(空↓+多↑)", both_good), ("双恶化(空↑+多↓)", both_bad)]:
        if vals:
            up = sum(1 for x in vals if x > 0)
            print(
                "{}: {}次, 胜率{:.0f}%, 均值{:+.2f}%".format(
                    label, len(vals), up / len(vals) * 100, sum(vals) / len(vals)
                )
            )

    # ===== 对比总结 =====
    print()
    print("=" * 60)
    print("总对比: 绝对值 vs 趋势")
    print("=" * 60)

    all_tests = [
        ("绝对值-双空>50%(偏空)", [results[i + 1]["mkt"] for i, r in enumerate(results) if i + 1 < len(results) and r["dual_bear"] > 50]),
        ("绝对值-双多>50%(偏多)", [results[i + 1]["mkt"] for i, r in enumerate(results) if i + 1 < len(results) and r["dual_bull"] > 50]),
        ("趋势-双空↓>1%(改善)", improving),
        ("趋势-双多↑>1%(改善)", improving2),
        ("趋势-双改善叠加", both_good),
        ("趋势-双恶化叠加", both_bad),
    ]

    fmt = "{:25s} | {:>4s} | {:>4s} | {:>8s}"
    print(fmt.format("因子", "样本", "胜率", "平均"))
    print("-" * 50)
    for name, vals in all_tests:
        if not vals:
            continue
        up = sum(1 for x in vals if x > 0)
        print(fmt.format(name, str(len(vals)), "{:.0f}%".format(up / len(vals) * 100), "{:+.2f}%".format(sum(vals) / len(vals))))

    # ===== 最近两周 =====
    print()
    print("=" * 60)
    print("最近两周逐日趋势")
    print("=" * 60)
    hdr = "{:>10s} | {:>6s} | {:>8s} | {:>6s} | {:>8s} | {:>7s} | 解读"
    print(hdr.format("日期", "双空", "Δ双空", "双多", "Δ双多", "市场"))
    print("-" * 70)
    for r in results[-14:]:
        ba = "↑差" if r["d_bear"] > 0.5 else ("↓好" if r["d_bear"] < -0.5 else "→")
        bl = "↑好" if r["d_bull"] > 0.5 else ("↓差" if r["d_bull"] < -0.5 else "→")
        interp = ""
        if r["d_bear"] < -1 and r["d_bull"] > 1:
            interp = "🔥双改善"
        elif r["d_bear"] > 1 and r["d_bull"] < -1:
            interp = "🔴双恶化"
        elif r["d_bull"] > r.get("d_bear", 0) + 1:
            interp = "🟢偏改善"
        elif r["d_bear"] > r.get("d_bull", 0) + 1:
            interp = "🟠偏恶化"

        line = "{:>10s} | {:5.1f}% | {:>8s} | {:5.1f}% | {:>8s} | {:+6.2f}% | {}"
        print(line.format(r["date"], r["dual_bear"], "{:+.1f}% {}".format(r["d_bear"], ba), r["dual_bull"], "{:+.1f}% {}".format(r["d_bull"], bl), r["mkt"], interp))


if __name__ == "__main__":
    main()
