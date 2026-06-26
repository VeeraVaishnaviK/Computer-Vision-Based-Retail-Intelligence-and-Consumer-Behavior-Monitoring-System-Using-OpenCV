/**
 * Ultimate Retail Intelligence JS
 */

let zoneAnalyticsChart;
let queueChart;

Chart.defaults.color = '#6B7280';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.scale.grid.color = '#F3F4F6';

async function fetchSummary() {
    try {
        const response = await fetch('/api/summary');
        if (!response.ok) return;
        const data = await response.json();
        
        // Populate KPIs
        document.getElementById('val-entries').innerText = data.total_entries || 0;
        document.getElementById('val-active').innerText = data.active_visitors || 0;
        document.getElementById('val-exits').innerText = data.total_exits || 0;
        document.getElementById('val-peak').innerText = data.peak_occupancy || 0;
        document.getElementById('val-density').innerText = (data.crowd_density || 0) + '%';
        
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
        
        // Calculate average dwell across all zones for KPI
        const totalDwell = data.reduce((acc, curr) => acc + curr.avg_dwell, 0);
        const avgTotalDwell = totalDwell / data.length;
        document.getElementById('val-dwell').innerText = avgTotalDwell.toFixed(1) + 's';

        if (!zoneAnalyticsChart) {
            const ctx = document.getElementById('zoneAnalyticsChart').getContext('2d');
            zoneAnalyticsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Visits',
                            data: visits,
                            backgroundColor: '#2563EB', // Blue
                            yAxisID: 'y',
                            borderRadius: 4
                        },
                        {
                            label: 'Dwell (s)',
                            data: dwell,
                            backgroundColor: '#10B981', // Green
                            yAxisID: 'y1',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { display: false } },
                        y: { position: 'left', title: { display: true, text: 'Visits' } },
                        y1: { position: 'right', grid: { drawOnChartArea: false } }
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
        
        // Update Queue KPIs
        document.getElementById('val-queue').innerText = latest.queue_length;
        const badge = document.getElementById('val-qstatus');
        
        let bgClass = 'bg-success';
        if(latest.crowd_level === 'MEDIUM') bgClass = 'bg-warning text-dark';
        if(latest.crowd_level === 'HIGH' || latest.crowd_level === 'CRITICAL') bgClass = 'bg-danger';
        
        badge.innerHTML = `<span class="badge ${bgClass} fs-6">${latest.crowd_level}</span>`;

        // Chart
        const labels = data.map(d => {
            const dObj = new Date(d.timestamp);
            return `${dObj.getHours().toString().padStart(2,'0')}:${dObj.getMinutes().toString().padStart(2,'0')}`;
        });
        const lengths = data.map(d => d.queue_length);
        
        if (!queueChart) {
            const ctx = document.getElementById('queueChart').getContext('2d');
            queueChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'People',
                        data: lengths,
                        borderColor: '#F59E0B', // Orange
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
                        y: { beginAtZero: true, suggestedMax: 5 }
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

async function fetchEvents() {
    try {
        const response = await fetch('/api/events');
        if (!response.ok) return;
        const events = await response.json();
        
        const container = document.getElementById('event-timeline');
        if (events.length === 0) {
            container.innerHTML = '<div class="p-4 text-center text-muted">No events recorded yet.</div>';
            return;
        }
        
        container.innerHTML = '';
        events.forEach(ev => {
            const timeObj = new Date(ev.timestamp);
            const timeStr = `${timeObj.getHours().toString().padStart(2,'0')}:${timeObj.getMinutes().toString().padStart(2,'0')}:${timeObj.getSeconds().toString().padStart(2,'0')}`;
            
            let colorClass = '';
            let text = '';
            
            if (ev.event_type === 'ENTRY') {
                colorClass = 'bg-success-light';
                text = `Customer #${ev.visitor_id} entered the store`;
            } else if (ev.event_type === 'EXIT') {
                colorClass = 'bg-danger-light';
                text = `Customer #${ev.visitor_id} exited`;
            } else if (ev.event_type === 'ZONE_ENTER') {
                text = `Customer #${ev.visitor_id} entered ${ev.zone_name}`;
            }
            
            const html = `
                <div class="timeline-item ${colorClass}">
                    <span class="timeline-time">${timeStr}</span>
                    <p class="timeline-content">${text}</p>
                </div>
            `;
            container.innerHTML += html;
        });
        
    } catch (e) { console.error("Event error", e); }
}

function updateHeatmap() {
    const img = document.getElementById('heatmap-img');
    const tempImg = new Image();
    tempImg.onload = function() { img.src = this.src; };
    tempImg.src = '/api/heatmap?t=' + new Date().getTime();
}

function updateTime() {
    document.getElementById('current-time').innerText = new Date().toLocaleTimeString();
}

function updateAll() {
    fetchSummary();
    fetchZones();
    fetchQueue();
    fetchEvents();
    updateHeatmap();
}

// Check if Video Stream breaks
const videoStream = document.getElementById('video-stream');
const videoOverlay = document.getElementById('video-overlay');
videoStream.onerror = function() {
    videoOverlay.style.display = 'block';
}

// Init
setInterval(updateTime, 1000);
updateAll();
// Fetch data every 2 seconds
setInterval(updateAll, 2000);
