import os
import sys
import subprocess
import signal
import logging
from app.config_manager import load_config
from app.config_manager import config_root

logger = logging.getLogger("Pingpong")

def main():
    logger.info("Starting Pingpong Wrapper...")
    
    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    if str(config.get("ENABLE_PINGPONG", "false")).lower() != "true":
        logger.info("Pingpong is disabled in configuration. Exiting.")
        sys.exit(0)

    key = config.get("PINGPONG_KEY")
    if not key:
        logger.error("PINGPONG_KEY is missing in configuration.")
        sys.exit(1)

    binary_path = os.path.join(config_root(), "PINGPONG")
    if not os.path.exists(binary_path):
        logger.error(f"Pingpong binary not found at {binary_path}")
        sys.exit(1)

    # Ensure executable
    try:
        os.chmod(binary_path, 0o755)
    except Exception as e:
        logger.warning(f"Could not chmod binary: {e}")

    cmd = [binary_path, f"--key={key}"]
    logger.info("Launching Pingpong...")
    
    # Run process
    # We run unbuffered to ensure logs flow to journalctl
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=config_root()
    )

    def handle_sigterm(signum, frame):
        logger.info("Received SIGTERM, stopping Pingpong...")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    # Stream logs
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.strip(), flush=True)
    except Exception as e:
        logger.error(f"Error reading process output: {e}")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
        logger.info("Pingpong wrapper exited.")

if __name__ == "__main__":
    main()
