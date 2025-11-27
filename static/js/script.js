document.addEventListener('DOMContentLoaded', function() {
    const sensorDataTableBody = document.querySelector('#sensor-data-table tbody');
    const chartDataTypeSelect = document.getElementById('chartDataType');
    const hamburger = document.querySelector('.hamburger');
    const sidebar = document.querySelector('.sidebar');
    const connectionDot = document.getElementById('connection-dot');
    const connectionText = document.getElementById('connection-text');
    const sidebarStatusText = document.getElementById('sidebar-status-text');
    const statusMessage = document.getElementById('status-message');

    const btnAuto = document.getElementById('btn-auto');
    const btnManual = document.getElementById('btn-manual');
    const btnOff = document.getElementById('btn-off');
    
    const manualControls = document.getElementById('manual-controls');
    const btnOpen = document.getElementById('btn-open');
    const btnClose = document.getElementById('btn-close');

    let lineChartInstance;

    // Hamburger menu toggle
    if (hamburger && sidebar) {
        hamburger.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 1024 && 
                !sidebar.contains(e.target) && 
                !hamburger.contains(e.target) &&
                sidebar.classList.contains('active')) {
                sidebar.classList.remove('active');
            }
        });
        
        // Prevent sidebar from closing when clicking inside it
        sidebar.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    // Create or update chart
    function createOrUpdateLineChart(data, dataType) {
        const ctx = document.getElementById('lineChart').getContext('2d');
        const labels = data.map(row => new Date(row.waktu).toLocaleTimeString()).reverse();
        const chartData = data.map(row => row[dataType]).reverse();
        const color = dataType === 'temperature' ? 'rgb(239, 68, 68)' : 'rgb(59, 130, 246)';
        
        if (lineChartInstance) {
            lineChartInstance.destroy();
        }
        
        lineChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ 
                    label: dataType === 'temperature' ? 'Suhu (°C)' : 'Kelembaban (%)', 
                    data: chartData, 
                    borderColor: color, 
                    backgroundColor: color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });
    }

    // Update data from server
    function updateData() {
        fetch('/data')
            .then(res => {
                if (!res.ok) throw new Error('Network response was not ok');
                return res.json();
            })
            .then(data => {
                // Update connection status
                connectionDot.style.backgroundColor = '#10b981';
                connectionText.textContent = 'Online';

                // Update current sensor data
                if (data.latest) {
                    document.getElementById('current-waktu').textContent = data.latest.waktu;
                    document.getElementById('current-temperature').textContent = data.latest.temperature;
                    document.getElementById('current-humidity').textContent = data.latest.humidity;
                    document.getElementById('current-rain').textContent = data.latest.rain_value;
                    document.getElementById('current-ldr').textContent = data.latest.ldr_value;
                    document.getElementById('current-jemuran-status').textContent = data.latest.status_jemuran;
                }

                // Update button states based on system status
                const sysStatus = data.flask_system_status;
                const currentMode = data.control_mode;

                // Reset all button classes
                btnAuto.classList.remove('active');
                btnManual.classList.remove('active');
                btnOff.classList.remove('active');
                
                // Reset OFF button styling
                btnOff.style.backgroundColor = 'transparent';
                btnOff.style.color = '#ef4444';

                if (sysStatus === 'OFF' && currentMode === 'AUTO') {
                    // System is turned OFF
                    console.log("State: SYSTEM OFF");
                    btnOff.classList.add('active');
                    btnOff.style.backgroundColor = '#ef4444'; 
                    btnOff.style.color = 'white';
                    manualControls.style.display = 'none';
                    sidebarStatusText.textContent = "SISTEM MATI";
                    sidebarStatusText.style.color = '#ef4444';
                    statusMessage.textContent = "Sistem dinonaktifkan. Sensor dan motor mati.";
                } 
                else if (currentMode === 'MANUAL') {
                    // Manual mode active
                    console.log("State: MANUAL");
                    btnManual.classList.add('active');
                    manualControls.style.display = 'flex';
                    sidebarStatusText.textContent = "MODE MANUAL";
                    sidebarStatusText.style.color = '#fbbf24';
                    statusMessage.textContent = "Kontrol manual aktif. Gunakan tombol di bawah.";
                } 
                else {
                    // Auto mode active
                    console.log("State: AUTO");
                    btnAuto.classList.add('active');
                    manualControls.style.display = 'none';
                    sidebarStatusText.textContent = "MODE AUTO";
                    sidebarStatusText.style.color = '#10b981';
                    statusMessage.textContent = "Sistem berjalan otomatis menggunakan sensor.";
                }

                // Update table and chart
                if (data.history && data.history.length > 0) {
                    sensorDataTableBody.innerHTML = '';
                    data.history.forEach(row => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
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
                    createOrUpdateLineChart(data.history, chartDataTypeSelect.value);
                }
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                connectionDot.style.backgroundColor = '#ef4444';
                connectionText.textContent = 'Offline';
                sidebarStatusText.textContent = "TIDAK TERHUBUNG";
                sidebarStatusText.style.color = '#ef4444';
            });
    }

    // Mode button event listeners
    btnAuto.addEventListener('click', () => {
        console.log("Clicked AUTO");
        fetch('/set_mode', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({ mode: 'AUTO' }) 
        })
        .then(response => {
            if (response.ok) {
                updateData();
            }
        })
        .catch(error => console.error('Error setting AUTO mode:', error));
    });

    btnManual.addEventListener('click', () => {
        console.log("Clicked MANUAL");
        fetch('/set_mode', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({ mode: 'MANUAL' }) 
        })
        .then(response => {
            if (response.ok) {
                updateData();
            }
        })
        .catch(error => console.error('Error setting MANUAL mode:', error));
    });

    btnOff.addEventListener('click', () => {
        console.log("Clicked MATIKAN");
        fetch('/set_mode', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({ mode: 'OFF' }) 
        })
        .then(response => {
            if (response.ok) {
                updateData();
            }
        })
        .catch(error => console.error('Error turning OFF system:', error));
    });

    // Manual control button event listeners
    btnOpen.addEventListener('click', () => {
        console.log("Clicked OPEN");
        fetch('/manual_control', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({ command: 'OPEN' }) 
        })
        .then(response => {
            if (response.ok) {
                statusMessage.textContent = "Perintah BUKA dikirim.";
                setTimeout(updateData, 500);
            }
        })
        .catch(error => console.error('Error sending OPEN command:', error));
    });

    btnClose.addEventListener('click', () => {
        console.log("Clicked CLOSE");
        fetch('/manual_control', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({ command: 'CLOSE' }) 
        })
        .then(response => {
            if (response.ok) {
                statusMessage.textContent = "Perintah TUTUP dikirim.";
                setTimeout(updateData, 500);
            }
        })
        .catch(error => console.error('Error sending CLOSE command:', error));
    });

    // Chart data type change listener
    chartDataTypeSelect.addEventListener('change', () => {
        updateData();
    });

    // Initial data load and periodic updates
    updateData();
    setInterval(updateData, 2000);
});