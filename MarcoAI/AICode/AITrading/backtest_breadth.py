"""
选股策略回测：市场宽度过滤 × 五信号选股
对比: 无过滤 vs 有宽度过滤
"""
import os
from typing import Optional

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


def load_stock(filepath: str) -> list[tuple[str, float, float, float, float, float]]:
    """date, open, high, low, close, volume, amount"""
    rows = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            p = line.strip().split("|")
            if len(p) < 7:
                continue
            try:
                rows.append(
                    (
                        p[0].strip(),
                        float(p[1]),
                        float(p[2]),
                        float(p[3]),
                        float(p[4]),
                        float(p[5]),
                        float(p[6]),
                    )
                )
            except (ValueError, IndexError):
                continue
    return rows


def ma(vals, w):
    if len(vals) < w:
        return None
    return sum(vals[-w:]) / w


# 大票池 — 主板, 非ST, >200亿 (代表性样本)
POOL = {
    "万华化学": "600309.SH",
    "中国平安": "601318.SH",
    "大华股份": "002236.SZ",
    "海康威视": "002415.SZ",
    "浪潮信息": "000977.SZ",
    "工业富联": "601138.SH",
    "中科曙光": "603019.SH",
    "紫金矿业": "601899.SH",
    "中兴通讯": "000063.SZ",
    "招商银行": "600036.SH",
    "中国神华": "601088.SH",
    "中国石油": "601857.SH",
    "长江电力": "600900.SH",
    "五粮液": "000858.SZ",
    "泸州老窖": "000568.SZ",
    "伊利股份": "600887.SH",
    "恒瑞医药": "600276.SH",
    "立讯精密": "002475.SZ",
    "洛阳钼业": "603993.SH",
    "隆基绿能": "601012.SH",
}


def check_signal_1(stock_data: list, day_idx: int) -> bool:
    """① 近5日内有放量低点+长下影线"""
    for i in range(max(1, day_idx - 5), day_idx):
        if i < 5:
            continue
        date, o, h, l, c, vol, amt = stock_data[i]
        prev_vols = [stock_data[j][5] for j in range(max(0, i - 5), i)]
        avg_vol = sum(prev_vols) / len(prev_vols) if prev_vols else vol
        vol_spike = vol > avg_vol * 1.2
        body = abs(c - o)
        lower_shadow = min(o, c) - l
        upper_shadow = h - max(o, c)
        long_lower = lower_shadow > body and lower_shadow > upper_shadow
        if vol_spike and long_lower:
            return True
    return False


def check_signal_3(stock_data: list, day_idx: int) -> bool:
    """③ MA5今日拐头（今日>昨日，且之前没拐）"""
    if day_idx < 6:
        return False
    closes = [r[4] for r in stock_data]
    m5_today = ma(closes[: day_idx + 1], 5)
    m5_yesterday = ma(closes[:day_idx], 5)
    m5_daybefore = ma(closes[: day_idx - 1], 5)
    if None in (m5_today, m5_yesterday, m5_daybefore):
        return False
    # 今天拐头: 昨天 <= 前天 且 今天 > 昨天
    return m5_yesterday <= m5_daybefore and m5_today > m5_yesterday


def check_signal_4(stock_data: list, day_idx: int) -> bool:
    """④ 5日涨跌由负转正/逼近零轴"""
    if day_idx < 5:
        return False
    ret5_today = (stock_data[day_idx][4] - stock_data[day_idx - 5][4]) / stock_data[day_idx - 5][4] * 100
    ret5_yesterday = (stock_data[day_idx - 1][4] - stock_data[day_idx - 6][4]) / stock_data[day_idx - 6][4] * 100
    return (ret5_today > 0 and ret5_yesterday < 0) or (ret5_today > -2 and ret5_today < 5)


def check_signal_5(stock_data: list, day_idx: int) -> bool:
    """⑤ 扣抵顺风 — T-4 < 当前价"""
    if day_idx < 4:
        return False
    return stock_data[day_idx - 4][4] < stock_data[day_idx][4]


