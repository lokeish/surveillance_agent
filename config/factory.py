"""
Pipeline Configuration Factory.

Builds PipelineConfig dataclasses from Dynaconf settings and
resolved camera IP. Keeps config building logic clean and
separated from the DI container.
"""

import logging
from typing import Tuple

from dynaconf import Dynaconf

from network.camera_scanner import CameraScanner
from video_pipeline.config import (
    PipelineConfig,
    StreamConfig,
    MotionConfig,
    RecordingConfig,
)

logger = logging.getLogger(__name__)


class PipelineConfigFactory:
    """
    Builds PipelineConfig from Dynaconf settings + CameraScanner.

    Responsible for:
        1. Resolving camera IP (from config or auto-discovery)
        2. Validating camera credentials
        3. Mapping Dynaconf settings → dataclass configs
        4. Constructing the RTSP URL
    """

    def __init__(self, settings: Dynaconf, camera_scanner: CameraScanner) -> None:
        self._settings = settings
        self._camera_scanner = camera_scanner

    def build(self) -> PipelineConfig:
        """Build the complete PipelineConfig."""
        camera_ip = self._resolve_camera_ip()
        camera_user, camera_password = self._resolve_credentials()

        return PipelineConfig(
            stream=self._build_stream(camera_ip, camera_user, camera_password),
            motion=self._build_motion(),
            recording=self._build_recording(),
        )

    # ──────────────────────────────────────────────
    # Camera resolution
    # ──────────────────────────────────────────────

    def _resolve_camera_ip(self) -> str:
        """Resolve camera IP from config or auto-discovery."""
        camera_ip = self._camera_scanner.get_camera_ip()
        if not camera_ip:
            raise ValueError(
                "No camera IP available. Set SURVEILLANCE_CAMERA__IP in .env "
                "or ensure a camera is on the network for auto-discovery."
            )
        return camera_ip

    def _resolve_credentials(self) -> Tuple[str, str]:
        """Resolve and validate camera credentials."""
        camera_user = self._settings.get("camera.user", "")
        camera_password = self._settings.get("camera.password", "")

        if not camera_user or not camera_password:
            raise ValueError(
                "Missing camera credentials. Set SURVEILLANCE_CAMERA__USER and "
                "SURVEILLANCE_CAMERA__PASSWORD in .env"
            )
        return camera_user, camera_password

    # ──────────────────────────────────────────────
    # Config builders
    # ──────────────────────────────────────────────

    def _build_stream(self, camera_ip: str, user: str, password: str) -> StreamConfig:
        """Build StreamConfig with RTSP URL."""
        cfg = self._settings.stream
        stream = StreamConfig(
            stream_path=cfg.get("stream_path", "/stream1"),
            rtsp_port=int(cfg.get("rtsp_port", 554)),
            process_fps=int(cfg.get("process_fps", 5)),
            connection_timeout=int(cfg.get("connection_timeout", 10)),
            max_reconnect_attempts=int(cfg.get("max_reconnect_attempts", 0)),
            reconnect_delay=int(cfg.get("reconnect_delay", 5)),
        )
        stream.rtsp_url = (
            f"rtsp://{user}:{password}@"
            f"{camera_ip}:{stream.rtsp_port}{stream.stream_path}"
        )
        return stream

    def _build_motion(self) -> MotionConfig:
        """Build MotionConfig."""
        cfg = self._settings.motion
        return MotionConfig(
            sensitivity=int(cfg.get("sensitivity", 25)),
            blur_kernel=int(cfg.get("blur_kernel", 21)),
            min_motion_area_pct=float(cfg.get("min_motion_area_pct", 0.5)),
            min_contour_area=int(cfg.get("min_contour_area", 500)),
        )

    def _build_recording(self) -> RecordingConfig:
        """Build RecordingConfig."""
        cfg = self._settings.recording
        ts_color = cfg.get("timestamp_color", [255, 255, 255])
        bg_color = cfg.get("timestamp_bg_color", [0, 0, 0])

        return RecordingConfig(
            output_dir=cfg.get("output_dir", "./recordings"),
            codec=cfg.get("codec", "mp4v"),
            file_extension=cfg.get("file_extension", ".mp4"),
            pre_buffer_seconds=int(cfg.get("pre_buffer_seconds", 3)),
            post_buffer_seconds=int(cfg.get("post_buffer_seconds", 10)),
            max_recording_seconds=int(cfg.get("max_recording_seconds", 300)),
            timestamp_overlay=bool(cfg.get("timestamp_overlay", True)),
            timestamp_font_scale=float(cfg.get("timestamp_font_scale", 0.7)),
            timestamp_position=cfg.get("timestamp_position", "bottom-left"),
            timestamp_color=tuple(ts_color),
            timestamp_bg_color=tuple(bg_color),
        )
