"""
养家恐慌指数 v2 — 四维加权版
==============================
Yangjia Panic Index v2: breadth × depth × structure × persistence

基于养家心法框架：
  "崩溃盘解脱的那一刻，差不多就是底部了"
  "麻木的状态一直累积到某一个阶段，需要寻找一种解脱"

改进点 vs v1:
  ① 广度 — 延续原版 PANIC_INDEX（下跌占比），保留
  ② 深度 — 新增：价格跌幅映射，区分"温和普跌"和"窒息式杀跌"
  ③ 结构 — 新增：panic_bottom / breadth_thrust / breadth_divergence 信号加权
  ④ 持续性 — 新增：EMA 平滑，恐慌不会一天归零

用法:
  python3.11 panic_v2.py                          # 输出最新一天 + 对比原版
  python3.11 panic_v2.py --full                   # 输出全部历史
  python3.11 panic_v2.py --today                  # 仅今日信号 + 模型推荐
"""

import sys
import os
from dataclasses import dataclass
from typing import Optional

# ── 路径 ──────────────────────────────────────────────────
BASE = r"C:\Lazy\MarcoAI\AIData"

PANIC_FILE   = os.path.join(BASE, "1D_PANIC_INDEX")
PRICE_FILE   = os.path.join(BASE, "1D_PRICE")
SIGNALS_FILE = os.path.join(BASE, "1D_MOTION_SIGNALS")

MODEL_FILES = {
    "31":       os.path.join(BASE, "TARGET", "31_RATIO"),
    "311":      os.path.join(BASE, "TARGET", "311_RATIO"),
    "TOP_1":    os.path.join(BASE, "TARGET", "TOP_1_RATIO"),
}

OUTPUT_FILE = os.path.join(BASE, "1D_PANIC_INDEX_V2")


# ── 数据结构 ──────────────────────────────────────────────
@dataclass
class PanicDay:
    date: str
    breadth: float          # ① 广度 (0-100)，原版恐慌指数
    depth: float            # ② 深度 (0-100)，价格跌幅映射
    structure_factor: float # ③ 结构因子 (0.6-1.3)
    raw: float              # 加权前原始值
    panic_v2: float         # EMA 平滑后的养家恐慌指数 v2
    price_col2: float       # 1D_PRICE col2
    price_return: float     # col2日收益率(%)
    signals: list[str]      # 当日信号列表
    model_best: str         # 最优模型


