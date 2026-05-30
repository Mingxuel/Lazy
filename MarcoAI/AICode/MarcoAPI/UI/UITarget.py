import json
import os
import sys
import webbrowser

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Path import PATH_AIDATA_TARGET_31, PATH_AIDATA_1D_WIN_COUNT, PATH_AIDATA_TARGET_31_RATIO, PATH_AIDATA_TARGET_311_RATIO
from AICode.MarcoAPI.DataAligned import READ_ALIGNED_LINES


def SHOW_TARGET_1D():
    """三列可视化：D行日期轴(垂直)+十字虚线+悬浮窗+滚动条+联动拖拽。"""
    target_dir = PATH_AIDATA_TARGET_31()
    if not os.path.isdir(target_dir):
        print('[SHOW] 目标数据目录不存在')
        return

    fnames = sorted(os.listdir(target_dir), reverse=True)
    latest = None
    stocks = []
    for fname in fnames:
        fpath = os.path.join(target_dir, fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath, 'r') as f:
            cur = []
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 8:
                    cur.append({
                        'code': parts[0],
                        'open': parts[1],
                        'high': parts[2],
                        'low': parts[3],
                        'close': parts[4],
                        'volume': parts[5],
                        'amount': parts[6],
                        'pre_close': parts[7],
                    })
            if cur:
                latest = fname
                stocks = cur
                break

    if not latest:
        print('[SHOW] 无有效数据')
        return

    win_data = []
    win_path = PATH_AIDATA_1D_WIN_COUNT()
    for date, line in READ_ALIGNED_LINES(win_path):
        if line:
            parts = line.split('|')
            win_data.append({
                'date': date,
                'up': int(parts[1]),
                'flat': int(parts[2]),
                'down': int(parts[3]),
                'total': int(parts[4]),
            })
        else:
            win_data.append({
                'date': date,
                'up': 0,
                'flat': 0,
                'down': 0,
                'total': 0,
            })

    # ratio 数据（对齐读取，确保与 win_data 行数一致）
    ratio_data = []
    ratio_path = PATH_AIDATA_TARGET_31_RATIO()
    for date, line in READ_ALIGNED_LINES(ratio_path):
        if line:
            parts = line.split('|')
            ratio_data.append({'date': date, 'val': float(parts[1])})
        else:
            ratio_data.append({'date': date, 'val': 0.0})

    # 311_RATIO 数据（对齐读取，第6行）
    ratio311_data = []
    ratio311_path = PATH_AIDATA_TARGET_311_RATIO()
    for date, line in READ_ALIGNED_LINES(ratio311_path):
        if line:
            parts = line.split('|')
            ratio311_data.append({'date': date, 'val': float(parts[1])})
        else:
            ratio311_data.append({'date': date, 'val': 0.0})

    # 计算列宽：与D行日期标签总宽一致(10px/条)
    col_chart_w = max(3000, len(win_data) * 11)

    # 8×8 颜色矩阵
    colors_64 = [
        '#ff0000','#ff4500','#ff8c00','#ffd700','#ffff00','#adff2f','#00ff00','#00ff7f',
        '#00ffff','#00bfff','#1e90ff','#0000ff','#8a2be2','#9400d3','#ff00ff','#ff1493',
        '#dc143c','#b22222','#8b0000','#cd5c5c','#f08080','#ff6347','#ff6600','#f4a460',
        '#b8860b','#bdb76b','#808000','#9acd32','#32cd32','#228b22','#006400','#008080',
        '#20b2aa','#00ced1','#5f9ea0','#4682b4','#4169e1','#483d8b','#4b0082','#8b008b',
        '#9932cc','#da70d6','#dda0dd','#ff69b4','#db7093','#ffc0cb','#a52a2a','#d2691e',
        '#cd853f','#8fbc8f','#2e8b57','#556b2f','#808080','#c0c0c0','#ffffff','#696969',
        '#a9a9a9','#2f4f4f','#000000','#bc8f8f','#6495ed','#e9967a','#f5a623','#00e5ff'
    ]
    color_opts_8x8 = ''.join(f'<span style="background:{c}" data-color="{c}"></span>' for c in colors_64)

    data_json = json.dumps(stocks, ensure_ascii=False)
    win_json = json.dumps(win_data, ensure_ascii=False)
    ratio_json = json.dumps(ratio_data, ensure_ascii=False)
    ratio311_json = json.dumps(ratio311_data, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Target 1D</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@900&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ height:100%; background:#131722; color:#d1d4dc; font-family:'Segoe UI',sans-serif; }}
  body {{ padding:10px 20px 20px 0; }}

  html, body {{ height:100%; overflow:hidden; }}
  #scroll-wrap {{ overflow:auto; width:100%; height:calc(100vh - 30px); overscroll-behavior-x:none; touch-action:pan-y; }}
  #scroll-wrap::-webkit-scrollbar {{ display:none; }}
  #scroll-wrap {{ -ms-overflow-style:none; scrollbar-width:none; }}

  table {{ table-layout:fixed; width:{col_chart_w + 460}px; border-collapse:collapse; }}
  td {{ padding:8px 10px; border-bottom:1px solid #2b2b43; vertical-align:middle; background:#131722; }}
  .col-idx {{ position:sticky; left:0; z-index:3; width:240px; text-align:center; color:#ffffff; font-size:200px; font-weight:900; line-height:1; }}
  .col-chart {{ width:{col_chart_w}px; position:relative; }}
  .col-param {{ position:sticky; right:0; z-index:3; width:220px; padding-left:20px; }}

  /* D 行 - 冻结在顶部 */
  .row-date {{ position:sticky; top:0; z-index:4; }}
  .row-date td {{ padding:0 0 10px; background:#131722; }}
  .row-date .data-area {{ display:flex; align-items:stretch; height:80px; padding:0 10px 0 5px; }}
  .row-date .data-area {{ display:flex; align-items:stretch; height:80px; }}
  .date-axis {{ position:relative; height:100%; }}
  .date-axis .dl {{ position:absolute; top:0; bottom:0; writing-mode:vertical-rl; text-orientation:upright; font-size:8px; color:#d1d4dc; text-align:center; border-left:1px solid #5a5f7a; display:flex; align-items:center; justify-content:center; }}
  .date-axis .dl.hl {{ background:#ffffff15; font-weight:bold; color:#ffffff; }}

  /* 图表容器 */
  .chart-box {{ position:relative; user-select:none; margin:0; cursor:crosshair; }}


  .chart-label .tag {{ font-size:10px; padding:2px 8px; border-radius:10px; font-weight:normal; }}
  .chart-label .tag.blue {{ background:#2962ff22; color:#2962ff; border:1px solid #2962ff44; }}
  .chart-label .tag.green {{ background:#26a69a22; color:#26a69a; border:1px solid #26a69a44; }}
  .chart-label .tag.red {{ background:#ef535022; color:#ef5350; border:1px solid #ef535044; }}

  .param-group {{ display:flex; flex-direction:column; gap:4px; }}
  .param-row {{ display:flex; align-items:center; gap:6px; }}
  .param-row label {{ font-size:11px; color:#787b86; min-width:48px; text-align:right; }}
  .param-row input {{ flex:1; min-width:40px; padding:4px 6px; border:1px solid #2b2b43; background:#1e222d; color:#d1d4dc; font-size:11px; border-radius:4px; outline:none; }}
  .param-row input:focus {{ border-color:#2962ff; }}
  .param-row input[type="checkbox"] {{ flex:unset; min-width:unset; width:16px; height:16px; }}
  .color-picker {{ position:relative; }}
  .color-swatch {{ width:22px; height:22px; border:1px solid #2b2b43; border-radius:3px; cursor:pointer; flex-shrink:0; }}
  .color-grid {{ position:fixed; z-index:31; display:none; grid-template-columns:repeat(8,18px); gap:1px; background:#1e222d; padding:3px; border:1px solid #2b2b43; border-radius:4px; }}
  .color-grid.show {{ display:grid; }}
  .color-grid span {{ width:18px; height:18px; cursor:pointer; border-radius:2px; border:1px solid transparent; }}
  .color-grid span:hover {{ border-color:#fff; }}
  .param-row input.height-input {{ min-width:60px; }}

  /* 十字虚线 */
  #cross-v {{ position:fixed; top:0; bottom:0; width:0; border-left:1px dashed #787b8666; z-index:10; pointer-events:none; display:none; }}

  /* 统一悬浮窗 */
  #custom-tooltip {{ position:fixed; z-index:30; background:#1e222d; border:1px solid #2b2b43; border-radius:6px; padding:8px 12px; font-size:12px; line-height:1.8; pointer-events:none; display:none; box-shadow:0 4px 12px rgba(0,0,0,0.4); }}
  #custom-tooltip .tt-date {{ font-size:13px; font-weight:700; color:#fff; margin-bottom:4px; text-align:center; }}
  #custom-tooltip .tt-row {{ display:flex; justify-content:space-between; gap:20px; }}
  #custom-tooltip .tt-label {{ color:#787b86; }}
  #custom-tooltip .tt-value {{ color:#d1d4dc; font-weight:600; text-align:right; }}
  #custom-tooltip .tt-up {{ color:#ef5350; }}
  #custom-tooltip .tt-dn {{ color:#00e5ff; }}
  #custom-tooltip .tt-sep {{ border-bottom:1px solid #2b2b43; margin:4px 0; }}

  .up {{ color:#ef5350; }} .dn {{ color:#00e5ff; }}
  .empty {{ color:#485c7b; font-size:14px; padding:40px; text-align:center; }}
</style>
</head>
<body>

<div id="cross-v"></div>
<div id="custom-tooltip"></div>
<div class="color-grid" id="global-color-grid">{color_opts_8x8}</div>
<div id="scroll-wrap">
  <table>
    <tbody>
      <!-- 日期轴（冻结） -->
      <tr class="row-date">
        <td class="col-idx" style="font-family:'Orbitron',sans-serif;font-size:40px;line-height:80px;">100,000</td>
        <td>
          <div class="data-area">
            <div class="date-axis-wrap">
              <div class="date-axis" id="date-axis"></div>
            </div>
          </div>
        </td>
        <td class="col-param"></td>
      </tr>
      <!-- 第2行：上升均线 -->
      <tr>
        <td class="col-idx" style="padding:0;"><div style="font-size:13px;font-weight:normal;color:#d1d4dc;line-height:1.2;"><span style="font-size:10px;background:#2962ff22;color:#2962ff;border:1px solid #2962ff44;padding:1px 6px;border-radius:8px;">MA</span></div><div style="font-family:'Orbitron',sans-serif;font-size:48px;font-weight:900;line-height:1;">MA</div></td>
        <td style="padding:0 5px 0 0;">
          <div class="chart-box" style="height:120px;">
            <canvas id="c-ma"></canvas>
          </div>
        </td>
        <td class="col-param">
          <div class="param-group">
            <div class="param-row"><label>MA1</label><input class="ma-period" type="number" value="5" min="0" data-ma="0"><div class="color-picker"><div class="color-swatch ma-swatch" data-ma="0" style="background:#f5a623"></div></div></div>
            <div class="param-row"><label>MA2</label><input class="ma-period" type="number" value="10" min="0" data-ma="1"><div class="color-picker"><div class="color-swatch ma-swatch" data-ma="1" style="background:#1e90ff"></div></div></div>
            <div class="param-row"><label>MA3</label><input class="ma-period" type="number" value="0" min="0" data-ma="2"><div class="color-picker"><div class="color-swatch ma-swatch" data-ma="2" style="background:#808080"></div></div></div>
            <div class="param-row"><label>数据线</label><input type="checkbox" class="ma-line-toggle" checked></div>
            <div class="param-row"><label>高度</label><input class="height-input" type="number" value="180" min="60" step="10" data-target="c-ma"></div>
          </div>
        </td>
      </tr>
      <!-- 第3行：每日上涨个数 -->
      <tr>
        <td class="col-idx" style="padding:0;border-bottom:none;"><div style="font-size:13px;font-weight:normal;color:#d1d4dc;line-height:1.2;"><span style="font-size:10px;background:#ef535022;color:#ef5350;border:1px solid #ef535044;padding:1px 6px;border-radius:8px;">WIN</span></div><div style="font-family:'Orbitron',sans-serif;font-size:48px;font-weight:900;line-height:1;">UP</div></td>
        <td style="padding:0;border-bottom:none;line-height:0;">
          <div class="chart-box" style="height:270px;">
            <canvas id="c-up"></canvas>
          </div>
        </td>
        <td class="col-param" style="border-bottom:none;"></td>
      </tr>
      <!-- 第4行：下跌柱状图 -->
      <tr>
        <td class="col-idx" style="padding:0;border-top:none;"><div style="font-size:13px;font-weight:normal;color:#d1d4dc;line-height:1.2;"><span style="font-size:10px;background:#00e5ff22;color:#00e5ff;border:1px solid #00e5ff44;padding:1px 6px;border-radius:8px;">LOSE</span></div><div style="font-family:'Orbitron',sans-serif;font-size:48px;font-weight:900;line-height:1;">DOWN</div></td>
        <td style="padding:0;border-top:none;line-height:0;">
          <div class="chart-box" style="height:270px;">
            <canvas id="c-dn"></canvas>
          </div>
        </td>
        <td class="col-param" style="padding:0;border-top:none;"></td>
      </tr>
      <!-- 第5行：31_RATIO -->
      <tr>
        <td class="col-idx"><div style="font-size:13px;font-weight:normal;color:#d1d4dc;line-height:1.2;"><span style="font-size:10px;background:#ff8c0022;color:#ff8c00;border:1px solid #ff8c0044;padding:1px 6px;border-radius:8px;">D-DAY</span></div><div style="font-family:'Orbitron',sans-serif;font-size:48px;font-weight:900;line-height:1.1;">31<br>RATIO</div></td>
        <td style="padding:10px 5px 10px 0;">
          <div class="chart-box" style="height:180px;">
            <canvas id="c-ratio"></canvas>
          </div>
        </td>
        <td class="col-param">
          <div class="param-group">
            <div class="param-row"><label>线颜色</label><div class="color-picker"><div class="color-swatch ratio-swatch ratio-line-swatch" style="background:#26a69a"></div></div></div>
            <div class="param-row"><label>上升色</label><div class="color-picker"><div class="color-swatch ratio-swatch ratio-up-swatch" style="background:#ef5350"></div></div></div>
            <div class="param-row"><label>下降色</label><div class="color-picker"><div class="color-swatch ratio-swatch ratio-dn-swatch" style="background:#00e5ff"></div></div></div>
            <div class="param-row"><label>高度</label><input class="height-input" type="number" value="180" min="60" step="10" data-target="c-ratio"></div>
          </div>
        </td>
      </tr>
      <!-- 第6行：311_RATIO -->
      <tr>
        <td class="col-idx"><div style="font-size:13px;font-weight:normal;color:#d1d4dc;line-height:1.2;"><span style="font-size:10px;background:#7c4dff22;color:#7c4dff;border:1px solid #7c4dff44;padding:1px 6px;border-radius:8px;">D-DAY + 1</span></div><div style="font-family:'Orbitron',sans-serif;font-size:48px;font-weight:900;line-height:1.1;">311<br>RATIO</div></td>
        <td style="padding:10px 5px 10px 0;">
          <div class="chart-box" style="height:180px;">
            <canvas id="c-ratio311"></canvas>
          </div>
        </td>
        <td class="col-param">
          <div class="param-group">
            <div class="param-row"><label>线颜色</label><div class="color-picker"><div class="color-swatch ratio-swatch ratio-line-swatch" style="background:#26a69a"></div></div></div>
            <div class="param-row"><label>上升色</label><div class="color-picker"><div class="color-swatch ratio-swatch ratio-up-swatch" style="background:#ef5350"></div></div></div>
            <div class="param-row"><label>下降色</label><div class="color-picker"><div class="color-swatch ratio-swatch ratio-dn-swatch" style="background:#00e5ff"></div></div></div>
            <div class="param-row"><label>高度</label><input class="height-input" type="number" value="180" min="60" step="10" data-target="c-ratio311"></div>
          </div>
        </td>
      </tr>
      <!-- 4 行空白（高度 200px） -->
      <tr style="height:200px;"><td class="col-idx"></td><td></td><td class="col-param"></td></tr>
      <tr style="height:200px;"><td class="col-idx"></td><td></td><td class="col-param"></td></tr>
      <tr style="height:200px;"><td class="col-idx"></td><td></td><td class="col-param"></td></tr>
      <tr style="height:200px;"><td class="col-idx"></td><td></td><td class="col-param"></td></tr>
    </tbody>
  </table>
</div>

<script>
const stocks = {data_json};
const winData = {win_json};
const ratioData = {ratio_json};
const ratio311Data = {ratio311_json};
let charts = [];

/* ---- 鼠标中键拖动 ---- */
const wrap = document.getElementById('scroll-wrap');
const crossV = document.getElementById('cross-v');
let dragging = false, sx = 0, ss = 0;

document.addEventListener('mousedown', e => {{
  if (e.button !== 1 || !e.target.closest('#scroll-wrap')) return;
  e.preventDefault();
  dragging = true;
  sx = e.clientX;
  ss = wrap.scrollLeft;
  wrap.style.cursor = 'grabbing';
}});

document.addEventListener('mousemove', e => {{
  if (dragging) {{
    wrap.scrollLeft = ss - (e.clientX - sx);
  }} else if (e.target.closest('#scroll-wrap')) {{
    crossV.style.display = 'block';
    crossV.style.left = e.clientX + 'px';
    // 联动所有图表高亮
    syncAllChartsHover(e);
  }} else {{
    crossV.style.display = 'none';
    clearAllHovers();
  }}
}});

document.addEventListener('mouseup', e => {{
  if (e.button === 1 && dragging) {{
    dragging = false;
    wrap.style.cursor = '';
  }}
  crossV.style.display = 'none';
  clearAllHovers();
}});

wrap.addEventListener('mouseleave', () => {{ crossV.style.display = 'none'; clearAllHovers(); }});

// 阻止中键点击默认的自动滚动行为
document.addEventListener('auxclick', e => {{ if (e.button === 1) e.preventDefault(); }});

// 联动所有图表hover
function syncAllChartsHover(e) {{
  const refChart = charts.find(c => c.canvas && c.canvas.id === 'c-up');
  if (!refChart) return;
  const rect = refChart.canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  // 通过 X 轴刻度反查数据索引
  const xScale = refChart.scales.x;
  if (!xScale) return;
  const idx = xScale.getValueForPixel(mouseX);
  if (idx == null || idx < 0 || idx >= winData.length) return;
  const dataIdx = Math.round(idx);

  charts.forEach(ch => {{
    if (!ch || !ch.canvas) return;
    const activeElements = [];
    for (let d = 0; d < ch.data.datasets.length; d++) {{
      const m = ch.getDatasetMeta(d);
      if (m && m.data && m.data[dataIdx]) {{
        activeElements.push({{ datasetIndex:d, index:dataIdx }});
      }}
    }}
    ch.setActiveElements(activeElements);
    ch.update('none');
  }});

  // D行日期高亮
  const dateLabels = document.querySelectorAll('#date-axis .dl');
  dateLabels.forEach((el, i) => {{ el.classList.toggle('hl', i === dataIdx); }});

  // 统一悬浮窗内容
  const d = winData[dataIdx];
  const r = ratioData[dataIdx];
  const r311 = ratio311Data[dataIdx];
  const tt = document.getElementById('custom-tooltip');
  const upPct = d.total > 0 ? (d.up / d.total * 100).toFixed(1) : '0.0';
  const dnPct = d.total > 0 ? (d.down / d.total * 100).toFixed(1) : '0.0';
  tt.innerHTML =
    '<div class="tt-date">' + d.date + '</div>' +
    '<div class="tt-sep"></div>' +
    '<div class="tt-row"><span class="tt-label">上涨</span><span class="tt-value tt-up">' + d.up + ' <span style="font-weight:400;color:#787b86;font-size:11px">(' + upPct + '%)</span></span></div>' +
    '<div class="tt-row"><span class="tt-label">下跌</span><span class="tt-value tt-dn">' + d.down + ' <span style="font-weight:400;color:#787b86;font-size:11px">(' + dnPct + '%)</span></span></div>' +
    '<div class="tt-row"><span class="tt-label">平盘</span><span class="tt-value">' + d.flat + '</span></div>' +
    '<div class="tt-row"><span class="tt-label">总数</span><span class="tt-value">' + d.total + '</span></div>' +
    '<div class="tt-sep"></div>' +
    '<div class="tt-row"><span class="tt-label">31_RATIO</span><span class="tt-value ' + (r.val >= 0 ? 'tt-up' : 'tt-dn') + '">' + (r.val >= 0 ? '+' : '') + r.val.toFixed(2) + '%</span></div>' +
    '<div class="tt-row"><span class="tt-label">311_RATIO</span><span class="tt-value ' + (r311.val >= 0 ? 'tt-up' : 'tt-dn') + '">' + (r311.val >= 0 ? '+' : '') + r311.val.toFixed(2) + '%</span></div>';
  tt.style.display = 'block';
  // 定位在鼠标附近，自动保持在视窗内
  let tx = e.clientX + 16;
  let ty = e.clientY + 16;
  const tw = tt.offsetWidth;
  const th = tt.offsetHeight;
  if (tx + tw > window.innerWidth - 10) tx = e.clientX - tw - 16;
  if (ty + th > window.innerHeight - 10) ty = e.clientY - th - 16;
  if (tx < 10) tx = 10;
  if (ty < 10) ty = 10;
  tt.style.left = tx + 'px';
  tt.style.top = ty + 'px';
}}

function clearAllHovers() {{
  charts.forEach(ch => {{
    if (!ch) return;
    ch.setActiveElements([]);
    if (ch.tooltip) ch.tooltip.setActiveElements([], {{ x:0, y:0 }});
    ch.update('none');
  }});
  document.querySelectorAll('#date-axis .dl.hl').forEach(el => el.classList.remove('hl'));
}}

/* ---- 行高调整 ---- */
document.addEventListener('input', e => {{
  const input = e.target.closest('.height-input');
  if (!input) return;
  const targetId = input.dataset.target;
  const h = parseInt(input.value) || 120;
  const row = input.closest('tr');
  if (!row) return;
  const box = row.querySelector('.chart-box');
  const canvas = document.getElementById(targetId);
  if (!box || !canvas) return;
  box.style.height = h + 'px';
  const ch = charts.find(c => c.canvas === canvas);
  if (ch) ch.resize();
}});

/* ---- MA 配置变化时重绘 ---- */
function rebuildMAChart() {{
  const ch = charts.find(c => c.canvas && c.canvas.id === 'c-ma');
  if (!ch) return;
  const upVals = winData.map(d => d.up);
  const showLine = document.querySelector('.ma-line-toggle').checked;
  const datasets = [];
  if (showLine) {{
    datasets.push({{ label:'UP', data:upVals, borderColor:'#26a69a', backgroundColor:'rgba(38,166,154,0.08)', fill:true, tension:0.3, pointRadius:0, pointHoverRadius:4, borderWidth:1.5 }});
  }}
  for (let maIdx = 0; maIdx < 3; maIdx++) {{
    const periodInput = document.querySelector('.ma-period[data-ma="'+maIdx+'"]');
    const swatch = document.querySelector('.ma-swatch[data-ma="'+maIdx+'"]');
    if (!periodInput || !swatch) continue;
    const period = parseInt(periodInput.value) || 0;
    const color = swatch.dataset.color || swatch.style.background;
    if (period <= 0) continue;
    const maData = upVals.map((v,i) => i<period-1 ? null : +(upVals.slice(i-period+1,i+1).reduce((a,b)=>a+b,0)/period).toFixed(2));
    datasets.push({{ label:'MA'+period, data:maData, borderColor:color, borderDash:[3,2], fill:false, tension:0.3, pointRadius:0, pointHoverRadius:6, pointHoverBackgroundColor:'#ffffff', borderWidth:1 }});
  }}
  ch.data.datasets = datasets;
  ch.update();
}}

function rebuildRatioCharts() {{
  const rc = getRatioColors();
  const upColor = hexToRgba(rc.up, 0.18);
  const dnColor = hexToRgba(rc.dn, 0.18);
  charts.forEach(ch => {{
    if (!ch || !ch.canvas) return;
    const id = ch.canvas.id;
    if (id !== 'c-ratio' && id !== 'c-ratio311') return;
    ch.data.datasets[0].borderColor = rc.line;
    ch.data.datasets[0].fill.above = upColor;
    ch.data.datasets[0].fill.below = dnColor;
    ch.update();
  }});
}}

let activeColorSwatch = null;

// 颜色矩阵点击
document.addEventListener('click', e => {{
  const grid = document.getElementById('global-color-grid');
  // 点击颜色方格
  const span = e.target.closest('.color-grid span');
  if (span) {{
    if (activeColorSwatch) {{
      activeColorSwatch.style.background = span.dataset.color;
      activeColorSwatch.dataset.color = span.dataset.color;
      grid.classList.remove('show');
      if (activeColorSwatch.classList.contains('ratio-swatch')) {{
        rebuildRatioCharts();
      }} else {{
        rebuildMAChart();
      }}
      activeColorSwatch = null;
    }}
    return;
  }}
  // 点击色块显示/隐藏网格
  const sw = e.target.closest('.ma-swatch, .ratio-swatch');
  if (sw) {{
    if (activeColorSwatch === sw) {{
      grid.classList.remove('show');
      activeColorSwatch = null;
      return;
    }}
    const r = sw.getBoundingClientRect();
    grid.style.top = (r.bottom + 2) + 'px';
    grid.style.right = (window.innerWidth - r.right) + 'px';
    grid.style.left = 'auto';
    grid.classList.add('show');
    activeColorSwatch = sw;
    return;
  }}
  // 点击外部关闭
  if (!e.target.closest('.color-picker')) {{
    grid.classList.remove('show');
    activeColorSwatch = null;
  }}
}});

document.addEventListener('input', e => {{
  if (e.target.closest('.ma-period')) rebuildMAChart();
}});
document.addEventListener('change', e => {{
  if (e.target.closest('.ma-line-toggle')) rebuildMAChart();
}});

/* ---- 构建 D 行日期轴（1:1 垂直标签） ---- */
function buildDateAxis() {{
  const axis = document.getElementById('date-axis');
  if (!axis || winData.length === 0) return;
  const barW = 11; // 每根柱子宽度 11px
  const totalW = winData.length * barW;
  axis.style.width = totalW + 'px';

  winData.forEach(d => {{
    const el = document.createElement('div');
    el.className = 'dl';
    el.textContent = d.date;
    axis.appendChild(el);
  }});
}}

/* ---- 图表 ---- */
function destroyCharts() {{ charts.forEach(c => c.destroy()); charts = []; }}

function init() {{
  if (stocks.length === 0) {{
    document.querySelector('#scroll-wrap table tbody').innerHTML =
      '<tr><td colspan="3" class="empty">暂无数据</td></tr>';
    return;
  }}
  buildDateAxis();
  setTimeout(() => renderCharts(), 60);
}}

function renderCharts() {{
  const records = stocks.map(s => ({{
    code: s.code,
    close: parseFloat(s.close),
    pre: parseFloat(s.pre_close),
    pct: (parseFloat(s.close)-parseFloat(s.pre_close))/parseFloat(s.pre_close)*100,
  }}));

  const chartWidth = Math.max(3000, winData.length * 11);
  // 统一上下图Y轴范围
  const maxUpVal = Math.max(...winData.map(d => d.up));
  const maxDnVal = Math.max(...winData.map(d => d.down));
  const globalMax = Math.max(maxUpVal, maxDnVal);

  /* ---- 第2行：上升均线（用 UP 数据 + 最多3条MA，默认 5/10/0） ---- */
  const ctx1 = document.getElementById('c-ma');
  if (ctx1 && winData.length > 0) {{
    const upVals = winData.map(d => d.up);
    const datasets = [
      {{ label:'UP', data:upVals, borderColor:'#26a69a', backgroundColor:'rgba(38,166,154,0.08)', fill:true, tension:0.3, pointRadius:0, pointHoverRadius:6, pointHoverBackgroundColor:'#ffffff', borderWidth:1.5 }}
    ];
    for (let maIdx = 0; maIdx < 3; maIdx++) {{
      const periodInput = document.querySelector('.ma-period[data-ma="'+maIdx+'"]');
      const sw = document.querySelector('.ma-swatch[data-ma="'+maIdx+'"]');
      if (!periodInput || !sw) continue;
      const p = parseInt(periodInput.value) || 0;
      const color = sw.style.background;
      if (p <= 0) continue;
      const ma = upVals.map((v,i) => i<p-1 ? null : +(upVals.slice(i-p+1,i+1).reduce((a,b)=>a+b,0)/p).toFixed(2));
      datasets.push({{ label:'MA'+p, data:ma, borderColor:color, borderDash:[3,2], fill:false, tension:0.3, pointRadius:0, pointHoverRadius:6, pointHoverBackgroundColor:'#ffffff', borderWidth:1 }});
    }}
    charts.push(new Chart(ctx1, {{
      type:'line',
      data:{{ labels: winData.map(d => d.date), datasets: datasets }},
      options:{{
        responsive:true, maintainAspectRatio:false,
        plugins:{{ legend:{{ display:false }}, tooltip:{{ enabled:false }} }},
        scales:{{
          x:{{ offset:true, ticks:{{ display:false }}, grid:{{ display:false }} }},
          y:{{ display:false }}
        }}
      }}
    }}));
  }}

  /* ---- 第3行：每日上涨个数 ---- */
  const ctx2 = document.getElementById('c-up');
  if (ctx2 && winData.length > 0) {{
    const upVals = winData.map(d => d.up);
    // 用真实日期作为 labels（供 tooltip 使用），但 X 轴隐藏
    const ch = new Chart(ctx2, {{
      type:'bar',
      data:{{
        labels: winData.map(d => d.date),
        datasets:[{{ label:'上涨个数', data:upVals, backgroundColor:'#ef5350', borderColor:'#b71c1c', hoverBackgroundColor:'#ff8a80', hoverBorderColor:'#ffffff', hoverBorderWidth:2, borderWidth:1, borderRadius:1, barPercentage:0.92, categoryPercentage:1 }}]
      }},
      options:{{
        responsive:true, maintainAspectRatio:false,
        interaction:{{ mode:'index', intersect:false }},
        plugins:{{ legend:{{ display:false }}, tooltip:{{ enabled:false }} }},
        scales:{{
          x:{{ offset:true, ticks:{{ display:false }}, grid:{{ display:false }} }},
          y:{{ display:true, position:'right', ticks:{{ display:false }}, grid:{{ color:'#485c7b55', borderDash:[3,4], lineWidth:1 }}, border:{{ display:false }}, max:globalMax }}
        }}
      }}
    }});
    charts.push(ch);
  }}

  /* ---- 第4行：下跌柱状图（用 winData.down，向下柱子） ---- */
  const ctx3 = document.getElementById('c-dn');
  if (ctx3 && winData.length > 0) {{
    const dnVals = winData.map(d => -d.down);  // 负值，柱子向下
    charts.push(new Chart(ctx3, {{
      type:'bar',
      data:{{
        labels: winData.map(d => d.date),
        datasets:[{{ label:'下跌个数', data:dnVals, backgroundColor:'#00e5ff', borderColor:'#00b8d4', hoverBackgroundColor:'#69f0ae', hoverBorderColor:'#ffffff', hoverBorderWidth:2, borderWidth:1, borderRadius:1, barPercentage:0.92, categoryPercentage:1 }}]
      }},
      options:{{
        responsive:true, maintainAspectRatio:false,
        interaction:{{ mode:'index', intersect:false }},
        plugins:{{ legend:{{ display:false }}, tooltip:{{ enabled:false }} }},
        scales:{{
          x:{{ offset:true, ticks:{{ display:false }}, grid:{{ display:false }} }},
          y:{{ display:true, position:'right', ticks:{{ display:false }}, grid:{{ color:'#485c7b55', borderDash:[3,4], lineWidth:1 }}, border:{{ display:false }} }}
        }}
      }}
    }}));
  }}

/* ---- 辅助函数：获取ratio颜色配置 ---- */
function getRatioColors() {{
  const ls = document.querySelector('.ratio-line-swatch');
  const us = document.querySelector('.ratio-up-swatch');
  const ds = document.querySelector('.ratio-dn-swatch');
  return {{
    line: (ls && ls.dataset.color) || '#26a69a',
    up: (us && us.dataset.color) || '#ef5350',
    dn: (ds && ds.dataset.color) || '#00e5ff',
  }};
}}
function hexToRgba(hex, alpha) {{
  if (!hex || hex.startsWith('rgba') || hex.startsWith('rgb')) return hex || 'rgba(0,0,0,0.18)';
  const h = hex.replace('#','');
  const r = parseInt(h.substring(0,2),16);
  const g = parseInt(h.substring(2,4),16);
  const b = parseInt(h.substring(4,6),16);
  return `rgba(${{r}},${{g}},${{b}},${{alpha}})`;
}}
function makeRatioChartOptions() {{
  return {{
    responsive:true, maintainAspectRatio:false,
    interaction:{{ mode:'index', intersect:false }},
    plugins:{{ legend:{{ display:false }}, tooltip:{{ enabled:false }} }},
    scales:{{
      x:{{ offset:true, ticks:{{ display:false }}, grid:{{ display:false }} }},
      y:{{ display:true, position:'right', min:-11, max:11,
        ticks:{{ display:false, stepSize:5 }},
        afterBuildTicks: axis => {{ axis.ticks = axis.ticks.filter(t => t.value === -5 || t.value === 5); }},
        grid:{{ color:'#485c7b55', borderDash:[3,4], lineWidth:1 }},
        border:{{ display:false }}
      }}
    }}
  }};
}}

  /* ---- 第5行：31_RATIO（单线 + 上下不同色阴影） ---- */
  const ctx4 = document.getElementById('c-ratio');
  if (ctx4 && ratioData.length > 0) {{
    const vals = ratioData.map(d => d.val);
    const rc = getRatioColors();
    charts.push(new Chart(ctx4, {{
      type:'line',
      data:{{
        labels: ratioData.map(d => d.date),
        datasets:[{{
          label:'RATIO', data:vals,
          borderColor:rc.line,
          fill:{{ target:{{ value:0 }}, above:hexToRgba(rc.up,0.18), below:hexToRgba(rc.dn,0.18) }},
          tension:0.2, pointRadius:0, pointHoverRadius:5, pointHoverBackgroundColor:'#ffffff', borderWidth:1.2
        }}]
      }},
      options: makeRatioChartOptions()
    }}));
  }}

  /* ---- 第6行：311_RATIO（单线 + 上下不同色阴影） ---- */
  const ctx5 = document.getElementById('c-ratio311');
  if (ctx5 && ratio311Data.length > 0) {{
    const vals = ratio311Data.map(d => d.val);
    const rc = getRatioColors();
    charts.push(new Chart(ctx5, {{
      type:'line',
      data:{{
        labels: ratio311Data.map(d => d.date),
        datasets:[{{
          label:'311RATIO', data:vals,
          borderColor:rc.line,
          fill:{{ target:{{ value:0 }}, above:hexToRgba(rc.up,0.18), below:hexToRgba(rc.dn,0.18) }},
          tension:0.2, pointRadius:0, pointHoverRadius:5, pointHoverBackgroundColor:'#ffffff', borderWidth:1.2
        }}]
      }},
      options: makeRatioChartOptions()
    }}));
  }}

  // 用 Chart.js 柱子的精确 X 坐标定位 D 行标签
  setTimeout(() => {{
    const ch = charts.find(c => c.canvas && c.canvas.id === 'c-up');
    if (!ch) return;
    const meta = ch.getDatasetMeta(0);
    if (!meta || !meta.data || !meta.data.length) return;
    const axis = document.getElementById('date-axis');
    if (!axis) return;
    const labels = axis.querySelectorAll('.dl');
    if (!labels.length) return;
    // 获取第一个柱子的左边界作为偏移基准
    const firstX = meta.data[0].x;
    const lastX = meta.data[meta.data.length - 1].x;
    // 计算每根柱子的实际间距（Chart.js 可能不等距）
    const gaps = [];
    for (let i = 1; i < meta.data.length; i++) {{
      gaps.push(meta.data[i].x - meta.data[i-1].x);
    }}
    const avgGap = gaps.length > 0 ? Math.round(gaps.reduce((a,b)=>a+b,0)/gaps.length) : 11;
    const totalW = lastX - firstX + avgGap;
    axis.style.width = totalW + 'px';
    axis.style.paddingLeft = firstX + 'px';
    // 用每个柱子的精确 X 坐标定位 label
    labels.forEach((el, i) => {{
      const cx = meta.data[i].x - firstX;
      el.style.left = cx + 'px';
      el.style.width = avgGap + 'px';
      el.style.transform = 'translateX(-50%)';
    }});
  }}, 400);
}}

init();
</script>
</body>
</html>'''

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'target_1d.html')
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    webbrowser.open(output)
    print(f'[SHOW] {latest} ({len(stocks)} stocks, {len(win_data)} days) -> {output}')
