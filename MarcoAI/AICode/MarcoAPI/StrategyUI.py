"""
策略回测 + 实盘目标股综合看板生成器

功能:
    生成一个自包含的交互式 HTML 面板（AICode/MarcoAPI/UI/StrategyDashboard.html）：
        TAB1 策略回测
           - 自由选择策略
           - 三种卖出方式（first/last/avg）逐日资金曲线对比（Chart.js 折线图）
           - 每月 / 季度 / 每年收益
        TAB2 实盘候选池
           - 候选股票池按日期倒序显示（默认最新日期，T-2 日收盘后确定，下个交易日可买入）
           - 点击候选股展示日线 K 线图（LightweightCharts，MA5/10/20/60 + 成交量）
    双击 HTML 即可在浏览器中交互，无需服务器。

数据来源:
    MarcoAI/AIData/Strategy/{策略名}/  每日选股文件（回测）
    MarcoAI/AIData/TARGET/{策略名}/{日期}   T-2 日候选股票池（实盘，每行 代码|名称|市值）
    MarcoAI/AIData/1D_ORIGIN/{代码}    原始日线（K 线，MA 由前端计算）
"""

import json
import os
import re
import sys
import webbrowser
from typing import Any

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Backtest import (
    _load_strategy, _daily_return, INIT_CAPITAL, SELL_MODES
)
from AICode.MarcoAPI.Update.Path import (
    PATH_AIDATA_STRATEGY, PATH_AIDATA_TARGET, PATH_AIDATA_1D_ORIGIN, PATH_AIDATA
)
from AICode.MarcoAPI.Update.Update1D import UPDATE_ALL

KLINE_DAYS = 120  # 内嵌每只候选股最近 120 天 K 线数据

# 同花顺板块 XML：模板与拷贝目标目录（实盘机）
THS_TEMPLATE_FILE = PATH_AIDATA() + "/THS/blockstockV3.xml"
THS_TARGET_DIR = r"C:\同花顺远航版\bin\users\狗蛋儿家的金"
THS_BLOCK_NAME = "blockstockV3.xml"

# 板块占位符
PLACEHOLDER_TPO3  = "===TPO3==="
PLACEHOLDER_TPO31 = "===TPO31==="


def _read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="ignore")


def _to_float(v: str) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _load_strategy_detail(strategies: list[str]) -> dict[str, dict[str, list[dict[str, object]]]]:
    """加载各策略每天的选股详情，返回 {策略: {日期: [{code,name,market,open,high,low,close,pre,vol,amount,chg}]}}"""
    out: dict[str, dict[str, list[dict[str, object]]]] = {}
    for name in strategies:
        daily = _load_strategy(name)
        detail: dict[str, list[dict[str, object]]] = {}
        for date in sorted(daily):
            rows = []
            for r in daily[date]:
                if len(r) < 11:
                    continue
                close = _to_float(r[7])
                pre = _to_float(r[10])
                item = {
                    "code": r[0],
                    "name": r[1] if len(r) > 1 else "",
                    "market": r[2] if len(r) > 2 else "",
                    "open": _to_float(r[4]),
                    "high": _to_float(r[5]),
                    "low": _to_float(r[6]),
                    "close": close,
                    "pre": pre,
                    "vol": _to_float(r[8]),
                    "amount": _to_float(r[9]),
                    "chg": round((close - pre) / pre * 100, 2) if pre else 0.0,
                }
                rows.append(item)
            detail[date] = rows
        out[name] = detail
    return out


def _build_strategy_payload(strategy_name: str) -> dict[str, object]:
    """构建单个策略的回测数据"""
    daily = _load_strategy(strategy_name)
    dates = sorted(daily)

    modes = {}
    for mode in SELL_MODES:
        capital = INIT_CAPITAL
        capitals = []
        for date in dates:
            capital *= (1.0 + _daily_return(daily[date], mode))
            capitals.append(round(capital, 2))
        modes[mode] = {
            "capitals": capitals,
            "total": round(capital / INIT_CAPITAL - 1.0, 6),
            "final": round(capital, 2),
        }

    # 每月/季度/每年收益（区间复利）
    month = {m: {} for m in SELL_MODES}
    quarter = {m: {} for m in SELL_MODES}
    year = {m: {} for m in SELL_MODES}
    for mode in SELL_MODES:
        for date in dates:
            ret = _daily_return(daily[date], mode)
            ym = date[:6]
            month[mode][ym] = month[mode].get(ym, 1.0) * (1 + ret)
            qm = _quarter_of(date)
            quarter[mode][qm] = quarter[mode].get(qm, 1.0) * (1 + ret)
            y = date[:4]
            year[mode][y] = year[mode].get(y, 1.0) * (1 + ret)
        month[mode] = {k: round(v - 1, 6) for k, v in month[mode].items()}
        quarter[mode] = {k: round(v - 1, 6) for k, v in quarter[mode].items()}
        year[mode] = {k: round(v - 1, 6) for k, v in year[mode].items()}

    return {
        "name": strategy_name,
        "dates": dates,
        "modes": modes,
        "month": month,
        "quarter": quarter,
        "year": year,
    }


def _quarter_of(date: str) -> str:
    q = (int(date[4:6]) - 1) // 3 + 1
    return f"{date[:4]}Q{q}"


def _list_strategies() -> list[str]:
    base = PATH_AIDATA_STRATEGY()
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and d != "RESULT")


def _load_candidates(strategy_name: str) -> dict[str, list[list[str]]]:
    """读取策略候选池 {日期: [[code, name, market], ...]}（日期倒序，默认最新）"""
    base = PATH_AIDATA_TARGET(strategy_name)
    if not os.path.isdir(base):
        return {}
    candidates = {}
    for f in os.listdir(base):
        if not f.isdigit():
            continue
        rows = []
        for line in _read_text(os.path.join(base, f)).splitlines():
            line = line.strip()
            if not line:
                continue
            cols = line.split("|")
            code = cols[0]
            name = cols[1] if len(cols) > 1 else ""
            market_value = cols[2] if len(cols) > 2 else ""
            rows.append([code, name, market_value])
        if rows:
            candidates[f] = rows
    # 倒序（默认显示最新）
    return dict(sorted(candidates.items(), key=lambda x: x[0], reverse=True))


def _load_kline(codes: set[str], names: dict[str, str] | None = None) -> dict[str, dict[str, Any]]:
    """读取候选股的【全部历史】原始日线（1D_ORIGIN）。

    仅传原始 OHLCV，所有指标（MA/MACD/KDJ/BOLL/VWAP）与月线聚合
    均由前端 JS 动态计算，便于配置切换。names 提供 code->股票名称。
    """
    names = names or {}
    kline = {}
    for code in codes:
        path = os.path.join(PATH_AIDATA_1D_ORIGIN(), code)
        if not os.path.exists(path):
            continue
        lines = _read_text(path).splitlines()
        rows = [l.split("|") for l in lines if l.strip() and len(l.split("|")) >= 6]
        ohlcv = []
        for r in rows:
            # r[0] 是 YYYYMMDD（如 20260105），LightweightCharts 要求 YYYY-MM-DD
            t = r[0][:4] + '-' + r[0][4:6] + '-' + r[0][6:8]
            ohlcv.append({
                "time": t, "open": float(r[1]), "high": float(r[2]),
                "low": float(r[3]), "close": float(r[4]), "volume": float(r[5]),
            })
        kline[code] = {"ohlcv": ohlcv, "name": names.get(code, code)}
    return kline