# ── 数据加载 ──────────────────────────────────────────────
def load_panic_v1() -> dict[str, float]:
    """加载原版恐慌指数"""
    d = {}
    with open(PANIC_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            d[parts[0]] = float(parts[1])
    return d

def load_price() -> dict[str, tuple[float, float]]:
    """加载 1D_PRICE: date -> (col1, col2)"""
    d = {}
    with open(PRICE_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            d[parts[0]] = (float(parts[1]), float(parts[2]))
    return d

def load_signals() -> dict[str, list[str]]:
    """加载 MOTION_SIGNALS: date -> [signal_types]"""
    d: dict[str, list[str]] = {}
    with open(SIGNALS_FILE, encoding="gbk") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            date = parts[0]
            sig_type = parts[1]
            if date not in d:
                d[date] = []
            d[date].append(sig_type)
    return d

def load_model_ratios() -> dict[str, dict[str, float]]:
    """加载模型收益率: model_name -> {date: return}"""
    ratios: dict[str, dict[str, float]] = {}
    for name, path in MODEL_FILES.items():
        ratios[name] = {}
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or "|" not in line:
                    continue
                parts = line.split("|")
                try:
                    ratios[name][parts[0]] = float(parts[1])
                except (ValueError, IndexError):
                    continue
    return ratios


# ── 核心算法 ──────────────────────────────────────────────
def compute_depth(price_col2: float, prev_price_col2: Optional[float]) -> float:
    """
    ② 深度：将价格日跌幅映射到 0-100

    养家逻辑：普跌 -2% 和 暴跌 -7% 的恐慌程度完全不同。
    用指数映射而非线性，让大跌被放大、小跌被压缩。
    """
    if prev_price_col2 is None or prev_price_col2 == 0:
        return 50.0  # 无前值，返回中性

    pct = (price_col2 - prev_price_col2) / prev_price_col2 * 100

    if pct >= 0:
        # 上涨 → 深度 = 0 ~ 20
        return max(0, 20 - abs(pct) * 4)

    # 下跌 → sigmoid 映射，-5% 时深度约 80
    abs_pct = abs(pct)
    if abs_pct <= 5:
        return abs_pct * 16          # -1% → 16, -3% → 48, -5% → 80
    else:
        return 80 + min(20, (abs_pct - 5) * 4)  # -6% → 84, -10% → 100


def compute_structure_factor(signals: list[str]) -> float:
    """
    ③ 结构因子：根据当日信号调整恐慌强度

    养家逻辑：
      panic_bottom     → 恐慌在释放，短期超卖，×1.15
      breadth_divergence → 价跌但涨家数未新低，恐慌在减弱，×0.85
      breadth_thrust   → 广度拐点，情绪修复中，×0.80

    无信号 → ×1.0
    多信号 → 取主要信号的因子
    """
    if not signals:
        return 1.0

    # 优先级：结构信号  > 广度信号
    has_panic = "panic_bottom" in signals
    has_divergence = "breadth_divergence" in signals
    has_thrust = "breadth_thrust" in signals

    if has_panic:
        return 1.15   # 恐慌底：可能到底了，但恐慌还在释放
    if has_divergence:
        return 0.85   # 广度背离：价虽新低但恐慌在减弱
    if has_thrust:
        return 0.80   # 广度拐点：情绪已经转向

    return 1.0


def compute_raw_panic(breadth: float, depth: float, structure: float) -> float:
    """
    原始恐慌 = breadth × depth 加权 × structure_factor

    广度主导（权重 0.40）→ 多少人跌
    深度主导（权重 0.40）→ 跌了多深
    结构调节（权重 0.20）→ 信号放大/收缩

    最后 × structure_factor 整体缩放
    """
    weighted = breadth * 0.40 + depth * 0.40 + (breadth * structure - breadth) * 0.20
    # structure 大于 1 时加剧恐慌，小于 1 时减弱恐慌
    raw = weighted * structure
    return max(0, min(100, raw))


def ema_smooth(values: list[float], alpha: float = 0.4) -> list[float]:
    """
    ④ EMA 平滑：养家说的"麻木状态一直累积"

    α = 0.4 → 今日占 40%，昨日的 EMA 占 60%
    好处：恐慌不会一天从 80 跳到 6（原版的问题）
    """
    result = []
    ema = values[0]  # 第一天的 EMA = 当天值
    result.append(ema)
    for v in values[1:]:
        ema = alpha * v + (1 - alpha) * ema
        result.append(round(ema, 1))
    return result


def best_model(date: str, model_ratios: dict) -> str:
    """Pick the model with best performance on this date (for reference)"""
    best = "N/A"
    best_val = -999
    for name, ratios in model_ratios.items():
        val = ratios.get(date)
        if val is not None and val > best_val:
            best_val = val
            best = name
    return best


# ── 主流程 ──────────────────────────────────────────────
def compute_panic_v2() -> list[PanicDay]:
    """计算完整的养家恐慌指数 v2 历史序列"""
    panic_v1 = load_panic_v1()
    prices = load_price()
    signals = load_signals()
    model_ratios = load_model_ratios()

    # 按日期排序
    dates = sorted(panic_v1.keys())

    # 第一步：计算每日原始恐慌（breadth × depth × structure）
    raw_panics: list[tuple[str, float]] = []
    days: list[PanicDay] = []

    prev_price = None
    for i, date in enumerate(dates):
        b = panic_v1.get(date, 0)          # ① 广度
        col1, col2 = prices.get(date, (0, 0))
        pct = 0.0
        if prev_price is not None and prev_price != 0:
            pct = (col2 - prev_price) / prev_price * 100
        d = compute_depth(col2, prev_price) # ② 深度
        sigs = signals.get(date, [])        # ③ 结构
        sf = compute_structure_factor(sigs)
        raw = compute_raw_panic(b, d, sf)

        raw_panics.append((date, raw))
        prev_price = col2

    # 第二步：EMA 平滑
    raw_vals = [r[1] for r in raw_panics]
    smoothed = ema_smooth(raw_vals)

    # 第三步：组装结果
    prev_price2 = None
    for i, date in enumerate(dates):
        b = panic_v1.get(date, 0)
        col1, col2 = prices.get(date, (0, 0))
        pct = 0.0
        if prev_price2 is not None and prev_price2 != 0:
            pct = (col2 - prev_price2) / prev_price2 * 100
        d = compute_depth(col2, prev_price2)
        sigs = signals.get(date, [])

        days.append(PanicDay(
            date=date,
            breadth=b,
            depth=d,
            structure_factor=compute_structure_factor(sigs),
            raw=round(raw_vals[i], 1),
            panic_v2=smoothed[i],
            price_col2=col2,
            price_return=round(pct, 2),
            signals=sigs,
            model_best=best_model(date, model_ratios),
        ))
        prev_price2 = col2

    return days


# ── 展示 ──────────────────────────────────────────────────
def print_header():
    print(f"{'日期':<10} {'原版':>6} {'广度':>6} {'深度':>6} {'结构':>6} {'加权':>6} {'v2 EMA':>7}  {'价格Δ%':>7}  {'信号':<20} {'模型'}")
    print("-" * 105)


def print_day(d: PanicDay):
    sig_str = ",".join(d.signals) if d.signals else "—"
    print(
        f"{d.date:<10} "
        f"{d.breadth:>6.1f} "
        f"{d.breadth:>6.1f} "
        f"{d.depth:>6.1f} "
        f"{d.structure_factor:>5.2f}x "
        f"{d.raw:>6.1f} "
        f"{d.panic_v2:>7.1f}  "
        f"{d.price_return:>+7.2f}%  "
        f"{sig_str:<20} "
        f"{d.model_best}"
    )


def print_today_analysis(days: list[PanicDay]):
    """最新一天的完整分析"""
    if not days:
        print("无数据")
        return

    d = days[-1]
    print(f"\n{'='*60}")
    print(f"  养家恐慌指数 v2 — {d.date}")
    print(f"{'='*60}")
    print(f"  原版 PANIC  : {d.breadth:.1f}")
    print(f"  广度 (原版)  : {d.breadth:.1f}  (下跌占比)")
    print(f"  深度 (价格)  : {d.depth:.1f}  (价格日跌 {d.price_return:+.2f}%)")
    print(f"  结构因子    : {d.structure_factor:.2f}x  ({','.join(d.signals) if d.signals else '无特殊信号'})")
    print(f"  加权原始值   : {d.raw:.1f}")
    print(f"  ─────────────────────────────")
    print(f"  养家恐慌 v2  : {d.panic_v2:.1f}  ← EMA 平滑后")

    # 恐慌等级判断
    if d.panic_v2 >= 75:
        level = "🔴 极度恐慌 — 崩溃盘正在释放，接近底部"
    elif d.panic_v2 >= 55:
        level = "🟠 高度恐慌 — 恐慌在累积，等加速杀跌"
    elif d.panic_v2 >= 35:
        level = "🟡 中度恐慌 — 分歧中，多看少动"
    elif d.panic_v2 >= 15:
        level = "🟢 低恐慌 — 情绪修复中，回暖窗口"
    else:
        level = "✅ 无恐慌 — 正常市场，按节奏操作"

    print(f"\n  等级判定: {level}")

    # 趋势判断
    if len(days) >= 3:
        trend = [days[i].panic_v2 for i in range(-3, 0)]
        if trend[-1] > trend[0] + 10:
            print(f"  趋势: 🔴 恐慌在加速上升 ({trend[0]:.0f} → {trend[-1]:.0f})")
        elif trend[-1] > trend[0]:
            print(f"  趋势: 🟠 恐慌在缓慢上升 ({trend[0]:.0f} → {trend[-1]:.0f})")
        elif trend[-1] < trend[0] - 10:
            print(f"  趋势: 🟢 恐慌在快速消退 ({trend[0]:.0f} → {trend[-1]:.0f}) — 回暖信号")
        elif trend[-1] < trend[0]:
            print(f"  趋势: 🟡 恐慌在缓慢消退 ({trend[0]:.0f} → {trend[-1]:.0f})")
        else:
            print(f"  趋势: ⚪ 持平")

    # 模型推荐
    if d.model_best != "N/A":
        print(f"\n  最优模型: {d.model_best}")

    # 养家策略建议
    print(f"\n  ── 养家策略建议 ──")
    if d.panic_v2 >= 70:
        print("  仓位: ≤10% | 策略: 等崩溃盘出清 → 放量下影线 → 试探性买入")
        print("  养家: '崩溃盘解脱的那一刻，差不多就是底部了'")
    elif d.panic_v2 >= 50:
        print("  仓位: ≤20% | 策略: 等恐慌加速或消退，不要抄底")
        print("  养家: '下跌中期，强势股反弹遭到更多抛压'")
    elif d.panic_v2 >= 30:
        print("  仓位: 20-40% | 策略: 回暖分歧期，MA5 拐点信号可试探")
        print("  养家: '反复震荡后，市场信心逐步恢复'")
    elif d.panic_v2 >= 15:
        print("  仓位: 40-60% | 策略: 回暖确认，积极选股")
    else:
        print("  仓位: 60-80% | 策略: 正常市场节奏，按信号操作")

    print(f"{'='*60}\n")


def main():
    days = compute_panic_v2()

    if not days:
        print("❌ 无数据，请检查 AIData 目录")
        return

    # 保存到输出文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for d in days:
            f.write(f"{d.date}|{d.panic_v2:.1f}|{d.breadth:.1f}|{d.depth:.1f}|{d.structure_factor:.2f}|{d.raw:.1f}\n")
    print(f"✅ 已保存到 {OUTPUT_FILE} ({len(days)} 条)\n")

    if "--full" in sys.argv:
        print_header()
        for d in days:
            print_day(d)
    elif "--today" in sys.argv:
        print_today_analysis(days)
    else:
        # 默认：最近 10 天 + 今日分析
        print(f"{'最近10天 v2 对比原版':^105}")
        print_header()
        for d in days[-10:]:
            print_day(d)
        print()
        print_today_analysis(days)


# ===== MA 交叉趋势联动 ====

MA_CROSS_FILE = r"C:\Lazy\MarcoAI\AIData\1D_MA_CROSS"


def load_ma_trend():
    """加载 MA 交叉趋势数据"""
    data = {}
    if not os.path.exists(MA_CROSS_FILE):
        return data
    with open(MA_CROSS_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 8:
                continue
            try:
                date = parts[0]
                dual_bear = float(parts[1])
                dual_bull = float(parts[2])
                pb = float(parts[3])
                ab = float(parts[4])
                pu = float(parts[5])
                au = float(parts[6])
                judgment = parts[7]
            except (ValueError, IndexError):
                continue
            data[date] = {
                "dual_bear": dual_bear,
                "dual_bull": dual_bull,
                "pb": pb,
                "ab": ab,
                "pu": pu,
                "au": au,
                "judgment": judgment,
            }
    return data


def compute_slope(data: dict, date: str, window: int = 5) -> float:
    """计算双空在 window 天内的变化斜率"""
    dates = sorted(data.keys())
    if date not in dates:
        return 0
    idx = dates.index(date)
    if idx < window:
        return 0
    prev = data[dates[idx - window]]["dual_bear"]
    curr = data[date]["dual_bear"]
    return curr - prev


def ma_trend_judgment(slope: float, improve_days: int, worsen_days: int) -> str:
    """根据 MA 趋势给出综合判断"""
    if improve_days >= 4:
        return "🔥 连续4天改善 — 最强做多信号，仓位可到80%"
    if improve_days >= 3:
        return "🔥 连续3天改善 — 回暖确认，仓位可到60%"
    if worsen_days >= 3:
        return "🔴 连续3天恶化 — 危险，仓位降到20%以下"
    if slope < -8:
        return "🟢 急降改善 — 积极选股"
    if slope < -3:
        return "🟢 缓降改善 — 正常选股"
    if slope > 8:
        return "⚠️ 急升恶化 — 等反弹，不选股"
    if slope > 3:
        return "🔴 缓升恶化 — 最危险，坚决不选股"
    return "🟡 横盘中性 — 谨慎选股"


def print_ma_trend_summary():
    """打印 MA 交叉趋势摘要"""
    data = load_ma_trend()
    if not data:
        return

    dates = sorted(data.keys())
    if len(dates) < 10:
        return

    latest = data[dates[-1]]
    slope_5 = compute_slope(data, dates[-1], 5)
    slope_10 = compute_slope(data, dates[-1], 10) if len(dates) >= 10 else 0

    # 统计最近 N 天的改善/恶化
    recent_n = min(10, len(dates))
    improve_count = 0
    worsen_count = 0
    for i in range(len(dates) - recent_n, len(dates)):
        if i == 0:
            continue
        d_bear = data[dates[i]]["dual_bear"] - data[dates[i - 1]]["dual_bear"]
        d_bull = data[dates[i]]["dual_bull"] - data[dates[i - 1]]["dual_bull"]
        if d_bear < -0.5 and d_bull > 0.5:
            improve_count += 1
        if d_bear > 0.5 and d_bull < -0.5:
            worsen_count += 1

    judgment = ma_trend_judgment(slope_5, improve_count, worsen_count)

    print()
    print("=" * 60)
    print("📊 MA 交叉趋势（市场宽度）")
    print("=" * 60)
    print("  最新日期: {}".format(dates[-1]))
    print("  双空(MA10<MA5): {:.1f}%  |  双多(MA10>MA5): {:.1f}%".format(latest["dual_bear"], latest["dual_bull"]))
    print("  价格 MA10<MA5: {:.1f}%  |  成交额 MA10<MA5: {:.1f}%".format(latest["pb"], latest["ab"]))
    print("  5日斜率: {:+.1f}%  |  10日斜率: {:+.1f}%".format(slope_5, slope_10))
    print("  最近{}天: 改善{}天, 恶化{}天".format(recent_n, improve_count, worsen_count))
    print("  → {}".format(judgment))
    print("=" * 60)


if __name__ == "__main__":
    main()
    print_ma_trend_summary()
