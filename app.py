from flask import Flask, render_template, request, jsonify
import random
import string
import time
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')

# Storage
active_codes = {}
paired_connections = {}
user_sessions = {}

def generate_pairing_code():
    return ''.join(random.choices(string.digits, k=6))

def cleanup_expired_codes():
    current_time = time.time()
    expired_codes = []
    
    for code, data in active_codes.items():
        if current_time - data['created_at'] > 600:  # 10 minutes
            expired_codes.append(code)
    
    for code in expired_codes:
        session_id = active_codes[code]['session_id']
        if session_id in user_sessions:
            user_sessions[session_id]['generated_codes'] = [
                c for c in user_sessions[session_id]['generated_codes'] 
                if c['code'] != code
            ]
        del active_codes[code]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate')
def generate_page():
    return render_template('generate.html')

@app.route('/pair')
def pair_page():
    return render_template('pair.html')

@app.route('/status')
def status_page():
    return render_template('status.html')

@app.route('/api/generate-code', methods=['POST'])
def api_generate_code():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        session_id = data.get('session_id', '').strip()
        device_info = data.get('device_info', {})
        
        if not session_id.startswith('Nexty~'):
            return jsonify({'error': 'Session ID must start with Nexty~'}), 400
        
        if len(session_id) < 10:
            return jsonify({'error': 'Invalid Session ID'}), 400
        
        cleanup_expired_codes()
        
        code = generate_pairing_code()
        attempts = 0
        while code in active_codes and attempts < 10:
            code = generate_pairing_code()
            attempts += 1
        
        if attempts >= 10:
            return jsonify({'error': 'Failed to generate code'}), 500
        
        active_codes[code] = {
            'session_id': session_id,
            'created_at': time.time(),
            'paired': False,
            'paired_with': None,
            'device_info': device_info
        }
        
        if session_id not in user_sessions:
            user_sessions[session_id] = {
                'generated_codes': [],
                'paired_connections': [],
                'created_at': time.time(),
                'last_active': time.time()
            }
        
        user_sessions[session_id]['generated_codes'].append({
            'code': code,
            'created_at': time.time(),
            'status': 'active'
        })
        user_sessions[session_id]['last_active'] = time.time()
        
        return jsonify({
            'success': True,
            'code': code,
            'session_id': session_id,
            'expires_in': 600,
            'message': 'Pairing code generated successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/pair-device', methods=['POST'])
def api_pair_device():
    try:
        data = request.get_json()
        pairing_code = data.get('pairing_code', '').strip()
        session_id = data.get('session_id', '').strip()
        
        if not pairing_code or not session_id:
            return jsonify({'error': 'Pairing code and Session ID required'}), 400
        
        if not session_id.startswith('Nexty~'):
            return jsonify({'error': 'Session ID must start with Nexty~'}), 400
        
        cleanup_expired_codes()
        
        if pairing_code not in active_codes:
            return jsonify({'error': 'Invalid pairing code'}), 404
        
        code_data = active_codes[pairing_code]
        
        if time.time() - code_data['created_at'] > 600:
            del active_codes[pairing_code]
            return jsonify({'error': 'Pairing code expired'}), 410
        
        if code_data['paired']:
            return jsonify({'error': 'Code already used'}), 409
        
        if code_data['session_id'] == session_id:
            return jsonify({'error': 'Cannot pair with yourself'}), 400
        
        code_data['paired'] = True
        code_data['paired_with'] = session_id
        code_data['paired_at'] = time.time()
        
        connection_id = f"{code_data['session_id']}_{session_id}"
        paired_connections[connection_id] = {
            'device1': code_data['session_id'],
            'device2': session_id,
            'pairing_code': pairing_code,
            'paired_at': time.time()
        }
        
        for sess_id in [code_data['session_id'], session_id]:
            if sess_id not in user_sessions:
                user_sessions[sess_id] = {
                    'generated_codes': [],
                    'paired_connections': [],
                    'created_at': time.time(),
                    'last_active': time.time()
                }
            user_sessions[sess_id]['paired_connections'].append(connection_id)
            user_sessions[sess_id]['last_active'] = time.time()
        
        return jsonify({
            'success': True,
            'message': 'Devices paired successfully!',
            'connection_id': connection_id,
            'paired_with': code_data['session_id']
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/check-status', methods=['POST'])
def api_check_status():
    try:
        data = request.get_json()
        session_id = data.get('session_id', '').strip()
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        if not session_id.startswith('Nexty~'):
            return jsonify({'error': 'Session ID must start with Nexty~'}), 400
        
        cleanup_expired_codes()
        
        active_session_codes = []
        for code, data in active_codes.items():
            if data['session_id'] == session_id:
                active_session_codes.append({
                    'code': code,
                    'created_at': data['created_at'],
                    'paired': data['paired'],
                    'paired_with': data['paired_with']
                })
        
        pairing_status = []
        for conn_id, conn_data in paired_connections.items():
            if conn_data['device1'] == session_id or conn_data['device2'] == session_id:
                partner = conn_data['device2'] if conn_data['device1'] == session_id else conn_data['device1']
                pairing_status.append({
                    'paired_with': partner,
                    'paired_at': conn_data['paired_at'],
                    'pairing_code': conn_data['pairing_code']
                })
        
        return jsonify({
            'session_id': session_id,
            'active_codes': active_session_codes,
            'pairing_status': pairing_status
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/stats')
def api_stats():
    cleanup_expired_codes()
    return jsonify({
        'active_codes': len(active_codes),
        'paired_connections': len(paired_connections),
        'user_sessions': len(user_sessions)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
