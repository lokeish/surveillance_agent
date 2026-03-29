"""
Configuration management for the Motion-Triggered Recording Pipeline.

Loads settings from:
  1. config.yaml  - Pipeline settings (motion sensitivity, recording params, etc.)
  2. .env         - Camera credentials (RTSP URL, camera user/password)
"""

import os
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Tuple, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


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
class LoggingConfig:
    """Logging settings."""
    level: str = "INFO"
    log_to_file: bool = True
    log_file: str = "./logs/surveillance.log"


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration."""
    stream: StreamConfig = field(default_factory=StreamConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _build_rtsp_url(camera_user: str, camera_password: str, camera_ip: str,
                     port: int, stream_path: str) -> str:
    """Construct RTSP URL from components."""
    return f"rtsp://{camera_user}:{camera_password}@{camera_ip}:{port}{stream_path}"


def load_config(config_path: Optional[str] = None, env_path: Optional[str] = None) -> PipelineConfig:
    """
    Load pipeline configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to config.yaml (default: PROJECT_ROOT/config.yaml)
        env_path: Path to .env file (default: PROJECT_ROOT/.env)
    
    Returns:
        PipelineConfig with all settings loaded
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If required environment variables are missing
    """
    # Resolve paths
    if config_path is None:
        config_path = PROJECT_ROOT / "config.yaml"
    else:
        config_path = Path(config_path)

    if env_path is None:
        env_path = PROJECT_ROOT / ".env"
    else:
        env_path = Path(env_path)

    # Load environment variables
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded environment from: {env_path}")
    else:
        logger.warning(f"Environment file not found: {env_path}")

    # Validate required env vars
    camera_ip = os.getenv("TAPO_IP")
    camera_user = os.getenv("CAMERA_USER")
    camera_password = os.getenv("CAMERA_PASSWORD")

    if not all([camera_ip, camera_user, camera_password]):
        raise ValueError(
            "Missing required environment variables. Ensure these are set in .env:\n"
            "  TAPO_IP, CAMERA_USER, CAMERA_PASSWORD"
        )

    # Load YAML config
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}. Using defaults.")
        yaml_config = {}
    else:
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f) or {}
        logger.debug(f"Loaded config from: {config_path}")

    # Parse sections
    stream_cfg = yaml_config.get("stream", {})
    motion_cfg = yaml_config.get("motion", {})
    recording_cfg = yaml_config.get("recording", {})
    logging_cfg = yaml_config.get("logging", {})

    # Build stream config
    stream = StreamConfig(
        stream_path=stream_cfg.get("stream_path", "/stream1"),
        rtsp_port=stream_cfg.get("rtsp_port", 554),
        process_fps=stream_cfg.get("process_fps", 5),
        connection_timeout=stream_cfg.get("connection_timeout", 10),
        max_reconnect_attempts=stream_cfg.get("max_reconnect_attempts", 0),
        reconnect_delay=stream_cfg.get("reconnect_delay", 5),
    )

    # Build RTSP URL from env + config
    stream.rtsp_url = _build_rtsp_url(
        camera_user, camera_password, camera_ip,
        stream.rtsp_port, stream.stream_path
    )

    # Build motion config
    motion = MotionConfig(
        sensitivity=motion_cfg.get("sensitivity", 25),
        blur_kernel=motion_cfg.get("blur_kernel", 21),
        min_motion_area_pct=motion_cfg.get("min_motion_area_pct", 0.5),
        min_contour_area=motion_cfg.get("min_contour_area", 500),
    )

    # Build recording config
    ts_color = recording_cfg.get("timestamp_color", [255, 255, 255])
    bg_color = recording_cfg.get("timestamp_bg_color", [0, 0, 0])

    recording = RecordingConfig(
        output_dir=recording_cfg.get("output_dir", "./recordings"),
        codec=recording_cfg.get("codec", "mp4v"),
        file_extension=recording_cfg.get("file_extension", ".mp4"),
        pre_buffer_seconds=recording_cfg.get("pre_buffer_seconds", 3),
        post_buffer_seconds=recording_cfg.get("post_buffer_seconds", 10),
        max_recording_seconds=recording_cfg.get("max_recording_seconds", 300),
        timestamp_overlay=recording_cfg.get("timestamp_overlay", True),
        timestamp_font_scale=recording_cfg.get("timestamp_font_scale", 0.7),
        timestamp_position=recording_cfg.get("timestamp_position", "bottom-left"),
        timestamp_color=tuple(ts_color),
        timestamp_bg_color=tuple(bg_color),
    )

    # Build logging config
    log = LoggingConfig(
        level=logging_cfg.get("level", "INFO"),
        log_to_file=logging_cfg.get("log_to_file", True),
        log_file=logging_cfg.get("log_file", "./logs/surveillance.log"),
    )

    config = PipelineConfig(
        stream=stream,
        motion=motion,
        recording=recording,
        logging=log,
    )

    return config


def setup_logging(config: LoggingConfig) -> None:
    """Configure logging based on settings."""
    log_level = getattr(logging, config.level.upper(), logging.INFO)

    # Root logger format
    formatter = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)-24s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if config.log_to_file:
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        logger.debug(f"Logging to file: {log_path.absolute()}")
