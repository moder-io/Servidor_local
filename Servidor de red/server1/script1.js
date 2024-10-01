document.getElementById('scanButton').addEventListener('click', () => {
    fetch('/scan')
        .then(response => response.json())
        .then(data => {
            const devicesDiv = document.getElementById('devices');
            devicesDiv.innerHTML = '<h2>Dispositivos Encontrados:</h2>';
            data.forEach(device => {
                devicesDiv.innerHTML += `<p>${device.ip} - ${device.hostname} (${device.state})</p>`;
            });
        })
        .catch(error => {
            console.error('Error al escanear la red:', error);
        });
});

document.getElementById('bandwidthButton').addEventListener('click', () => {
    fetch('/bandwidth')
        .then(response => response.json())
        .then(data => {
            const bandwidthDiv = document.getElementById('bandwidth');
            bandwidthDiv.innerHTML = '<h2>Uso de Ancho de Banda:</h2>';
            for (const [interface, stats] of Object.entries(data)) {
                bandwidthDiv.innerHTML += `<p>${interface}: ${stats.bytes_sent} bytes enviados, ${stats.bytes_recv} bytes recibidos</p>`;
            }
        })
        .catch(error => {
            console.error('Error al obtener el uso de ancho de banda:', error);
        });
});


document.getElementById('logsButton').addEventListener('click', () => {
    fetch('/logs')
        .then(response => response.text())
        .then(data => {
            const logsDiv = document.getElementById('logs');
            logsDiv.innerHTML = '<h2>Logs de Actividad:</h2>' + `<pre>${data}</pre>`;
        })
        .catch(error => {
            console.error('Error al obtener logs:', error);
        });
});


document.getElementById('networkProcessesButton').addEventListener('click', getNetworkProcesses);

function getNetworkProcesses() {
    fetch('/network_processes')
        .then(response => response.json())
        .then(data => {
            let htmlContent = '<h3>Procesos de Red Activos:</h3><table><tr><th>PID</th><th>Nombre</th><th>Estado</th><th>Dirección Local</th><th>Dirección Remota</th><th>Tipo</th></tr>';
            data.forEach(process => {
                htmlContent += `<tr>
                    <td>${process.pid}</td>
                    <td>${process.name}</td>
                    <td>${process.status}</td>
                    <td>${process.local_address}</td>
                    <td>${process.remote_address}</td>
                    <td>${process.type}</td>
                </tr>`;
            });
            htmlContent += '</table>';
            document.getElementById('networkProcesses').innerHTML = htmlContent;
        })
        .catch(error => {
            console.error('Error al obtener procesos de red:', error);
            document.getElementById('networkProcesses').innerHTML = `<p>Error: ${error.message}</p>`;
        });
}

document.getElementById('pingLatencyButton').addEventListener('click', getPingLatency);

function getPingLatency() {
    fetch('/ping_latency')
        .then(response => response.json())
        .then(data => {
            let htmlContent = '<h3>Ping y Latencia:</h3><ul>';
            for (const [host, latency] of Object.entries(data)) {
                htmlContent += `<li>${host}: ${latency} ms</li>`;
            }
            htmlContent += '</ul>';
            document.getElementById('pingLatency').innerHTML = htmlContent;
        })
        .catch(error => {
            console.error('Error al obtener ping y latencia:', error);
            document.getElementById('pingLatency').innerHTML = `<p>Error: ${error.message}</p>`;
        });
}