from flask import Flask, render_template, request, jsonify, session
import random
import string
import time
import threading
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'whatsapp-pair-bot-secret-2024'

# Storage for active pairing sessions
pairing_sessions = {}
connected_devices = {}

def generate_pairing_code():
    """6-digit pairing code like WhatsApp Web"""
    return ''.join(random.choices(string.digits, k=6))

def generate_session_id():
    """WhatsApp session ID generate"""
    return f"Nexty~{''.join(random.choices(string.ascii_letters + string.digits, k=20))}"

def cleanup_expired_sessions():
    """20 minutes purane sessions delete karega"""
    current_time = time.time()
    expired_sessions = []
    
    for phone, data in pairing_sessions.items():
        if current_time - data['created_at'] > 1200:  # 20 minutes
            expired_sessions.append(phone)
    
    for phone in expired_sessions:
        del pairing_sessions[phone]

# Background cleanup thread
def start_cleanup_thread():
    def cleanup_worker():
        while True:
            time.sleep(300)  # 5 minutes
            cleanup_expired_sessions()
    
    thread = threading.Thread(target=cleanup_worker, daemon=True)
    thread.start()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start-pairing', methods=['POST'])
def start_pairing():
    """Phone number se pairing start karega"""
    phone_number = request.form.get('phone_number', '').strip()
    
    if not phone_number:
        return render_template('index.html', error='Please enter phone number')
    
    # Phone number format check
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    # Cleanup old sessions
    cleanup_expired_sessions()
    
    # Generate pairing code and session
    pairing_code = generate_pairing_code()
    session_id = generate_session_id()
    
    # Store pairing session
    pairing_sessions[phone_number] = {
        'pairing_code': pairing_code,
        'session_id': session_id,
        'created_at': time.time(),
        'status': 'waiting',  # waiting, scanning, connected
        'qr_scanned': False,
        'device_connected': False,
        'last_updated': time.time()
    }
    
    # Session mein store karo
    session['phone_number'] = phone_number
    session['pairing_code'] = pairing_code
    session['session_id'] = session_id
    
    return render_template('pairing.html',
                         phone_number=phone_number,
                         pairing_code=pairing_code,
                         session_id=session_id)

@app.route('/check-pairing-status')
def check_pairing_status():
    """Real-time pairing status check"""
    phone_number = request.args.get('phone_number')
    
    if not phone_number or phone_number not in pairing_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_data = pairing_sessions[phone_number]
    
    return jsonify({
        'status': session_data['status'],
        'qr_scanned': session_data['qr_scanned'],
        'device_connected': session_data['device_connected'],
        'pairing_code': session_data['pairing_code'],
        'session_id': session_data['session_id'],
        'timestamp': time.time()
    })

# WhatsApp Bot API Routes
@app.route('/api/verify-pairing', methods=['POST'])
def api_verify_pairing():
    """WhatsApp bot pairing code verify karega"""
    data = request.get_json()
    pairing_code = data.get('pairing_code', '').strip()
    phone_number = data.get('phone_number', '').strip()
    
    if not pairing_code or not phone_number:
        return jsonify({'error': 'Pairing code and phone number required'}), 400
    
    # Find session by pairing code
    target_phone = None
    for phone, session_data in pairing_sessions.items():
        if session_data['pairing_code'] == pairing_code:
            target_phone = phone
            break
    
    if not target_phone:
        return jsonify({'error': 'Invalid pairing code'}), 404
    
    session_data = pairing_sessions[target_phone]
    
    # Update status to scanning
    session_data['status'] = 'scanning'
    session_data['qr_scanned'] = True
    session_data['last_updated'] = time.time()
    
    return jsonify({
        'success': True,
        'status': 'qr_scanned',
        'message': 'QR code scanned successfully',
        'session_id': session_data['session_id']
    })

@app.route('/api/confirm-connection', methods=['POST'])
def api_confirm_connection():
    """Device connection confirm karega"""
    data = request.get_json()
    pairing_code = data.get('pairing_code', '').strip()
    phone_number = data.get('phone_number', '').strip()
    
    if not pairing_code:
        return jsonify({'error': 'Pairing code required'}), 400
    
    # Find session by pairing code
    target_phone = None
    for phone, session_data in pairing_sessions.items():
        if session_data['pairing_code'] == pairing_code:
            target_phone = phone
            break
    
    if not target_phone:
        return jsonify({'error': 'Invalid pairing code'}), 404
    
    session_data = pairing_sessions[target_phone]
    
    # Update to connected
    session_data['status'] = 'connected'
    session_data['device_connected'] = True
    session_data['last_updated'] = time.time()
    
    # Store connected device
    connected_devices[target_phone] = {
        'session_id': session_data['session_id'],
        'connected_at': time.time(),
        'pairing_code': pairing_code
    }
    
    return jsonify({
        'success': True,
        'status': 'connected',
        'message': 'Device connected successfully',
        'session_id': session_data['session_id'],
        'phone_number': target_phone
    })

@app.route('/api/get-session', methods=['POST'])
def api_get_session():
    """Session ID get karega"""
    data = request.get_json()
    phone_number = data.get('phone_number', '').strip()
    pairing_code = data.get('pairing_code', '').strip()
    
    if not phone_number or not pairing_code:
        return jsonify({'error': 'Phone number and pairing code required'}), 400
    
    if phone_number not in pairing_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_data = pairing_sessions[phone_number]
    
    if session_data['pairing_code'] != pairing_code:
        return jsonify({'error': 'Invalid pairing code'}), 400
    
    return jsonify({
        'session_id': session_data['session_id'],
        'status': session_data['status'],
        'connected': session_data['device_connected']
    })

@app.route('/success')
def success():
    """Pairing successful page"""
    phone_number = request.args.get('phone')
    session_id = request.args.get('session_id')
    
    return render_template('success.html',
                         phone_number=phone_number,
                         session_id=session_id)

@app.route('/inbox')
def inbox():
    """Session ID inbox"""
    phone_number = request.args.get('phone')
    
    if not phone_number or phone_number not in pairing_sessions:
        return "Session not found", 404
    
    session_data = pairing_sessions[phone_number]
    
    return render_template('inbox.html',
                         phone_number=phone_number,
                         session_id=session_data['session_id'],
                         status=session_data['status'])

# Start cleanup thread
start_cleanup_thread()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
