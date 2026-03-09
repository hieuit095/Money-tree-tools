import os
import subprocess
import threading
import time
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_current_version() -> Dict[str, str]:
    """Return info about the currently installed version."""
    try:
        local_hash = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL
        ).strip().decode('utf-8')
        commit_date = subprocess.check_output(
            ['git', 'log', '-1', '--format=%ci'], cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL
        ).strip().decode('utf-8')
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL
        ).strip().decode('utf-8')
        return {
            "hash": local_hash,
            "short_hash": local_hash[:7],
            "date": commit_date,
            "branch": branch
        }
    except Exception:
        return {"hash": "unknown", "short_hash": "unknown", "date": "", "branch": ""}

def check_for_updates() -> Dict[str, Any]:
    """Check if updates are available on origin/main."""
    try:
        # Fetch remote updates
        subprocess.check_output(['git', 'fetch'], stderr=subprocess.STDOUT, cwd=PROJECT_ROOT, timeout=30)

        # Get local HEAD hash
        local_hash = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=PROJECT_ROOT
        ).strip().decode('utf-8')

        # Identify remote branch (main or master fallback)
        remote_branch = 'origin/main'
        try:
            remote_hash = subprocess.check_output(
                ['git', 'rev-parse', 'origin/main'], cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL
            ).strip().decode('utf-8')
        except subprocess.CalledProcessError:
            remote_hash = subprocess.check_output(
                ['git', 'rev-parse', 'origin/master'], cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL
            ).strip().decode('utf-8')
            remote_branch = 'origin/master'

        status = "up-to-date"
        behind_count = 0
        changelog = []

        if local_hash != remote_hash:
            status = "update-available"
            # Commits behind
            try:
                count_output = subprocess.check_output(
                    ['git', 'rev-list', '--count', f'HEAD..{remote_branch}'],
                    cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL
                ).strip().decode('utf-8')
                behind_count = int(count_output) if count_output.isdigit() else 0
            except Exception:
                behind_count = 1

            # Changelog
            try:
                log_output = subprocess.check_output(
                    ['git', 'log', '--oneline', '--no-decorate', f'HEAD..{remote_branch}', '-n', '10'],
                    cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL
                ).strip().decode('utf-8')
                changelog = [line.strip() for line in log_output.splitlines() if line.strip()]
            except Exception:
                changelog = []

        return {
            "status": status,
            "local_hash": local_hash,
            "local_short": local_hash[:7],
            "remote_hash": remote_hash,
            "remote_short": remote_hash[:7],
            "behind_count": behind_count,
            "changelog": changelog,
            "branch": remote_branch
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def perform_update() -> Dict[str, Any]:
    """Perform git pull, submodule update, and pip install."""
    steps = []
    try:
        # 1. Stash any local changes
        try:
            subprocess.check_output(['git', 'stash'], stderr=subprocess.STDOUT, cwd=PROJECT_ROOT)
            steps.append("Local changes stashed")
        except Exception:
            pass

        # 2. Pull
        pull_out = subprocess.check_output(['git', 'pull', '--ff-only'], stderr=subprocess.STDOUT, cwd=PROJECT_ROOT).decode('utf-8')
        steps.append("Source code updated")

        # 3. Submodules
        try:
            subprocess.check_output(['git', 'submodule', 'update', '--init', '--recursive'], stderr=subprocess.STDOUT, cwd=PROJECT_ROOT)
            steps.append("Submodules updated")
        except Exception:
            pass

        # 4. Pip install requirements
        venv_pip = os.path.join(PROJECT_ROOT, 'venv', 'bin', 'pip')
        if not os.path.exists(venv_pip):
             venv_pip = os.path.join(PROJECT_ROOT, 'venv', 'Scripts', 'pip.exe')
        
        if os.path.exists(venv_pip):
            try:
                subprocess.check_output([venv_pip, 'install', '-r', 'requirements.txt'], stderr=subprocess.STDOUT, cwd=PROJECT_ROOT)
                steps.append("Dependencies updated")
            except Exception as e:
                steps.append(f"Pip error: {str(e)}")
        
        return {"status": "success", "message": "\n".join(steps)}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": e.output.decode('utf-8') if e.output else str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def schedule_restart():
    """Restarts the server by exiting. Systemd handles the restart."""
    def restart():
        time.sleep(2)
        os._exit(0)
    threading.Thread(target=restart).start()
