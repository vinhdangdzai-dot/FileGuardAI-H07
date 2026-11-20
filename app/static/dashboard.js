/* Charts use only server-rendered data; no fabricated series or new API. */
(() => {
  'use strict';
  if (typeof Chart === 'undefined') return;
  Chart.defaults.font.family = 'Segoe UI, system-ui, sans-serif';
  const charts = new Map();
  function palette() {
    const style = getComputedStyle(document.documentElement);
    const get = name => style.getPropertyValue('--'+name).trim();
    return {muted:get('muted'), text:get('text'), line:get('chart-grid'), surface:get('raised'),
      colors:[get('chart-one'),get('chart-two'),get('chart-three')],
      decisions:[get('chart-allow'),get('chart-block'),get('chart-miss')], fill:get('chart-fill')};
  }
  const initial = palette();
  Chart.defaults.color = initial.muted;
  Chart.defaults.borderColor = initial.line;
  const colors = initial.colors;
  function recolor(id, chart) {
    const theme = palette();
    chart.stop();
    const fontSize = parseFloat(getComputedStyle(document.documentElement).fontSize) * 8/9;
    Chart.defaults.font.size = fontSize;
    chart.options.plugins.legend.labels.font = {size:fontSize};
    chart.options.plugins.tooltip.titleFont = {size:fontSize};
    chart.options.plugins.tooltip.bodyFont = {size:fontSize};
    chart.options.color = theme.muted;
    chart.options.plugins.legend.labels.color = theme.muted;
    Object.assign(chart.options.plugins.tooltip, {backgroundColor:theme.surface, titleColor:theme.text, bodyColor:theme.text, borderColor:theme.line, borderWidth:1});
    Object.values(chart.options.scales || {}).forEach(scale => {
      scale.ticks.color = theme.muted;
      scale.ticks.font = {size:fontSize};
      scale.grid.color = theme.line;
      scale.border.color = theme.line;
    });
    if (id === 'eventsChart') chart.data.datasets[0].backgroundColor = theme.decisions;
    if (id === 'labelsChart') chart.data.datasets[0].backgroundColor = theme.colors.slice(0,2);
    if (id === 'trendChart') Object.assign(chart.data.datasets[0], {borderColor:theme.colors[0], backgroundColor:theme.fill});
    if (id === 'ipsTrendChart') {
      Object.assign(chart.data.datasets[0], {borderColor:theme.colors[0]});
      Object.assign(chart.data.datasets[1], {borderColor:theme.decisions[1], backgroundColor:theme.fill});
    }
    if (id === 'metricsChart') chart.data.datasets.forEach(dataset => { dataset.backgroundColor = theme.colors[dataset.fgPaletteIndex]; });
    chart.resize();
    chart.update('none');
    chart.draw();
  }
  const read = id => { const node = document.getElementById(id); return node ? JSON.parse(node.textContent) : null; };
  const base = {responsive:true, maintainAspectRatio:false, animation:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : {duration:300}, plugins:{legend:{position:'bottom',labels:{usePointStyle:true,padding:20}}}};
  function draw(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    try {
      const chart = new Chart(canvas, config);
      charts.set(id,chart);
      recolor(id,chart);
      const fallback = canvas.closest('.panel')?.querySelector('[data-chart-fallback]');
      if (fallback) fallback.hidden = true;
    } catch (_) { canvas.hidden = true; /* keep honest text/table fallback */ }
  }
  const decisions = read('chart-data');
  if (decisions) {
    draw('eventsChart', {type:'doughnut', data:{labels:['ALLOW','BLOCK','MISS'],datasets:[{data:[decisions.allowed,decisions.blocked,decisions.missed],backgroundColor:initial.decisions,borderWidth:0,hoverOffset:5}]},options:{...base,cutout:'76%'}});
    const times = read('trend-data') || [];
    const minutes = new Map();
    times.forEach(time => { const key = time.slice(0,16); minutes.set(key,(minutes.get(key)||0)+1); });
    const points = [...minutes.entries()].sort(([a],[b]) => a.localeCompare(b));
    draw('trendChart', {
      type: 'line',
      data: {
        labels: points.map(([time]) => time.replace('T',' ')),
        datasets: [{label:'Request trong bảng', data:points.map(([,count])=>count),
          borderColor:colors[0], backgroundColor:initial.fill, fill:true, tension:.25, pointRadius:3}]
      },
      options: {
        ...base,
        plugins: {legend:{display:false}},
        scales: {
          y: {beginAtZero:true, ticks:{precision:0}},
          x: {grid:{display:false}, ticks:{maxTicksLimit:5,maxRotation:0}}
        }
      }
    });
  }
  const evaluation = read('evaluation-data');
  const ipsTrend = read('ips-trend-data');
  if (ipsTrend) draw('ipsTrendChart', {type:'line',data:{labels:ipsTrend.map(x=>x.minute.replace('T',' ')),datasets:[
    {label:'Tổng request',data:ipsTrend.map(x=>x.total),borderColor:colors[0],backgroundColor:'transparent',tension:.25},
    {label:'BLOCK',data:ipsTrend.map(x=>x.blocked),borderColor:initial.decisions[1],backgroundColor:initial.fill,tension:.25,fill:true}
  ]},options:{...base,scales:{y:{beginAtZero:true,ticks:{precision:0}},x:{grid:{display:false},ticks:{maxTicksLimit:6,maxRotation:0}}}}});
  if (evaluation) {
    const metrics = ['accuracy','precision','recall','f1'];
    const methods = [['v1','LR v1'],['v2','LR v2 · thử nghiệm'],['regex','Regex']];
    draw('metricsChart',{type:'bar',data:{labels:['Accuracy','Precision','Recall','F1-score'],datasets:methods.filter(([key])=>evaluation[key]).map(([key,label])=>({label,fgPaletteIndex:{v1:0,v2:1,regex:2}[key],data:metrics.map(metric=>evaluation[key][metric]*100),backgroundColor:colors[{v1:0,v2:1,regex:2}[key]],borderRadius:4,maxBarThickness:28}))},options:{...base,scales:{y:{beginAtZero:true,max:100,ticks:{callback:value=>value+'%'}},x:{grid:{display:false}}}}});
  }
  const labels = read('training-label-data');
  if (labels) draw('labelsChart',{type:'doughnut',data:{labels:['Benign (0)','Suspicious (1)'],datasets:[{data:[labels['0']||0,labels['1']||0],backgroundColor:[colors[0],colors[1]],borderWidth:0}]},options:{...base,cutout:'72%'}});
  document.addEventListener('fileguard:textsizechange', () => charts.forEach((chart,id) => recolor(id,chart)));
  document.addEventListener('fileguard:themechange', () => charts.forEach((chart,id) => recolor(id,chart)));
})();
