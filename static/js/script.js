document.addEventListener('DOMContentLoaded', function() {
    const toggleSystemBtn = document.getElementById('toggle-system-btn');
    const systemStatusSpan = document.getElementById('system-status');
    const sensorDataTableBody = document.querySelector('#sensor-data-table tbody');

    function updateData() {
        fetch('/data')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Console log status sistem dari Flask
                console.log('Frontend received Flask system status:', data.flask_system_status);

                // Update latest sensor data (ini tetap dari database)
                if (data.latest) {
                    document.getElementById('current-waktu').textContent = data.latest.waktu;
                    document.getElementById('current-temperature').textContent = data.latest.temperature;
                    document.getElementById('current-humidity').textContent = data.latest.humidity;
                    document.getElementById('current-rain').textContent = data.latest.rain_value + (data.latest.rain_value === 0 ? " (Hujan)" : " (Tidak Hujan)");
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

                // Update system status display (ini dari status kontrol global Flask)
                const newSystemStatus = data.flask_system_status;
                systemStatusSpan.textContent = newSystemStatus;
                systemStatusSpan.classList.toggle('on', newSystemStatus === 'ON');
                systemStatusSpan.classList.toggle('off', newSystemStatus === 'OFF');

                toggleSystemBtn.textContent = (newSystemStatus === 'ON' ? 'MATIKAN SISTEM' : 'NYALAKAN SISTEM');
                toggleSystemBtn.classList.toggle('btn-off', newSystemStatus === 'ON');
                toggleSystemBtn.classList.toggle('btn-on', newSystemStatus === 'OFF');

                // Update table history data
                if (data.history) {
                    sensorDataTableBody.innerHTML = '';
                    data.history.forEach(row => {
                        if (row.status_system === 'ON') {
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
                        }
                    });
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
                // updateData akan memuat status terbaru dari Flask (flask_system_status)
                updateData(); 
            })
            .catch(error => {
                console.error('Error toggling system:', error);
                alert('Gagal mengubah status sistem: ' + error.message);
            });
        });

        updateData();
        setInterval(updateData, 5000);
    }
});