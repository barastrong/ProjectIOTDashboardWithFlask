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

    if (hamburger && sidebar) {
        hamburger.addEventListener('click', () => sidebar.classList.toggle('active'));
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 1024 && !sidebar.contains(e.target) && !hamburger.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
    }

    function createOrUpdateLineChart(data, dataType) {
        const ctx = document.getElementById('lineChart').getContext('2d');
        const labels = data.map(row => new Date(row.waktu).toLocaleTimeString()).reverse();
        const chartData = data.map(row => row[dataType]).reverse();
        const color = dataType === 'temperature' ? 'rgb(239, 68, 68)' : 'rgb(59, 130, 246)';
        
        if (lineChartInstance) lineChartInstance.destroy();
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
                    tension: 0.4
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    function updateData() {
        fetch('/data')
            .then(res => res.json())
            .then(data => {
                connectionDot.style.backgroundColor = '#10b981';
                connectionText.textContent = 'Online';

                if (data.latest) {
                    document.getElementById('current-waktu').textContent = data.latest.waktu;
                    document.getElementById('current-temperature').textContent = data.latest.temperature;
                    document.getElementById('current-humidity').textContent = data.latest.humidity;
                    document.getElementById('current-rain').textContent = data.latest.rain_value;
                    document.getElementById('current-ldr').textContent = data.latest.ldr_value;
                    document.getElementById('current-jemuran-status').textContent = data.latest.status_jemuran;
                }

                // LOGIKA TAMPILAN TOMBOL
                const sysStatus = data.flask_system_status;
                const currentMode = data.control_mode;

                // Reset Class
                btnAuto.classList.remove('active');
                btnManual.classList.remove('active');
                btnOff.classList.remove('active');
                
                // Styling tombol OFF biasa
                btnOff.style.backgroundColor = 'transparent';
                btnOff.style.color = '#ef4444';

                if (sysStatus === 'OFF' && currentMode === 'AUTO') {
                     // KASUS: DIMATIKAN
                     console.log("State: SYSTEM OFF");
                     btnOff.classList.add('active');
                     btnOff.style.backgroundColor = '#ef4444'; 
                     btnOff.style.color = 'white';
                     manualControls.style.display = 'none';
                     sidebarStatusText.textContent = "SISTEM MATI";
                     statusMessage.textContent = "Sistem dinonaktifkan. Sensor dan motor mati.";
                } 
                else if (currentMode === 'MANUAL') {
                    // KASUS: MANUAL
                    console.log("State: MANUAL");
                    btnManual.classList.add('active');
                    manualControls.style.display = 'flex';
                    sidebarStatusText.textContent = "MODE MANUAL";
                    statusMessage.textContent = "Kontrol manual aktif. Gunakan tombol di bawah.";
                } 
                else {
                    // KASUS: AUTO
                    console.log("State: AUTO");
                    btnAuto.classList.add('active');
                    manualControls.style.display = 'none';
                    sidebarStatusText.textContent = "MODE AUTO";
                    statusMessage.textContent = "Sistem berjalan otomatis menggunakan sensor.";
                }

                if (data.history) {
                    sensorDataTableBody.innerHTML = '';
                    data.history.forEach(row => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `<td>${row.waktu}</td><td>${row.temperature}</td><td>${row.humidity}</td><td>${row.rain_value}</td><td>${row.ldr_value}</td><td>${row.status_jemuran}</td><td>${row.status_system}</td>`;
                        sensorDataTableBody.appendChild(tr);
                    });
                    createOrUpdateLineChart(data.history, chartDataTypeSelect.value);
                }
            })
            .catch(error => {
                connectionDot.style.backgroundColor = '#ef4444';
                connectionText.textContent = 'Offline';
            });
    }

    // LISTENER TOMBOL
    btnAuto.addEventListener('click', () => {
        console.log("Clicked AUTO");
        fetch('/set_mode', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ mode: 'AUTO' }) })
        .then(() => updateData());
    });

    btnManual.addEventListener('click', () => {
        console.log("Clicked MANUAL");
        fetch('/set_mode', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ mode: 'MANUAL' }) })
        .then(() => updateData());
    });

    btnOff.addEventListener('click', () => {
        console.log("Clicked MATIKAN");
        // Kita kirim mode OFF ke endpoint baru atau endpoint set_mode
        fetch('/set_mode', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ mode: 'OFF' }) })
        .then(() => updateData());
    });

    btnOpen.addEventListener('click', () => {
        fetch('/manual_control', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ command: 'OPEN' }) });
    });

    btnClose.addEventListener('click', () => {
        fetch('/manual_control', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ command: 'CLOSE' }) });
    });

    chartDataTypeSelect.addEventListener('change', updateData);
    setInterval(updateData, 2000);
    updateData();
});