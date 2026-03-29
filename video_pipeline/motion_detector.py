"""
Motion Detection Module using Frame Differencing.

Compares consecutive frames to detect changes/motion.
Uses Gaussian blur + threshold + contour analysis for robust detection.
"""

import cv2
import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple
from .config import MotionConfig

logger = logging.getLogger(__name__)


@dataclass
class MotionResult:
    """Result of a motion detection analysis."""
    motion_detected: bool
    motion_score: float          # Percentage of frame with motion (0.0 - 100.0)
    contour_count: int           # Number of motion contours found
    largest_contour_area: int    # Area of the largest motion contour
    bounding_boxes: List[Tuple[int, int, int, int]]  # List of (x, y, w, h) for each contour
    diff_frame: Optional[np.ndarray] = None    # Thresholded diff (for debugging)
    contour_frame: Optional[np.ndarray] = None  # Frame with contours drawn (for debugging)


class MotionDetector:
    """
    Detects motion between consecutive frames using frame differencing.
    
    Algorithm:
    1. Convert frames to grayscale
    2. Apply Gaussian blur to reduce noise
    3. Compute absolute difference between frames
    4. Apply threshold to create binary motion mask
    5. Find contours in the motion mask
    6. Filter contours by minimum area
    7. Calculate motion score (% of frame with motion)
    8. Compare against threshold to determine if motion occurred
    """

    def __init__(self, config: MotionConfig):
        self.config = config
        self._prev_gray: Optional[np.ndarray] = None
        self._frame_count: int = 0
        self._total_pixels: int = 0

        logger.info(
            f"MotionDetector initialized: sensitivity={config.sensitivity}, "
            f"blur={config.blur_kernel}, min_area_pct={config.min_motion_area_pct}%, "
            f"min_contour={config.min_contour_area}px"
        )

    def reset(self) -> None:
        """Reset the detector state (e.g., after reconnection)."""
        self._prev_gray = None
        self._frame_count = 0
        logger.debug("Motion detector state reset")

    def detect(self, frame: np.ndarray, debug: bool = False) -> MotionResult:
        """
        Analyze a frame for motion compared to the previous frame.
        
        Args:
            frame: BGR frame from the camera (numpy array)
            debug: If True, include diff_frame and contour_frame in result
        
        Returns:
            MotionResult with detection details
        """
        self._frame_count += 1

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        gray = cv2.GaussianBlur(gray, (self.config.blur_kernel, self.config.blur_kernel), 0)

        # First frame: just store it and return no motion
        if self._prev_gray is None:
            self._prev_gray = gray
            self._total_pixels = gray.shape[0] * gray.shape[1]
            return MotionResult(
                motion_detected=False,
                motion_score=0.0,
                contour_count=0,
                largest_contour_area=0,
                bounding_boxes=[],
            )

        # Compute absolute difference between current and previous frame
        frame_diff = cv2.absdiff(self._prev_gray, gray)

        # Apply threshold to create binary motion mask
        _, thresh = cv2.threshold(
            frame_diff,
            self.config.sensitivity,
            255,
            cv2.THRESH_BINARY,
        )

        # Dilate to fill gaps in the motion mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        thresh = cv2.dilate(thresh, kernel, iterations=2)

        # Find contours in the motion mask
        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        # Filter contours by minimum area
        significant_contours = [
            c for c in contours
            if cv2.contourArea(c) >= self.config.min_contour_area
        ]

        # Calculate motion metrics
        motion_pixel_count = cv2.countNonZero(thresh)
        motion_score = (motion_pixel_count / self._total_pixels) * 100.0

        # Get bounding boxes for significant contours
        bounding_boxes = [cv2.boundingRect(c) for c in significant_contours]

        # Largest contour area
        largest_area = 0
        if significant_contours:
            largest_area = max(cv2.contourArea(c) for c in significant_contours)

        # Determine if motion is detected
        motion_detected = (
            motion_score >= self.config.min_motion_area_pct
            and len(significant_contours) > 0
        )

        # Build debug frames if requested
        diff_frame = None
        contour_frame = None
        if debug:
            diff_frame = thresh.copy()
            contour_frame = frame.copy()
            # Draw bounding boxes on the frame
            for (x, y, w, h) in bounding_boxes:
                cv2.rectangle(contour_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # Add motion score text
            cv2.putText(
                contour_frame,
                f"Motion: {motion_score:.2f}% ({len(significant_contours)} regions)",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

        # Update previous frame
        self._prev_gray = gray

        # Log motion events
        if motion_detected:
            logger.debug(
                f"🔴 Motion detected: score={motion_score:.2f}%, "
                f"contours={len(significant_contours)}, largest={largest_area}px"
            )

        return MotionResult(
            motion_detected=motion_detected,
            motion_score=motion_score,
            contour_count=len(significant_contours),
            largest_contour_area=largest_area,
            bounding_boxes=bounding_boxes,
            diff_frame=diff_frame,
            contour_frame=contour_frame,
        )