def compute_all_signals(stock_data: list, day_idx: int) -> tuple[int, list[str]]:
    """返回 (得分, [激活的信号名])"""
    signals = []
    if check_signal_1(stock_data, day_idx):
        signals.append("①放量低点")
    if check_signal_3(stock_data, day_idx):
        signals.append("③MA5拐头")
    if check_signal_4(stock_data, day_idx):
        signals.append("④5日转正")
    if check_signal_5(stock_data, day_idx):
        signals.append("⑤扣抵顺风")
    return len(signals), signals


def compute_market_breadth(all_stock_data: dict, all_dates: list, day_idx: int) -> dict:
    """计算当天市场宽度"""
    if day_idx < 9:
        return {"dual_bear": 50, "slope5": 0, "verdict": "数据不足"}

    date = all_dates[day_idx]
    pb = ab = pu = au = tot = 0
    for code, data in all_stock_data.items():
        closes = [r[4] for r in data if r[0] <= date]
        amounts = [r[6] for r in data if r[0] <= date]
        if len(closes) < 10:
            continue
        m5p = ma(closes, 5)
        m10p = ma(closes, 10)
        m5a = ma(amounts, 5)
        m10a = ma(amounts, 10)
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
        return {"dual_bear": 50, "slope5": 0, "verdict": "无数据"}

    dual_bear = min(pb, ab) / tot * 100
    slope5 = 0.0
    return {"dual_bear": dual_bear, "slope5": slope5, "verdict": ""}


def breadth_verdict(slope5: float) -> tuple[str, int, str]:
    """市场宽度判定 → (等级, 最低信号数, 标签)"""
    if slope5 < -8:
        return "GREEN_AGGRESSIVE", 2, "急降改善→积极"
    elif slope5 < -3:
        return "GREEN", 3, "缓降改善→正常"
    elif slope5 <= 3:
        return "YELLOW", 4, "横盘中性→谨慎"
    elif slope5 <= 8:
        return "RED", 99, "缓升恶化→不选"
    else:
        return "RED_FAST", 99, "急升恶化→不选"


