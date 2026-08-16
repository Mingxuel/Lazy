// 验证指标计算逻辑正确性（与前端 JS 相同的实现）
const data = [];
// 构造 40 天模拟数据：时间 2026-01-01 起递增，价格缓慢上涨
let price = 20;
for (let i = 1; i <= 40; i++) {
  price = price * (1 + 0.01 * Math.sin(i / 5) + 0.005);
  const open = price;
  const close = price * (1 + 0.02 * Math.sin(i / 3));
  const high = Math.max(open, close) * 1.02;
  const low = Math.min(open, close) * 0.98;
  const dd = String(i).padStart(2, '0');
  data.push({ time: `2026-01-${dd}`, open: +open.toFixed(2), high: +high.toFixed(2), low: +low.toFixed(2), close: +close.toFixed(2), volume: 1000 + i * 10 });
}

// 月线聚合
function monthKey(time) { return time.slice(0, 7); }
function aggregateMonthly(daily) {
  const map = new Map();
  daily.forEach(d => {
    const mk = monthKey(d.time);
    const g = map.get(mk);
    if (!g) map.set(mk, { time: d.time.slice(0,7)+'-01', open: d.open, high: d.high, low: d.low, close: d.close, volume: d.volume });
    else { g.high = Math.max(g.high, d.high); g.low = Math.min(g.low, d.low); g.close = d.close; g.volume += d.volume; }
  });
  return Array.from(map.values()).sort((a,b) => a.time < b.time ? -1 : 1);
}

// MA
function calcMA(d, period) {
  const out = []; let sum = 0;
  for (let i = 0; i < d.length; i++) {
    sum += d[i].close;
    if (i >= period) sum -= d[i - period].close;
    if (i >= period - 1) out.push({ time: d[i].time, value: +(sum / period).toFixed(3) });
  }
  return out;
}
// EMA
function emaArr(values, period) {
  const k = 2 / (period + 1); const out = []; let prev = null;
  for (let i = 0; i < values.length; i++) { prev = i===0 ? values[i] : values[i]*k + prev*(1-k); out.push(prev); }
  return out;
}
// MACD
function calcMACD(d) {
  const c = d.map(x => x.close);
  const e12 = emaArr(c,12), e26 = emaArr(c,26);
  const dif = c.map((_,i) => e12[i]-e26[i]);
  const dea = emaArr(dif,9);
  return { lastDif: +dif[dif.length-1].toFixed(3), lastDea: +dea[dea.length-1].toFixed(3), lastBar: +((dif[dif.length-1]-dea[dea.length-1])*2).toFixed(3) };
}
// KDJ
function calcKDJ(d, n=9, m1=3, m2=3) {
  let k=50, D=50, last=null;
  for (let i=0;i<d.length;i++) {
    let rsv=50;
    if (i>=n-1) {
      let hh=-Infinity, ll=Infinity;
      for (let j=i-n+1;j<=i;j++){ hh=Math.max(hh,d[j].high); ll=Math.min(ll,d[j].low); }
      rsv = (hh===ll)?50:(d[i].close-ll)/(hh-ll)*100;
    }
    k=(m1-1)/m1*k+(1/m1)*rsv;
    D=(m2-1)/m2*D+(1/m2)*k;
    last={K:+k.toFixed(2),D:+D.toFixed(2),J:+(3*k-2*D).toFixed(2)};
  }
  return last;
}
// BOLL
function calcBOLL(d, period=20, mult=2) {
  let last=null;
  for (let i=period-1;i<d.length;i++) {
    let s=0; for(let j=i-period+1;j<=i;j++) s+=d[j].close;
    const ma=s/period; let v=0; for(let j=i-period+1;j<=i;j++) v+=(d[j].close-ma)**2;
    const sd=Math.sqrt(v/period);
    last={up:+(ma+mult*sd).toFixed(3), mid:+ma.toFixed(3), low:+(ma-mult*sd).toFixed(3)};
  }
  return last;
}
// VWAP
function calcVWAP(d) {
  let pv=0, v=0;
  for (let i=0;i<d.length;i++){ const tp=(d[i].high+d[i].low+d[i].close)/3; pv+=tp*d[i].volume; v+=d[i].volume; }
  return +(pv/(v||1)).toFixed(3);
}

console.log("data len:", data.length);
console.log("MA5 last:", JSON.stringify(calcMA(data,5).slice(-1)[0]));
console.log("MA20 last:", JSON.stringify(calcMA(data,20).slice(-1)[0]));
console.log("MACD:", JSON.stringify(calcMACD(data)));
console.log("KDJ:", JSON.stringify(calcKDJ(data)));
console.log("BOLL:", JSON.stringify(calcBOLL(data)));
console.log("VWAP:", calcVWAP(data));
const m = aggregateMonthly(data);
console.log("monthly bars:", m.length, "first:", JSON.stringify(m[0]));
