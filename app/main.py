import os
import sys
import time
import threading
import subprocess
from functools import wraps
from flask import Flask, render_template, jsonify, request, redirect, url_for, Response
from app.system_monitor import get_cpu_stats, get_memory_stats, get_network_stats
from app.docker_manager import (
    control_container,
    get_container_logs,
    get_containers,
    stop_all,
    SERVICE_MAP,
)
from app.native_manager import (
    control_uprock,
    control_wipter,
    get_uprock_details,
    get_uprock_logs,
    get_wipter_details,
    get_wipter_logs,
    is_systemd_unit_present,
    WIPTER_SYSTEMD_UNIT,
    control_pingpong,
    get_pingpong_details,
    get_pingpong_logs,
    PINGPONG_SYSTEMD_UNIT,
)
from app.config_manager import load_config, save_config, get_required_fields, get_config_sections
from app import zram_manager
from app.watchdog import start_watchdog
from app.load_guard import start_load_guard
from app.priority_manager import effective_priority_services, serialize_priority_services
from app.systemd_notify import notify_ready, start_watchdog_ping
from app.log_utils import parse_tail
from app.runtime_state import load_last_apply
from app.apply_manager import get_apply_status, start_apply

app = Flask(__name__)

def check_auth(username, password):
    config = load_config()
    valid_user = config.get('WEB_USERNAME') or 'admin'
    valid_pass = config.get('WEB_PASSWORD') or 'admin'
    
    # Debug logging for auth failures
    if username != valid_user or password != valid_pass:
        print(f"Auth Failed: Received user='{username}', pass='***'", flush=True)
        # print(f"Expected: user='{valid_user}', pass='{valid_pass}'", flush=True) # Uncomment for deep debug
        
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
    last_apply = load_last_apply()
    return render_template('dashboard.html', config=config, fields=fields, sections=sections, last_apply=last_apply)


@app.route("/api/apply/status")
@requires_auth
def apply_status():
    return jsonify(get_apply_status())

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
    config = load_config()
    priority = effective_priority_services(config)
    enable_by_name = {
        "honeygain": "ENABLE_HONEYGAIN",
        "traffmonetizer": "ENABLE_TRAFFMONETIZER",
        "packetstream": "ENABLE_PACKETSTREAM",
        "packetshare": "ENABLE_PACKETSHARE",
        "repocket": "ENABLE_REPOCKET",
        "earnfm": "ENABLE_EARNFM",
        "grass": "ENABLE_GRASS",
        "mysterium": "ENABLE_MYSTERIUM",
        "pawns": "ENABLE_PAWNS",
        "proxyrack": "ENABLE_PROXYRACK",
        "bitping": "ENABLE_BITPING",
        "wizardgain": "ENABLE_WIZARDGAIN",
        "wipter": "ENABLE_WIPTER",
        "peer2profit": "ENABLE_PEER2PROFIT",
    }

    data = []
    for item in get_containers():
        name = (item or {}).get("name")
        if isinstance(name, str):
            enable_key = enable_by_name.get(name)
            if enable_key:
                item["enabled"] = config.get(enable_key, "false").lower() == "true"
            else:
                item["enabled"] = None
            item["priority"] = name.strip().lower() in priority
        item["status_raw"] = item.get("status")
        data.append(item)

    if is_systemd_unit_present(WIPTER_SYSTEMD_UNIT):
        wipter = get_wipter_details()
        wipter["enabled"] = config.get("ENABLE_WIPTER", "false").lower() == "true"
        wipter["priority"] = "wipter" in priority
        wipter["status_raw"] = wipter.get("status")
        data.append(wipter)

    uprock = get_uprock_details()
    uprock["enabled"] = config.get("ENABLE_UPROCK", "false").lower() == "true"
    uprock["priority"] = "uprock" in priority
    uprock["status_raw"] = uprock.get("status")
    data.append(uprock)

    pingpong = get_pingpong_details()
    pingpong["enabled"] = config.get("ENABLE_PINGPONG", "false").lower() == "true"
    pingpong["priority"] = "pingpong" in priority
    pingpong["status_raw"] = pingpong.get("status")
    data.append(pingpong)

    return jsonify(data)


@app.route("/api/system/priorities", methods=["GET"])
@requires_auth
def get_priorities():
    config = load_config()
    priority = sorted(effective_priority_services(config))
    return jsonify({"priority_services": priority})


@app.route("/api/system/priorities", methods=["POST"])
@requires_auth
def set_priority():
    payload = request.get_json(silent=True) or {}
    service = payload.get("service")
    enabled = payload.get("priority")
    if not isinstance(service, str) or not service.strip():
        return jsonify({"status": "error", "message": "Invalid service"}), 400
    if not isinstance(enabled, bool):
        return jsonify({"status": "error", "message": "Invalid priority value"}), 400

    name = service.strip().lower()
    allowed = set(SERVICE_MAP.values()) | {"uprock", "wipter", "pingpong"}
    if name not in allowed:
        return jsonify({"status": "error", "message": "Unknown service"}), 400

    config = load_config()
    current = set(effective_priority_services(config))
    if enabled:
        current.add(name)
    else:
        current.discard(name)

    save_config({"PRIORITY_SERVICES": serialize_priority_services(current)})
    return jsonify({"status": "success", "priority_services": sorted(current)})

