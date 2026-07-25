"""
HISTORY MA5/MA10 交叉分析
验证：当 MA10 在 MA5 下方（价格+成交额）→ 行情不好
      当 MA10 在 MA5 上方 → 行情好
"""
import os
from collections import defaultdict

HISTORY_DIR = r"C:\Lazy\MarcoAI\AIData\TARGET\HISTORY"
PRICE_FILE = r"C:\Lazy\MarcoAI\AIData\1D_PRICE"

def load_history(date_str):
    """加载单日 HISTORY: code -> {open,high,low,close,vol,amt,ma5}"""
    path = os.path.join(HISTORY_DIR, date_str)
    if not os.path.exists(path):
        return {}
    stocks = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or '|' not in line:
                continue
            parts = line.split('|')
            if len(parts) < 8:
                continue
            code = parts[0]
            stocks[code] = {
                'open': float(parts[1]),
                'high': float(parts[2]),
                'low': float(parts[3]),
                'close': float(parts[4]),
                'volume': float(parts[5]),
                'amount': float(parts[6]),
                'ma5': float(parts[7]),
            }
    return stocks

def load_price_index():
    """加载价格指数: date -> (col1, col2)"""
    prices = {}
    with open(PRICE_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or '|' not in line:
                continue
            parts = line.split('|')
            if len(parts) >= 3:
                prices[parts[0]] = (float(parts[1]), float(parts[2]))
    return prices

def compute_ma(values, n):
    """计算 MA(n)"""
    if len(values) < n:
        return None
    return sum(values[-n:]) / n

def analyze(dates, min_stocks=10):
    """分析各日的 MA5/MA10 交叉占比"""
    prices = load_price_index()
    
    # 先收集所有股票各日的收盘价和成交额
    all_data = defaultdict(lambda: defaultdict(dict))  # code -> date -> data
    
    for d in dates:
        stocks = load_history(d)
        for code, data in stocks.items():
            all_data[code][d] = data
    
    print(f"{'日期':<10} {'价格MA10<MA5':>14} {'成交额MA10<MA5':>14} {'双指标偏空':>12} {'双指标偏多':>12} {'价格指数':>10} {'市场方向':>10}")
    print("-" * 100)
    
    results = []
    
    for day_idx, d in enumerate(dates):
        # 取最近10个交易日的日期列表
        if day_idx < 9:
            continue
        window = dates[day_idx-9:day_idx+1]
        
        price_bear = 0  # MA10 < MA5
        price_bull = 0  # MA10 > MA5
        amt_bear = 0
        amt_bull = 0
        total = 0
        
        for code in all_data:
            closes = []
            amounts = []
            has_data = True
            for wd in window:
                if wd in all_data[code]:
                    closes.append(all_data[code][wd]['close'])
                    amounts.append(all_data[code][wd]['amount'])
                else:
                    has_data = False
                    break
            
            if not has_data or len(closes) < 10:
                continue
            total += 1
            
            ma5_price = compute_ma(closes, 5)
            ma10_price = compute_ma(closes, 10)
            ma5_amt = compute_ma(amounts, 5)
            ma10_amt = compute_ma(amounts, 10)
            
            if ma5_price and ma10_price:
                if ma10_price < ma5_price:
                    price_bear += 1
                elif ma10_price > ma5_price:
                    price_bull += 1
            
            if ma5_amt and ma10_amt:
                if ma10_amt < ma5_amt:
                    amt_bear += 1
                elif ma10_amt > ma5_amt:
                    amt_bull += 1
        
        price_bear_pct = price_bear / total * 100 if total else 0
        amt_bear_pct = amt_bear / total * 100 if total else 0
        
        # 双指标偏空：价格MA10<MA5 且 成交额MA10<MA5
        # 双指标偏多：价格MA10>MA5 且 成交额MA10>MA5
        # 用占比近似估算
        dual_bear = min(price_bear_pct, amt_bear_pct) if (price_bear_pct or amt_bear_pct) else 0
        price_bull_pct = price_bull / total * 100 if total else 0
        amt_bull_pct = amt_bull / total * 100 if total else 0
        dual_bull = min(price_bull_pct, amt_bull_pct) if (price_bull_pct or amt_bull_pct) else 0
        
        price_idx = prices.get(d, (None, None))
        idx_val = price_idx[1] if price_idx[1] else (price_idx[0] or 0)
        
        # 市场方向判断
        if day_idx > 0:
            prev_price = prices.get(dates[day_idx-1], (0,0))
            prev_val = prev_price[1] if prev_price[1] else prev_price[0]
            if prev_val:
                change = (idx_val - prev_val) / prev_val * 100
                direction = f"{change:+.2f}%"
            else:
                direction = "N/A"
        else:
            direction = "N/A"
        
        print(f"{d:<10} {price_bear_pct:>10.1f}% ({price_bear}/{total}) {amt_bear_pct:>10.1f}% ({amt_bear}/{total}) {dual_bear:>8.1f}% {dual_bull:>8.1f}% {idx_val:>10.4f} {direction:>10}")
        
        results.append({
            'date': d,
            'price_bear_pct': price_bear_pct,
            'amt_bear_pct': amt_bear_pct,
            'dual_bear': dual_bear,
            'dual_bull': dual_bull,
            'price_idx': idx_val,
            'direction': direction,
            'total': total,
        })
    
    return results

if __name__ == '__main__':
    dates = sorted(os.listdir(HISTORY_DIR))
    dates = [d for d in dates if os.path.isfile(os.path.join(HISTORY_DIR, d))]
    dates = sorted(dates)
    
    print(f"共 {len(dates)} 个交易日")
    print()
    analyze(dates)
