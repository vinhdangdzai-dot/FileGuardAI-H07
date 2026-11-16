(() => {
  const node = document.getElementById('chart-data');
  const canvas = document.getElementById('eventsChart');
  if (!node || !canvas || typeof Chart === 'undefined') return;
  const stats = JSON.parse(node.textContent);
  new Chart(canvas, {
    type: 'doughnut',
    data: {labels: ['Cho phép', 'Từ chối', 'Không tìm thấy'], datasets: [{
      data: [stats.allowed, stats.blocked, stats.missed],
      backgroundColor: ['#21a477', '#da6464', '#9aabbc']
    }]},
    options: {responsive: true, plugins: {legend: {position:'bottom'}}}
  });
})();
