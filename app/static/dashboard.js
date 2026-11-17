/* Charts use only server-rendered data; no fabricated series or new API. */
(() => {
  'use strict';
  if (typeof Chart === 'undefined') return;
  Chart.defaults.color = '#a1b1c8';
  Chart.defaults.borderColor = '#27354a';
  Chart.defaults.font.family = 'Segoe UI, system-ui, sans-serif';
  const colors = ['#64ddf2', '#b3a0ff', '#69deb0'];
  const read = id => { const node = document.getElementById(id); return node ? JSON.parse(node.textContent) : null; };
  const base = {responsive:true, maintainAspectRatio:false, animation:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : {duration:300}, plugins:{legend:{position:'bottom',labels:{usePointStyle:true,padding:20}}}};
  function draw(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    try {
      new Chart(canvas, config);
      const fallback = canvas.closest('.panel')?.querySelector('[data-chart-fallback]');
      if (fallback) fallback.hidden = true;
    } catch (_) { canvas.hidden = true; /* keep honest text/table fallback */ }
  }
  const decisions = read('chart-data');
  if (decisions) {
    draw('eventsChart', {type:'doughnut', data:{labels:['ALLOW','BLOCK','MISS'],datasets:[{data:[decisions.allowed,decisions.blocked,decisions.missed],backgroundColor:['#69deb0','#ff919d','#f2cb76'],borderWidth:0,hoverOffset:5}]},options:{...base,cutout:'76%'}});
    const times = read('trend-data') || [];
    const minutes = new Map();
    times.forEach(time => { const key = time.slice(0,16); minutes.set(key,(minutes.get(key)||0)+1); });
    const points = [...minutes.entries()].sort(([a],[b]) => a.localeCompare(b));
    draw('trendChart', {
      type: 'line',
      data: {
        labels: points.map(([time]) => time.replace('T',' ')),
        datasets: [{label:'Request trong bảng', data:points.map(([,count])=>count),
          borderColor:colors[0], backgroundColor:'#64ddf214', fill:true, tension:.25, pointRadius:3}]
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
  if (evaluation) {
    const metrics = ['accuracy','precision','recall','f1'];
    const methods = [['v1','LR v1'],['v2','LR v2 · thử nghiệm'],['regex','Regex']];
    draw('metricsChart',{type:'bar',data:{labels:['Accuracy','Precision','Recall','F1-score'],datasets:methods.filter(([key])=>evaluation[key]).map(([key,label],i)=>({label,data:metrics.map(metric=>evaluation[key][metric]*100),backgroundColor:colors[i],borderRadius:4,maxBarThickness:28}))},options:{...base,scales:{y:{beginAtZero:true,max:100,ticks:{callback:value=>value+'%'}},x:{grid:{display:false}}}}});
  }
  const labels = read('training-label-data');
  if (labels) draw('labelsChart',{type:'doughnut',data:{labels:['Benign (0)','Suspicious (1)'],datasets:[{data:[labels['0']||0,labels['1']||0],backgroundColor:[colors[0],colors[1]],borderWidth:0}]},options:{...base,cutout:'72%'}});
})();
