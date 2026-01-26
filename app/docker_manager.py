import docker
import subprocess
import os

client = None

def get_client():
    global client
    if not client:
        try:
            client = docker.from_env()
        except Exception as e:
            print(f"Docker connection error: {e}")
    return client

def get_containers():
    cli = get_client()
    if not cli: return []
    
    containers = []
    try:
        # List all containers, even stopped ones
        for c in cli.containers.list(all=True):
            # Only include containers that are part of our stack? 
            # Or all containers? User said "Docker List", implied all relevant ones.
            # We can filter by label if we added one, but displaying all is safer for visibility.
            
            mem_usage = 0
            state = c.status
            
            # Fetch stats only if running to be fast
            if state == 'running':
                try:
                    # stream=False gets a snapshot
                    stats = c.stats(stream=False)
                    # memory_stats.usage is standard
                    mem_usage = stats.get('memory_stats', {}).get('usage', 0)
                except Exception:
                    pass
            
            containers.append({
                "id": c.short_id,
                "name": c.name,
                "status": state,
                "memory": mem_usage
            })
    except Exception as e:
        print(f"Error listing containers: {e}")
        
    return containers

def control_container(service_name, action):
    # Use docker-compose command for better integration with the stack
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    cmd = []
    if action == "start":
        cmd = ["docker", "compose", "up", "-d", service_name]
    elif action == "stop":
        cmd = ["docker", "compose", "stop", service_name]
    elif action == "restart":
        cmd = ["docker", "compose", "restart", service_name]
    else:
        return False, "Invalid action"

    try:
        subprocess.run(cmd, cwd=cwd, check=True)
        return True, "Success"
    except subprocess.CalledProcessError as e:
        return False, str(e)

def stop_all():
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        subprocess.run(["docker", "compose", "stop"], cwd=cwd, check=True)
        return True, "Success"
    except subprocess.CalledProcessError as e:
        return False, str(e)