def _render_html(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    strategies_json = json.dumps(data.get("strategies", []), ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>策略回测 & 实盘目标股看板</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%230f172a'/%3E%3Crect width='64' height='64' rx='14' fill='url(%23g)'/%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='64' y2='64'%3E%3Cstop offset='0' stop-color='%232b6cb0'/%3E%3Cstop offset='1' stop-color='%231d4ed8'/%3E%3C/linearGradient%3E%3C/defs%3E%3Cpath d='M16 44 L26 34 L34 40 L48 24' stroke='white' stroke-width='4' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3Cpath d='M48 24 L42 24 M48 24 L48 30' stroke='white' stroke-width='4' fill='none' stroke-linecap='round'/%3E%3Crect x='30' y='28' width='5' height='12' rx='1.5' fill='%23f59e0b'/%3E%3C/svg%3E">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<!-- TradingView Lightweight Charts -->
<script src="https://unpkg.com/lightweight-charts@5.0.8/dist/lightweight-charts.standalone.production.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; }}
body {{ font-family: 'Microsoft YaHei', sans-serif; background: #0f1117; color: #e4e6eb; display: flex; overflow: hidden; }}
/* ---- 左侧快捷命令侧边栏 ---- */
.sidebar {{ width: 210px; min-width: 210px; background: #141821; border-right: 1px solid #262c38; display: flex; flex-direction: column; height: 100vh; }}
.sidebar .brand {{ padding: 18px 16px; font-size: 15px; font-weight: 700; color: #e4e6eb; border-bottom: 1px solid #262c38; letter-spacing: .5px; }}
.sidebar .brand small {{ display: block; font-size: 11px; color: #6b7280; font-weight: 400; margin-top: 3px; }}
.sidebar .section {{ padding: 14px 16px 6px; font-size: 11px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; }}
.sidebar .cmds {{ padding: 4px 12px 12px; overflow-y: auto; }}
.sidebar .cmd {{ display: flex; align-items: center; gap: 8px; width: 100%; text-align: left; background: #1c2029; color: #e4e6eb; border: 1px solid #2a3140; border-radius: 7px; padding: 9px 11px; margin-bottom: 7px; font-size: 13px; cursor: pointer; transition: background .15s, border-color .15s; }}
.sidebar .cmd:hover {{ background: #252b38; border-color: #3a4556; }}
.sidebar .cmd:active {{ transform: translateY(1px); }}
.sidebar .cmd .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #2b6cb0; flex-shrink: 0; }}
.sidebar .cmd.danger .dot {{ background: #ef5350; }}
.sidebar .cmd.running {{ opacity: .6; pointer-events: none; }}
.sidebar .cmd.running .spinner {{ display: inline-block; width: 12px; height: 12px; border: 2px solid #9aa0a6; border-top-color: transparent; border-radius: 50%; animation: spin .8s linear infinite; flex-shrink: 0; }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.sidebar .cmd .spinner {{ display: none; }}
.sidebar .cmd-output {{ padding: 12px 14px 16px; border-top: 1px solid #262c38; overflow: hidden; display: flex; flex-direction: column; min-height: 90px; }}
.sidebar .cmd-output .label {{ font-size: 11px; color: #9aa0a6; margin-bottom: 6px; }}
.sidebar .cmd-output pre {{ flex: 1; font-size: 11px; line-height: 1.5; color: #b8c0cc; white-space: pre-wrap; word-break: break-all; overflow-y: auto; max-height: 22vh; font-family: Consolas, monospace; }}
.main {{ flex: 1; padding: 20px; overflow-y: auto; }}
h1 {{ font-size: 22px; margin-bottom: 16px; }}
.toolbar {{ display: flex; gap: 16px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }}
.toolbar label {{ font-size: 13px; color: #9aa0a6; }}
select {{ background: #1c2029; color: #e4e6eb; border: 1px solid #333a46; padding: 8px 10px; border-radius: 6px; font-size: 14px; }}
/* TAB */
.tabs {{ display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid #262c38; }}
.tab {{ padding: 10px 22px; cursor: pointer; font-size: 14px; color: #9aa0a6; border: 1px solid transparent; border-bottom: none; border-radius: 8px 8px 0 0; }}
.tab.active {{ color: #fff; background: #171a21; border-color: #262c38; }}
.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; }}
.card {{ background: #171a21; border: 1px solid #262c38; border-radius: 10px; padding: 18px; margin-bottom: 18px; }}
.card h2 {{ font-size: 15px; color: #9aa0a6; margin-bottom: 12px; font-weight: 500; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
@media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 6px 8px; text-align: left; border-bottom: 1px solid #262c38; }}
th {{ color: #9aa0a6; font-weight: 500; }}
.pos {{ color: #26a69a; }} .neg {{ color: #ef5350; }}
.chart-wrap {{ position: relative; height: 320px; }}
#panel-detail table {{ font-size: 12px; }}
#panel-detail td {{ white-space: nowrap; }}
#panel-detail tbody tr:hover {{ background: #1c2029; }}
#detail-groups {{ max-height: 74vh; overflow-y: auto; }}
.detail-date-head {{ background: #1c2029; color: #ffca28; font-size: 12px; font-weight: 600; padding: 6px 10px; margin: 8px 0 4px; border-radius: 5px; border-left: 3px solid #ffca28; }}
.detail-date-head:first-child {{ margin-top: 0; }}
table.detail-table {{ width: 100%; border-collapse: collapse; margin-bottom: 4px; table-layout: fixed; }}
table.detail-table th, table.detail-table td {{ padding: 5px 6px; text-align: right; border-bottom: 1px solid #232a36; overflow: hidden; text-overflow: ellipsis; }}
table.detail-table th:first-child, table.detail-table td:first-child {{ text-align: center; }}
table.detail-table thead th {{ position: sticky; top: 0; background: #141821; color: #9aa0a6; font-weight: 600; z-index: 1; }}
table.detail-table tbody tr:hover {{ background: #1c2029; }}
/* 固定列宽 */
table.detail-table th:nth-child(1) {{ width: 30px; }}
table.detail-table th:nth-child(2) {{ width: 78px; }}
table.detail-table th:nth-child(3) {{ width: 86px; }}
table.detail-table th:nth-child(4) {{ width: 66px; }}
table.detail-table th:nth-child(5) {{ width: 78px; }}
table.detail-table th:nth-child(n+6):nth-child(-n+10) {{ width: 56px; }}
table.detail-table th:nth-child(11) {{ width: 78px; }}
table.detail-table th:nth-child(12) {{ width: 82px; }}
#panel-detail .card {{ padding: 12px 16px 8px; }}
.mode-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 6px; }}
.b-first {{ background: #42a5f5; color: #0b1a2a; }}
.b-last {{ background: #ef5350; color: #2a0b0b; }}
.b-avg {{ background: #26a69a; color: #07201c; }}
.legend {{ display: flex; gap: 16px; margin-bottom: 8px; flex-wrap: wrap; }}
/* 候选池 */
.cand-layout {{ display: grid; grid-template-columns: 220px 280px 1fr; gap: 14px; }}
@media (max-width: 1000px) {{ .cand-layout {{ grid-template-columns: 1fr; }} }}
.date-list, .stock-list {{ max-height: 62vh; overflow-y: auto; }}
.date-item, .stock-item {{ padding: 7px 10px; cursor: pointer; border-radius: 6px; font-size: 13px; margin-bottom: 2px; }}
.date-item:hover, .stock-item:hover {{ background: #1f2530; }}
.date-item.active, .stock-item.active {{ background: #2b6cb0; color: #fff; }}
.stock-count {{ color: #9aa0a6; font-size: 12px; margin-left: 6px; }}
.stock-market {{ color: #6b7280; font-size: 11px; margin-left: 4px; }}
#kline {{ width: 100%; height: 62vh; display: flex; flex-direction: column; }}
#kline-main {{ flex: 3 1 0; min-height: 0; }}
.kline-ind {{ flex: 1 1 0; min-height: 0; margin-top: 4px; }}
.chart-title {{ font-size: 13px; color: #c9cdd4; margin-bottom: 8px; min-height: 18px; }}
.kline-info {{ font-size: 12px; color: #9aa0a6; margin-bottom: 6px; min-height: 16px; font-family: Consolas, monospace; }}
.kline-info .up {{ color: #ef5350; }}
.kline-info .down {{ color: #26a69a; }}
.chg-big {{ font-size: 20px; font-weight: 700; margin-right: 10px; }}
.chg-big.up {{ color: #ef5350; }}
.chg-big.down {{ color: #26a69a; }}
.empty-hint {{ color: #6b7280; font-size: 13px; padding: 20px; text-align: center; }}
/* K 线工具栏 */
.kline-toolbar {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }}
.kline-toolbar select, .kline-toolbar input[type="color"] {{
  background: #1c2029; color: #e4e6eb; border: 1px solid #2a3140; border-radius: 6px; padding: 5px 8px; font-size: 12px; height: 28px;
}}
.kline-toolbar select:focus {{ outline: none; border-color: #2b6cb0; }}
.kline-toolbar button {{
  background: #1c2029; color: #e4e6eb; border: 1px solid #2a3140; border-radius: 6px; padding: 5px 10px; font-size: 12px; cursor: pointer; height: 28px;
}}
.kline-toolbar button:hover {{ background: #252b38; border-color: #3a4556; }}
.kline-chk {{ display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: #c9cdd4; cursor: pointer; }}
.kline-chk input {{ accent-color: #2b6cb0; }}
.kline-ma-config {{ display: none; background: #161a22; border: 1px solid #2a3140; border-radius: 6px; padding: 8px; margin-bottom: 8px; }}
.ma-row {{ display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }}
.ma-row span {{ color: #9aa0a6; font-size: 12px; width: 24px; }}
.ma-row input[type="number"] {{ width: 60px; background: #1c2029; color: #e4e6eb; border: 1px solid #2a3140; border-radius: 5px; padding: 4px 6px; font-size: 12px; }}
.ma-row input[type="color"] {{ width: 32px; height: 24px; padding: 0; border: 1px solid #2a3140; border-radius: 5px; background: none; cursor: pointer; }}
.ma-row .ma-del {{ width: 24px; height: 24px; background: #1c2029; color: #ef5350; border: 1px solid #2a3140; border-radius: 5px; cursor: pointer; font-size: 14px; line-height: 1; }}
.ma-row .ma-del:hover {{ background: #3a1f1f; border-color: #ef5350; }}
/* 指标栏管理 */
.kline-bars {{ display: none; background: #161a22; border: 1px solid #2a3140; border-radius: 6px; padding: 8px; margin-bottom: 8px; }}
.bar-row {{ display: flex; align-items: center; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }}
.bar-row .bar-label {{ color: #9aa0a6; font-size: 12px; width: 26px; }}
.bar-row select {{ background: #1c2029; color: #e4e6eb; border: 1px solid #2a3140; border-radius: 5px; padding: 4px 6px; font-size: 12px; }}
.bar-row .bar-volma {{ color: #9aa0a6; font-size: 11px; }}
.bar-row .bar-volma-input {{ width: 70px; background: #1c2029; color: #e4e6eb; border: 1px solid #2a3140; border-radius: 5px; padding: 4px 6px; font-size: 12px; }}
.bar-row .bar-del {{ width: 24px; height: 24px; background: #1c2029; color: #ef5350; border: 1px solid #2a3140; border-radius: 5px; cursor: pointer; font-size: 14px; line-height: 1; }}
.bar-row .bar-del:hover {{ background: #3a1f1f; border-color: #ef5350; }}
/* 涨跌颜色配置 */
.kline-color-config {{ display: none; background: #161a22; border: 1px solid #2a3140; border-radius: 6px; padding: 8px; margin-bottom: 8px; }}
</style>
</head>
<body>
<!-- ============ 左侧快捷命令侧边栏 ============ -->
<div class="sidebar">
  <div class="brand">MarcoAI 控制台<small>策略回测 &amp; 实盘看板</small></div>
  <div class="section">数据更新</div>
  <div class="cmds" id="cmd-list"></div>
  <div class="cmd-output">
    <div class="label">命令输出</div>
    <pre id="cmd-output"></pre>
  </div>
</div>

<!-- ============ 主内容区 ============ -->
<div class="main">
<h1>📊 策略回测 & 实盘目标股看板</h1>
<div class="tabs">
  <div class="tab active" data-tab="backtest" onclick="switchTab('backtest')">策略回测</div>
  <div class="tab" data-tab="candidate" onclick="switchTab('candidate')">实盘候选池</div>
  <div class="tab" data-tab="detail" onclick="switchTab('detail')">策略选股</div>
</div>

<div id="panel-backtest" class="tab-panel active">
  <div class="toolbar">
    <div><label>策略：</label>
      <select id="strategy-select"></select>
    </div>
    <div><label>统计口径：</label>
      <select id="period-select">
        <option value="month">每月</option>
        <option value="quarter">每季度</option>
        <option value="year">每年</option>
      </select>
    </div>
  </div>
  <div class="card">
    <h2>三种卖出方式资金曲线对比（起始资金 10 万，复利）</h2>
    <div class="legend" id="legend"></div>
    <div class="chart-wrap"><canvas id="capital-chart"></canvas></div>
  </div>
  <div class="grid">
    <div class="card">
      <h2>收益统计（按统计口径）</h2>
      <table id="period-table"><thead><tr><th>期间</th><th>first</th><th>last</th><th>avg</th></tr></thead><tbody></tbody></table>
    </div>
    <div class="card">
      <h2>总收益率</h2>
      <div id="total-info"></div>
      <div class="chart-wrap" style="height:200px"><canvas id="total-chart"></canvas></div>
    </div>
  </div>
</div>

<div id="panel-candidate" class="tab-panel">
  <div class="toolbar">
    <div><label>策略：</label>
      <select id="strategy-select-2"></select>
    </div>
  </div>
  <div class="card">
    <h2>实盘候选股票池（T-2 日收盘后确定，下个交易日可买入；日期倒序，默认最新）</h2>
    <div class="cand-layout">
      <div style="background:#1a1e27;border-radius:8px;padding:10px">
        <div style="font-size:13px;color:#9aa0a6;margin-bottom:8px">候选池日期</div>
        <div class="date-list" id="date-list"></div>
      </div>
      <div style="background:#1a1e27;border-radius:8px;padding:10px">
        <div style="font-size:13px;color:#9aa0a6;margin-bottom:8px">候选股票</div>
        <div class="stock-list" id="stock-list"></div>
      </div>
      <div style="background:#1a1e27;border-radius:8px;padding:10px">
        <div class="chart-title" id="kline-title"></div>
        <div class="kline-info" id="kline-info"></div>
        <div class="kline-toolbar">
          <select id="kline-period" title="周期">
            <option value="day">日线</option>
            <option value="month">月线</option>
          </select>
          <button id="kline-bar-btn" type="button">指标栏</button>
          <label class="kline-chk"><input type="checkbox" id="kline-boll"> BOLL</label>
          <label class="kline-chk"><input type="checkbox" id="kline-vwap"> VWAP</label>
          <button id="kline-ma-btn" type="button">MA 配置</button>
          <button id="kline-ma-add" type="button" style="display:none">+</button>
          <button id="kline-color-btn" type="button">涨跌颜色</button>
        </div>
        <div class="kline-bars" id="kline-bars"></div>
        <div class="kline-ma-config" id="kline-ma-config"></div>
        <div class="kline-color-config" id="kline-color-config"></div>
        <div id="kline">
          <div id="kline-main"><div class="empty-hint">请选择候选池日期与个股</div></div>
        </div>
      </div>
    </div>
  </div>
</div>

<div id="panel-detail" class="tab-panel">
  <div class="toolbar">
    <div><label>策略：</label>
      <select id="detail-strategy"></select>
    </div>
    <div><label>月份：</label>
      <select id="detail-date"></select>
    </div>
    <div id="detail-count" style="font-size:12px;color:#9aa0a6;"></div>
  </div>
  <div id="detail-groups" class="card"></div>
</div>

<script>
const DATA = {payload};
let current = {{ strategy: null, period: 'month', candStrategy: null, date: null, code: null }};

function switchTab(name) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.getElementById('panel-backtest').classList.toggle('active', name === 'backtest');
  document.getElementById('panel-candidate').classList.toggle('active', name === 'candidate');
  document.getElementById('panel-detail').classList.toggle('active', name === 'detail');
  // 候选池 TAB 激活时重绘 K 线（容器可见后再渲染）
  if (name === 'candidate' && current.code) {{
    requestAnimationFrame(() => selectStock(current.code));
  }}
}}

// 策略下拉（回测）
const strategySelect = document.getElementById('strategy-select');
DATA.strategies.forEach(s => {{
  const opt = document.createElement('option'); opt.value = s; opt.textContent = s; strategySelect.appendChild(opt);
}});
strategySelect.value = DATA.strategies[0];
loadStrategy();
// 策略下拉（候选池）
const strategySelect2 = document.getElementById('strategy-select-2');
DATA.strategies.forEach(s => {{
  const opt = document.createElement('option'); opt.value = s; opt.textContent = s; strategySelect2.appendChild(opt);
}});
strategySelect2.value = DATA.strategies[0];

function fmtPct(v) {{ return (v * 100).toFixed(2) + '%'; }}
function pctClass(v) {{ return v >= 0 ? 'pos' : 'neg'; }}
function fmtYi(v) {{ const n = parseFloat(v); return isNaN(n) ? '' : (n / 1e8).toFixed(2) + '亿'; }}

/* ------- 回测 ------- */
function loadStrategy() {{
  current.strategy = strategySelect.value;
  updateCharts();
}}

function updateCharts() {{
  const st = DATA.backtest[current.strategy];
  if (!st) return;
  const labels = st.dates;
  const colors = {{ first: '#42a5f5', last: '#ef5350', avg: '#26a69a' }};
  const legend = document.getElementById('legend');
  legend.innerHTML = Object.keys(st.modes).map(m =>
    `<span class="mode-badge b-${{m}}">${{m}}</span> 总收益: <b class="${{pctClass(st.modes[m].total)}}">${{fmtPct(st.modes[m].total)}}</b> 最终资金: ${{st.modes[m].final.toFixed(2)}}`
  ).join('&nbsp;&nbsp;');
  renderCapitalChart(labels, st.modes, colors);
  renderPeriodTable(st);
  renderTotalChart(st);
}}

function renderCapitalChart(labels, modes, colors) {{
  const ctx = document.getElementById('capital-chart').getContext('2d');
  if (window.capitalChart) window.capitalChart.destroy();
  const datasets = Object.keys(modes).map(m => ({{
    label: m, data: modes[m].capitals, borderColor: colors[m], backgroundColor: colors[m],
    borderWidth: 2, pointRadius: 0, tension: 0.2,
  }}));
  window.capitalChart = new Chart(ctx, {{
    type: 'line', data: {{ labels, datasets }},
    options: {{ responsive: true, maintainAspectRatio: false, interaction: {{ mode: 'index', intersect: false }},
      plugins: {{ legend: {{ labels: {{ color: '#e4e6eb' }} }} }},
      scales: {{ x: {{ ticks: {{ color: '#9aa0a6', maxTicksLimit: 12 }} }}, y: {{ ticks: {{ color: '#9aa0a6' }} }} }} }}
  }});
}}

function renderPeriodTable(st) {{
  const key = current.period;
  const periodData = st[key];
  const allPeriods = new Set();
  Object.values(periodData).forEach(m => Object.keys(m).forEach(p => allPeriods.add(p)));
  const sorted = [...allPeriods].sort();
  const tbody = document.querySelector('#period-table tbody');
  tbody.innerHTML = sorted.map(p =>
    `<tr><td>${{p}}</td>` + ['first','last','avg'].map(m => {{
      const v = periodData[m][p]; const vv = v === undefined ? null : v;
      return `<td class="${{vv===null?'':pctClass(vv)}}">${{vv===null?'-':fmtPct(vv)}}</td>`;
    }}).join('') + '</tr>'
  ).join('');
}}

function renderTotalChart(st) {{
  const ctx = document.getElementById('total-chart').getContext('2d');
  if (window.totalChart) window.totalChart.destroy();
  const modes = ['first','last','avg'];
  window.totalChart = new Chart(ctx, {{
    type: 'bar', data: {{ labels: modes, datasets: [{{
      label: '总收益率', data: modes.map(m => st.modes[m].total),
      backgroundColor: modes.map(m => m==='first'?'#42a5f5':(m==='last'?'#ef5350':'#26a69a'))
    }}] }},
    options: {{ responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{ y: {{ ticks: {{ color: '#9aa0a6', callback: v => (v*100).toFixed(0)+'%' }} }} }} }}
  }});
}}

/* ------- 实盘候选池 ------- */
function loadCandidates() {{
  current.candStrategy = strategySelect2.value;
  // JS 的 Object.keys 对数字键会升序，这里手动倒序
  const dates = Object.keys(DATA.candidates[current.candStrategy] || {{}}).sort().reverse();
  const list = document.getElementById('date-list');
  list.innerHTML = '';
  if (dates.length === 0) {{ list.innerHTML = '<div class="empty-hint">无候选池</div>'; return; }}
  dates.forEach(d => {{
    const n = DATA.candidates[current.candStrategy][d].length;
    const el = document.createElement('div');
    el.className = 'date-item';
    el.innerHTML = d + '<span class="stock-count">' + n + '只</span>';
    el.onclick = () => {{ selectDate(d); }};
    list.appendChild(el);
  }});
  selectDate(dates[0]);  // 默认最新
}}

function selectDate(date) {{
  current.date = date;
  document.querySelectorAll('.date-item').forEach(el => {{
    el.classList.toggle('active', el.textContent.startsWith(date));
  }});
  const stocks = DATA.candidates[current.candStrategy][date] || [];
  const list = document.getElementById('stock-list');
  list.innerHTML = '';
  if (stocks.length === 0) {{ list.innerHTML = '<div class="empty-hint">该日无候选股</div>'; return; }}
  stocks.forEach(s => {{
    const el = document.createElement('div');
    el.className = 'stock-item';
    el.innerHTML = s[0] + ' ' + s[1] + (s[2] ? '<span class="stock-market">' + fmtYi(s[2]) + '</span>' : '');
    el.onclick = () => {{ selectStock(s[0]); }};
    list.appendChild(el);
  }});
  selectStock(stocks[0][0]);
}}

/* ==================== K 线增强（分栏指标/MA配置/BOLL/VWAP/月线） ==================== */
/* klineState：周期(day/month)、副图指标(volume/macd/kdj)、MA列表、BOLL/VWAP开关 */
const klineState = {{
  period: 'day',
  bars: [{{ type: 'volume', volMA: [5, 10] }}],   // 指标栏列表，最多 MAX_BARS 个
  ma: [{{ p: 5, c: '#42a5f5' }}, {{ p: 10, c: '#ffca28' }}, {{ p: 20, c: '#ab47bc' }}, {{ p: 60, c: '#66bb6a' }}],
  showBOLL: false,
  showVWAP: false,
  colors: {{ up: '#ef5350', down: '#26a69a', limitUp: '#f5c518' }},  // 涨/跌/涨停颜色
}};
const MAX_BARS = 3;

/* ---- 周期数据：日线原样，月线聚合 ---- */
function monthKey(time) {{ return time.slice(0, 7); }}  // "2026-01"
function aggregateMonthly(daily) {{
  const map = new Map();
  daily.forEach(d => {{
    const mk = monthKey(d.time);
    const g = map.get(mk);
    if (!g) {{
      map.set(mk, {{ time: d.time.slice(0, 7) + '-01', open: d.open, high: d.high, low: d.low, close: d.close, volume: d.volume }});
    }} else {{
      g.high = Math.max(g.high, d.high);
      g.low = Math.min(g.low, d.low);
      g.close = d.close;
      g.volume += d.volume;
    }}
  }});
  return Array.from(map.values()).sort((a, b) => a.time < b.time ? -1 : 1);
}}
function getSeriesData(k) {{
  return klineState.period === 'month' ? aggregateMonthly(k.ohlcv) : k.ohlcv;
}}

/* ---- 指标计算 ---- */
function calcMA(data, period) {{
  const out = [];
  let sum = 0;
  for (let i = 0; i < data.length; i++) {{
    sum += data[i].close;
    if (i >= period) sum -= data[i - period].close;
    if (i >= period - 1) out.push({{ time: data[i].time, value: +(sum / period).toFixed(3) }});
  }}
  return out;
}}
function emaArr(values, period) {{
  const k = 2 / (period + 1);
  const out = [];
  let prev = null;
  for (let i = 0; i < values.length; i++) {{
    prev = i === 0 ? values[i] : values[i] * k + prev * (1 - k);
    out.push(prev);
  }}
  return out;
}}
function calcMACD(data) {{
  const closes = data.map(d => d.close);
  const ema12 = emaArr(closes, 12), ema26 = emaArr(closes, 26);
  const dif = closes.map((_, i) => ema12[i] - ema26[i]);
  const dea = emaArr(dif, 9);
  const bars = data.map((d, i) => ({{
    time: d.time, value: (dif[i] - dea[i]) * 2, color: (dif[i] - dea[i]) >= 0 ? '#ef535055' : '#26a69a55',
  }}));
  const difLine = data.map((d, i) => ({{ time: d.time, value: +dif[i].toFixed(3) }}));
  const deaLine = data.map((d, i) => ({{ time: d.time, value: +dea[i].toFixed(3) }}));
  return {{ bars, dif: difLine, dea: deaLine }};
}}
function calcKDJ(data, n = 9, m1 = 3, m2 = 3) {{
  const out = [];
  let rsv = [], k = 50, d = 50;
  for (let i = 0; i < data.length; i++) {{
    if (i >= n - 1) {{
      let hh = -Infinity, ll = Infinity;
      for (let j = i - n + 1; j <= i; j++) {{ hh = Math.max(hh, data[j].high); ll = Math.min(ll, data[j].low); }}
      rsv[i] = (hh === ll) ? 50 : (data[i].close - ll) / (hh - ll) * 100;
    }} else {{
      rsv[i] = 50;
    }}
    k = (m1 - 1) / m1 * k + (1 / m1) * rsv[i];
    d = (m2 - 1) / m2 * d + (1 / m2) * k;
    out.push({{ time: data[i].time, K: k, D: d, J: 3 * k - 2 * d }});
  }}
  return out;
}}
function calcBOLL(data, period = 20, mult = 2) {{
  const up = [], mid = [], low = [];
  for (let i = 0; i < data.length; i++) {{
    if (i >= period - 1) {{
      let s = 0;
      for (let j = i - period + 1; j <= i; j++) s += data[j].close;
      const ma = s / period;
      let v = 0;
      for (let j = i - period + 1; j <= i; j++) v += (data[j].close - ma) * (data[j].close - ma);
      const sd = Math.sqrt(v / period);
      const t = data[i].time;
      up.push({{ time: t, value: +(ma + mult * sd).toFixed(3) }});
      mid.push({{ time: t, value: +ma.toFixed(3) }});
      low.push({{ time: t, value: +(ma - mult * sd).toFixed(3) }});
    }}
  }}
  return {{ up, mid, low }};
}}
function calcVWAP(data) {{
  const out = [];
  let cumPV = 0, cumV = 0;
  for (let i = 0; i < data.length; i++) {{
    const tp = (data[i].high + data[i].low + data[i].close) / 3;
    cumPV += tp * data[i].volume;
    cumV += data[i].volume;
    out.push({{ time: data[i].time, value: +(cumPV / (cumV || 1)).toFixed(3) }});
  }}
  return out;
}}
/* 涨停幅度：创业/科创板20%，主板10% */
function limitRatio(code) {{
  const pure = code.split('.')[0];
  if (pure && (pure.startsWith('300') || pure.startsWith('301') || pure.startsWith('302') ||
               pure.startsWith('688') || pure.startsWith('689'))) return 0.20;
  return 0.10;
}}
/* 涨停价 = 前收×(1+涨幅)，四舍五入到分 */
function limitPrice(preClose, ratio) {{
  return Math.round(preClose * (1 + ratio) * 100) / 100;
}}
/* 标记每根K线是否涨停（收盘触及涨停价），返回 time -> isLimit 映射 */
function markLimitUp(data, code) {{
  const ratio = limitRatio(code);
  const map = new Map();
  for (let i = 1; i < data.length; i++) {{
    const pre = data[i - 1].close;
    if (pre > 0 && data[i].close >= limitPrice(pre, ratio)) map.set(data[i].time, true);
  }}
  return map;
}}
/* 成交量均线（VOL MA），对成交量序列求均值 */
function calcVolMA(data, period) {{
  const out = [];
  let sum = 0;
  for (let i = 0; i < data.length; i++) {{
    sum += data[i].volume;
    if (i >= period) sum -= data[i - period].volume;
    if (i >= period - 1) out.push({{ time: data[i].time, value: +(sum / period).toFixed(1) }});
  }}
  return out;
}}

/* ---- K 线渲染（LightweightCharts v5 原生分栏：主图 + 最多3个指标栏，自动对齐与十字线贯穿） ---- */
let _chart = null;
function destroyKline() {{
  if (_chart) {{ try {{ _chart.remove(); }} catch(e) {{}} _chart = null; }}
}}
/* 主图悬浮时在标题栏下方显示当天数据 */
function showDayInfo(chart, candleSeries, data) {{
  chart.subscribeCrosshairMove(param => {{
    const info = document.getElementById('kline-info');
    if (!param.time) {{ if (info && info.dataset.base) info.textContent = info.dataset.base; return; }}
    let d = param.seriesData ? param.seriesData.get(candleSeries) : null;
    if (!d) {{ for (let i = 0; i < data.length; i++) {{ if (data[i].time === param.time) {{ d = data[i]; break; }} }} }}
    if (!d) return;
    const base = info.dataset.base || '';
    const chg = d.open > 0 ? ((d.close - d.open) / d.open * 100).toFixed(2) : '0.00';
    const cls = d.close >= d.open ? 'up' : 'down';
    info.innerHTML = base + ' <span class="' + cls + '">' + d.time + '</span>' +
      ' 开 ' + d.open + ' 高 ' + d.high + ' 低 ' + d.low + ' 收 ' + d.close +
      ' 涨跌 <span class="' + cls + '">' + chg + '%</span>' +
      ' 量 ' + d.volume;
  }});
}}
/* 渲染单个指标栏（v5 addPane 分栏，pane 为独立窗格） */
function renderIndicatorBar(pane, bar, data, limitMap) {{
  if (bar.type === 'volume') {{
    const vol = pane.addSeries(LightweightCharts.HistogramSeries, {{ priceFormat: {{ type: 'volume' }} }});
    vol.setData(data.map(d => ({{
      time: d.time, value: d.volume,
      color: limitMap.has(d.time) ? klineState.colors.limitUp + 'aa' : (d.close >= d.open ? klineState.colors.up + '66' : klineState.colors.down + '66'),
    }})));
    // 成交量均线（可配置）
    (bar.volMA || []).forEach((p, i) => {{
      if (p <= 0) return;
      pane.addSeries(LightweightCharts.LineSeries, {{ color: i === 0 ? '#ffca28' : '#ff7043', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }})
        .setData(calcVolMA(data, p));
    }});
  }} else if (bar.type === 'macd') {{
    const macd = calcMACD(data);
    const b = pane.addSeries(LightweightCharts.HistogramSeries, {{}});
    b.setData(macd.bars.map(x => ({{
      time: x.time, value: x.value,
      color: x.value >= 0 ? klineState.colors.up + '55' : klineState.colors.down + '55',
    }})));
    pane.addSeries(LightweightCharts.LineSeries, {{ color: '#ffca28', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }}).setData(macd.dif);
    pane.addSeries(LightweightCharts.LineSeries, {{ color: '#66bb6a', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }}).setData(macd.dea);
  }} else if (bar.type === 'kdj') {{
    const kdj = calcKDJ(data);
    pane.addSeries(LightweightCharts.LineSeries, {{ color: '#42a5f5', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }}).setData(kdj.map(x => ({{ time: x.time, value: +x.K.toFixed(2) }})));
    pane.addSeries(LightweightCharts.LineSeries, {{ color: '#ffca28', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }}).setData(kdj.map(x => ({{ time: x.time, value: +x.D.toFixed(2) }})));
    pane.addSeries(LightweightCharts.LineSeries, {{ color: '#ab47bc', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }}).setData(kdj.map(x => ({{ time: x.time, value: +x.J.toFixed(2) }})));
  }}
}}
function renderKline(k) {{
  const data = getSeriesData(k);
  const box = document.getElementById('kline');
  box.innerHTML = '<div id="kline-main"></div>';
  destroyKline();

  const mainEl = document.getElementById('kline-main');
  _chart = LightweightCharts.createChart(mainEl, {{
    layout: {{ background: {{ type: LightweightCharts.ColorType.Solid, color: '#171a21' }}, textColor: '#d1d4dc' }},
    grid: {{ vertLines: {{ color: '#2b2b43' }}, horzLines: {{ color: '#2b2b43' }} }},
    rightPriceScale: {{ borderColor: '#2b2b43' }},
    timeScale: {{ borderColor: '#2b2b43' }},
    crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
    height: mainEl.offsetHeight || 600,
  }});

  // 涨停标记（黄色显示）
  const limitMap = markLimitUp(data, current.code);

  // 主图：K线（涨停日黄色）
  const c = klineState.colors;
  const candle = _chart.addSeries(LightweightCharts.CandlestickSeries, {{
    upColor: c.up, downColor: c.down, borderUpColor: c.up, borderDownColor: c.down,
    wickUpColor: c.up, wickDownColor: c.down,
  }});
  candle.setData(data.map(d => {{
    const o = {{ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close }};
    if (limitMap.has(d.time)) o.color = c.limitUp;
    return o;
  }}));
  // 主图：MA（可配置周期与颜色）
  klineState.ma.forEach(ma => {{
    if (ma.p <= 0) return;
    _chart.addSeries(LightweightCharts.LineSeries, {{ color: ma.c, lineWidth: 1, priceLineVisible: false, lastValueVisible: false }}).setData(calcMA(data, ma.p));
  }});
  // 主图：BOLL
  if (klineState.showBOLL) {{
    const boll = calcBOLL(data);
    _chart.addSeries(LightweightCharts.LineSeries, {{ color: '#90caf9', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }}).setData(boll.up);
    _chart.addSeries(LightweightCharts.LineSeries, {{ color: '#90caf9', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, priceLineVisible: false, lastValueVisible: false }}).setData(boll.mid);
    _chart.addSeries(LightweightCharts.LineSeries, {{ color: '#90caf9', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }}).setData(boll.low);
  }}
  // 主图：VWAP
  if (klineState.showVWAP) {{
    _chart.addSeries(LightweightCharts.LineSeries, {{ color: '#ff7043', lineWidth: 2, priceLineVisible: true, lastValueVisible: true }}).setData(calcVWAP(data));
  }}

  // 各指标栏：v5 原生分栏（addPane），价格刻度/时间轴/十字线自动对齐
  klineState.bars.forEach(bar => {{
    const pane = _chart.addPane();
    renderIndicatorBar(pane, bar, data, limitMap);
  }});

  _chart.timeScale().fitContent();
  showDayInfo(_chart, candle, data);
}}

/* 标题栏 HTML：涨跌幅放最前（大字号红绿色），后跟名称/代码/周期 */
function klineTitleHtml(k, code) {{
  let chg = '';
  if (k && k.ohlcv.length) {{
    const last = k.ohlcv[k.ohlcv.length - 1];
    const prev = k.ohlcv.length > 1 ? k.ohlcv[k.ohlcv.length - 2].close : last.open;
    const pct = prev > 0 ? (last.close - prev) / prev * 100 : 0;
    const cls = pct >= 0 ? 'up' : 'down';
    chg = '<span class="chg-big ' + cls + '">' + (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%</span>';
  }}
  const name = (k && k.name ? k.name + '  ' : '');
  const per = klineState.period === 'month' ? '月线' : '日线';
  const n = k ? k.ohlcv.length : 0;
  return '<span style="font-size:14px;font-weight:600;color:#e4e6eb">' + name + code + '  ' + per + '（共 ' + n + ' 根）</span> ' + chg;
}}
function selectStock(code) {{
  current.code = code;
  document.querySelectorAll('.stock-item').forEach(el => {{
    el.classList.toggle('active', el.textContent.startsWith(code));
  }});
  const k = DATA.kline[code];
  const title = document.getElementById('kline-title');
  title.innerHTML = klineTitleHtml(k, code);
  const info = document.getElementById('kline-info');
  const base = (k && k.name ? k.name + '  ' : '') + code + '  ' + (klineState.period === 'month' ? '月线' : '日线');
  info.dataset.base = base;
  info.textContent = base;
  if (!k || k.ohlcv.length === 0) {{
    destroyKline();
    document.getElementById('kline').innerHTML = '<div id="kline-main"><div class="empty-hint">暂无 K 线数据</div></div>';
    return;
  }}
  requestAnimationFrame(() => renderKline(k));
}}

/* ---- MA 配置面板 ---- */
function renderMaConfig() {{
  const cfg = document.getElementById('kline-ma-config');
  if (cfg.style.display === 'none') return;
  cfg.innerHTML = '';
  klineState.ma.forEach((ma, i) => {{
    const row = document.createElement('div');
    row.className = 'ma-row';
    row.innerHTML = '<span>MA</span><input type="number" class="ma-p" value="' + ma.p + '" min="1" max="250" title="周期">' +
      '<input type="color" class="ma-c" value="' + ma.c + '" title="颜色">' +
      '<button type="button" class="ma-del">×</button>';
    row.querySelector('.ma-p').onchange = e => {{ ma.p = +e.target.value || 5; rerenderKline(); }};
    row.querySelector('.ma-c').oninput = e => {{ ma.c = e.target.value; rerenderKline(); }};
    row.querySelector('.ma-del').onclick = () => {{ klineState.ma.splice(i, 1); renderMaConfig(); rerenderKline(); }};
    cfg.appendChild(row);
  }});
}}
function rerenderKline() {{
  if (current.code && DATA.kline[current.code]) {{
    requestAnimationFrame(() => renderKline(DATA.kline[current.code]));
  }}
}}
/* ---- 指标栏管理面板 ---- */
function renderBarConfig() {{
  const box = document.getElementById('kline-bars');
  box.innerHTML = '';
  klineState.bars.forEach((bar, i) => {{
    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = '<span class="bar-label">栏' + (i + 1) + '</span>' +
      '<select class="bar-type">' +
      '<option value="volume"' + (bar.type === 'volume' ? ' selected' : '') + '>成交量</option>' +
      '<option value="macd"' + (bar.type === 'macd' ? ' selected' : '') + '>MACD</option>' +
      '<option value="kdj"' + (bar.type === 'kdj' ? ' selected' : '') + '>KDJ</option>' +
      '</select>' +
      '<span class="bar-volma" title="成交量均线，逗号分隔">VOL MA:</span>' +
      '<input type="text" class="bar-volma-input" value="' + (bar.volMA || []).join(',') + '" placeholder="5,10">' +
      '<button type="button" class="bar-del">×</button>';
    row.querySelector('.bar-type').onchange = e => {{ bar.type = e.target.value; renderBarConfig(); rerenderKline(); }};
    row.querySelector('.bar-volma-input').onchange = e => {{
      const arr = e.target.value.split(',').map(x => parseInt(x, 10)).filter(x => !isNaN(x) && x > 0);
      bar.volMA = arr.length ? arr.slice(0, 3) : [5, 10];
      rerenderKline();
    }};
    row.querySelector('.bar-del').onclick = () => {{
      klineState.bars.splice(i, 1);
      renderBarConfig(); rerenderKline();
    }};
    // 非成交量栏隐藏 VOL MA 配置
    if (bar.type !== 'volume') {{
      row.querySelector('.bar-volma').style.display = 'none';
      row.querySelector('.bar-volma-input').style.display = 'none';
    }}
    box.appendChild(row);
  }});
  const add = document.createElement('button');
  add.type = 'button';
  add.textContent = '+ 添加指标栏';
  add.style.cssText = 'width:100%;margin-top:4px;background:#1c2029;color:#e4e6eb;border:1px solid #2a3140;border-radius:6px;padding:5px;font-size:12px;cursor:pointer;';
  add.onclick = () => {{
    if (klineState.bars.length >= MAX_BARS) return;
    const types = ['volume', 'macd', 'kdj'].filter(t => !klineState.bars.some(b => b.type === t));
    klineState.bars.push({{ type: types[0] || 'macd', volMA: [5, 10] }});
    renderBarConfig(); rerenderKline();
  }};
  if (klineState.bars.length < MAX_BARS) box.appendChild(add);
}}
/* ---- 涨跌/涨停颜色配置面板 ---- */
function renderColorConfig() {{
  const box = document.getElementById('kline-color-config');
  box.innerHTML = '';
  const defs = [['up', '涨', klineState.colors.up], ['down', '跌', klineState.colors.down], ['limitUp', '涨停', klineState.colors.limitUp]];
  defs.forEach(([key, label, val]) => {{
    const row = document.createElement('div');
    row.className = 'ma-row';
    row.innerHTML = '<span>' + label + '</span><input type="color" value="' + val + '" title="' + label + '">';
    row.querySelector('input').oninput = e => {{ klineState.colors[key] = e.target.value; renderColorConfig(); rerenderKline(); }};
    box.appendChild(row);
  }});
}}
function initKlineControls() {{
  document.getElementById('kline-period').onchange = e => {{
    klineState.period = e.target.value;
    const k = current.code && DATA.kline[current.code];
    document.getElementById('kline-title').innerHTML = klineTitleHtml(k, current.code || '');
    rerenderKline();
  }};
  const barsPanel = document.getElementById('kline-bars');
  const barBtn = document.getElementById('kline-bar-btn');
  function toggleBarsPanel(forceShow) {{
    const show = (forceShow !== undefined) ? forceShow : (barsPanel.style.display === 'none' || barsPanel.style.display === '');
    barsPanel.style.display = show ? 'block' : 'none';
    if (show) renderBarConfig();
  }}
  barBtn.onclick = () => toggleBarsPanel();
  document.getElementById('kline-boll').onchange = e => {{ klineState.showBOLL = e.target.checked; rerenderKline(); }};
  document.getElementById('kline-vwap').onchange = e => {{ klineState.showVWAP = e.target.checked; rerenderKline(); }};
  const maBtn = document.getElementById('kline-ma-btn');
  const cfg = document.getElementById('kline-ma-config');
  maBtn.onclick = () => {{
    const show = (cfg.style.display === 'none' || cfg.style.display === '');
    cfg.style.display = show ? 'block' : 'none';
    if (show) renderMaConfig();
  }};
  const addBtn = document.getElementById('kline-ma-add');
  addBtn.onclick = () => {{
    klineState.ma.push({{ p: 5, c: '#e91e63' }});
    renderMaConfig(); rerenderKline();
  }};
  addBtn.style.display = 'inline-block';
  // 涨跌颜色面板开关
  const colorBtn = document.getElementById('kline-color-btn');
  const colorCfg = document.getElementById('kline-color-config');
  colorBtn.onclick = () => {{
    const show = (colorCfg.style.display === 'none' || colorCfg.style.display === '');
    colorCfg.style.display = show ? 'block' : 'none';
    if (show) renderColorConfig();
  }};
  renderBarConfig();
}}
initKlineControls();
loadCandidates();  // 所有函数与 klineState 声明就绪后再加载候选池，避免 TDZ 报错

/* ------- 策略选股详情 TAB ------- */
function fmtNum(v) {{
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿';
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '万';
  return v.toFixed(2);
}}
function loadDetail() {{
  const s = document.getElementById('detail-strategy').value;
  const m = document.getElementById('detail-date').value;  // YYYYMM
  const detail = DATA.strategy_detail[s] || {{}};
  // 收集该月所有日期（降序），同一天的多只股票框在一起
  const dates = Object.keys(detail).filter(d => d.startsWith(m)).sort().reverse();
  let total = 0;
  const box = document.getElementById('detail-groups');
  box.innerHTML = '';
  dates.forEach(date => {{
    const rows = detail[date];
    if (!rows || rows.length === 0) return;
    // 日期区块标题（显示为 YYYY-MM-DD）
    const head = document.createElement('div');
    head.className = 'detail-date-head';
    head.textContent = date.slice(0, 4) + '-' + date.slice(4, 6) + '-' + date.slice(6, 8) + '（' + rows.length + ' 只）';
    box.appendChild(head);
    // 该日股票表格
    const table = document.createElement('table');
    table.className = 'detail-table';
    table.innerHTML = '<thead><tr><th>#</th><th>代码</th><th>名称</th><th>涨跌幅%</th><th>市值(亿)</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th><th>前收</th><th>成交量</th><th>成交额(万)</th></tr></thead>';
    const tbody = document.createElement('tbody');
    rows.forEach((row, i) => {{
      total++;
      const cls = row.chg >= 0 ? 'neg' : 'pos';  // 涨红跌绿
      const tr = document.createElement('tr');
      tr.innerHTML = '<td>' + (i + 1) + '</td>' +
        '<td>' + row.code + '</td><td>' + row.name + '</td>' +
        '<td class="' + cls + '">' + row.chg.toFixed(2) + '</td>' +
        '<td>' + fmtNum(row.market) + '</td>' +
        '<td>' + row.open.toFixed(2) + '</td><td>' + row.high.toFixed(2) + '</td>' +
        '<td>' + row.low.toFixed(2) + '</td><td>' + row.close.toFixed(2) + '</td>' +
        '<td>' + row.pre.toFixed(2) + '</td>' +
        '<td>' + fmtNum(row.vol) + '</td>' +
        '<td>' + fmtNum(row.amount) + '</td>';
      tbody.appendChild(tr);
    }});
    table.appendChild(tbody);
    box.appendChild(table);
  }});
  document.getElementById('detail-count').textContent = m.slice(0, 4) + '年' + m.slice(4, 6) + '月 共选股 ' + total + ' 只（' + dates.length + ' 个交易日）';
}}
function initDetailTab() {{
  const sel = document.getElementById('detail-strategy');
  DATA.strategies.forEach(s => {{
    const opt = document.createElement('option'); opt.value = s; opt.textContent = s; sel.appendChild(opt);
  }});
  sel.value = DATA.strategies[0];
  sel.onchange = fillDetailDates;
  document.getElementById('detail-date').onchange = loadDetail;
  fillDetailDates();
}}
function fillDetailDates() {{
  const s = document.getElementById('detail-strategy').value;
  const dates = Object.keys(DATA.strategy_detail[s] || {{}}).sort().reverse();
  // 提取月份 YYYYMM 去重降序（日期为 20260814，取前 6 位即 202608）
  const months = Array.from(new Set(dates.map(d => d.slice(0, 6))));
  const ds = document.getElementById('detail-date');
  ds.innerHTML = '';
  months.forEach(mth => {{
    const opt = document.createElement('option');
    opt.value = mth;
    opt.textContent = mth.slice(0, 4) + '年' + mth.slice(4, 6) + '月';  // 202608 -> 2026年08月
    ds.appendChild(opt);
  }});
  if (months.length) ds.value = months[0];
  loadDetail();
}}
initDetailTab();

strategySelect.addEventListener('change', loadStrategy);
strategySelect2.addEventListener('change', loadCandidates);
document.getElementById('period-select').addEventListener('change', e => {{ current.period = e.target.value; updateCharts(); }});

/* ==================== 左侧快捷命令 ==================== */
const cmdList = document.getElementById('cmd-list');
const cmdOutput = document.getElementById('cmd-output');
const STRATEGIES = {strategies_json};

function logCmd(msg) {{
  cmdOutput.textContent = (cmdOutput.textContent ? cmdOutput.textContent + '\\n' : '') + '[' + new Date().toLocaleTimeString() + '] ' + msg;
  cmdOutput.scrollTop = cmdOutput.scrollHeight;
}}

/* 访问方式：file://（双击打开）用 marcoai:// 协议触发命令；http 服务用 fetch */
const IS_FILE_PROTOCOL = (location.protocol === 'file:');

/* 通过 marcoai:// 自定义协议触发本地 Python 命令（无需服务，双击即用） */
function runViaProtocol(cmd, payload, btn) {{
  btn.classList.add('running');
  btn.querySelector('.spinner').style.display = 'inline-block';
  logCmd('执行: ' + cmd + '（通过 marcoai:// 协议）');
  let url = 'marcoai://run?cmd=' + encodeURIComponent(cmd);
  if (payload && payload.strategy) url += '&strategy=' + encodeURIComponent(payload.strategy);
  try {{
    location.href = url;
    logCmd('已发起，结果将弹窗显示');
  }} catch (err) {{
    logCmd('发起失败: ' + err + '（请确认已运行 register_protocol.py 注册协议）');
  }}
  btn.classList.remove('running');
  btn.querySelector('.spinner').style.display = 'none';
}}

/* 统一命令执行入口 */
async function runCommand(cmd, payload, btn) {{
  if (IS_FILE_PROTOCOL) {{
    runViaProtocol(cmd, payload, btn);
    return;
  }}
  btn.classList.add('running');
  btn.querySelector('.spinner').style.display = 'inline-block';
  try {{
    logCmd('执行: ' + cmd);
    const res = await fetch('/api/cmd', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(Object.assign({{ cmd }}, payload || {{}})),
    }});
    const data = await res.json();
    if (data.ok) {{
      logCmd(data.output || '完成');
    }} else {{
      logCmd('失败: ' + (data.error || '未知错误'));
    }}
    return data;
  }} catch (err) {{
    logCmd('请求失败: ' + err + '（请确认已启动本地服务，命令：python AICode/MarcoAPI/StrategyService.py）');
    return null;
  }} finally {{
    btn.classList.remove('running');
    btn.querySelector('.spinner').style.display = 'none';
  }}
}}

/* ---- 命令1：数据更新 ---- */
function onClickUpdateData(btn) {{
  const ok = confirm('将更新通达信日线数据和 MarcoAI\\\\AIData\\\\INFO\\\\SZ100.xlsx 股票池。\\n\\n确定开始更新吗？');
  if (!ok) {{ logCmd('已取消数据更新'); return; }}
  runCommand('UPDATE_DATA', null, btn);
}}

/* ---- 命令2：更新同花顺板块 ---- */
function onClickUpdateTHS(btn) {{
  if (!STRATEGIES.length) {{ logCmd('无可用策略'); return; }}
  const sel = document.getElementById('ths-strategy');
  const strategy = sel ? sel.value : '';
  if (!strategy) {{ logCmd('请先选择策略'); return; }}
  const ok = confirm('将根据策略 ' + strategy + ' 更新同花顺板块 blockstockV3.xml，\\n最新日期股票->TPO3，前一日期->TPO31，并覆盖 C:\\\\同花顺远航版\\\\bin\\\\users\\\\狗蛋儿家的金\\\\blockstockV3.xml。\\n\\n确定继续吗？');
  if (!ok) {{ logCmd('已取消同花顺更新'); return; }}
  runCommand('UPDATE_THS', {{ strategy }}, btn);
}}

/* ---- 命令3：git 同步 ---- */
function onClickGitSync(btn) {{
  const ok = confirm('将执行 git add . && git commit -m "Updated" && git push，\\n把当前改动提交并推送到远程仓库。\\n\\n确定继续吗？');
  if (!ok) {{ logCmd('已取消 git 同步'); return; }}
  runCommand('GIT_SYNC', null, btn);
}}

/* 渲染侧边栏命令按钮 */
const btnData = {{
  title: '数据更新',
  desc: '通达信日线 + SZ100 股票池',
  danger: true,
  onClick: onClickUpdateData,
}};
function addCmdBtn(label, desc, danger, onClick) {{
  const btn = document.createElement('button');
  btn.className = 'cmd' + (danger ? ' danger' : '');
  btn.innerHTML = '<span class="spinner"></span><span class="dot"></span><span>' + label + '</span>';
  btn.onclick = () => onClick(btn);
  cmdList.appendChild(btn);
  if (desc) {{
    const tip = document.createElement('div');
    tip.style.cssText = 'font-size:11px;color:#6b7280;margin:-4px 2px 8px;line-height:1.4;';
    tip.textContent = desc;
    cmdList.appendChild(tip);
  }}
}}
addCmdBtn('数据更新', '更新通达信日线数据与 SZ100.xlsx 股票池', true, onClickUpdateData);

/* 同花顺更新：策略下拉 + 按钮 */
const thsRow = document.createElement('div');
thsRow.style.cssText = 'margin:6px 0 4px;';
thsRow.innerHTML = '<div style="font-size:11px;color:#9aa0a6;margin-bottom:4px;">选择策略</div>';
const sel = document.createElement('select');
sel.id = 'ths-strategy';
sel.style.cssText = 'width:100%;background:#1c2029;color:#e4e6eb;border:1px solid #2a3140;border-radius:6px;padding:7px 9px;font-size:13px;';
STRATEGIES.forEach(s => {{
  const opt = document.createElement('option'); opt.value = s; opt.textContent = s; sel.appendChild(opt);
}});
thsRow.appendChild(sel);
cmdList.appendChild(thsRow);

addCmdBtn('更新同花顺板块', '按策略把最新/前一日股票写入 blockstockV3.xml 并拷贝到实盘机', false, onClickUpdateTHS);

/* git 同步按钮 */
addCmdBtn('git 同步', 'git add . && commit && push 推送到远程仓库', false, onClickGitSync);
</script>
</div><!-- /.main -->
</body>
</html>
"""


def _list_strategy_files(strategy_name: str) -> list[str]:
    """返回策略目录下按日期升序的全部文件名（仅数字日期），无则返回空列表"""
    base = os.path.join(PATH_AIDATA_STRATEGY(), strategy_name)
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base) if d.isdigit())


def _read_strategy_stocks(strategy_name: str, date: str) -> list[str]:
    """读取某策略某日期的选股股票代码列表（带 .SH/.SZ 后缀，如 603087.SH）"""
    path = os.path.join(PATH_AIDATA_STRATEGY(), strategy_name, date)
    if not os.path.isfile(path):
        return []
    codes = []
    for line in _read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        code = line.split("|")[0].strip()
        if code:
            codes.append(code)
    return codes


def _code_to_ths_security(code: str) -> str:
    """把带后缀代码转成同花顺板块 security 行，如 603087.SH -> <security market="USHA" code="603087" />"""
    c = code.strip()
    pure = c.split(".")[0]
    market = "USHA" if c.endswith(".SH") else "USZA"
    return f'    <security market="{market}" code="{pure}" />'


def CMD_UPDATE_DATA() -> str:
    """【快捷命令】更新全部数据：通达信日线、SZ100 股票池、加工日线、策略、候选池等"""
    try:
        UPDATE_ALL()
        return "数据更新完成"
    except Exception as exc:
        return f"数据更新失败: {exc}"


def CMD_UPDATE_THS(strategy_name: str) -> str:
    """【快捷命令】把指定策略的最新日期股票写入同花顺板块 XML 并拷贝到实盘机目录。

    - 最新日期股票 -> 替换模板 ===TPO3===
    - 最新日前一日期股票 -> 替换模板 ===TPO31===（该日为空则替换为空值，板块留空）
    - 拷贝模板到 THS_TARGET_DIR 覆盖同名文件，然后删除本地拷贝。
    """
    if not strategy_name:
        return "未选择策略"
    if not os.path.isfile(THS_TEMPLATE_FILE):
        return f"同花顺模板不存在: {THS_TEMPLATE_FILE}"

    dates = _list_strategy_files(strategy_name)
    if not dates:
        return f"策略 {strategy_name} 无数据"
    latest = dates[-1]
    prev = dates[-2] if len(dates) >= 2 else None

    tpo3 = _read_strategy_stocks(strategy_name, latest)
    tpo31 = _read_strategy_stocks(strategy_name, prev) if prev else []

    tpo3_block = "\n".join(_code_to_ths_security(c) for c in tpo3)
    tpo31_block = "\n".join(_code_to_ths_security(c) for c in tpo31)

    # 读取模板并替换占位符：有股票则填入 securities（首尾不加换行），为空则整行清理（不留占位符/空行，兼容 CRLF/LF）
    raw = _read_text(THS_TEMPLATE_FILE)
    for ph, block in ((PLACEHOLDER_TPO3, tpo3_block), (PLACEHOLDER_TPO31, tpo31_block)):
        if block:
            raw = raw.replace(ph, block)
        else:
            raw = re.sub(r"\r?\n" + re.escape(ph), "", raw).replace(ph, "")

    # 拷贝一份模板到目标目录覆盖同名文件，然后删除本地拷贝
    # newline="" 保持模板原始换行（CRLF），避免文本模式把 \n 再转成 \r\n 导致 \r\r\n
    if not os.path.isdir(THS_TARGET_DIR):
        return f"同花顺目标目录不存在: {THS_TARGET_DIR}"
    target_file = os.path.join(THS_TARGET_DIR, THS_BLOCK_NAME)
    with open(target_file, "w", encoding="utf-8", newline="") as f:
        f.write(raw)

    detail = (
        f"策略 {strategy_name}: {latest} 共 {len(tpo3)} 只(TPO3), "
        f"{prev or '无'} 共 {len(tpo31)} 只(TPO31)"
    )
    print(f"CMD_UPDATE_THS: 已写入 {target_file}\n{detail}")
    return f"同花顺板块已更新:\n{detail}\n已覆盖: {target_file}"


def GENERATE_STRATEGY_UI(strategy_name: str | None = None, open_browser: bool = True) -> str:
    """生成策略回测 + 实盘目标股综合看板 HTML 并返回文件路径。

    参数:
        strategy_name: 指定策略名；None 时包含所有策略
        open_browser:  是否自动打开浏览器
    """
    if strategy_name:
        strategies = [strategy_name]
    else:
        strategies = _list_strategies()
        if not strategies:
            print("STRATEGY_UI: Strategy 目录下无策略")
            return ""

    # 回测数据
    backtest = {}
    for name in strategies:
        backtest[name] = _build_strategy_payload(name)

    # 候选池 + K 线
    candidates = {}
    all_codes = set()
    code_names: dict[str, str] = {}
    for name in strategies:
        candidates[name] = _load_candidates(name)
        for rows in candidates[name].values():
            for r in rows:
                all_codes.add(r[0])
                if len(r) >= 2 and r[0] not in code_names:
                    code_names[r[0]] = r[1]
    kline = _load_kline(all_codes, code_names)

    # 策略选股详情（第三个 TAB）
    strategy_detail = _load_strategy_detail(strategies)

    data = {
        "strategies": strategies,
        "backtest": backtest,
        "candidates": candidates,
        "kline": kline,
        "strategy_detail": strategy_detail,
    }

    html = _render_html(data)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "UI", "StrategyDashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"STRATEGY_UI: 综合看板已生成 {out_path}")

    if open_browser:
        webbrowser.open("file:///" + out_path.replace("\\", "/"))
    return out_path


if __name__ == "__main__":
    GENERATE_STRATEGY_UI()