@app.route('/control/<action>/<service>', methods=['POST'])
@requires_auth
def control(action, service):
    if service == "all" and action == "stop":
        success, msg = stop_all()
        control_wipter("stop")
        control_uprock("stop")
        control_pingpong("stop")
    elif service == "wipter":
        success, msg = control_wipter(action)
        if not success and "not installed" in (msg or "").lower():
            success, msg = control_container(service, action)
    elif service == "uprock":
        success, msg = control_uprock(action)
    elif service == "pingpong":
        success, msg = control_pingpong(action)
    else:
        success, msg = control_container(service, action)
    
    if success:
        return jsonify({"status": "success", "message": msg})
    else:
        return jsonify({"status": "error", "message": msg}), 500

@app.route('/api/logs/<service>')
@requires_auth
def get_logs(service):
    try:
        tail = parse_tail(request.args.get("tail"))
    except ValueError:
        return jsonify({"logs": "Invalid tail value"}), 400
    if service == "wipter":
        if is_systemd_unit_present(WIPTER_SYSTEMD_UNIT):
            logs = get_wipter_logs(tail=tail)
        else:
            logs = get_container_logs(service, tail=tail)
    elif service == "uprock":
        logs = get_uprock_logs(tail=tail)
    elif service == "pingpong":
        logs = get_pingpong_logs(tail=tail)
    else:
        logs = get_container_logs(service, tail=tail)
    return jsonify({"logs": logs})

@app.route('/save-config', methods=['POST'])
@requires_auth
def save_configuration():
    raw = request.form.to_dict(flat=False)
    data = {}
    for key, values in raw.items():
        if not values:
            continue
        if key.startswith("ENABLE_"):
            data[key] = "true" if "true" in values else "false"
        else:
            data[key] = values[-1]
    save_config(data)

    start_apply()
    
    return redirect(url_for('dashboard'))

@app.route('/api/check-update')
@requires_auth
def check_update():
    try:
        # Ensure we run git commands in the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Fetch remote updates
        subprocess.check_output(['git', 'fetch'], stderr=subprocess.STDOUT, cwd=project_root)
        
        # Get local and remote HEAD hashes
        local_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project_root).strip().decode('utf-8')
        remote_hash = subprocess.check_output(['git', 'rev-parse', 'origin/main'], cwd=project_root).strip().decode('utf-8')
        
        # Check if behind
        status = "up-to-date"
        if local_hash != remote_hash:
             status = "update-available"
             
        return jsonify({
            "status": status,
            "local_hash": local_hash,
            "remote_hash": remote_hash
        })
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "message": f"Git error: {e.output.decode('utf-8') if e.output else str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/perform-update', methods=['POST'])
@requires_auth
def perform_update():
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Pull updates
        output = subprocess.check_output(['git', 'pull'], stderr=subprocess.STDOUT, cwd=project_root).decode('utf-8')
        
        # Sync submodule
        output += "\n" + subprocess.check_output(['git', 'submodule', 'update', '--init', '--recursive'], stderr=subprocess.STDOUT, cwd=project_root).decode('utf-8')
        
        def restart_server():
            time.sleep(1)
            os._exit(0)
            
        threading.Thread(target=restart_server).start()
        
        return jsonify({"status": "success", "message": output})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "message": f"Update failed: {e.output.decode('utf-8') if e.output else str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/system/zram", methods=["GET"])
@requires_auth
def get_zram_settings():
    config = load_config()
    status = zram_manager.get_status()
    configured = config.get("ZRAM_SIZE_MB", "").strip()
    status["configured_size_mb"] = int(configured) if configured.isdigit() else None
    return jsonify(status)


@app.route("/api/system/zram", methods=["POST"])
@requires_auth
def set_zram_settings():
    payload = request.get_json(silent=True) or {}
    size_mb = payload.get("size_mb")
    try:
        validated = zram_manager.validate_zram_size_mb(size_mb)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid ZRAM size"}), 400

    save_config({"ZRAM_SIZE_MB": "" if validated is None else str(validated)})

    try:
        result = zram_manager.apply_size_mb(validated)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Start the watchdog service in a background thread
    # The check for WERKZEUG_RUN_MAIN ensures it doesn't run twice when debug mode is on
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        start_watchdog()
        start_load_guard()
        start_watchdog_ping()
        notify_ready()
        
    app.run(host='0.0.0.0', port=5000, debug=False)
