document.addEventListener('DOMContentLoaded', function() {
    const toggleSystemBtn = document.getElementById('toggle-system-btn');
    const systemStatusSpan = document.getElementById('system-status');
    const sensorDataTableBody = document.querySelector('#sensor-data-table tbody');
    const chartDataTypeSelect = document.getElementById('chartDataType');
    const hamburger = document.querySelector('.hamburger');
    const sidebar = document.querySelector('.sidebar');

    let lineChartInstance;
    let globalHistoryData = [];

    // Toggle Sidebar untuk Mobile
    if (hamburger && sidebar) {
        hamburger.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });

        // Close sidebar saat klik di luar sidebar pada mobile
        document.addEventListener('click', function(event) {
            if (window.innerWidth <= 1024) {
                if (!sidebar.contains(event.target) && !hamburger.contains(event.target)) {
                    sidebar.classList.remove('active');
                }
            }
        });
    }

    function createOrUpdateLineChart(data, dataType) {
        const ctx = document.getElementById('lineChart').getContext('2d');
        const labels = data.map(row => new Date(row.waktu).toLocaleTimeString()).reverse();
        let chartData, labelText, borderColor, backgroundColor;

        if (dataType === 'temperature') {
            chartData = data.map(row => row.temperature).reverse();
            labelText = 'Suhu (°C)';
            borderColor = 'rgb(239, 68, 68)';
            backgroundColor = 'rgba(239, 68, 68, 0.1)';
        } else if (dataType === 'humidity') {
            chartData = data.map(row => row.humidity).reverse();
            labelText = 'Kelembaban (%)';
            borderColor = 'rgb(59, 130, 246)';
            backgroundColor = 'rgba(59, 130, 246, 0.1)';
        }

        if (lineChartInstance) {
            lineChartInstance.destroy();
        }

        lineChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: labelText,
                        data: chartData,
                        borderColor: borderColor,
                        backgroundColor: backgroundColor,
                        tension: 0.4,
                        fill: true,
                        borderWidth: 3,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        pointBackgroundColor: borderColor,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: 13,
                                weight: '600'
                            },
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        borderColor: borderColor,
                        borderWidth: 2
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            font: {
                                size: 12
                            }
                        },
                        title: {
                            display: true,
                            text: labelText,
                            font: {
                                size: 13,
                                weight: '600'
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
    }

    function updateData() {
        fetch('/data')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Frontend received Flask system status:', data.flask_system_status);

                if (data.latest) {
                    document.getElementById('current-waktu').textContent = data.latest.waktu;
                    document.getElementById('current-temperature').textContent = data.latest.temperature;
                    document.getElementById('current-humidity').textContent = data.latest.humidity;
                    // Logika tampilan sensor hujan yang diperbaiki: nilai rendah = hujan
                    document.getElementById('current-rain').textContent =
                        data.latest.rain_value >= 500 
                        ? data.latest.rain_value + " (Hujan)" 
                        : data.latest.rain_value + " (Tidak Hujan)";
                    document.getElementById('current-ldr').textContent = data.latest.ldr_value;
                    document.getElementById('current-jemuran-status').textContent = data.latest.status_jemuran;
                } else {
                    document.getElementById('current-waktu').textContent = 'N/A';
                    document.getElementById('current-temperature').textContent = 'N/A';
                    document.getElementById('current-humidity').textContent = 'N/A';
                    document.getElementById('current-rain').textContent = 'N/A';
                    document.getElementById('current-ldr').textContent = 'N/A';
                    document.getElementById('current-jemuran-status').textContent = 'N/A';
                }

                const newSystemStatus = data.flask_system_status;
                systemStatusSpan.textContent = newSystemStatus;
                systemStatusSpan.classList.toggle('on', newSystemStatus === 'ON');
                systemStatusSpan.classList.toggle('off', newSystemStatus === 'OFF');

                toggleSystemBtn.textContent = (newSystemStatus === 'ON' ? 'MATIKAN SISTEM' : 'NYALAKAN SISTEM');
                toggleSystemBtn.classList.toggle('btn-off', newSystemStatus === 'ON');
                toggleSystemBtn.classList.toggle('btn-on', newSystemStatus === 'OFF');

                if (data.history) {
                    sensorDataTableBody.innerHTML = '';
                    const filteredHistory = data.history.filter(row => row.status_system === 'ON');
                    globalHistoryData = filteredHistory;

                    filteredHistory.forEach(row => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${row.id}</td>
                            <td>${row.waktu}</td>
                            <td>${row.temperature}</td>
                            <td>${row.humidity}</td>
                            <td>${row.rain_value}</td>
                            <td>${row.ldr_value}</td>
                            <td>${row.status_jemuran}</td>
                            <td>${row.status_system}</td>
                        `;
                        sensorDataTableBody.appendChild(tr);
                    });
                    
                    createOrUpdateLineChart(globalHistoryData, chartDataTypeSelect.value);
                } else {
                    sensorDataTableBody.innerHTML = '<tr><td colspan="8">Tidak ada data riwayat sensor yang tersedia atau sistem nonaktif.</td></tr>';
                    globalHistoryData = [];
                    if (lineChartInstance) {
                        lineChartInstance.destroy();
                    }
                }
            })
            .catch(error => {
                console.error('Error fetching data:', error);
            });
    }

    if (toggleSystemBtn) {
        toggleSystemBtn.addEventListener('click', function() {
            const currentStatus = systemStatusSpan.textContent.trim();
            const newStatus = (currentStatus === 'ON' ? 'OFF' : 'ON');

            fetch('/toggle_system', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status_system: newStatus })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || 'Failed to toggle system'); });
                }
                return response.json();
            })
            .then(data => {
                updateData(); 
            })
            .catch(error => {
                console.error('Error toggling system:', error);
                alert('Gagal mengubah status sistem: ' + error.message);
            });
        });

        chartDataTypeSelect.addEventListener('change', () => {
            if (globalHistoryData.length > 0) {
                createOrUpdateLineChart(globalHistoryData, chartDataTypeSelect.value);
            } else {
                if (lineChartInstance) {
                    lineChartInstance.destroy();
                }
            }
        });

        updateData();
        setInterval(updateData, 5000);
    }
});