"""
Face Detection Module.

Uses OpenCV's YuNet model for fast and accurate face detection.
"""

import cv2
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """Represents a detected face with its bounding box and confidence."""
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    landmarks: Optional[np.ndarray] = None  # 5 facial landmarks (eyes, nose, mouth corners)


class FaceDetector:
    """
    Face detector using OpenCV's YuNet model.
    
    YuNet is a lightweight face detection model that provides:
    - Fast inference speed
    - High accuracy
    - 5-point facial landmarks
    """

    def __init__(self, model_path: str, score_threshold: float = 0.5,
                 nms_threshold: float = 0.3, top_k: int = 5000):
        """
        Initialize the face detector.
        
        Args:
            model_path: Path to YuNet ONNX model file
            score_threshold: Minimum confidence score for detection (0.0-1.0)
            nms_threshold: Non-maximum suppression threshold
            top_k: Maximum number of faces to detect
        """
        self.model_path = Path(model_path)
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.top_k = top_k

        # Validate model file exists
        if not self.model_path.exists():
            raise FileNotFoundError(f"Face detection model not found: {self.model_path}")

        # Initialize detector
        self._detector = cv2.FaceDetectorYN.create(
            str(self.model_path),
            "",
            (0, 0),
            score_threshold=self.score_threshold,
            nms_threshold=self.nms_threshold,
            top_k=self.top_k,
        )

        logger.info(f"Face detector initialized with model: {self.model_path.name}")
        logger.debug(f"  Score threshold: {self.score_threshold}")
        logger.debug(f"  NMS threshold: {self.nms_threshold}")

    def detect(self, frame: np.ndarray) -> List[DetectedFace]:
        """
        Detect faces in the given frame.
        
        Args:
            frame: Input image (BGR format)
        
        Returns:
            List of DetectedFace objects, sorted by confidence (highest first)
        """
        if frame is None or frame.size == 0:
            logger.warning("Empty frame provided to face detector")
            return []

        # Set input size to match frame dimensions
        height, width = frame.shape[:2]
        self._detector.setInputSize((width, height))

        # Run detection
        _, faces = self._detector.detect(frame)

        if faces is None or len(faces) == 0:
            return []

        # Convert to DetectedFace objects
        detected_faces = []
        for face in faces:
            # Face format: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, confidence]
            x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
            confidence = float(face[-1])
            
            # Extract 5-point landmarks (right eye, left eye, nose tip, right mouth corner, left mouth corner)
            landmarks = face[4:14].reshape(5, 2)

            detected_faces.append(DetectedFace(
                bbox=(x, y, w, h),
                confidence=confidence,
                landmarks=landmarks,
            ))

        # Sort by confidence (highest first)
        detected_faces.sort(key=lambda f: f.confidence, reverse=True)

        logger.debug(f"Detected {len(detected_faces)} face(s)")
        return detected_faces

    def draw_detections(self, frame: np.ndarray, faces: List[DetectedFace],
                       draw_landmarks: bool = True) -> np.ndarray:
        """
        Draw bounding boxes and landmarks on the frame.
        
        Args:
            frame: Input image
            faces: List of detected faces
            draw_landmarks: Whether to draw facial landmarks
        
        Returns:
            Frame with drawn detections
        """
        output = frame.copy()

        for face in faces:
            x, y, w, h = face.bbox
            confidence = face.confidence

            # Draw bounding box
            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Draw confidence score
            label = f"{confidence:.2f}"
            cv2.putText(output, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Draw landmarks
            if draw_landmarks and face.landmarks is not None:
                for landmark in face.landmarks:
                    cv2.circle(output, tuple(landmark.astype(int)), 2, (255, 0, 0), -1)

        return output

    def get_face_region(self, frame: np.ndarray, face: DetectedFace,
                       padding: float = 0.0) -> Optional[np.ndarray]:
        """
        Extract face region from frame with optional padding.
        
        Args:
            frame: Input image
            face: Detected face
            padding: Padding ratio (e.g., 0.2 = 20% padding on each side)
        
        Returns:
            Cropped face region, or None if invalid
        """
        x, y, w, h = face.bbox
        
        # Apply padding
        if padding > 0:
            pad_w = int(w * padding)
            pad_h = int(h * padding)
            x = max(0, x - pad_w)
            y = max(0, y - pad_h)
            w = min(frame.shape[1] - x, w + 2 * pad_w)
            h = min(frame.shape[0] - y, h + 2 * pad_h)

        # Validate bounds
        if x < 0 or y < 0 or x + w > frame.shape[1] or y + h > frame.shape[0]:
            logger.warning("Face region out of bounds")
            return None

        return frame[y:y+h, x:x+w]
