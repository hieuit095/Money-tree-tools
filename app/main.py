from functools import wraps
from flask import Flask, render_template, jsonify, request, redirect, url_for, Response
from app.system_monitor import get_cpu_stats, get_memory_stats, get_network_stats
from app.docker_manager import get_containers, control_container, stop_all
from app.config_manager import load_config, save_config, get_required_fields, get_config_sections

app = Flask(__name__)

def check_auth(username, password):
    config = load_config()
    valid_user = config.get('WEB_USERNAME') or 'admin'
    valid_pass = config.get('WEB_PASSWORD') or 'admin'
    return username == valid_user and password == valid_pass

def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def dashboard():
    config = load_config()
    fields = get_required_fields()
    sections = get_config_sections()
    return render_template('dashboard.html', config=config, fields=fields, sections=sections)

@app.route('/api/stats')
@requires_auth
def stats():
    cpu = get_cpu_stats()
    mem = get_memory_stats()
    net = get_network_stats()
    return jsonify({
        "cpu": cpu,
        "memory": mem,
        "network": net
    })

@app.route('/api/containers')
@requires_auth
def containers():
    data = get_containers()
    return jsonify(data)

@app.route('/control/<action>/<service>', methods=['POST'])
@requires_auth
def control(action, service):
    if service == "all" and action == "stop":
        success, msg = stop_all()
    else:
        success, msg = control_container(service, action)
    
    if success:
        return jsonify({"status": "success", "message": msg})
    else:
        return jsonify({"status": "error", "message": msg}), 500

@app.route('/save-config', methods=['POST'])
@requires_auth
def save_configuration():
    data = request.form.to_dict()
    save_config(data)
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
