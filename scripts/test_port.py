import socket
import sys

ip = "192.168.1.18"
port = 22

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
try:
    s.connect((ip, port))
    print(f"Port {port} on {ip} is OPEN")
    s.close()
except Exception as e:
    print(f"Port {port} on {ip} is CLOSED or UNREACHABLE: {e}")
