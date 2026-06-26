/**
 * Corporate BI Dashboard Logic
 */

let zoneAnalyticsChart;
let queueChart;

// Setup Light Theme defaults for Corporate look
Chart.defaults.color = '#666666';
Chart.defaults.font.family = "'Roboto', -apple-system, sans-serif";
Chart.defaults.scale.grid.color = '#e0e0e0';
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(255, 255, 255, 0.9)';
Chart.defaults.plugins.tooltip.titleColor = '#333333';
Chart.defaults.plugins.tooltip.bodyColor = '#666666';
Chart.defaults.plugins.tooltip.borderColor = '#e0e0e0';
Chart.defaults.plugins.tooltip.borderWidth = 1;

async function fetchSummary() {
    try {
        const response = await fetch('/api/summary');
        if (!response.ok) return;
        const data = await response.json();
        
        document.getElementById('val-entries').innerText = data.total_entries || 0;
        document.getElementById('val-active').innerText = data.active_visitors || 0;
        document.getElementById('val-peak').innerText = data.peak_occupancy || 0;
    } catch (e) { console.error("Summary error", e); }
}

async function fetchZones() {
    try {
        const response = await fetch('/api/zones');
        if (!response.ok) return;
        const data = await response.json();
        if (data.length === 0) return;
        
        const labels = data.map(d => d.zone_name);
        const visits = data.map(d => d.total_visits);
        const dwell = data.map(d => d.avg_dwell.toFixed(1));

        if (!zoneAnalyticsChart) {
            const ctx = document.getElementById('zoneAnalyticsChart').getContext('2d');
            zoneAnalyticsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Total Visits',
                            data: visits,
                            backgroundColor: '#2c7be5', // Corporate Blue
                            yAxisID: 'y',
                            borderRadius: 4
                        },
                        {
                            label: 'Avg Dwell Time (s)',
                            data: dwell,
                            backgroundColor: '#00d27a', // Corporate Green
                            yAxisID: 'y1',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        x: {
                            grid: { display: false }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: { display: true, text: 'Visits' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            title: { display: true, text: 'Seconds' }
                        }
                    }
                }
            });
        } else {
            zoneAnalyticsChart.data.labels = labels;
            zoneAnalyticsChart.data.datasets[0].data = visits;
            zoneAnalyticsChart.data.datasets[1].data = dwell;
            zoneAnalyticsChart.update();
        }
    } catch (e) { console.error("Zone error", e); }
}

async function fetchQueue() {
    try {
        const response = await fetch('/api/queue');
        if (!response.ok) return;
        const data = await response.json();
        
        if (data.length === 0) return;

        const latest = data[data.length - 1];
        document.getElementById('val-queue').innerText = latest.queue_length;
        const badge = document.getElementById('queue-badge');
        badge.innerText = "Status: " + latest.crowd_level;
        badge.className = 'kpi-label badge-' + latest.crowd_level.toLowerCase();

        const labels = data.map(d => {
            const dObj = new Date(d.timestamp);
            return `${dObj.getHours().toString().padStart(2,'0')}:${dObj.getMinutes().toString().padStart(2,'0')}`;
        });
        const lengths = data.map(d => d.queue_length);
        
        if (!queueChart) {
            const ctx = document.getElementById('queueChart').getContext('2d');
            queueChart = new Chart(ctx, {
                type: 'bar', // Using bar chart for queue volume over time is very BI
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'People in Queue',
                        data: lengths,
                        backgroundColor: '#e63757', // Alert red/pink
                        borderRadius: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { 
                            ticks: { maxTicksLimit: 10 },
                            grid: { display: false }
                        },
                        y: { 
                            beginAtZero: true, 
                            suggestedMax: 5 
                        }
                    }
                }
            });
        } else {
            queueChart.data.labels = labels;
            queueChart.data.datasets[0].data = lengths;
            queueChart.update('none');
        }
    } catch (e) { console.error("Queue error", e); }
}

function updateHeatmap() {
    const img = document.getElementById('heatmap-img');
    const fallback = document.getElementById('heatmap-fallback');
    
    const tempImg = new Image();
    tempImg.onload = function() {
        img.src = this.src;
        img.style.display = 'block';
        fallback.style.display = 'none';
    };
    tempImg.onerror = function() {
        img.style.display = 'none';
        fallback.style.display = 'block';
    };
    tempImg.src = '/api/heatmap?t=' + new Date().getTime();
}

function updateAll() {
    fetchSummary();
    fetchZones();
    fetchQueue();
    updateHeatmap();
    document.getElementById('update-time').innerText = new Date().toLocaleTimeString();
}

document.getElementById('refresh-btn').addEventListener('click', () => {
    updateAll();
});

// Init
updateAll();
setInterval(updateAll, 3000);
