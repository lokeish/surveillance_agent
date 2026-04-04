import socket
from concurrent.futures import ThreadPoolExecutor

COMMON_CAMERA_PORTS = [80, 554, 8080, 8000, 8899, 88, 8554, 37777]

def is_port_open(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)   # increased timeout
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def scan_ip(ip):
    open_ports = []
    for port in COMMON_CAMERA_PORTS:
        if is_port_open(ip, port):
            open_ports.append(port)

    if open_ports:
        print(f"[+] {ip} -> Open Ports: {open_ports}")

    # smarter detection
    if 554 in open_ports or 8554 in open_ports:
        print(f"[📷] Likely Camera (RTSP): {ip}")
        return ip

    return None

def scan_network(base_ip):
    found = []

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        for i in range(1, 255):
            ip = f"{base_ip}.{i}"
            futures.append(executor.submit(scan_ip, ip))

        for f in futures:
            result = f.result()
            if result:
                found.append(result)

    return found

def get_base_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't actually connect, just figures out local IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    base_ip = ".".join(ip.split(".")[:3])
    return base_ip

if __name__ == "__main__":
    base_ip = get_base_ip()
    cameras = scan_network(base_ip)

    print("\nDetected Cameras:", cameras)