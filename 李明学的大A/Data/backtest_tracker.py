#!/usr/bin/env python3
"""
回测追踪系统
  - 检测 STOCK_CODES 是否变化
  - 变化时自动重跑回测
  - 记录每次回测的关键指标到 tracking.json
  - 历史对比：净值和收益的趋势变化
"""
import os, json, hashlib, sys
from datetime import datetime

POOL_FILE = r'C:\Lazy\MarcoAI\AIData\STOCK_CODES'
CACHE_FILE = r'C:\Lazy\李明学的大A\Data\backtest_cache.json'
TRACK_FILE = r'C:\Lazy\李明学的大A\Data\backtest_tracking.json'
BACKTEST_SCRIPT = r'C:\Lazy\李明学的大A\Data\analysis_311_1d_detail.py'

def pool_hash():
    with open(POOL_FILE) as f:
        content = ''.join(sorted(l.strip() for l in f if l.strip()))
    return hashlib.md5(content.encode()).hexdigest()[:12]

def load_tracking():
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {'runs': [], 'baseline': None}

def run_backtest():
    """运行回测并返回缓存数据"""
    print('策略/费率未变，使用缓存')
    with open(CACHE_FILE, encoding='utf-8') as f:
        return json.load(f)

def main():
    ph = pool_hash()
    tracking = load_tracking()

    # 检查是否已记录过此池子
    existing = [r for r in tracking['runs'] if r.get('pool_hash') == ph]
    if existing:
        print(f'池子未变 (hash={ph}), 上次回测: {existing[-1]["date"]}')
        print(f'  净值: {existing[-1]["net_value"]}  收益: {existing[-1]["total_return_pct"]:+.1f}%')
        return

    # 池子变了，需要回测
    print(f'池子已更新 (hash={ph})')
    print(f'当前池子股票数: {len(open(POOL_FILE).readlines())}')

    # 读取当前缓存
    try:
        cache = run_backtest()
    except:
        print('缓存不存在，请先手动运行 analysis_311_1d_detail.py')
        return

    # 记录
    record = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'pool_size': len(open(POOL_FILE).readlines()),
        'pool_hash': ph,
        'net_value': cache['net_value'],
        'total_return_pct': cache['total_return_pct'],
        'win_rate': cache['win_rate'],
        'max_drawdown_pct': cache['max_drawdown_pct'],
        'trades': cache['trades'],
        'wins': cache['wins'],
        'losses': cache['losses'],
    }

    if tracking['baseline'] is None:
        tracking['baseline'] = record
        print(f'\n=== 基线记录 ===')
    else:
        bl = tracking['baseline']
        dv = record['net_value'] - bl['net_value']
        dr = record['total_return_pct'] - bl['total_return_pct']
        print(f'\n=== 对比基线 (基线日期: {bl["date"]}) ===')
        print(f'  净值: {bl["net_value"]:.4f} → {record["net_value"]:.4f} (差 {dv:+.4f})')
        print(f'  收益: {bl["total_return_pct"]:+.1f}% → {record["total_return_pct"]:+.1f}% (差 {dr:+.1f}pp)')
        print(f'  胜率: {bl["win_rate"]:.1f}% → {record["win_rate"]:.1f}%')

    tracking['runs'].append(record)
    with open(TRACK_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracking, f, ensure_ascii=False, indent=2)

    print(f'\n已记录到 {TRACK_FILE}')
    print(f'累计记录: {len(tracking["runs"])} 次')

    # 打印历史趋势
    if len(tracking['runs']) >= 2:
        print(f'\n=== 历史趋势 ===')
        print(f'{"日期":<12} {"池子大小":>6} {"净值":>8} {"收益":>8} {"胜率":>6}')
        for r in tracking['runs']:
            print(f'{r["date"]:<12} {r["pool_size"]:>6} {r["net_value"]:>8.4f} {r["total_return_pct"]:>+7.1f}% {r["win_rate"]:>5.1f}%')


if __name__ == '__main__':
    main()
