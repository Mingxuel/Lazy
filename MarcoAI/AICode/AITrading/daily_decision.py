"""
每日隔日交易决策引擎
输入: 1D_MA_CROSS, 1D_PANIC_INDEX, 1D日线数据
输出: 买不买 → 买什么 → 买多少
"""
import os
from datetime import datetime
from typing import Optional

DATA_DIR = r"C:\Lazy\MarcoAI\AIData\1D"
PANIC_FILE = r"C:\Lazy\MarcoAI\AIData\1D_PANIC_INDEX"
MA_CROSS_FILE = r"C:\Lazy\MarcoAI\AIData\1D_MA_CROSS"

# 大票池
POOL = {
    "万华化学": "600309.SH", "中国平安": "601318.SH", "大华股份": "002236.SZ",
    "海康威视": "002415.SZ", "浪潮信息": "000977.SZ", "工业富联": "601138.SH",
    "中科曙光": "603019.SH", "紫金矿业": "601899.SH", "中兴通讯": "000063.SZ",
    "招商银行": "600036.SH", "中国神华": "601088.SH", "中国石油": "601857.SH",
    "长江电力": "600900.SH", "五粮液": "000858.SZ", "泸州老窖": "000568.SZ",
    "伊利股份": "600887.SH", "恒瑞医药": "600276.SH", "立讯精密": "002475.SZ",
    "洛阳钼业": "603993.SH", "隆基绿能": "601012.SH",
}


def load_stock(fp: str) -> list:
    rows = []
    if not os.path.exists(fp):
        return rows
    with open(fp, encoding="utf-8") as f:
        for line in f:
            p = line.strip().split("|")
            if len(p) < 7:
                continue
            try:
                rows.append((p[0].strip(), float(p[1]), float(p[2]), float(p[3]),
                             float(p[4]), float(p[5]), float(p[6])))
            except (ValueError, IndexError):
                continue
    return rows


def ma(v, w):
    if len(v) < w: return None
    return sum(v[-w:]) / w


def load_latest(filepath: str) -> Optional[float]:
    if not os.path.exists(filepath):
        return None
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()
    if not lines:
        return None
    last = lines[-1].strip().split("|")
    if len(last) < 2:
        return None
    try:
        return float(last[1])
    except ValueError:
        return None


def load_ma_trend() -> dict:
    d = {}
    if not os.path.exists(MA_CROSS_FILE):
        return d
    with open(MA_CROSS_FILE, encoding="utf-8") as f:
        for line in f:
            p = line.strip().split("|")
            if len(p) < 3: continue
            try:
                d[p[0]] = {"db": float(p[1]), "dbull": float(p[2])}
            except: continue
    return d


def compute_slope(ma_data: dict, window: int = 5) -> float:
    dates = sorted(ma_data.keys())
    if len(dates) < window + 1:
        return 0
    return ma_data[dates[-1]]["db"] - ma_data[dates[-1 - window]]["db"]


def check_signal_3(data: list, idx: int) -> bool:
    """③ MA5今日拐头"""
    if idx < 6: return False
    cl = [r[4] for r in data]
    m5t = ma(cl[:idx+1], 5)
    m5y = ma(cl[:idx], 5)
    m5d = ma(cl[:idx-1], 5)
    if None in (m5t, m5y, m5d): return False
    return m5y <= m5d and m5t > m5y


def check_signal_4(data: list, idx: int) -> bool:
    """④ 5日涨跌由负转正/逼近零轴"""
    if idx < 5: return False
    r0 = (data[idx][4] - data[idx-5][4]) / data[idx-5][4] * 100
    r1 = (data[idx-1][4] - data[idx-6][4]) / data[idx-6][4] * 100
    return (r0 > 0 and r1 < 0) or (-2 < r0 < 5)


def check_signal_1(data: list, idx: int) -> bool:
    """① 近5日有放量低点+长下影"""
    for i in range(max(1, idx-5), idx):
        if i < 5: continue
        o, h, l, c, vol = data[i][1], data[i][2], data[i][3], data[i][4], data[i][5]
        pv = [data[j][5] for j in range(max(0, i-5), i)]
        av = sum(pv) / len(pv) if pv else vol
        body = abs(c - o)
        ls = min(o, c) - l
        us = h - max(o, c)
        if vol > av * 1.2 and ls > body and ls > us:
            return True
    return False


