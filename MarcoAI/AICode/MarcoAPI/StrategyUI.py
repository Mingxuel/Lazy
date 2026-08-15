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


def _load_kline(codes: set[str]) -> dict[str, dict[str, Any]]:
    """读取候选股的最近 KLINE_DAYS 天原始日线（1D_ORIGIN），并自行计算 MA5/10/20/60 均线"""
    kline = {}
    for code in codes:
        path = os.path.join(PATH_AIDATA_1D_ORIGIN(), code)
        if not os.path.exists(path):
            continue
        lines = _read_text(path).splitlines()
        rows = [l.split("|") for l in lines if l.strip() and len(l.split("|")) >= 6]
        rows = rows[-KLINE_DAYS:]
        closes = [float(r[4]) for r in rows]
        ohlcv = []
        ma = {5: [], 10: [], 20: [], 60: []}
        for i, r in enumerate(rows):
            # r[0] 是 YYYYMMDD（如 20260105），LightweightCharts 要求 YYYY-MM-DD
            t = r[0][:4] + '-' + r[0][4:6] + '-' + r[0][6:8]
            ohlcv.append({
                "time": t, "open": float(r[1]), "high": float(r[2]),
                "low": float(r[3]), "close": float(r[4]), "volume": float(r[5]),
            })
            for p in (5, 10, 20, 60):
                if i >= p - 1:
                    avg = sum(closes[i - p + 1:i + 1]) / p
                    ma[p].append({"time": t, "value": round(avg, 2)})
        kline[code] = {"ohlcv": ohlcv, "ma5": ma[5], "ma10": ma[10], "ma20": ma[20], "ma60": ma[60]}
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
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
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
#kline {{ width: 100%; height: 60vh; }}
.chart-title {{ font-size: 13px; color: #c9cdd4; margin-bottom: 8px; min-height: 18px; }}
.empty-hint {{ color: #6b7280; font-size: 13px; padding: 20px; text-align: center; }}
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
        <div id="kline"><div class="empty-hint">请选择候选池日期与个股</div></div>
      </div>
    </div>
  </div>
</div>

<script>
const DATA = {payload};
let current = {{ strategy: null, period: 'month', candStrategy: null, date: null, code: null }};

function switchTab(name) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.getElementById('panel-backtest').classList.toggle('active', name === 'backtest');
  document.getElementById('panel-candidate').classList.toggle('active', name === 'candidate');
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
loadCandidates();

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

function selectStock(code) {{
  current.code = code;
  document.querySelectorAll('.stock-item').forEach(el => {{
    el.classList.toggle('active', el.textContent.startsWith(code));
  }});
  const k = DATA.kline[code];
  const title = document.getElementById('kline-title');
  title.textContent = code + '  日线（最近 ' + (k ? k.ohlcv.length : 0) + ' 日）';
  const container = document.getElementById('kline');
  if (!k || k.ohlcv.length === 0) {{
    container.innerHTML = '<div class="empty-hint">暂无 K 线数据</div>';
    return;
  }}
  // 延迟到容器布局完成后渲染
  requestAnimationFrame(() => renderKline(container, k));
}}

function renderKline(container, k) {{
  container.innerHTML = '';
  const chart = LightweightCharts.createChart(container, {{
    layout: {{ background: {{ type: LightweightCharts.ColorType.Solid, color: '#171a21' }}, textColor: '#d1d4dc' }},
    grid: {{ vertLines: {{ color: '#2b2b43' }}, horzLines: {{ color: '#2b2b43' }} }},
    rightPriceScale: {{ borderColor: '#2b2b43' }},
    timeScale: {{ borderColor: '#2b2b43' }},
  }});
  const candle = chart.addCandlestickSeries({{
    upColor: '#ef5350', downColor: '#26a69a', borderUpColor: '#ef5350', borderDownColor: '#26a69a',
    wickUpColor: '#ef5350', wickDownColor: '#26a69a',
  }});
  candle.setData(k.ohlcv);
  const colors = {{ 5: '#42a5f5', 10: '#ffca28', 20: '#ab47bc', 60: '#66bb6a' }};
  [5,10,20,60].forEach(p => {{
    const line = chart.addLineSeries({{ color: colors[p], lineWidth: 1, priceLineVisible: false, lastValueVisible: false }});
    line.setData(k['ma' + p]);
  }});
  const vol = chart.addHistogramSeries({{
    priceFormat: {{ type: 'volume' }}, priceScaleId: '', scaleMargins: {{ top: 0.8, bottom: 0 }},
  }});
  vol.setData(k.ohlcv.map(d => ({{ time: d.time, value: d.volume, color: d.close >= d.open ? '#ef535055' : '#26a69a55' }})));
  chart.timeScale().fitContent();
}}

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

/* 检测访问方式：双击 file:// 打开时无法调用 Python 命令，需通过本地服务访问 */
const IS_FILE_PROTOCOL = (location.protocol === 'file:');
function showServiceNotice() {{
  let bar = document.getElementById('service-notice');
  if (!bar) {{
    bar = document.createElement('div');
    bar.id = 'service-notice';
    bar.style.cssText = 'margin-bottom:14px;padding:10px 14px;border-radius:8px;font-size:13px;line-height:1.6;background:#2b1a1a;border:1px solid #ef5350;color:#ffb3b3;';
    document.getElementById('panel-backtest').parentElement.insertBefore(bar, document.getElementById('panel-backtest'));
  }}
  bar.textContent = '左侧快捷命令需通过本地服务才能执行。请先运行：python AICode/MarcoAPI/StrategyService.py，再访问 http://localhost:8765/ （当前为直接打开文件，命令无法触发）';
}}

/* 统一命令执行入口：POST 到本地服务 /api/cmd，后端执行对应 Python 脚本 */
async function runCommand(cmd, payload, btn) {{
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
    if (IS_FILE_PROTOCOL) {{
      showServiceNotice();
      logCmd('当前是直接打开文件，无法调用本地命令。请启动服务并访问 http://localhost:8765/ 后重试。');
    }} else {{
      logCmd('请求失败: ' + err + '（请确认已启动本地服务，命令：python AICode/MarcoAPI/StrategyService.py）');
    }}
    return null;
  }} finally {{
    btn.classList.remove('running');
    btn.querySelector('.spinner').style.display = 'none';
  }}
}}

if (IS_FILE_PROTOCOL) showServiceNotice();

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
    for name in strategies:
        candidates[name] = _load_candidates(name)
        for rows in candidates[name].values():
            for r in rows:
                all_codes.add(r[0])
    kline = _load_kline(all_codes)

    data = {
        "strategies": strategies,
        "backtest": backtest,
        "candidates": candidates,
        "kline": kline,
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
