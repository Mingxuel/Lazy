"""ETF金叉买入/死叉卖出策略回测
策略：全市场History MA10上穿MA5+成交额MA10上穿MA5(金叉)→买指数ETF，死叉卖出
"""
import os

DATA_DIR = r'C:\Lazy\MarcoAI\AIData\1D'
PRICE_FILE = r'C:\Lazy\MarcoAI\AIData\1D_PRICE'

def load_price_index():
    d = {}
    with open(PRICE_FILE, encoding='utf-8') as f:
        for line in f:
            p = line.strip().split('|')
            if len(p) < 2:
                continue
            try:
                v1 = float(p[1])
                v2 = float(p[2]) if len(p) >= 3 else v1
                d[p[0].strip()] = (v1, v2)
            except ValueError:
                continue
    return d

def load_all():
    stocks = {}
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith(('.SZ', '.SH')):
            continue
        fp = os.path.join(DATA_DIR, fname)
        if os.path.getsize(fp) < 100:
            continue
        rows = []
        with open(fp, encoding='utf-8') as f:
            for line in f:
                p = line.strip().split('|')
                if len(p) < 7:
                    continue
                try:
                    rows.append((p[0].strip(), float(p[4]), float(p[6])))
                except ValueError:
                    continue
        if rows:
            stocks[os.path.splitext(fname)[0]] = rows
    return stocks

def ma(vals, w):
    if len(vals) < w:
        return None
    return sum(vals[-w:]) / w

print("加载全市场数据...")
prices = load_price_index()
all_stocks = load_all()
print(f"价格指数: {len(prices)}天, 个股: {len(all_stocks)}只")

# 计算每日全市场金叉/死叉占比
all_dates = sorted({d for s in all_stocks.values() for d, _, _ in s})
print(f"日期范围: {all_dates[0]} ~ {all_dates[-1]}")

# 先算每只股票每天的金叉/死叉，再汇总
from collections import defaultdict
daily_golden = defaultdict(int)
daily_death = defaultdict(int)
daily_total = defaultdict(int)

print("逐日计算全市场交叉信号...")
for code, rows in all_stocks.items():
    for idx in range(10, len(rows)):
        date = rows[idx][0]
        closes = [r[1] for r in rows[:idx + 1]]
        amounts = [r[2] for r in rows[:idx + 1]]

        m5p_t = ma(closes, 5)
        m10p_t = ma(closes, 10)
        m5a_t = ma(amounts, 5)
        m10a_t = ma(amounts, 10)
        m5p_y = ma(closes[:-1], 5)
        m10p_y = ma(closes[:-1], 10)
        m5a_y = ma(amounts[:-1], 5)
        m10a_y = ma(amounts[:-1], 10)

        if None in (m5p_t, m10p_t, m5a_t, m10a_t, m5p_y, m10p_y, m5a_y, m10a_y):
            continue

        daily_total[date] += 1

        # 价格金叉: 昨日MA5<=MA10 且 今日MA5>MA10
        price_g = m5p_y <= m10p_y and m5p_t > m10p_t
        price_d = m5p_y >= m10p_y and m5p_t < m10p_t
        # 成交额金叉
        amt_g = m5a_y <= m10a_y and m5a_t > m10a_t
        amt_d = m5a_y >= m10a_y and m5a_t < m10a_t

        if price_g or amt_g:
            daily_golden[date] += 1
        if price_d or amt_d:
            daily_death[date] += 1

# 百分比
market_golden = {}
market_death = {}
for d in sorted(daily_total.keys()):
    tot = daily_total[d]
    if tot > 0:
        market_golden[d] = daily_golden[d] / tot * 100
        market_death[d] = daily_death[d] / tot * 100

print(f"金叉数据: {len(market_golden)}天")

# ETF价格序列（用价格指数第二列）
etf_prices = []
for d in sorted(prices.keys()):
    v1, v2 = prices[d]
    etf_prices.append((d, v2 if v2 else v1))

# ── 回测 ──
print("\n回测金叉死叉策略...\n")

results = []
for GOLDEN_TH in [20, 25, 30, 35, 40]:
    for DEATH_TH in [20, 25, 30, 35, 40]:
        pos = False
        ep = 0
        ed = ''
        trades = []
        cv = 1.0

        for pi, (date, price) in enumerate(etf_prices):
            if date not in market_golden:
                continue
            gp = market_golden[date]
            dp = market_death[date]

            if not pos:
                if gp > GOLDEN_TH:
                    pos = True
                    ep = price
                    ed = date
            else:
                if dp > DEATH_TH:
                    pos = False
                    ret = (price - ep) / ep * 100
                    days = pi - next(i for i, (d, _) in enumerate(etf_prices) if d == ed)
                    trades.append({'entry': ed, 'exit': date, 'ret': ret, 'days': days})
                    cv *= (1 + ret / 100)
                    ep = 0

        if pos and ep > 0:
            ret = (etf_prices[-1][1] - ep) / ep * 100
            trades.append({'entry': ed, 'exit': etf_prices[-1][0], 'ret': ret, 'days': 0})
            cv *= (1 + ret / 100)

        if trades:
            w = sum(1 for t in trades if t['ret'] > 0)
            total_ret = (cv - 1) * 100
            buy_hold = (etf_prices[-1][1] - etf_prices[0][1]) / etf_prices[0][1] * 100
            exc = total_ret - buy_hold
            results.append((GOLDEN_TH, DEATH_TH, len(trades), w, w/len(trades)*100, total_ret, exc, trades))

# 按超额收益排序
results.sort(key=lambda x: -x[6])

print("=" * 80)
print("ETF金叉买入/死叉卖出 — 全参数敏感性分析")
print("=" * 80)
print(f"标的: 价格指数(ETF代理)")
print(f"买入持有基准: {(etf_prices[-1][1]-etf_prices[0][1])/etf_prices[0][1]*100:+.2f}%")
print()
print(f"{'买%':>5s} | {'卖%':>5s} | {'笔数':>4s} | {'胜率':>5s} | {'收益':>8s} | {'超额':>8s}")
print("-" * 55)

for r in results[:15]:  # top 15
    print(f"{r[0]:>4d}% | {r[1]:>4d}% | {r[2]:>4d} | {r[3]/r[2]*100:>4.0f}% | {r[5]:>+7.2f}% | {r[6]:>+7.2f}%")

# 最佳参数详析
best = results[0]
print(f"\n\n最佳参数: 买入金叉>{best[0]}% | 卖出死叉>{best[1]}%")
print(f"收益: {best[5]:+.2f}% | 超额: {best[6]:+.2f}% | 笔数: {best[2]}")
print()

trades = best[7]
print("逐笔交易:")
for t in trades:
    a = '✅' if t['ret'] > 0 else '❌'
    print(f"  {t['entry']} → {t['exit']} | {t['ret']:+.2f}% | {t['days']}天 {a}")

# 每年
print("\n分年:")
for yr in ['2025', '2026']:
    yt = [t for t in trades if t['exit'].startswith(yr)]
    if yt:
        yr_cv = 1.0
        for t in yt:
            yr_cv *= (1 + t['ret'] / 100)
        yr_ret = (yr_cv - 1) * 100
        yr_w = sum(1 for t in yt if t['ret'] > 0)
        print(f"  {yr}: {len(yt)}笔, 胜率{yr_w/len(yt)*100:.0f}%, 收益{yr_ret:+.2f}%")