def check_signal_5(data: list, idx: int) -> bool:
    """⑤ 扣抵顺风"""
    if idx < 4: return False
    return data[idx-4][4] < data[idx][4]


def score_stock(data: list, idx: int) -> tuple[int, list[str], float, float]:
    s = []
    sc = 0
    if check_signal_1(data, idx): sc += 1; s.append("①")
    if check_signal_3(data, idx): sc += 1; s.append("③")
    if check_signal_4(data, idx): sc += 1; s.append("④")
    if check_signal_5(data, idx): sc += 1; s.append("⑤")

    # MA5 数值
    cl = [r[4] for r in data[:idx+1]]
    m5 = ma(cl, 5)
    price = data[idx][4]
    dist = (price - m5) / m5 * 100 if m5 else 0
    return sc, s, m5 or 0, dist


def main():
    today_str = datetime.now().strftime("%Y%m%d")

    # 1. 加载市场宽度
    ma_data = load_ma_trend()
    slope5 = compute_slope(ma_data, 5)
    latest_db = ma_data[sorted(ma_data.keys())[-1]]["db"] if ma_data else 50

    # 2. 加载恐慌指数
    panic = load_latest(PANIC_FILE)

    # 3. 判定市场宽度
    if slope5 < -8:
        breadth_grade = "🔥急降改善"
        min_sig = 2
        position = 0.80
    elif slope5 < -3:
        breadth_grade = "🟢缓降改善"
        min_sig = 3
        position = 0.60
    elif slope5 <= 3:
        breadth_grade = "🟡横盘中性"
        min_sig = 3
        position = 0.30
    elif slope5 <= 8:
        breadth_grade = "🔴缓升恶化"
        min_sig = 99
        position = 0.0
    else:
        breadth_grade = "⚠️急升恶化"
        min_sig = 4  # 急升时允许极端信号买入
        position = 0.10

    # 4. 判定恐慌等级
    panic_grade = ""
    if panic is None:
        panic_grade = "无数据"
        panic_level = "?"
    elif panic < 20:
        panic_grade = "🟢低恐慌"
        panic_level = "LOW"
    elif panic < 40:
        panic_grade = "🟡正常"
        panic_level = "MID"
    else:
        panic_grade = "🔴高恐慌"
        panic_level = "HIGH"

    # 5. 判定情绪阶段 = 恐慌 × 宽度 交叉定位
    phase = ""
    strategy_name = ""
    strategy_signal = ""

    if panic_level == "HIGH" and breadth_grade in ("⚠️急升恶化", "🔴缓升恶化"):
        phase = "❄️ 冰点期"
        strategy_name = "等待 + 记录①放量低点票"
        strategy_signal = "① only"
        position = 0.05
    elif panic_level in ("MID", "LOW") and breadth_grade in ("🔥急降改善", "🟢缓降改善"):
        phase = "🌤️ 回暖期"
        strategy_name = "③+④ 拐点买入"
        strategy_signal = "③+④"
        if position < 0.3: position = 0.40
        if position > 0.6: position = 0.60
    elif panic_level == "LOW" and breadth_grade in ("🔥急降改善", "🟢缓降改善"):
        phase = "🔥 高潮期"
        strategy_name = "持有不动，MA5移动止盈"
        strategy_signal = "无新买点"
        position = 0.70
    elif panic_level in ("MID", "LOW") and breadth_grade == "🟡横盘中性":
        phase = "⚡ 分歧期"
        strategy_name = "③+④+⑤ 加强版"
        strategy_signal = "③+④+⑤"
        if position > 0.4: position = 0.30
    elif panic_level in ("MID", "LOW") and breadth_grade in ("🔴缓升恶化",):
        phase = "🌪️ 退潮期"
        strategy_name = "不买，清仓休息"
        strategy_signal = "无"
        position = 0.0
    elif panic_level == "HIGH" and breadth_grade in ("🔥急降改善", "🟢缓降改善"):
        phase = "🌤️ 回暖期（恐慌消退中）"
        strategy_name = "③+④ 拐点买入"
        strategy_signal = "③+④"
        position = 0.50
    else:
        # 混合状态 → 偏保守
        phase = "⚡ 分歧/退潮（信号矛盾）"
        strategy_name = "③+④+⑤ 加强版 + 半仓"
        strategy_signal = "③+④+⑤"
        if position > 0.3: position = 0.20

    # 5. 扫描股票池
    candidates = []
    pool_data = {}
    for name, code in POOL.items():
        data = load_stock(os.path.join(DATA_DIR, code))
        if not data:
            continue
        pool_data[name] = data
        # 找最新日期
        idx = len(data) - 1
        sc, sg, m5, dist = score_stock(data, idx)
        if sc < 2:  # 至少 2 信号
            continue
        # 核心要求：必须有 ③
        has_s3 = "③" in sg
        has_s4 = "④" in sg
        candidates.append({
            "name": name, "code": code,
            "score": sc, "signals": sg,
            "has_core": has_s3 and has_s4,
            "m5": m5, "dist": dist,
            "close": data[idx][4],
        })

    # 6. 排序：③+④ 优先 → 信号分 → 距 MA5 近
    candidates.sort(key=lambda c: (
        -c["has_core"],
        -c["score"],
        abs(c["dist"]),
    ))

    # ===== 输出 =====
    print()
    print("=" * 60)
    print("  每日隔日交易决策 — {}".format(today_str))
    print("=" * 60)

    print()
    print("┌─ 环境 ─────────────────────")
    print("│ 判断阶段: {}  →  {} ".format(phase, strategy_name))
    print("│ 恐慌指数: {}  |  v2={:.1f}".format(
        panic_grade, panic if panic else 0))
    print("│ 市场宽度: {}  |  双空={:.1f}%  |  5日斜率={:+.1f}%".format(
        breadth_grade, latest_db, slope5))
    print("│ 核心信号: {}  |  建议仓位: {}%".format(strategy_signal, int(position * 100)))
    print("└────────────────────────────")

    # 核心决策
    if breadth_grade == "🔴缓升恶化":
        print()
        print("🚫 今日不买 — 市场宽度在缓慢恶化（阴跌模式）")
        print("   回测: 缓升阶段隔日胜率仅 44%，是最危险的信号")
        print("   等待: 双空斜率翻绿（急降/缓降）后再选股")
        return

    if not candidates:
        print()
        print("🚫 今日无候选 — 没有股票触发 ③+④ 核心信号")
        return

    # 过滤：只要 ③+④ 或 ③ 单独 + 高分
    core = [c for c in candidates if c["has_core"]]
    secondary = [c for c in candidates if not c["has_core"] and c["score"] >= min_sig]

    picks = core + secondary
    picks = picks[:5]

    if not picks:
        print()
        print("🚫 今日无合格候选 — 有信号但未达阈值（需≥{}分）".format(min_sig))
        if candidates:
            print("   以下被过滤（可以手动观察）:")
            for c in candidates[:5]:
                print("     {} ({}/4: {})".format(c["name"], c["score"], ",".join(c["signals"])))
        return

    print()
    print("┌─ 买入候选 ─────────────────")
    for i, c in enumerate(picks, 1):
        star = "⭐" if c["has_core"] else "  "
        signals_str = ",".join(c["signals"])
        print("│ {}{}. {} [{}]  {:.2f} | MA5={:.2f} ({:+.1f}%) | {}/4: {}".format(
            star, i, c["name"], c["code"],
            c["close"], c["m5"], c["dist"],
            c["score"], signals_str))
    print("└────────────────────────────")

    print()
    print("┌─ 操作 ─────────────────────")
    allocated = position / max(len(picks), 1)
    for i, c in enumerate(picks, 1):
        if i == 1 and c["has_core"]:
            print("│ {}. {} → 买 {:.0f}% 仓位".format(i, c["name"], allocated * 100))
        elif c["has_core"]:
            print("│ {}. {} → 买 {:.0f}% 仓位".format(i, c["name"], allocated * 100 * 0.7))
        else:
            print("│ {}. {} → 轻仓 {:.0f}% (无③+④)".format(i, c["name"], allocated * 100 * 0.3))

    print("│")
    print("│ 买入时间: 14:50-14:57")
    print("│ 卖出时间: 次日 9:30-9:45")
    if position > 0.5:
        print("│ 止损: 跌破 MA5 无条件走")
    else:
        print("│ 止损: 跌破今日开盘价走")
    print("└────────────────────────────")


if __name__ == "__main__":
    main()
