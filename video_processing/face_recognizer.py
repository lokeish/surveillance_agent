"""
Face Recognition Module.

Uses OpenCV's SFace model for face recognition and matching.
Manages known faces database for identification.
"""

import cv2
import logging
import pickle
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np
from dataclasses import dataclass

from .face_detector import DetectedFace

logger = logging.getLogger(__name__)


@dataclass
class FaceMatch:
    """Represents a face match result."""
    person_name: str
    similarity_score: float
    is_match: bool


class FaceRecognizer:
    """
    Face recognizer using OpenCV's SFace model.
    
    SFace provides:
    - 128-dimensional face embeddings
    - Cosine similarity matching
    - High accuracy for face verification
    """

    def __init__(self, model_path: str, match_threshold: float = 0.36,
                 known_faces_dir: Optional[str] = None):
        """
        Initialize the face recognizer.
        
        Args:
            model_path: Path to SFace ONNX model file
            match_threshold: Cosine similarity threshold for matching (0.0-1.0)
            known_faces_dir: Directory containing known face images
        """
        self.model_path = Path(model_path)
        self.match_threshold = match_threshold
        self.known_faces_dir = Path(known_faces_dir) if known_faces_dir else None

        # Validate model file exists
        if not self.model_path.exists():
            raise FileNotFoundError(f"Face recognition model not found: {self.model_path}")

        # Initialize recognizer
        self._recognizer = cv2.FaceRecognizerSF.create(
            str(self.model_path),
            "",
        )

        # Known faces database: {person_name: feature_vector}
        self._known_faces: Dict[str, np.ndarray] = {}

        logger.info(f"Face recognizer initialized with model: {self.model_path.name}")
        logger.debug(f"  Match threshold: {self.match_threshold}")

        # Load known faces if directory provided
        if self.known_faces_dir and self.known_faces_dir.exists():
            self._load_known_faces()

    def extract_feature(self, frame: np.ndarray, face: DetectedFace) -> Optional[np.ndarray]:
        """
        Extract 128-d feature vector from a detected face.
        
        Args:
            frame: Input image
            face: Detected face with landmarks
        
        Returns:
            128-dimensional feature vector, or None if extraction fails
        """
        try:
            # Convert bbox and landmarks to the format expected by alignCrop
            face_box = np.array([
                face.bbox[0], face.bbox[1], face.bbox[2], face.bbox[3],
                *face.landmarks.flatten()
            ], dtype=np.float32)

            # Align and crop face
            aligned_face = self._recognizer.alignCrop(frame, face_box)

            # Extract feature
            feature = self._recognizer.feature(aligned_face)

            return feature

        except Exception as e:
            logger.error(f"Failed to extract face feature: {e}")
            return None

    def match(self, feature1: np.ndarray, feature2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two face features.
        
        Args:
            feature1: First face feature vector
            feature2: Second face feature vector
        
        Returns:
            Cosine similarity score (higher = more similar)
        """
        score = self._recognizer.match(
            feature1, feature2,
            cv2.FaceRecognizerSF_FR_COSINE
        )
        return float(score)

    def identify(self, frame: np.ndarray, face: DetectedFace) -> Optional[FaceMatch]:
        """
        Identify a face by comparing against known faces database.
        
        Args:
            frame: Input image
            face: Detected face
        
        Returns:
            FaceMatch object with best match, or None if no known faces
        """
        if not self._known_faces:
            logger.warning("No known faces loaded. Cannot identify.")
            return None

        # Extract feature from detected face
        feature = self.extract_feature(frame, face)
        if feature is None:
            return None

        # Find best match
        best_match_name = None
        best_match_score = -1.0

        for person_name, known_feature in self._known_faces.items():
            score = self.match(feature, known_feature)
            if score > best_match_score:
                best_match_score = score
                best_match_name = person_name

        # Check if best match exceeds threshold
        is_match = best_match_score > self.match_threshold

        return FaceMatch(
            person_name=best_match_name or "Unknown",
            similarity_score=best_match_score,
            is_match=is_match,
        )

    def add_known_face(self, person_name: str, feature: np.ndarray) -> None:
        """
        Add a known face to the database.
        
        Args:
            person_name: Name/identifier for the person
            feature: Face feature vector
        """
        self._known_faces[person_name] = feature
        logger.info(f"Added known face: {person_name}")

    def remove_known_face(self, person_name: str) -> bool:
        """
        Remove a known face from the database.
        
        Args:
            person_name: Name of person to remove
        
        Returns:
            True if removed, False if not found
        """
        if person_name in self._known_faces:
            del self._known_faces[person_name]
            logger.info(f"Removed known face: {person_name}")
            return True
        return False

    def save_known_faces(self, filepath: str) -> None:
        """
        Save known faces database to file.
        
        Args:
            filepath: Path to save database
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'wb') as f:
            pickle.dump(self._known_faces, f)

        logger.info(f"Saved {len(self._known_faces)} known faces to {filepath}")

    def load_known_faces_from_file(self, filepath: str) -> None:
        """
        Load known faces database from file.
        
        Args:
            filepath: Path to database file
        """
        filepath = Path(filepath)
        if not filepath.exists():
            logger.warning(f"Known faces file not found: {filepath}")
            return

        with open(filepath, 'rb') as f:
            self._known_faces = pickle.load(f)

        logger.info(f"Loaded {len(self._known_faces)} known faces from {filepath}")

    def _load_known_faces(self) -> None:
        """
        Load known faces from images in the known_faces_dir.
        
        Expected structure:
          known_faces/
            person1.jpg
            person2.png
            ...
        
        The filename (without extension) becomes the person's name.
        """
        if not self.known_faces_dir or not self.known_faces_dir.exists():
            logger.warning(f"Known faces directory not found: {self.known_faces_dir}")
            return

        # Import detector here to avoid circular dependency
        from .face_detector import FaceDetector
        from .config import FaceDetectionConfig

        # Create temporary detector for loading known faces
        detector = FaceDetector(
            model_path=str(self.model_path.parent / "face_detection_yunet_2023mar.onnx"),
            score_threshold=0.5,
        )

        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        loaded_count = 0

        for image_path in self.known_faces_dir.iterdir():
            if image_path.suffix.lower() not in image_extensions:
                continue

            person_name = image_path.stem

            # Load image
            img = cv2.imread(str(image_path))
            if img is None:
                logger.warning(f"Failed to load image: {image_path}")
                continue

            # Detect face
            faces = detector.detect(img)
            if not faces:
                logger.warning(f"No face detected in {image_path}")
                continue

            # Use first detected face
            face = faces[0]

            # Extract feature
            feature = self.extract_feature(img, face)
            if feature is None:
                logger.warning(f"Failed to extract feature from {image_path}")
                continue

            # Add to known faces
            self.add_known_face(person_name, feature)
            loaded_count += 1

        logger.info(f"Loaded {loaded_count} known faces from {self.known_faces_dir}")

    @property
    def known_faces_count(self) -> int:
        """Get number of known faces in database."""
        return len(self._known_faces)

    @property
    def known_faces_names(self) -> List[str]:
        """Get list of known face names."""
        return list(self._known_faces.keys())
