/**
 * Retail Intelligence Dashboard JS
 * Handles data fetching, Chart.js rendering, and auto-refresh logic.
 */

// Global Chart Instances
let zoneVisitsChart;
let zoneDwellChart;
let queueChart;

// Chart.js Default styling for Dark Theme
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.05)';
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.cornerRadius = 8;

// Colors for zones
const zoneColors = {
    'Electronics': 'rgba(59, 130, 246, 0.8)', // Blue
    'Grocery': 'rgba(16, 185, 129, 0.8)',     // Green
    'Fashion': 'rgba(139, 92, 246, 0.8)',     // Purple
    'Billing': 'rgba(245, 158, 11, 0.8)'      // Orange
};

const zoneColorsSolid = {
    'Electronics': '#3b82f6',
    'Grocery': '#10b981',
    'Fashion': '#8b5cf6',
    'Billing': '#f59e0b'
};

// ==========================================
// Data Fetching
// ==========================================

async function fetchSummary() {
    try {
        const response = await fetch('/api/summary');
        if (!response.ok) throw new Error("No data");
        const data = await response.json();
        
        document.getElementById('val-entries').innerText = data.total_entries || 0;
        document.getElementById('val-exits').innerText = data.total_exits || 0;
        document.getElementById('val-peak').innerText = data.peak_occupancy || 0;
        document.getElementById('val-active').innerText = data.active_visitors || 0;
    } catch (e) {
        console.log("Summary data not available yet.");
    }
}

async function fetchZones() {
    try {
        const response = await fetch('/api/zones');
        if (!response.ok) throw new Error("No data");
        const data = await response.json();
        
        if (data.length === 0) return;
        
        const labels = data.map(d => d.zone_name);
        const visits = data.map(d => d.total_visits);
        const dwell = data.map(d => d.avg_dwell.toFixed(1));
        const bgColors = labels.map(l => zoneColors[l] || 'rgba(148, 163, 184, 0.8)');
        const borderColors = labels.map(l => zoneColorsSolid[l] || '#94a3b8');

        // Update Visits Chart
        if (!zoneVisitsChart) {
            const ctx = document.getElementById('zoneVisitsChart').getContext('2d');
            zoneVisitsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Total Visits',
                        data: visits,
                        backgroundColor: bgColors,
                        borderColor: borderColors,
                        borderWidth: 1,
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });
        } else {
            zoneVisitsChart.data.labels = labels;
            zoneVisitsChart.data.datasets[0].data = visits;
            zoneVisitsChart.update();
        }

        // Update Dwell Chart
        if (!zoneDwellChart) {
            const ctx = document.getElementById('zoneDwellChart').getContext('2d');
            zoneDwellChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: dwell,
                        backgroundColor: bgColors,
                        borderColor: 'transparent',
                        borderWidth: 2,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: { position: 'right' }
                    }
                }
            });
        } else {
            zoneDwellChart.data.labels = labels;
            zoneDwellChart.data.datasets[0].data = dwell;
            zoneDwellChart.update();
        }
    } catch (e) {
        console.log("Zone data not available yet.");
    }
}

async function fetchQueue() {
    try {
        const response = await fetch('/api/queue');
        if (!response.ok) throw new Error("No data");
        const data = await response.json();
        
        if (data.length === 0) return;

        // Extract time (HH:MM:SS) for x-axis
        const labels = data.map(d => {
            const dObj = new Date(d.timestamp);
            return `${dObj.getHours().toString().padStart(2,'0')}:${dObj.getMinutes().toString().padStart(2,'0')}:${dObj.getSeconds().toString().padStart(2,'0')}`;
        });
        const lengths = data.map(d => d.queue_length);
        
        // Update crowd badge based on latest data
        const latest = data[data.length - 1];
        const badge = document.getElementById('queue-badge');
        badge.innerText = latest.crowd_level;
        badge.className = 'badge ' + latest.crowd_level.toLowerCase();

        if (!queueChart) {
            const ctx = document.getElementById('queueChart').getContext('2d');
            
            // Create gradient
            let gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(244, 63, 94, 0.5)'); // Rose
            gradient.addColorStop(1, 'rgba(244, 63, 94, 0.0)');

            queueChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Queue Length',
                        data: lengths,
                        borderColor: '#f43f5e',
                        backgroundColor: gradient,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4, // smooth curves
                        pointRadius: 2,
                        pointBackgroundColor: '#f43f5e'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, suggestedMax: 5 }
                    }
                }
            });
        } else {
            queueChart.data.labels = labels;
            queueChart.data.datasets[0].data = lengths;
            queueChart.update('none'); // Update without full animation for smoother polling
        }
    } catch (e) {
        console.log("Queue data not available yet.");
    }
}

function updateHeatmap() {
    const img = document.getElementById('heatmap-img');
    // Append timestamp to bust browser cache
    img.src = '/api/heatmap?t=' + new Date().getTime();
}

// ==========================================
// Initialization and Polling
// ==========================================

function updateAll() {
    fetchSummary();
    fetchZones();
    fetchQueue();
    updateHeatmap();
    
    // Update timestamp
    const now = new Date();
    document.getElementById('update-time').innerText = now.toLocaleTimeString();
}

// Event Listeners
document.getElementById('refresh-btn').addEventListener('click', () => {
    const btn = document.getElementById('refresh-btn');
    btn.innerText = "Refreshing...";
    updateAll();
    setTimeout(() => { btn.innerText = "Refresh Data"; }, 500);
});

// Initial load
updateAll();

// Auto-refresh every 3 seconds for live dashboard feel
setInterval(updateAll, 3000);
