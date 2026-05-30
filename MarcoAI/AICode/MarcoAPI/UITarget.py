import json
import os
import sys
import webbrowser

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, os.path.dirname(_root))
from AICode.MarcoAPI.Path import PATH_AIDATA_TARGET_31, PATH_AIDATA_1D_WIN_COUNT


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
    if os.path.isfile(win_path):
        with open(win_path, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 3:
                    win_data.append({
                        'date': parts[0],
                        'up': int(parts[1]),
                        'flat': int(parts[2]),
                        'down': int(parts[3]) if len(parts) > 3 else 0,
                        'total': int(parts[4]) if len(parts) > 4 else 0,
                    })

    # 计算列宽：与D行日期标签总宽一致(10px/条)
    col_chart_w = max(3000, len(win_data) * 11)

    data_json = json.dumps(stocks, ensure_ascii=False)
    win_json = json.dumps(win_data, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Target 1D</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ height:100%; background:#131722; color:#d1d4dc; font-family:'Segoe UI',sans-serif; }}
  body {{ padding:20px; }}

  html, body {{ height:100%; overflow:hidden; }}
  #scroll-wrap {{ overflow:auto; width:100%; height:calc(100vh - 40px); overscroll-behavior-x:none; touch-action:pan-y; }}
  #scroll-wrap::-webkit-scrollbar {{ display:none; }}
  #scroll-wrap {{ -ms-overflow-style:none; scrollbar-width:none; }}

  table {{ table-layout:fixed; width:{col_chart_w + 460}px; border-collapse:separate; border-spacing:0; }}
  td {{ padding:8px 10px; border-bottom:1px solid #1e222d; vertical-align:middle; background:#131722; }}
  .col-idx {{ position:sticky; left:0; z-index:3; width:240px; text-align:center; color:#ffffff; font-size:200px; font-weight:900; }}
  .col-chart {{ width:{col_chart_w}px; position:relative; }}
  .col-param {{ position:sticky; right:0; z-index:3; width:220px; padding-left:20px; }}

  /* D 行 - 冻结在顶部 */
  .row-date {{ position:sticky; top:0; z-index:4; }}
  .row-date td {{ padding:10px 0; background:#131722; }}
  .row-date .data-area {{ display:flex; align-items:stretch; height:80px; padding:0 10px 0 15px; }}
  .row-date .data-area {{ display:flex; align-items:stretch; height:80px; }}
  .date-axis {{ position:relative; height:100%; }}
  .date-axis .dl {{ position:absolute; top:0; bottom:0; writing-mode:vertical-rl; text-orientation:upright; font-size:8px; color:#d1d4dc; text-align:center; border-left:1px solid #5a5f7a; display:flex; align-items:center; justify-content:center; }}

  /* 图表容器 */
  .chart-box {{ position:relative; user-select:none; }}          
  .chart-box {{ cursor:crosshair; }}

  .chart-label {{ font-size:13px; color:#d1d4dc; font-weight:bold; margin-bottom:4px; display:flex; align-items:center; gap:8px; }}
  .chart-label .tag {{ font-size:10px; padding:2px 8px; border-radius:10px; font-weight:normal; }}
  .chart-label .tag.blue {{ background:#2962ff22; color:#2962ff; border:1px solid #2962ff44; }}
  .chart-label .tag.green {{ background:#26a69a22; color:#26a69a; border:1px solid #26a69a44; }}
  .chart-label .tag.red {{ background:#ef535022; color:#ef5350; border:1px solid #ef535044; }}

  .param-group {{ display:flex; flex-direction:column; gap:4px; }}
  .param-row {{ display:flex; align-items:center; gap:6px; }}
  .param-row label {{ font-size:11px; color:#787b86; min-width:48px; text-align:right; }}
  .param-row input {{ flex:1; min-width:50px; padding:4px 6px; border:1px solid #2b2b43; background:#1e222d; color:#d1d4dc; font-size:11px; border-radius:4px; outline:none; transition:border-color 0.15s; }}
  .param-row input:focus {{ border-color:#2962ff; }}
  .param-row input.height-input {{ min-width:60px; }}

  /* 十字虚线 */
  #cross-v {{ position:fixed; top:0; bottom:0; width:0; border-left:1px dashed #787b8666; z-index:10; pointer-events:none; display:none; }}

  .up {{ color:#26a69a; }} .dn {{ color:#ef5350; }}
  .empty {{ color:#485c7b; font-size:14px; padding:40px; text-align:center; }}
</style>
</head>
<body>

<div id="cross-v"></div>
<div id="scroll-wrap">
  <table>
    <tbody>
      <!-- 日期轴（冻结） -->
      <tr class="row-date">
        <td class="col-idx"></td>
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
        <td class="col-idx">1</td>
        <td>
          <div class="chart-label">上升均线 <span class="tag blue">MA</span></div>
          <div class="chart-box" style="height:120px;">
            <canvas id="c-ma"></canvas>
          </div>
        </td>
        <td class="col-param">
          <div class="param-group">
            <div class="param-row"><label>周期</label><input type="text" value="5"></div>
            <div class="param-row"><label>类型</label><input type="text" value="SMA"></div>
            <div class="param-row"><label>高度</label><input class="height-input" type="number" value="120" min="60" step="10" data-target="c-ma"></div>
          </div>
        </td>
      </tr>
      <!-- 第3行：每日上涨个数 -->
      <tr>
        <td class="col-idx">2</td>
        <td>
          <div class="chart-label">每日上涨个数 <span class="tag green">1D_WIN</span></div>
          <div class="chart-box" style="height:270px;">
            <canvas id="c-up"></canvas>
          </div>
        </td>
        <td class="col-param">
          <div class="param-group">
            <div class="param-row"><label>颜色</label><input type="text" value="#26a69a"></div>
            <div class="param-row"><label>显示日</label><input type="text" value="全部"></div>
            <div class="param-row"><label>高度</label><input class="height-input" type="number" value="270" min="100" step="10" data-target="c-up"></div>
          </div>
        </td>
      </tr>
      <!-- 第4行：下跌柱状图 -->
      <tr>
        <td class="col-idx">3</td>
        <td>
          <div class="chart-label">下跌柱状图 <span class="tag red" id="tag-dn">-0</span></div>
          <div class="chart-box" style="height:120px;">
            <canvas id="c-dn"></canvas>
          </div>
        </td>
        <td class="col-param">
          <div class="param-group">
            <div class="param-row"><label>最高%</label><input type="text" value="0"></div>
            <div class="param-row"><label>颜色</label><input type="text" value="#ef5350"></div>
            <div class="param-row"><label>高度</label><input class="height-input" type="number" value="120" min="60" step="10" data-target="c-dn"></div>
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
let charts = [];
const tagDn = document.getElementById('tag-dn');

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
  }} else {{
    crossV.style.display = 'none';
  }}
}});

document.addEventListener('mouseup', e => {{
  if (e.button === 1 && dragging) {{
    dragging = false;
    wrap.style.cursor = '';
  }}
  crossV.style.display = 'none';
}});

wrap.addEventListener('mouseleave', () => {{ crossV.style.display = 'none'; }});

// 阻止中键点击默认的自动滚动行为
document.addEventListener('auxclick', e => {{ if (e.button === 1) e.preventDefault(); }});

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
  let dn=0;
  stocks.forEach(s => {{ if ((parseFloat(s.close)-parseFloat(s.pre_close))<0) dn++; }});
  tagDn.textContent = '-'+dn;
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

  /* ---- 第2行：上升均线 ---- */
  const sorted = [...records].sort((a,b) => a.close - b.close);
  const labels1 = sorted.map(s => s.code);
  const closes = sorted.map(s => s.close);
  const period = 3;
  const ma = closes.map((v,i) => i<period-1 ? null : +(closes.slice(i-period+1,i+1).reduce((a,b)=>a+b,0)/period).toFixed(2));
  const ctx1 = document.getElementById('c-ma');
  if (ctx1) {{
    const ch = new Chart(ctx1, {{
      type:'line',
      data:{{
        labels: labels1,
        datasets:[
          {{ label:'收盘价', data:closes, borderColor:'#26a69a', backgroundColor:'rgba(38,166,154,0.08)', fill:true, tension:0.3, pointRadius:2, pointHoverRadius:5 }},
          {{ label:'MA('+period+')', data:ma, borderColor:'#f5a623', borderDash:[4,2], fill:false, tension:0.3, pointRadius:1 }}
        ]}},
      options:{{
        responsive:true, maintainAspectRatio:false,
        plugins:{{ legend:{{ display:false }} }},
        scales:{{
          x:{{ ticks:{{ font:{{ size:9 }}, color:'#787b86' }}, grid:{{ color:'#2b2b43' }} }},
          y:{{ ticks:{{ font:{{ size:9 }}, color:'#787b86' }}, grid:{{ color:'#2b2b43' }} }}
        }}
      }}
    }});
    charts.push(ch);
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
        datasets:[{{ label:'上涨个数', data:upVals, backgroundColor:'#26a69a', borderColor:'#0d904f', borderWidth:1, borderRadius:1, barPercentage:0.92, categoryPercentage:1 }}]
      }},
      options:{{
        responsive:true, maintainAspectRatio:false,
        interaction:{{ mode:'index', intersect:false }},
        plugins:{{ legend:{{ display:false }}, tooltip:{{ callbacks:{{ title: items => winData[items[0].dataIndex].date, label: ctx => '上涨: ' + ctx.parsed.y }} }} }},
        scales:{{
          x:{{ offset:true, ticks:{{ display:false }}, grid:{{ display:false }} }},
          y:{{ display:true, position:'right', ticks:{{ display:false }}, grid:{{ color:'#485c7b55', borderDash:[3,4], lineWidth:1 }}, border:{{ display:false }} }}
        }}
      }}
    }});
    charts.push(ch);
  }}

  /* ---- 第4行：下跌柱状图 ---- */
  const dn = records.filter(r => r.pct < 0).sort((a,b) => a.pct - b.pct);
  const ctx3 = document.getElementById('c-dn');
  if (ctx3) {{
    const has = dn.length > 0;
    charts.push(new Chart(ctx3, {{
      type:'bar',
      data:{{
        labels: has ? dn.map(s=>s.code) : [''],
        datasets:[{{ label:'跌幅%', data: has ? dn.map(s=>Math.abs(s.pct)) : [0], backgroundColor:'#ef5350', borderRadius:3 }}]
      }},
      options:{{
        responsive:true, maintainAspectRatio:false,
        indexAxis:'y',
        plugins:{{ legend:{{ display:false }}, tooltip:{{ callbacks:{{ label: ctx => '-'+ctx.parsed.x.toFixed(2)+'%' }} }} }},
        scales:{{
          x:{{ ticks:{{ font:{{ size:9 }}, color:'#787b86' }}, grid:{{ color:'#2b2b43' }} }},
          y:{{ ticks:{{ font:{{ size:9 }}, color:'#787b86' }}, grid:{{ display:false }} }}
        }}
      }}
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

    output = str(target_dir) + '.target_1d.html'
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    webbrowser.open(output)
    print(f'[SHOW] {latest} ({len(stocks)} stocks, {len(win_data)} days) -> {output}')
