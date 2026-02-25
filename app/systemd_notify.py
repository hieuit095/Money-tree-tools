import os
import socket
import threading
import time
from typing import Optional


def _notify(message: str) -> None:
    notify_socket = os.environ.get("NOTIFY_SOCKET")
    if not notify_socket:
        return

    address = notify_socket
    if address.startswith("@"):
        address = "\0" + address[1:]

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.sendto(message.encode("utf-8", errors="replace"), address)
    finally:
        sock.close()


def notify_ready() -> None:
    _notify("READY=1")
    _notify("STATUS=Running")


def start_watchdog_ping() -> Optional[threading.Thread]:
    watchdog_usec = os.environ.get("WATCHDOG_USEC", "").strip()
    watchdog_pid = os.environ.get("WATCHDOG_PID", "").strip()
    if not watchdog_usec.isdigit():
        return None
    if watchdog_pid and watchdog_pid.isdigit() and int(watchdog_pid) != os.getpid():
        return None

    interval_s = max(int(watchdog_usec) / 1_000_000 / 2, 1.0)

    def loop() -> None:
        while True:
            _notify("WATCHDOG=1")
            time.sleep(interval_s)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread
