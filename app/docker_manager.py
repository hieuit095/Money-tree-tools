import docker
import subprocess
import os
from app.config_manager import load_config
from app.igm_paths import igm_root
from app.igm_mapping import IGM_SERVICES, build_igm_env, write_igm_temp_env_file
from app.log_utils import truncate_utf8_text
from app.proxy_manager import apply_proxy_configuration
from app.native_manager import is_systemd_unit_present, WIPTER_SYSTEMD_UNIT

client = None

COMPOSE_TIMEOUT_SECONDS = int(os.environ.get("MONEYTREE_DOCKER_COMPOSE_TIMEOUT", "1200") or "1200")

SERVICE_MAP = {
    "ENABLE_HONEYGAIN": "honeygain",
    "ENABLE_TRAFFMONETIZER": "traffmonetizer",
    "ENABLE_PACKETSTREAM": "packetstream",
    "ENABLE_PACKETSHARE": "packetshare",
    "ENABLE_REPOCKET": "repocket",
    "ENABLE_EARNFM": "earnfm",
    "ENABLE_GRASS": "grass",
    "ENABLE_MYSTERIUM": "mysterium",
    "ENABLE_PAWNS": "pawns",
    "ENABLE_PROXYRACK": "proxyrack",
    "ENABLE_BITPING": "bitping",
    "ENABLE_WIZARDGAIN": "wizardgain",
    "ENABLE_WIPTER": "wipter",
    "ENABLE_PEER2PROFIT": "peer2profit"
}

IGM_COMPOSE_FILES = [
    "compose/compose.yml",
    "compose/compose.unlimited.yml",
    "compose/compose.hosting.yml",
    "compose/compose.local.yml",
    "compose/compose.single.yml",
    "compose/compose.service.yml",
]

IGM_PROJECT_NAME = "moneytree-igm"


def _compose_file_args() -> list[str]:
    root = igm_root()
    args: list[str] = []
    for rel in IGM_COMPOSE_FILES:
        args.extend(["-f", os.path.join(root, rel)])
    return args


def _docker_compose(args: list[str], env_file: str) -> subprocess.CompletedProcess:
    cmd = ["docker", "compose", "--project-name", IGM_PROJECT_NAME, "--env-file", env_file] + _compose_file_args() + ["--profile", "ENABLED", "--profile", "DISABLED"] + args
    try:
        return subprocess.run(cmd, cwd=igm_root(), check=False, capture_output=True, text=True, timeout=COMPOSE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"docker compose timed out after {COMPOSE_TIMEOUT_SECONDS}s")


def get_client():
    global client
    if not client:
        try:
            client = docker.from_env(timeout=10)
        except Exception as e:
            print(f"Docker connection error: {e}")
    return client

def get_containers():
    cli = get_client()
    if not cli: return []
    
    containers = []
    try:
        for c in cli.containers.list(all=True):
            labels = getattr(c, "labels", {}) or {}
            if labels.get("project") not in {"standard", "proxy"}:
                continue
            service_name = labels.get("com.docker.compose.service") or c.name
            
            mem_usage = 0
            state = c.status
            exit_code = None
            state_error = None
            health = None
            
            # Fetch stats only if running to be fast
            if state == 'running':
                try:
                    # stream=False gets a snapshot
                    stats = c.stats(stream=False)
                    # memory_stats.usage is standard
                    mem_usage = stats.get('memory_stats', {}).get('usage', 0)
                except Exception:
                    pass
                try:
                    attrs = getattr(c, "attrs", {}) or {}
                    health = (((attrs.get("State") or {}).get("Health") or {}).get("Status"))
                except Exception:
                    pass
            else:
                try:
                    attrs = getattr(c, "attrs", {}) or {}
                    st = attrs.get("State") or {}
                    if isinstance(st, dict):
                        exit_code = st.get("ExitCode")
                        state_error = st.get("Error") or None
                        health = ((st.get("Health") or {}).get("Status"))
                except Exception:
                    pass
            
            containers.append({
                "id": c.short_id,
                "name": service_name,
                "container_name": c.name,
                "status": state,
                "exit_code": exit_code,
                "error": state_error,
                "health": health,
                "memory": mem_usage
            })
    except Exception as e:
        print(f"Error listing containers: {e}")
        
    return containers

def control_container(service_name, action):
    cli = get_client()
    if not cli:
        return False, "Docker client not available"

    if action not in {"start", "stop", "restart"}:
        return False, "Invalid action"

    def _get_target():
        try:
            return cli.containers.get(service_name)
        except docker.errors.NotFound:
            try:
                matches = cli.containers.list(all=True, filters={"label": f"com.docker.compose.service={service_name}"})
                if matches:
                    return matches[0]
            except Exception:
                pass
            raise

    try:
        container = _get_target()
        try:
            try:
                container.reload()
            except Exception:
                pass

            if service_name == "wipter" and action in {"start", "restart"}:
                state = (getattr(container, "attrs", {}) or {}).get("State") or {}
                status = (state.get("Status") or getattr(container, "status", "") or "").lower()
                exit_code = state.get("ExitCode")
                should_force_recreate = status in {"restarting", "exited", "dead"} or (
                    status != "running" and isinstance(exit_code, int) and exit_code != 0
                )
                if should_force_recreate:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass
                    raise docker.errors.NotFound("wipter force-recreate")

            if action == "start":
                container.start()
            elif action == "stop":
                container.stop(timeout=6)
            else:
                container.restart(timeout=6)
            return True, "Success"
        except docker.errors.NotFound:
            raise
        except Exception:
            pass
    except docker.errors.NotFound:
        config = load_config()
        env = build_igm_env(config)
        spec = IGM_SERVICES.get(service_name)
        if spec:
            env[spec.profile_var] = "ENABLED"
        env_file = write_igm_temp_env_file(env)
        try:
            if action == "start":
                result = _docker_compose(["up", "-d", "--force-recreate", service_name], env_file=env_file)
                if result.returncode == 0:
                    return True, "Success"
                return False, (result.stderr or result.stdout or "").strip() or "Failed to deploy container"
            if action == "stop":
                result = _docker_compose(["stop", service_name], env_file=env_file)
                if result.returncode == 0:
                    return True, "Success"
                msg = (result.stderr or result.stdout or "").strip()
                return True, msg or "Not running"
            result = _docker_compose(["restart", service_name], env_file=env_file)
            if result.returncode == 0:
                return True, "Success"
            return False, (result.stderr or result.stdout or "").strip() or "Failed to restart container"
        finally:
            if os.path.exists(env_file):
                os.remove(env_file)
    except Exception as e:
        return False, str(e)

    if action in {"start", "restart"}:
        try:
            stale = _get_target()
            stale.remove(force=True)
        except Exception:
            pass

    config = load_config()
    env = build_igm_env(config)
    spec = IGM_SERVICES.get(service_name)
    if spec:
        env[spec.profile_var] = "ENABLED"
    env_file = write_igm_temp_env_file(env)
    try:
        if action == "start":
            result = _docker_compose(["up", "-d", "--force-recreate", service_name], env_file=env_file)
            if result.returncode == 0:
                return True, "Success"
            return False, (result.stderr or result.stdout or "").strip() or "Failed to deploy container"
        if action == "stop":
            result = _docker_compose(["stop", service_name], env_file=env_file)
            if result.returncode == 0:
                return True, "Success"
            msg = (result.stderr or result.stdout or "").strip()
            return True, msg or "Not running"
        result = _docker_compose(["restart", service_name], env_file=env_file)
        if result.returncode == 0:
            return True, "Success"
        return False, (result.stderr or result.stdout or "").strip() or "Failed to restart container"
    finally:
        if os.path.exists(env_file):
            os.remove(env_file)

def stop_all():
    cli = get_client()
    if not cli:
        return False, "Docker client not available"
    try:
        for c in cli.containers.list(all=True):
            labels = getattr(c, "labels", {}) or {}
            project = (labels.get("project") or "").strip().lower()
            compose_project = (labels.get("com.docker.compose.project") or "").strip()
            managed = project in {"standard", "proxy"} or compose_project == IGM_PROJECT_NAME
            if not managed:
                continue
            if (getattr(c, "status", "") or "").lower() != "running":
                continue
            try:
                c.stop(timeout=6)
            except Exception:
                pass
        return True, "Success"
    except Exception as e:
        return False, str(e)

def apply_docker_configuration():
    """
    Reads the current configuration and starts/stops containers based on ENABLE_* flags.
    """
    config = load_config()
    results = []
    containers = get_containers()
    status_by_name = {c.get("name"): c.get("status") for c in containers if isinstance((c or {}).get("name"), str)}
    
    for enable_key, service_name in SERVICE_MAP.items():
        if service_name == "wipter" and is_systemd_unit_present(WIPTER_SYSTEMD_UNIT):
            results.append("wipter: docker -> skipped (native systemd service detected)")
            continue
        should_enable = config.get(enable_key, 'false').lower() == 'true'
        current_status = (status_by_name.get(service_name) or "").lower()
        
        if should_enable:
            if current_status == "running":
                results.append(f"{service_name}: start -> OK (already running)")
                continue
            success, msg = control_container(service_name, "start")
            action = "start"
        else:
            if current_status == "":
                results.append(f"{service_name}: stop -> OK (not installed)")
                continue
            if current_status not in {"running", "restarting", "paused", "created"}:
                results.append(f"{service_name}: stop -> OK (already stopped)")
                continue
            success, msg = control_container(service_name, "stop")
            action = "stop"
            
        results.append(f"{service_name}: {action} -> {'OK' if success else msg}")
        
    proxy_success, proxy_msg = apply_proxy_configuration(config)
    results.append(f"multi-proxy: {'OK' if proxy_success else 'ERROR'} -> {proxy_msg}")
    return results

def get_container_logs(service_name, tail=200):
    cli = get_client()
    if not cli: return "Docker client not available"
    
    try:
        try:
            container = cli.containers.get(service_name)
        except docker.errors.NotFound:
            matches = cli.containers.list(all=True, filters={"label": f"com.docker.compose.service={service_name}"})
            if not matches:
                raise
            container = matches[0]
        logs = container.logs(tail=tail).decode("utf-8", errors="replace")
        return truncate_utf8_text(logs, max_bytes=5 * 1024 * 1024)
    except docker.errors.NotFound:
        return f"Container '{service_name}' not found"
    except Exception as e:
        return f"Error getting logs: {str(e)}"
