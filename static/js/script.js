// Generate Pairing Code
async function generateCode() {
    const sessionId = document.getElementById('sessionId').value.trim();
    const deviceInfo = document.getElementById('deviceInfo').value.trim();
    const resultDiv = document.getElementById('result');
    
    if (!sessionId) {
        alert('Please enter your Session ID');
        return;
    }
    
    if (!sessionId.startsWith('Nexty~')) {
        alert('Session ID must start with "Nexty~"');
        return;
    }
    
    try {
        const payload = {
            session_id: sessionId
        };
        
        if (deviceInfo) {
            try {
                payload.device_info = JSON.parse(deviceInfo);
            } catch (e) {
                alert('Invalid JSON in device info');
                return;
            }
        }
        
        const response = await fetch('/api/generate-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('generatedCode').textContent = data.code;
            document.getElementById('resultSessionId').textContent = data.session_id;
            document.getElementById('codeMessage').textContent = data.message;
            resultDiv.style.display = 'block';
            resultDiv.scrollIntoView({ behavior: 'smooth' });
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Network error: ' + error.message);
    }
}

// Pair Device
async function pairDevice() {
    const pairingCode = document.getElementById('pairingCode').value.trim();
    const sessionId = document.getElementById('pairSessionId').value.trim();
    const resultDiv = document.getElementById('pairResult');
    
    if (!pairingCode || !sessionId) {
        alert('Please enter both pairing code and session ID');
        return;
    }
    
    if (!sessionId.startsWith('Nexty~')) {
        alert('Session ID must start with "Nexty~"');
        return;
    }
    
    try {
        const response = await fetch('/api/pair-device', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                pairing_code: pairingCode,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('pairResultTitle').textContent = 'Success!';
            document.getElementById('pairResultTitle').style.color = 'green';
            document.getElementById('pairResultMessage').textContent = data.message;
            document.getElementById('pairedWithSession').textContent = data.paired_with;
            document.getElementById('connectionId').textContent = data.connection_id;
            document.getElementById('pairSuccessInfo').style.display = 'block';
            resultDiv.style.display = 'block';
        } else {
            document.getElementById('pairResultTitle').textContent = 'Error';
            document.getElementById('pairResultTitle').style.color = 'red';
            document.getElementById('pairResultMessage').textContent = data.error;
            document.getElementById('pairSuccessInfo').style.display = 'none';
            resultDiv.style.display = 'block';
        }
        
        resultDiv.scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        alert('Network error: ' + error.message);
    }
}

// Check Status
async function checkStatus() {
    const sessionId = document.getElementById('statusSessionId').value.trim();
    const resultDiv = document.getElementById('statusResult');
    const refreshBtn = document.getElementById('refreshBtn');
    
    if (!sessionId) {
        alert('Please enter your Session ID');
        return;
    }
    
    if (!sessionId.startsWith('Nexty~')) {
        alert('Session ID must start with "Nexty~"');
        return;
    }
    
    try {
        const response = await fetch('/api/check-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayStatus(data);
            resultDiv.style.display = 'block';
            refreshBtn.style.display = 'inline-block';
            resultDiv.scrollIntoView({ behavior: 'smooth' });
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Network error: ' + error.message);
    }
}

function displayStatus(data) {
    const activeCodesList = document.getElementById('activeCodesList');
    const connectionsList = document.getElementById('connectionsList');
    
    // Display active codes
    if (data.active_codes && data.active_codes.length > 0) {
        activeCodesList.innerHTML = data.active_codes.map(code => `
            <div class="code-item">
                <strong>Code:</strong> ${code.code}<br>
                <strong>Status:</strong> ${code.paired ? 'Paired' : 'Active'}<br>
                ${code.paired_with ? `<strong>Paired with:</strong> ${code.paired_with}<br>` : ''}
                <strong>Created:</strong> ${new Date(code.created_at * 1000).toLocaleString()}
            </div>
        `).join('');
    } else {
        activeCodesList.innerHTML = '<p>No active pairing codes</p>';
    }
    
    // Display connections
    if (data.pairing_status && data.pairing_status.length > 0) {
        connectionsList.innerHTML = data.pairing_status.map(conn => `
            <div class="connection-item">
                <strong>Connected with:</strong> ${conn.paired_with}<br>
                <strong>Pairing Code:</strong> ${conn.pairing_code}<br>
                <strong>Connected at:</strong> ${new Date(conn.paired_at * 1000).toLocaleString()}
            </div>
        `).join('');
    } else {
        connectionsList.innerHTML = '<p>No active connections</p>';
    }
}

function refreshStatus() {
    checkStatus();
}

// Auto-refresh status every 30 seconds if status page is open
if (window.location.pathname === '/status') {
    setInterval(() => {
        const sessionId = document.getElementById('statusSessionId').value.trim();
        if (sessionId && document.getElementById('statusResult').style.display !== 'none') {
            checkStatus();
        }
    }, 30000);
          }
