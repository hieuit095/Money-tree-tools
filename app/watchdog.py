import time
import threading
import logging
import urllib.request
from app.config_manager import load_config
from app.docker_manager import get_containers, control_container, SERVICE_MAP
from app.native_manager import control_uprock, control_wipter, get_uprock_details, get_wipter_details
from app.native_manager import is_systemd_unit_present, WIPTER_SYSTEMD_UNIT
from app.runtime_state import load_load_guard_state

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Watchdog")

def check_and_recover():
    """
    Check the status of all services and attempt to recover those that should be running.
    """
    logger.info("Watchdog cycle started: checking services status...")
    config = load_config()
    state = load_load_guard_state() or {}
    paused = set()
    raw_paused = state.get("paused") or []
    if isinstance(raw_paused, list):
        for item in raw_paused:
            if isinstance(item, str) and item.strip():
                paused.add(item.strip().lower())
    
    # 1. Check Docker Services
    containers = get_containers()
    container_dict = {c['name']: c['status'] for c in containers}
    
    for enable_key, service_name in SERVICE_MAP.items():
        if service_name == "wipter" and is_systemd_unit_present(WIPTER_SYSTEMD_UNIT):
            continue
        if service_name in paused:
            continue
        should_be_running = config.get(enable_key, 'false').lower() == 'true'
        current_status = container_dict.get(service_name)
        
        if should_be_running:
            if current_status != 'running':
                logger.warning(f"Service '{service_name}' should be running but is '{current_status}'. Attempting recovery...")
                success, msg = control_container(service_name, "start")
                if success:
                    logger.info(f"Successfully recovered service '{service_name}'.")
                else:
                    logger.error(f"Failed to recover service '{service_name}': {msg}")
            # else:
            #    logger.debug(f"Service '{service_name}' is running as expected.")
        else:
            if current_status == "running":
                logger.warning(f"Service '{service_name}' is running but is configured disabled. Stopping...")
                success, msg = control_container(service_name, "stop")
                if success:
                    logger.info(f"Successfully stopped service '{service_name}'.")
                else:
                    logger.error(f"Failed to stop service '{service_name}': {msg}")

    if config.get("ENABLE_MYSTERIUM", "false").lower() == "true" and container_dict.get("mysterium") == "running":
        try:
            with urllib.request.urlopen("http://127.0.0.1:4050/healthcheck", timeout=5) as resp:
                if getattr(resp, "status", 200) != 200:
                    raise RuntimeError(f"HTTP {getattr(resp, 'status', 'unknown')}")
        except Exception as exc:
            logger.warning(f"Service 'mysterium' healthcheck failed: {exc}. Restarting container...")
            success, msg = control_container("mysterium", "restart")
            if success:
                logger.info("Successfully restarted container 'mysterium' after failed healthcheck.")
            else:
                logger.error(f"Failed to restart container 'mysterium' after failed healthcheck: {msg}")

    should_be_running = config.get("ENABLE_WIPTER", "false").lower() == "true"
    wipter_status = get_wipter_details()["status"]
    if should_be_running and wipter_status != "running" and "wipter" not in paused:
        logger.warning(f"Service 'wipter' should be running but is '{wipter_status}'. Attempting recovery...")
        success, msg = control_wipter("start")
        if success:
            logger.info("Successfully recovered service 'wipter'.")
        else:
            logger.error(f"Failed to recover service 'wipter': {msg}")
    if not should_be_running and wipter_status == "running":
        logger.warning("Service 'wipter' is running but is configured disabled. Stopping...")
        success, msg = control_wipter("stop")
        if success:
            logger.info("Successfully stopped service 'wipter'.")
        else:
            logger.error(f"Failed to stop service 'wipter': {msg}")

    should_be_running = config.get("ENABLE_UPROCK", "false").lower() == "true"
    uprock_status = get_uprock_details()["status"]
    if should_be_running and uprock_status != "running" and "uprock" not in paused:
        logger.warning(f"Service 'uprock' should be running but is '{uprock_status}'. Attempting recovery...")
        success, msg = control_uprock("start")
        if success:
            logger.info("Successfully recovered service 'uprock'.")
        else:
            logger.error(f"Failed to recover service 'uprock': {msg}")
    if not should_be_running and uprock_status == "running":
        logger.warning("Service 'uprock' is running but is configured disabled. Stopping...")
        success, msg = control_uprock("stop")
        if success:
            logger.info("Successfully stopped service 'uprock'.")
        else:
            logger.error(f"Failed to stop service 'uprock': {msg}")

    logger.info("Watchdog cycle completed.")

def watchdog_loop(interval=300):
    """
    Infinite loop for the watchdog service.
    interval: time in seconds between checks (default 5 minutes)
    """
    logger.info(f"Watchdog service initialized with {interval}s interval.")
    # Initial wait to let the system settle during startup
    time.sleep(10)
    
    while True:
        try:
            check_and_recover()
        except Exception as e:
            logger.error(f"Error in watchdog loop: {e}")
        
        time.sleep(interval)

def start_watchdog():
    """
    Start the watchdog service in a background thread.
    """
    config = load_config()
    interval_str = str(config.get("WATCHDOG_INTERVAL_SEC", "")).strip()
    interval = int(interval_str) if interval_str.isdigit() else 300
    interval = max(interval, 30)
    thread = threading.Thread(target=watchdog_loop, args=(interval,), daemon=True)
    thread.start()
    return thread
