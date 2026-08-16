// 模拟浏览器 window 环境加载 v5 standalone
const fs = require('fs');
const src = fs.readFileSync('e:/Lazy/MarcoAI/_lwc5.js', 'utf-8');
global.window = global;
global.document = { createElement: () => ({ style: {}, getContext: () => ({}) }), documentElement: {} };
global.navigator = { userAgent: 'node' };
global.devicePixelRatio = 1;
try {
  eval(src);
} catch (e) {
  console.log('eval error:', e.message);
}
const L = global.LightweightCharts || global.window.LightweightCharts;
console.log('LightweightCharts:', typeof L);
if (L) {
  const names = ['CandlestickSeries','LineSeries','HistogramSeries','SolidColor','VerticalGradientColor','ColorType','LineStyle','CrosshairMode','createChart','PaneApi'];
  names.forEach(n => console.log(n + ':', typeof L[n], typeof L[n] !== 'undefined' ? String(L[n]).slice(0,40) : ''));
  if (L.LineStyle) console.log('LineStyle keys:', Object.keys(L.LineStyle).join(','));
  if (L.ColorType) console.log('ColorType keys:', Object.keys(L.ColorType).join(','));
}
