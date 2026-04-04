"""
Video Processing Module for Surveillance Agent.

This module provides face detection, recognition, and AI-powered analysis
of surveillance footage to identify and track individuals.
"""

from .face_detector import FaceDetector
from .face_recognizer import FaceRecognizer
from .video_analyzer import VideoAnalyzer
from .whatsapp_notifier import WhatsAppNotifier
from .config import VideoProcessingConfig, load_config

__all__ = [
    "FaceDetector",
    "FaceRecognizer", 
    "VideoAnalyzer",
    "WhatsAppNotifier",
    "VideoProcessingConfig",
    "load_config",
]
