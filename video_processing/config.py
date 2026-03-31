"""
Configuration management for Video Processing Module.

Loads settings from:
  1. config.yaml  - Video processing settings (face detection thresholds, etc.)
  2. .env         - API keys (OpenAI, etc.)
"""

import os
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Tuple
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class FaceDetectionConfig:
    """Face detection settings."""
    model_path: str = "video_processing/face_detection_yunet_2023mar.onnx"
    score_threshold: float = 0.5
    nms_threshold: float = 0.3
    top_k: int = 5000


@dataclass
class FaceRecognitionConfig:
    """Face recognition settings."""
    model_path: str = "video_processing/face_recognition_sface_2021dec.onnx"
    match_threshold: float = 0.36  # Cosine similarity threshold
    known_faces_dir: str = "video_processing/known_faces"


@dataclass
class VideoAnalysisConfig:
    """Video analysis settings."""
    sample_interval_seconds: int = 2  # Sample every N seconds
    max_frames_per_analysis: int = 10  # Max frames to send to AI
    resize_width: int = 640
    resize_height: int = 480
    ai_model: str = "gpt-4o"
    ai_detail_level: str = "low"  # low, high, or auto


@dataclass
class WhatsAppNotificationConfig:
    """WhatsApp notification settings."""
    enabled: bool = False
    target_number: str = ""
    channel: str = "whatsapp"
    send_on_trigger: bool = True  # Send alert when triggers detected


@dataclass
class VideoProcessingConfig:
    """Top-level video processing configuration."""
    face_detection: FaceDetectionConfig = field(default_factory=FaceDetectionConfig)
    face_recognition: FaceRecognitionConfig = field(default_factory=FaceRecognitionConfig)
    video_analysis: VideoAnalysisConfig = field(default_factory=VideoAnalysisConfig)
    whatsapp_notification: WhatsAppNotificationConfig = field(default_factory=WhatsAppNotificationConfig)
    openai_api_key: str = ""


def load_config(config_path: Optional[str] = None, env_path: Optional[str] = None) -> VideoProcessingConfig:
    """
    Load video processing configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to config.yaml (default: PROJECT_ROOT/config.yaml)
        env_path: Path to .env file (default: PROJECT_ROOT/.env)
    
    Returns:
        VideoProcessingConfig with all settings loaded
    
    Raises:
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

    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_api_key:
        logger.warning("OPENAI_API_KEY not found in environment. AI analysis will not work.")

    # Load YAML config
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}. Using defaults.")
        yaml_config = {}
    else:
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f) or {}
        logger.debug(f"Loaded config from: {config_path}")

    # Parse video_processing section
    vp_config = yaml_config.get("video_processing", {})
    
    # Face detection config
    face_det_cfg = vp_config.get("face_detection", {})
    face_detection = FaceDetectionConfig(
        model_path=face_det_cfg.get("model_path", "video_processing/face_detection_yunet_2023mar.onnx"),
        score_threshold=face_det_cfg.get("score_threshold", 0.5),
        nms_threshold=face_det_cfg.get("nms_threshold", 0.3),
        top_k=face_det_cfg.get("top_k", 5000),
    )

    # Face recognition config
    face_rec_cfg = vp_config.get("face_recognition", {})
    face_recognition = FaceRecognitionConfig(
        model_path=face_rec_cfg.get("model_path", "video_processing/face_recognition_sface_2021dec.onnx"),
        match_threshold=face_rec_cfg.get("match_threshold", 0.36),
        known_faces_dir=face_rec_cfg.get("known_faces_dir", "video_processing/known_faces"),
    )

    # Video analysis config
    video_analysis_cfg = vp_config.get("video_analysis", {})
    video_analysis = VideoAnalysisConfig(
        sample_interval_seconds=video_analysis_cfg.get("sample_interval_seconds", 2),
        max_frames_per_analysis=video_analysis_cfg.get("max_frames_per_analysis", 10),
        resize_width=video_analysis_cfg.get("resize_width", 640),
        resize_height=video_analysis_cfg.get("resize_height", 480),
        ai_model=video_analysis_cfg.get("ai_model", "gpt-4o"),
        ai_detail_level=video_analysis_cfg.get("ai_detail_level", "low"),
    )

    # WhatsApp notification config
    whatsapp_cfg = vp_config.get("whatsapp_notification", {})
    
    # Get target number from environment variable or config
    whatsapp_target = os.getenv("WHATSAPP_TARGET_NUMBER", "")
    if not whatsapp_target:
        whatsapp_target = whatsapp_cfg.get("target_number", "")
    
    whatsapp_notification = WhatsAppNotificationConfig(
        enabled=whatsapp_cfg.get("enabled", False),
        target_number=whatsapp_target,
        channel=whatsapp_cfg.get("channel", "whatsapp"),
        send_on_trigger=whatsapp_cfg.get("send_on_trigger", True),
    )
    
    if whatsapp_notification.enabled and not whatsapp_notification.target_number:
        logger.warning("WhatsApp notifications enabled but no target number configured. "
                      "Set WHATSAPP_TARGET_NUMBER in .env or whatsapp_notification.target_number in config.yaml")

    config = VideoProcessingConfig(
        face_detection=face_detection,
        face_recognition=face_recognition,
        video_analysis=video_analysis,
        whatsapp_notification=whatsapp_notification,
        openai_api_key=openai_api_key,
    )

    return config
