from flask import Flask, render_template, request, jsonify
import random
import string
import time
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-123')

# Simple storage
pairing_data = {}

def generate_code():
    return ''.join(random.choices(string.digits, k=6))

def generate_session():
    return f"Nexty~{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start-pairing', methods=['POST'])
def start_pairing():
    try:
        phone = request.form.get('phone_number', '').strip()
        
        if not phone:
            return render_template('index.html', error='Phone number required')
        
        if not phone.startswith('+'):
            phone = '+' + phone
        
        # Generate codes
        pair_code = generate_code()
        session_id = generate_session()
        
        # Store data
        pairing_data[phone] = {
            'pair_code': pair_code,
            'session_id': session_id,
            'created_at': time.time(),
            'status': 'waiting'
        }
        
        return render_template('pairing.html',
                             phone_number=phone,
                             pairing_code=pair_code,
                             session_id=session_id)
                             
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/check-status')
def check_status():
    try:
        phone = request.args.get('phone_number')
        
        if not phone or phone not in pairing_data:
            return jsonify({'error': 'Not found'}), 404
        
        data = pairing_data[phone]
        return jsonify({
            'status': data['status'],
            'pairing_code': data['pair_code'],
            'session_id': data['session_id']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Simple API routes
@app.route('/api/verify', methods=['POST'])
def api_verify():
    try:
        data = request.get_json()
        pair_code = data.get('pairing_code', '')
        phone = data.get('phone_number', '')
        
        # Find phone by pair code
        target_phone = None
        for ph, session_data in pairing_data.items():
            if session_data['pair_code'] == pair_code:
                target_phone = ph
                break
        
        if not target_phone:
            return jsonify({'error': 'Invalid code'}), 404
        
        pairing_data[target_phone]['status'] = 'scanning'
        
        return jsonify({
            'success': True,
            'session_id': pairing_data[target_phone]['session_id']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/connect', methods=['POST'])
def api_connect():
    try:
        data = request.get_json()
        pair_code = data.get('pairing_code', '')
        
        # Find phone by pair code
        target_phone = None
        for ph, session_data in pairing_data.items():
            if session_data['pair_code'] == pair_code:
                target_phone = ph
                break
        
        if not target_phone:
            return jsonify({'error': 'Invalid code'}), 404
        
        pairing_data[target_phone]['status'] = 'connected'
        
        return jsonify({
            'success': True,
            'phone': target_phone,
            'session_id': pairing_data[target_phone]['session_id']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/inbox')
def inbox():
    try:
        phone = request.args.get('phone')
        
        if not phone or phone not in pairing_data:
            return "Session not found", 404
        
        data = pairing_data[phone]
        
        return render_template('inbox.html',
                             phone_number=phone,
                             session_id=data['session_id'],
                             status=data['status'])
                             
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
