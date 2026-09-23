// --- CHART INTERFACE (Dashboard) ---
document.addEventListener('DOMContentLoaded', () => {
    const dashboardEl = document.getElementById('view-dashboard');
    if (!dashboardEl) return;

    // Parse JSON safely from data attributes
    const monthlyData = JSON.parse(dashboardEl.getAttribute('data-monthly') || '[]');
    const jockeyNames = JSON.parse(dashboardEl.getAttribute('data-jockey-names') || '[]');
    const jockeyWins = JSON.parse(dashboardEl.getAttribute('data-jockey-wins') || '[]');
    const trainerNames = JSON.parse(dashboardEl.getAttribute('data-trainer-names') || '[]');
    const trainerWins = JSON.parse(dashboardEl.getAttribute('data-trainer-wins') || '[]');
    const ageLabels = JSON.parse(dashboardEl.getAttribute('data-age-labels') || '[]');
    const ageChartData = JSON.parse(dashboardEl.getAttribute('data-age-data') || '[]');

    const renderChart = () => {
        const mainCtx = document.getElementById('mainChart');
        if(mainCtx) {
            window.chartInstance = new Chart(mainCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                    datasets: [{
                        label: 'Total Races',
                        data: monthlyData,
                        backgroundColor: '#4f46e5',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--border-color') }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        const bColor = getComputedStyle(document.documentElement).getPropertyValue('--border-color');
        const tColor = getComputedStyle(document.documentElement).getPropertyValue('--text-muted');

        const jCtx = document.getElementById('jockeyChart');
        if(jCtx) {
            window.jockeyChartInstance = new Chart(jCtx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: jockeyNames,
                    datasets: [{
                        data: jockeyWins,
                        backgroundColor: ['#4f46e5', '#3b82f6', '#10b981', '#f59e0b', '#ec4899']
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { color: tColor } } },
                    cutout: '50%'
                }
            });
        }

        const tCtx = document.getElementById('trainerChart');
        if(tCtx) {
            window.trainerChartInstance = new Chart(tCtx.getContext('2d'), {
                type: 'pie',
                data: {
                    labels: trainerNames,
                    datasets: [{
                        data: trainerWins,
                        backgroundColor: ['#ef4444', '#f97316', '#eab308', '#22c55e', '#0ea5e9']
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'left', labels: { color: tColor } } }
                }
            });
        }

        const aCtx = document.getElementById('ageChart');
        if(aCtx) {
            window.ageChartInstance = new Chart(aCtx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: ageLabels,
                    datasets: [{
                        label: 'Horses',
                        data: ageChartData,
                        fill: true,
                        backgroundColor: 'rgba(139, 92, 246, 0.2)',
                        borderColor: '#8b5cf6',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: bColor } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
    };

    window.updateChartTheme = () => {
        const bColor = getComputedStyle(document.documentElement).getPropertyValue('--border-color');
        const tColor = getComputedStyle(document.documentElement).getPropertyValue('--text-muted');

        [window.chartInstance, window.jockeyChartInstance, window.trainerChartInstance, window.ageChartInstance].forEach(chart => {
            if(chart) {
                if(chart.options.scales && chart.options.scales.y) {
                    chart.options.scales.y.grid.color = bColor;
                    chart.options.scales.y.ticks.color = tColor;
                    chart.options.scales.x.ticks.color = tColor;
                }
                if(chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
                    chart.options.plugins.legend.labels.color = tColor;
                }
                chart.update();
            }
        });
    };

    renderChart();
    updateChartTheme();
});
