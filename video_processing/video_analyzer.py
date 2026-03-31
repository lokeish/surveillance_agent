"""
Video Analyzer Module.

Analyzes surveillance videos for face detection, recognition, and AI-powered insights.
Integrates face detection, recognition, and OpenAI GPT-4 for activity analysis.
"""

import cv2
import base64
import logging
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime

from .face_detector import FaceDetector, DetectedFace
from .face_recognizer import FaceRecognizer, FaceMatch
from .config import VideoProcessingConfig
from .whatsapp_notifier import WhatsAppNotifier

logger = logging.getLogger(__name__)


@dataclass
class FrameAnalysis:
    """Analysis result for a single frame."""
    frame_idx: int
    timestamp: float
    faces: List[DetectedFace] = field(default_factory=list)
    face_matches: List[Optional[FaceMatch]] = field(default_factory=list)
    is_trigger: bool = False  # True if frame contains unknown/trigger faces


@dataclass
class VideoAnalysisResult:
    """Complete video analysis result."""
    video_path: str
    total_frames: int
    analyzed_frames: int
    trigger_frames: List[FrameAnalysis] = field(default_factory=list)
    ai_summary: Optional[str] = None
    analysis_duration: float = 0.0


class VideoAnalyzer:
    """
    Main video analyzer that orchestrates face detection, recognition,
    and AI-powered activity analysis.
    """

    def __init__(self, config: VideoProcessingConfig):
        """
        Initialize the video analyzer.
        
        Args:
            config: Video processing configuration
        """
        self.config = config

        # Initialize face detector
        logger.info("Initializing face detector...")
        self._detector = FaceDetector(
            model_path=config.face_detection.model_path,
            score_threshold=config.face_detection.score_threshold,
            nms_threshold=config.face_detection.nms_threshold,
            top_k=config.face_detection.top_k,
        )

        # Initialize face recognizer
        logger.info("Initializing face recognizer...")
        self._recognizer = FaceRecognizer(
            model_path=config.face_recognition.model_path,
            match_threshold=config.face_recognition.match_threshold,
            known_faces_dir=config.face_recognition.known_faces_dir,
        )

        # OpenAI client (lazy initialization)
        self._openai_client = None

        # Initialize WhatsApp notifier if enabled
        self._whatsapp_notifier = None
        if config.whatsapp_notification.enabled:
            if config.whatsapp_notification.target_number:
                self._whatsapp_notifier = WhatsAppNotifier(
                    target_number=config.whatsapp_notification.target_number,
                    channel=config.whatsapp_notification.channel,
                )
                logger.info(f"  WhatsApp notifications enabled for {config.whatsapp_notification.target_number}")
            else:
                logger.warning("  WhatsApp notifications enabled but no target number configured")

        logger.info("Video analyzer initialized")
        logger.info(f"  Known faces loaded: {self._recognizer.known_faces_count}")

    def analyze_video(self, video_path: str, use_ai_summary: bool = True) -> VideoAnalysisResult:
        """
        Analyze a video file for faces and activities.
        
        Args:
            video_path: Path to video file
            use_ai_summary: Whether to generate AI summary of trigger events
        
        Returns:
            VideoAnalysisResult with complete analysis
        """
        start_time = datetime.now()
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info("=" * 60)
        logger.info(f"  🎥 ANALYZING VIDEO: {video_path.name}")
        logger.info("=" * 60)

        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_interval = int(fps * self.config.video_analysis.sample_interval_seconds)

        logger.info(f"Video info: {total_frames} frames @ {fps:.1f} FPS")
        logger.info(f"Sampling every {self.config.video_analysis.sample_interval_seconds}s "
                   f"({sample_interval} frames)")

        # Analyze frames
        trigger_frames = []
        analyzed_count = 0
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Sample frames at configured interval
            if frame_idx % sample_interval == 0:
                analysis = self._analyze_frame(frame, frame_idx, frame_idx / fps)
                analyzed_count += 1

                if analysis.is_trigger:
                    trigger_frames.append(analysis)
                    logger.info(f"🔔 Frame {frame_idx}: Trigger detected "
                              f"({len(analysis.faces)} face(s))")

            frame_idx += 1

        cap.release()

        logger.info(f"Analysis complete: {analyzed_count} frames analyzed, "
                   f"{len(trigger_frames)} trigger frames found")

        # Generate AI summary if requested
        ai_summary = None
        if use_ai_summary and trigger_frames:
            ai_summary = self._generate_ai_summary(video_path, trigger_frames)

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        result = VideoAnalysisResult(
            video_path=str(video_path),
            total_frames=total_frames,
            analyzed_frames=analyzed_count,
            trigger_frames=trigger_frames,
            ai_summary=ai_summary,
            analysis_duration=duration,
        )

        logger.info("=" * 60)
        logger.info(f"  ✅ Analysis completed in {duration:.2f}s")
        logger.info("=" * 60)

        # Send WhatsApp notification if enabled and triggers detected
        if self._whatsapp_notifier and trigger_frames and self.config.whatsapp_notification.send_on_trigger:
            logger.info("📱 Sending WhatsApp notification...")
            success = self._whatsapp_notifier.send_video_analysis_summary(
                video_name=video_path.name,
                trigger_count=len(trigger_frames),
                ai_summary=ai_summary,
                analysis_duration=duration,
            )
            if not success:
                logger.warning("Failed to send WhatsApp notification")

        return result

    def _analyze_frame(self, frame: np.ndarray, frame_idx: int,
                      timestamp: float) -> FrameAnalysis:
        """
        Analyze a single frame for faces and matches.
        
        Args:
            frame: Input frame
            frame_idx: Frame index
            timestamp: Timestamp in seconds
        
        Returns:
            FrameAnalysis with detection and recognition results
        """
        # Detect faces
        faces = self._detector.detect(frame)

        # Recognize faces
        face_matches = []
        is_trigger = False

        for face in faces:
            match = self._recognizer.identify(frame, face)
            face_matches.append(match)

            # Check if this is a trigger (unknown person)
            if match is None or not match.is_match:
                is_trigger = True

        return FrameAnalysis(
            frame_idx=frame_idx,
            timestamp=timestamp,
            faces=faces,
            face_matches=face_matches,
            is_trigger=is_trigger,
        )

    def _generate_ai_summary(self, video_path: Path,
                            trigger_frames: List[FrameAnalysis]) -> Optional[str]:
        """
        Generate AI-powered summary of trigger events using GPT-4.
        
        Args:
            video_path: Path to video file
            trigger_frames: List of trigger frame analyses
        
        Returns:
            AI-generated summary, or None if generation fails
        """
        if not self.config.openai_api_key:
            logger.warning("OpenAI API key not configured. Skipping AI summary.")
            return None

        # Initialize OpenAI client if needed
        if self._openai_client is None:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.config.openai_api_key)
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")
                return None

        logger.info(f"🤖 Generating AI summary from {len(trigger_frames)} trigger frames...")

        # Prepare frames for AI analysis
        encoded_frames = []
        cap = cv2.VideoCapture(str(video_path))

        max_frames = min(len(trigger_frames), self.config.video_analysis.max_frames_per_analysis)

        for i, analysis in enumerate(trigger_frames[:max_frames]):
            # Seek to frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, analysis.frame_idx)
            ret, frame = cap.read()

            if not ret:
                continue

            # Resize frame
            frame_resized = cv2.resize(
                frame,
                (self.config.video_analysis.resize_width,
                 self.config.video_analysis.resize_height)
            )

            # Encode to base64
            _, buffer = cv2.imencode('.jpg', frame_resized)
            encoded = base64.b64encode(buffer).decode('utf-8')
            encoded_frames.append(encoded)

        cap.release()

        if not encoded_frames:
            logger.warning("No frames could be encoded for AI analysis")
            return None

        # Prepare messages for GPT-4
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are analyzing surveillance footage. Provide a concise summary of "
                              "activities observed, including: people detected, their actions, "
                              "approximate timing, and any notable events. Focus on factual observations."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analyze these {len(encoded_frames)} frames from surveillance footage. "
                                   f"What activities are happening?"
                        },
                        *[
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{frame}",
                                    "detail": self.config.video_analysis.ai_detail_level
                                }
                            }
                            for frame in encoded_frames
                        ]
                    ]
                }
            ]

            # Call GPT-4
            response = self._openai_client.chat.completions.create(
                model=self.config.video_analysis.ai_model,
                messages=messages,
                max_tokens=500,
            )

            summary = response.choices[0].message.content
            logger.info("✅ AI summary generated successfully")

            return summary

        except Exception as e:
            logger.error(f"Failed to generate AI summary: {e}")
            return None

    def get_known_faces(self) -> List[str]:
        """Get list of known face names."""
        return self._recognizer.known_faces_names

    def add_known_face_from_image(self, person_name: str, image_path: str) -> bool:
        """
        Add a new known face from an image file.
        
        Args:
            person_name: Name/identifier for the person
            image_path: Path to image file
        
        Returns:
            True if successful, False otherwise
        """
        image_path = Path(image_path)
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return False

        # Load image
        img = cv2.imread(str(image_path))
        if img is None:
            logger.error(f"Failed to load image: {image_path}")
            return False

        # Detect face
        faces = self._detector.detect(img)
        if not faces:
            logger.error(f"No face detected in image: {image_path}")
            return False

        # Extract feature from first face
        feature = self._recognizer.extract_feature(img, faces[0])
        if feature is None:
            logger.error(f"Failed to extract face feature from: {image_path}")
            return False

        # Add to known faces
        self._recognizer.add_known_face(person_name, feature)
        logger.info(f"✅ Added known face: {person_name}")

        return True
