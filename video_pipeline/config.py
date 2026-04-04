"""
Configuration dataclasses for the Motion-Triggered Recording Pipeline.

These are pure data containers — no config loading logic here.
Config loading is handled by Dynaconf (config/dynaconf.py) and
the DI container (container.py) builds these dataclasses from settings.
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class StreamConfig:
    """RTSP stream connection settings."""
    rtsp_url: str = ""
    stream_path: str = "/stream1"
    rtsp_port: int = 554
    process_fps: int = 5
    connection_timeout: int = 10
    max_reconnect_attempts: int = 0  # 0 = infinite
    reconnect_delay: int = 5


@dataclass
class MotionConfig:
    """Motion detection algorithm settings."""
    sensitivity: int = 25
    blur_kernel: int = 21
    min_motion_area_pct: float = 0.5
    min_contour_area: int = 500


@dataclass
class RecordingConfig:
    """Video recording and output settings."""
    output_dir: str = "./recordings"
    codec: str = "mp4v"
    file_extension: str = ".mp4"
    pre_buffer_seconds: int = 3
    post_buffer_seconds: int = 10
    max_recording_seconds: int = 300
    timestamp_overlay: bool = True
    timestamp_font_scale: float = 0.7
    timestamp_position: str = "bottom-left"
    timestamp_color: Tuple[int, int, int] = (255, 255, 255)
    timestamp_bg_color: Tuple[int, int, int] = (0, 0, 0)


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration."""
    stream: StreamConfig = field(default_factory=StreamConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
