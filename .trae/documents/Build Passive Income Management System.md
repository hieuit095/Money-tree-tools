# Money Tree Tools - Passive Income Management System Plan

This plan outlines the creation of a centralized, lightweight Python management tool for Ubuntu Server (low-spec optimization) to manage passive income Docker containers.

## 1. Project Structure
We will create a modular Flask application.
```text
Money-tree-tools/
├── app/
│   ├── __init__.py
│   ├── main.py              # Flask Application Entry Point
│   ├── system_monitor.py    # psutil wrapper for CPU/RAM/Net/Temp
│   ├── docker_manager.py    # docker-py wrapper & compose handling
│   ├── config_manager.py    # .env file handler
│   └── templates/
│       └── dashboard.html   # Main Dashboard UI
├── scripts/
│   ├── optimize_system.py   # Task 1: System Optimization Logic
│   └── install_docker.sh    # Helper for Docker installation
├── docker-compose.yml       # Task 2: Service Definitions
├── requirements.txt         # Python dependencies
├── setup.sh                 # Task 4: Automation Script
└── income-manager.service   # Systemd Service File
```

## 2. Implementation Steps

### Phase 1: System Optimization (Task 1)
Create `scripts/optimize.py` to perform the following (requires root):
*   **Swap:** Check for `/swapfile`. If missing, create 1GB file using `fallocate`, `chmod`, `mkswap`, `swapon`. Add to `/etc/fstab`.
*   **ZRAM:** Install `zram-config` or manually configure ZRAM via modprobe/sysctl if package unavailable.
*   **Sysctl:** Set `vm.swappiness=10` in `/etc/sysctl.conf` and apply live.

### Phase 2: Docker Composition & Configuration (Task 2)
*   **`docker-compose.yml`:** Define services (EarnApp, Honeygain, Grass, TraffMonetizer, Uprock, Earn.fm, PacketStream, Repocket, PacketShare).
    *   Use environment variables (e.g., `${EARNAPP_ID}`) for user inputs.
    *   Configure logging: `driver: "json-file", options: { "max-size": "5m", "max-file": "1" }`.
*   **`app/config_manager.py`:** Functions to read existing `.env` and write new values from the Web UI form.

### Phase 3: Backend & Monitor (Task 3 & Core)
*   **`app/system_monitor.py`:**
    *   `get_cpu_usage()`: User % + Temp (try `/sys/class/thermal/thermal_zone0/temp`).
    *   `get_ram_usage()`: Total, Used, Percent, Swap usage.
    *   `get_network_speed()`: Calculate delta of `psutil.net_io_counters()` over 1 second.
*   **`app/docker_manager.py`:**
    *   List containers with status (Up/Exited) and RAM usage (`stats` stream or on-demand inspection).
    *   Start/Stop/Restart functions wrapping `docker-compose` commands or `docker-py` controls.
*   **`app/main.py`:**
    *   Flask routes: `/` (Dashboard), `/api/stats` (JSON), `/api/containers` (JSON), `/save-config` (POST), `/control/<action>/<service>` (POST).

### Phase 4: Frontend (Task 3)
*   **`app/templates/dashboard.html`:**
    *   **Layout:** Dark mode, responsive grid (Tailwind CSS).
    *   **Widgets:**
        *   CPU/RAM Radial or Bar charts.
        *   Network Up/Down textual display.
        *   Service Cards: Status indicator (Green/Red), RAM usage, Start/Stop toggle.
        *   Config Section: Collapsible form for API Tokens/IDs.
    *   **Logic:**
        *   `HTMX` for form handling (Save Config, Start/Stop actions).
        *   Vanilla JS `setInterval` (3s) to fetch `/api/stats` and `/api/containers` to update DOM without reload.

### Phase 5: Automation (Task 4)
*   **`setup.sh`:**
    *   Update apt & install `docker.io`, `docker-compose-v2`, `python3-venv`, `python3-pip`.
    *   Create venv, install `requirements.txt`.
    *   Run `scripts/optimize.py`.
    *   Copy `income-manager.service` to `/etc/systemd/system/`.
    *   Enable and start the service.

## 3. Tech Stack
*   **Language:** Python 3
*   **Web Framework:** Flask
*   **System Libs:** `psutil`, `docker` (Python SDK)
*   **Frontend:** HTML5, Tailwind CSS (CDN), HTMX, JavaScript
*   **OS Target:** Ubuntu Server (Linux)
