import psutil
import time
import os

last_net_io = None
last_net_time = 0

def get_cpu_stats():
    # CPU usage
    usage = psutil.cpu_percent(interval=None)
    
    # Temp
    temp = 0.0
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            # Try common zones
            if 'cpu_thermal' in temps:
                temp = temps['cpu_thermal'][0].current
            elif 'thermal_zone0' in temps:
                temp = temps['thermal_zone0'][0].current
            # Fallback reading file directly if psutil fails on some embedded systems
            elif os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                     temp = int(f.read().strip()) / 1000.0
    except Exception:
        pass
        
    return {"usage": usage, "temp": temp}

def get_memory_stats():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "total": mem.total,
        "available": mem.available,
        "used": mem.used,
        "percent": mem.percent,
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_percent": swap.percent
    }

def get_network_stats():
    global last_net_io, last_net_time
    
    now = time.time()
    io = psutil.net_io_counters()
    
    if last_net_io is None:
        last_net_io = io
        last_net_time = now
        return {"up": 0, "down": 0}
        
    duration = now - last_net_time
    # Avoid extremely short durations causing spikes or div by zero
    if duration < 0.1: 
        return {"up": 0, "down": 0}
    
    sent_speed = (io.bytes_sent - last_net_io.bytes_sent) / duration
    recv_speed = (io.bytes_recv - last_net_io.bytes_recv) / duration
    
    last_net_io = io
    last_net_time = now
    
    return {"up": sent_speed, "down": recv_speed}
