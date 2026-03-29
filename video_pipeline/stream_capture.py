"""
RTSP Stream Capture Module.

Handles connecting to the camera's RTSP stream, reading frames,
and automatic reconnection on failure.
"""

import os
import cv2
import time
import logging
import threading
import numpy as np
from typing import Optional, Tuple
from .config import StreamConfig

logger = logging.getLogger(__name__)


class StreamCapture:
    """
    Thread-safe RTSP stream reader with automatic reconnection.
    
    Uses a background thread to continuously grab frames from the RTSP stream,
    ensuring the main processing loop always gets the latest frame without
    building up a buffer lag.
    """

    def __init__(self, config: StreamConfig):
        self.config = config
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._frame_timestamp: float = 0.0
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._connected = False
        self._frame_count = 0
        self._fps: float = 0.0
        self._frame_width: int = 0
        self._frame_height: int = 0

    @property
    def is_connected(self) -> bool:
        """Whether the stream is currently connected."""
        return self._connected

    @property
    def frame_size(self) -> Tuple[int, int]:
        """Return (width, height) of the stream frames."""
        return (self._frame_width, self._frame_height)

    @property
    def fps(self) -> float:
        """Return the stream FPS."""
        return self._fps

    @property
    def frame_count(self) -> int:
        """Total number of frames grabbed since connection."""
        return self._frame_count

    def connect(self) -> bool:
        """
        Establish connection to the RTSP stream.
        
        Returns:
            True if connection was successful, False otherwise.
        """
        rtsp_url_safe = self.config.rtsp_url.split("@")[-1] if "@" in self.config.rtsp_url else self.config.rtsp_url
        logger.info(f"Connecting to RTSP stream: rtsp://****@{rtsp_url_safe}")

        # Set OpenCV RTSP transport to TCP (more reliable than UDP)
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

        self._cap = cv2.VideoCapture(self.config.rtsp_url, cv2.CAP_FFMPEG)

        if not self._cap.isOpened():
            logger.error("Failed to open RTSP stream")
            self._connected = False
            return False

        # Read stream properties
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 15.0
        self._frame_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._frame_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Verify we can actually read a frame
        ret, frame = self._cap.read()
        if not ret or frame is None:
            logger.error("Connected but failed to read initial frame")
            self._cap.release()
            self._connected = False
            return False

        with self._lock:
            self._frame = frame
            self._frame_timestamp = time.time()

        self._connected = True
        self._frame_count = 1
        logger.info(
            f"✅ Stream connected: {self._frame_width}x{self._frame_height} @ {self._fps:.1f} FPS"
        )
        return True

    def start(self) -> bool:
        """
        Start the background frame-grabbing thread.
        
        Returns:
            True if started successfully.
        """
        if not self._connected:
            if not self.connect():
                return False

        self._running = True
        self._thread = threading.Thread(target=self._grab_loop, daemon=True, name="StreamCapture")
        self._thread.start()
        logger.info("Background frame grabber started")
        return True

    def stop(self) -> None:
        """Stop the frame-grabbing thread and release resources."""
        logger.info("Stopping stream capture...")
        self._running = False

        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        self._connected = False
        logger.info("Stream capture stopped")

    def read(self) -> Tuple[bool, Optional[np.ndarray], float]:
        """
        Read the latest frame from the stream.
        
        Returns:
            Tuple of (success, frame, timestamp):
                - success: True if a valid frame is available
                - frame: The latest frame as numpy array (BGR), or None
                - timestamp: Unix timestamp when the frame was grabbed
        """
        with self._lock:
            if self._frame is None:
                return False, None, 0.0
            return True, self._frame.copy(), self._frame_timestamp

    def _grab_loop(self) -> None:
        """
        Background loop that continuously grabs frames from the RTSP stream.
        
        This ensures we always have the latest frame available and prevents
        the OpenCV buffer from building up stale frames.
        """
        consecutive_failures = 0
        max_consecutive_failures = 30  # ~1 second of failures at 30fps

        while self._running:
            if self._cap is None or not self._cap.isOpened():
                self._handle_reconnection()
                continue

            ret, frame = self._cap.read()

            if ret and frame is not None:
                with self._lock:
                    self._frame = frame
                    self._frame_timestamp = time.time()
                self._frame_count += 1
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(
                        f"Stream read failed {consecutive_failures} times consecutively. Reconnecting..."
                    )
                    self._connected = False
                    self._handle_reconnection()
                    consecutive_failures = 0

        logger.debug("Frame grab loop exited")

    def _handle_reconnection(self) -> None:
        """Handle stream reconnection with configurable retry logic."""
        attempt = 0
        max_attempts = self.config.max_reconnect_attempts

        while self._running:
            attempt += 1

            if max_attempts > 0 and attempt > max_attempts:
                logger.error(f"Max reconnection attempts ({max_attempts}) reached. Giving up.")
                self._running = False
                return

            logger.info(
                f"Reconnection attempt {attempt}"
                + (f"/{max_attempts}" if max_attempts > 0 else "")
                + f" in {self.config.reconnect_delay}s..."
            )

            time.sleep(self.config.reconnect_delay)

            # Release old connection
            if self._cap is not None:
                self._cap.release()

            if self.connect():
                logger.info("✅ Reconnection successful!")
                return

            logger.warning(f"Reconnection attempt {attempt} failed")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
