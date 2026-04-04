"""
Network Camera Scanner Module.

Discovers cameras on the local network by scanning for common
camera ports (especially RTSP ports 554 and 8554).

All configuration values (ports, timeouts, worker counts) are
injected via Dynaconf settings — no hardcoded values.
"""

import socket
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from dynaconf import Dynaconf

logger = logging.getLogger(__name__)


class CameraScanner:
    """
    Scans the local network to discover IP cameras.

    Configuration is injected via Dynaconf settings instance.
    Reads from the 'network' section of config.yaml:
        - camera_ports: Ports to check on each IP
        - rtsp_ports: Ports that indicate an RTSP camera
        - scan_timeout: Socket connection timeout
        - max_workers: Thread pool size for parallel scanning
        - ip_range_start / ip_range_end: IP range to scan
    """

    def __init__(self, settings: Dynaconf) -> None:
        """
        Initialize CameraScanner with injected Dynaconf settings.

        Args:
            settings: Dynaconf settings instance with 'network' section.
        """
        self._settings = settings

        # Read network config from Dynaconf
        network_cfg = settings.network
        self._camera_ports: List[int] = list(network_cfg.camera_ports)
        self._rtsp_ports: List[int] = list(network_cfg.rtsp_ports)
        self._scan_timeout: float = float(network_cfg.scan_timeout)
        self._max_workers: int = int(network_cfg.max_workers)
        self._ip_range_start: int = int(network_cfg.ip_range_start)
        self._ip_range_end: int = int(network_cfg.ip_range_end)

        logger.info(
            f"CameraScanner initialized: ports={self._camera_ports}, "
            f"rtsp_ports={self._rtsp_ports}, timeout={self._scan_timeout}s, "
            f"workers={self._max_workers}, range=.{self._ip_range_start}-.{self._ip_range_end}"
        )

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def scan(self) -> List[str]:
        """
        Scan the local network and return a list of discovered camera IPs.

        Returns:
            List of IP addresses that have RTSP-compatible ports open.
        """
        base_ip = self._get_base_ip()
        logger.info(f"🔍 Scanning network {base_ip}.0/24 for cameras...")
        cameras = self._scan_network(base_ip)

        if cameras:
            logger.info(f"📷 Detected {len(cameras)} camera(s): {cameras}")
        else:
            logger.warning("No cameras found on the local network.")

        return cameras

    def get_camera_ip(self) -> Optional[str]:
        """
        Resolve camera IP: use configured value if set, otherwise auto-discover.

        Checks settings.camera.ip first. If null/empty, performs network scan
        and returns the first discovered camera IP.

        Returns:
            Camera IP address string, or None if no camera found.
        """
        # Check if IP is explicitly configured
        configured_ip = self._settings.get("camera.ip")
        if configured_ip:
            logger.info(f"Using configured camera IP: {configured_ip}")
            return str(configured_ip)

        # Auto-discover via network scan
        logger.info("No camera IP configured — starting auto-discovery...")
        cameras = self.scan()

        if not cameras:
            logger.error(
                "❌ No cameras discovered on the network. "
                "Please set camera IP manually via SURVEILLANCE_CAMERA__IP in .env"
            )
            return None

        if len(cameras) > 1:
            logger.warning(
                f"⚠️ Multiple cameras found: {cameras}. Using first one: {cameras[0]}"
            )

        return cameras[0]

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    def _is_port_open(self, ip: str, port: int) -> bool:
        """
        Check if a TCP port is open on the given IP.

        Args:
            ip: IP address to check.
            port: TCP port number.

        Returns:
            True if the port is open, False otherwise.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._scan_timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _get_base_ip(self) -> str:
        """
        Detect the local network base IP (first 3 octets).

        Uses a UDP socket trick to discover the local IP address
        without actually sending any data.

        Returns:
            Base IP string (e.g., "192.168.1").
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()

        base_ip = ".".join(ip.split(".")[:3])
        logger.debug(f"Local network base IP: {base_ip}")
        return base_ip

    def _scan_ip(self, ip: str) -> Optional[str]:
        """
        Scan a single IP for camera-related open ports.

        Args:
            ip: IP address to scan.

        Returns:
            The IP address if it has RTSP ports open, None otherwise.
        """
        open_ports = []
        for port in self._camera_ports:
            if self._is_port_open(ip, port):
                open_ports.append(port)

        # Check if any RTSP ports are open — strong indicator of a camera
        if any(port in open_ports for port in self._rtsp_ports):
            logger.debug(f"[📷] Likely camera (RTSP) at: {ip} (open ports: {open_ports})")
            return ip

        return None

    def _scan_network(self, base_ip: str) -> List[str]:
        """
        Scan the full IP range in parallel using a thread pool.

        Args:
            base_ip: First 3 octets of the network (e.g., "192.168.1").

        Returns:
            List of IP addresses that appear to be cameras.
        """
        found: List[str] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = []
            for i in range(self._ip_range_start, self._ip_range_end):
                ip = f"{base_ip}.{i}"
                futures.append(executor.submit(self._scan_ip, ip))

            for future in futures:
                result = future.result()
                if result:
                    found.append(result)

        return found