def main():
    print("加载数据...")
    prices = load_price()

    # 加载 POOL 里的股票
    pool_data = {}
    for name, code in POOL.items():
        fpath = os.path.join(DATA_DIR, code)
        if os.path.exists(fpath):
            data = load_stock(fpath)
            if len(data) > 20:
                pool_data[name] = data

    # 加载全部 676 只用于计算市场宽度
    all_data = {}
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith((".SZ", ".SH")):
            continue
        data = load_stock(os.path.join(DATA_DIR, fname))
        if len(data) > 20:
            all_data[os.path.splitext(fname)[0]] = data

    # 所有日期
    all_dates = sorted({d for s in all_data.values() for d, _, _, _, _, _, _ in s})

    print("POOL: {} 只, 全市场: {} 只".format(len(pool_data), len(all_data)))

    # 预先计算全市场宽度
    breadth_cache = {}
    for di in range(10, len(all_dates)):
        date = all_dates[di]
        pb = ab = pu = au = tot = 0
        for code, data in all_data.items():
            closes = [r[4] for r in data if r[0] <= date]
            amounts = [r[6] for r in data if r[0] <= date]
            if len(closes) < 10:
                continue
            m5p = ma(closes, 5)
            m10p = ma(closes, 10)
            m5a = ma(amounts, 5)
            m10a = ma(amounts, 10)
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
        slope5 = 0.0
        if di >= 15:
            prev_date = all_dates[di - 5]
            if prev_date in breadth_cache:
                slope5 = dual_bear - breadth_cache[prev_date]["dual_bear"]
        breadth_cache[date] = {"dual_bear": dual_bear, "slope5": slope5}

    # 回测
    print()
    print("=" * 90)
    print("逐日回测: 市场宽度过滤 × 五信号")
    print("=" * 90)

    all_picks = []  # 无过滤
    filtered_picks = []  # 有宽度过滤

    for day_idx in range(15, len(all_dates)):
        date = all_dates[day_idx]
        if date < "20260715":  # 只看最近
            continue
        if date > "20260723":
            break

        bw = breadth_cache.get(date, {"dual_bear": 50, "slope5": 0})
        slope5 = bw["slope5"]
        verdict, min_signals, tag = breadth_verdict(slope5)

        # 检查每只股票
        for name, data in pool_data.items():
            # 找到该股在 date 的索引
            stock_idx = None
            for i, r in enumerate(data):
                if r[0] == date:
                    stock_idx = i
                    break
            if stock_idx is None or stock_idx < 8:
                continue

            score, signals = compute_all_signals(data, stock_idx)

            # 无过滤：信号分 >= 2 就入选
            if score >= 2:
                nxt = None
                if stock_idx + 1 < len(data):
                    next_close = data[stock_idx + 1][4]
                    today_close = data[stock_idx][4]
                    nxt = (next_close - today_close) / today_close * 100

                all_picks.append(
                    {
                        "date": date,
                        "stock": name,
                        "score": score,
                        "signals": ",".join(signals),
                        "next_ret": nxt,
                        "filter": "无",
                        "slope5": slope5,
                        "dual_bear": bw["dual_bear"],
                    }
                )

            # 有宽度过滤
            if score >= min_signals:
                nxt = None
                if stock_idx + 1 < len(data):
                    next_close = data[stock_idx + 1][4]
                    today_close = data[stock_idx][4]
                    nxt = (next_close - today_close) / today_close * 100

                filtered_picks.append(
                    {
                        "date": date,
                        "stock": name,
                        "score": score,
                        "signals": ",".join(signals),
                        "next_ret": nxt,
                        "filter": tag,
                        "slope5": slope5,
                        "dual_bear": bw["dual_bear"],
                    }
                )

    # ===== 输出 =====
    print()
    print("=" * 90)
    print("每日选股明细（20只大票池）")
    print("=" * 90)

    hdr = "{:>8s} | {:>6s} | {:>6s} | {:>6s} | {:>10s} | {:>8s} | {:20s} | 选股逻辑"
    print(hdr.format("日期", "双空", "斜率", "得分", "隔日收益", "宽度过滤", "信号"))
    print("-" * 100)

    # 按日期分组展示
    all_dates_shown = sorted(set(p["date"] for p in all_picks))
    for d in all_dates_shown:
        day_all = [p for p in all_picks if p["date"] == d]
        day_filt = [p for p in filtered_picks if p["date"] == d]

        bw = breadth_cache.get(d, {"dual_bear": 50, "slope5": 0})

        for p in day_all:
            ret_s = "{:+.2f}%".format(p["next_ret"]) if p["next_ret"] is not None else "N/A"
            # 检查是否被过滤掉
            if p in day_filt:
                filt_tag = p["filter"]
            else:
                filt_tag = "❌被过滤"

            print(
                "{:>8s} | {:5.0f}% | {:+5.0f}% | {:2d}/4 | {:>10s} | {:>8s} | {:20s}".format(
                    d, bw["dual_bear"], bw["slope5"], p["score"], ret_s, filt_tag, p["signals"]
                )
            )
        if day_all:
            print()

    # ===== 统计对比 =====
    print()
    print("=" * 90)
    print("策略对比统计")
    print("=" * 90)

    for label, picks in [("无宽度过滤", all_picks), ("有宽度过滤", filtered_picks)]:
        valid = [p for p in picks if p["next_ret"] is not None]
        if not valid:
            continue
        wins = sum(1 for p in valid if p["next_ret"] > 0)
        avg = sum(p["next_ret"] for p in valid) / len(valid)
        max_w = max(p["next_ret"] for p in valid)
        max_l = min(p["next_ret"] for p in valid)

        fmt = "{:15s}: {:3d}笔, 胜率{:3.0f}%, 均值{:+.2f}%, 最佳{:+.2f}%, 最差{:+.2f}%"
        print(fmt.format(label, len(valid), wins / len(valid) * 100, avg, max_w, max_l))

        # 按宽度阶段分组
        if label == "有宽度过滤":
            for tag in ["急降改善→积极", "缓降改善→正常", "横盘中性→谨慎", "缓升恶化→不选", "急升恶化→不选"]:
                sub = [p for p in valid if p["filter"] == tag]
                if sub:
                    sub_wins = sum(1 for p in sub if p["next_ret"] > 0)
                    sub_avg = sum(p["next_ret"] for p in sub) / len(sub)
                    print("  ├─ {}: {}笔, 胜率{:.0f}%, 均值{:+.2f}%".format(tag, len(sub), sub_wins / len(sub) * 100, sub_avg))


if __name__ == "__main__":
    main()
