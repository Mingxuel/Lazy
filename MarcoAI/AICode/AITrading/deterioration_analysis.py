"""历史急升阶段持续时间和反转模式分析"""
import os

DATA_DIR = r"C:\Lazy\MarcoAI\AIData\1D"
PRICE_FILE = r"C:\Lazy\MarcoAI\AIData\1D_PRICE"


def load_price():
    d = {}
    with open(PRICE_FILE, encoding="utf-8") as f:
        for line in f:
            p = line.strip().split("|")
            if len(p) < 2:
                continue
            try:
                v1 = float(p[1])
                v2 = float(p[2]) if len(p) >= 3 else v1
            except ValueError:
                continue
            d[p[0].strip()] = (v1, v2)
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


def ma(vals, w):
    if len(vals) < w:
        return None
    return sum(vals[-w:]) / w


def main():
    prices = load_price()
    stocks = load_all()
    all_dates = sorted({d for s in stocks.values() for d, _, _ in s})
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
            m5p = ma(cl, 5)
            m10p = ma(cl, 10)
            m5a = ma(am, 5)
            m10a = ma(am, 10)
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
        results.append(
            {
                "date": date,
                "idx": idx,
                "dual_bear": min(pb, ab) / tot * 100,
                "dual_bull": min(pu, au) / tot * 100,
            }
        )

    for i in range(len(results)):
        if i < 5:
            results[i]["slope5"] = 0
        else:
            results[i]["slope5"] = results[i]["dual_bear"] - results[i - 5]["dual_bear"]

    # ===== 1: 急升阶段持续多久 =====
    print("=" * 70)
    print("分析1：急升恶化阶段持续多久才结束")
    print("=" * 70)

    phases = []
    in_phase = False
    phase_start = ""
    phase_start_idx = 0
    for i, r in enumerate(results):
        if r["slope5"] > 8 and not in_phase:
            in_phase = True
            phase_start = r["date"]
            phase_start_idx = i
        elif r["slope5"] <= 8 and in_phase:
            in_phase = False
            end_idx = i
            duration = end_idx - phase_start_idx
            peak = max(results[j]["dual_bear"] for j in range(phase_start_idx, end_idx))
            r5 = 0.0
            r10 = 0.0
            if end_idx + 5 < len(results):
                for k in range(end_idx, min(end_idx + 5, len(results))):
                    if k > 0:
                        r5 += (results[k]["idx"] - results[k - 1]["idx"]) / results[k - 1]["idx"] * 100
            if end_idx + 10 < len(results):
                for k in range(end_idx, min(end_idx + 10, len(results))):
                    if k > 0:
                        r10 += (results[k]["idx"] - results[k - 1]["idx"]) / results[k - 1]["idx"] * 100
            phases.append(
                {"start": phase_start, "end": r["date"], "duration": duration, "peak": peak, "r5": r5, "r10": r10}
            )
    if in_phase:
        phases.append(
            {
                "start": phase_start,
                "end": results[-1]["date"],
                "duration": len(results) - phase_start_idx,
                "peak": max(r["dual_bear"] for r in results[phase_start_idx:]),
                "r5": None,
                "r10": None,
                "ongoing": True,
            }
        )

    fmt_h = "{:^12s} | {:^12s} | {:^5s} | {:^8s} | {:^8s} | {:^8s}"
    print(fmt_h.format("开始", "结束", "天数", "峰值双空", "5日反弹", "10日反弹"))
    print("-" * 70)
    for ph in phases:
        r5s = "{:+.1f}%".format(ph["r5"]) if ph.get("r5") is not None else "---"
        r10s = "{:+.1f}%".format(ph["r10"]) if ph.get("r10") is not None else "---"
        m = " ← 当前" if ph.get("ongoing") else ""
        print(
            "{:^12s} | {:^12s} | {:4d}天 | {:6.0f}% | {:>8s} | {:>8s}{}".format(
                ph["start"], ph["end"], ph["duration"], ph["peak"], r5s, r10s, m
            )
        )

    completed = [p for p in phases if not p.get("ongoing")]
    if completed:
        avg_dur = sum(p["duration"] for p in completed) / len(completed)
        avg_r5 = sum(p["r5"] for p in completed) / len(completed)
        avg_r10 = sum(p["r10"] for p in completed) / len(completed)
        pct5 = sum(1 for p in completed if p["r5"] > 0) / len(completed) * 100
        pct10 = sum(1 for p in completed if p["r10"] > 0) / len(completed) * 100
        print()
        print(
            "已完成 {} 次急升: 平均持续 {:.1f}天, 结束后5日反弹概率 {:.0f}%({:+.1f}%), 10日 {:.0f}%({:+.1f}%)".format(
                len(completed), avg_dur, pct5, avg_r5, pct10, avg_r10
            )
        )

    # ===== 2: 类似当前的精确匹配 =====
    print()
    print("=" * 70)
    print("分析2：双空从~40%飙到~52%（类似当前）之后10天路径")
    print("=" * 70)

    for i in range(len(results)):
        if i < 5:
            continue
        b5 = results[i - 5]["dual_bear"]
        b0 = results[i]["dual_bear"]
        slope = results[i]["slope5"]
        if 35 <= b5 <= 45 and 50 <= b0 <= 57 and slope > 8:
            print("匹配日: {} (双空 {:.0f}% → {:.0f}%, 斜率 {:.0f}%)".format(results[i]["date"], b5, b0, slope))
            cum = 0.0
            for j in range(1, 11):
                if i + j >= len(results):
                    break
                chg = (
                    (results[i + j]["idx"] - results[i + j - 1]["idx"])
                    / results[i + j - 1]["idx"]
                    * 100
                )
                cum += chg
                a = "▲" if chg > 1 else ("▼" if chg < -1 else "─")
                print(
                    "  +{:2d}天 {}  双空={:5.1f}%  日{:+.2f}%  累{:+.2f}% {}".format(
                        j, results[i + j]["date"], results[i + j]["dual_bear"], chg, cum, a
                    )
                )
            print()

    # ===== 3: 预判 =====
    print("=" * 70)
    print("结论")
    print("=" * 70)
    cur = results[-1]
    print("当前: {} 双空={:.1f}% 5日斜率={:+.1f}%".format(cur["date"], cur["dual_bear"], cur["slope5"]))

    over60 = sum(1 for r in results if r["dual_bear"] > 60)
    over70 = sum(1 for r in results if r["dual_bear"] > 70)
    print()
    print("双空 > 60%: {}/367天 ({:.0f}%)".format(over60, over60 / 367 * 100))
    print("双空 > 70%: {}/367天 ({:.0f}%)".format(over70, over70 / 367 * 100))

    if completed:
        print()
        print("急升阶段平均持续 {:.1f} 天 → 如果当前急升从 7/20 开始，已过 3 天".format(avg_dur))
        if avg_dur <= 5:
            print("预期: 下周初（1-3个交易日内）急升结束，进入均值回归")
        else:
            print("预期: 下周后半段才可能结束，需要更耐心")


if __name__ == "__main__":
    main()
