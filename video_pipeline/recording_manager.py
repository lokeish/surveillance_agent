"""
Recording Manager Module.

Handles video file writing with:
  - Pre-motion frame buffer (capture context before motion starts)
  - Active recording during motion
  - Post-motion cooldown (continue recording after motion stops)
  - Timestamp overlay on frames
"""

import cv2
import time
import logging
import numpy as np
from pathlib import Path
from collections import deque
from datetime import datetime
from typing import Optional, Tuple
from .config import RecordingConfig

logger = logging.getLogger(__name__)


class RecordingManager:
    """
    Manages video recording with pre/post motion buffering.
    
    States:
        IDLE       → Buffering frames, waiting for motion
        RECORDING  → Actively writing frames to video file
        COOLDOWN   → Motion stopped, but still recording for post_buffer_seconds
    """

    # Recording states
    STATE_IDLE = "IDLE"
    STATE_RECORDING = "RECORDING"
    STATE_COOLDOWN = "COOLDOWN"

    def __init__(self, config: RecordingConfig, frame_width: int, frame_height: int, fps: float):
        """
        Initialize the RecordingManager.
        
        Args:
            config: Recording configuration
            frame_width: Width of video frames
            frame_height: Height of video frames
            fps: Frames per second for the output video
        """
        self.config = config
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps = fps

        # State management
        self._state = self.STATE_IDLE
        self._writer: Optional[cv2.VideoWriter] = None
        self._current_file: Optional[str] = None
        self._recording_start_time: float = 0.0
        self._last_motion_time: float = 0.0
        self._frames_written: int = 0

        # Pre-motion buffer: circular buffer holding last N seconds of frames
        buffer_size = int(config.pre_buffer_seconds * fps)
        self._pre_buffer: deque = deque(maxlen=max(buffer_size, 1))

        # Statistics
        self._total_recordings: int = 0
        self._total_recording_seconds: float = 0.0

        # Create output directory
        self._output_dir = Path(config.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"RecordingManager initialized: {frame_width}x{frame_height} @ {fps:.1f}fps, "
            f"pre_buffer={config.pre_buffer_seconds}s ({buffer_size} frames), "
            f"post_buffer={config.post_buffer_seconds}s, "
            f"output={self._output_dir.absolute()}"
        )

    @property
    def state(self) -> str:
        """Current recording state."""
        return self._state

    @property
    def is_recording(self) -> bool:
        """Whether actively recording (RECORDING or COOLDOWN)."""
        return self._state in (self.STATE_RECORDING, self.STATE_COOLDOWN)

    @property
    def current_file(self) -> Optional[str]:
        """Path to the current recording file, if any."""
        return self._current_file

    @property
    def total_recordings(self) -> int:
        """Total number of recordings created."""
        return self._total_recordings

    def process_frame(self, frame: np.ndarray, timestamp: float, motion_detected: bool) -> None:
        """
        Process a frame based on current state and motion detection result.
        
        This is the main method called by the pipeline for every frame.
        
        Args:
            frame: BGR frame from the camera
            timestamp: Unix timestamp when the frame was captured
            motion_detected: Whether motion was detected in this frame
        """
        # Add timestamp overlay if configured
        if self.config.timestamp_overlay:
            frame = self._add_timestamp(frame, timestamp)

        if self._state == self.STATE_IDLE:
            self._handle_idle(frame, timestamp, motion_detected)

        elif self._state == self.STATE_RECORDING:
            self._handle_recording(frame, timestamp, motion_detected)

        elif self._state == self.STATE_COOLDOWN:
            self._handle_cooldown(frame, timestamp, motion_detected)

    def stop(self) -> None:
        """Finalize any active recording and release resources."""
        if self._writer is not None:
            self._finalize_recording()
        logger.info(
            f"RecordingManager stopped. Total recordings: {self._total_recordings}, "
            f"Total duration: {self._total_recording_seconds:.1f}s"
        )

    # ──────────────────────────────────────────────
    # State handlers
    # ──────────────────────────────────────────────

    def _handle_idle(self, frame: np.ndarray, timestamp: float, motion_detected: bool) -> None:
        """IDLE state: buffer frames, start recording on motion."""
        # Always add to pre-buffer
        self._pre_buffer.append((frame.copy(), timestamp))

        if motion_detected:
            # Motion detected! Start recording
            self._start_recording(timestamp)
            self._last_motion_time = timestamp

            # Write all pre-buffer frames first
            logger.debug(f"Writing {len(self._pre_buffer)} pre-buffer frames")
            for buffered_frame, buffered_ts in self._pre_buffer:
                self._write_frame(buffered_frame)

            self._state = self.STATE_RECORDING
            logger.info(f"🔴 MOTION STARTED → Recording to: {self._current_file}")

    def _handle_recording(self, frame: np.ndarray, timestamp: float, motion_detected: bool) -> None:
        """RECORDING state: write frames, transition to cooldown when motion stops."""
        self._write_frame(frame)

        if motion_detected:
            self._last_motion_time = timestamp
        else:
            # Motion stopped, enter cooldown
            self._state = self.STATE_COOLDOWN
            logger.debug("Motion stopped, entering cooldown...")

        # Safety: check max recording duration
        if self._check_max_duration(timestamp):
            return

    def _handle_cooldown(self, frame: np.ndarray, timestamp: float, motion_detected: bool) -> None:
        """COOLDOWN state: continue recording, resume if motion returns, stop after timeout."""
        self._write_frame(frame)

        if motion_detected:
            # Motion resumed! Back to RECORDING state
            self._last_motion_time = timestamp
            self._state = self.STATE_RECORDING
            logger.debug("Motion resumed during cooldown → back to RECORDING")
            return

        # Check if cooldown period has elapsed
        time_since_last_motion = timestamp - self._last_motion_time
        if time_since_last_motion >= self.config.post_buffer_seconds:
            logger.info(
                f"⬜ MOTION ENDED → Cooldown complete ({self.config.post_buffer_seconds}s). "
                f"Stopping recording."
            )
            self._finalize_recording()
            self._state = self.STATE_IDLE
            return

        # Safety: check max recording duration
        self._check_max_duration(timestamp)

    # ──────────────────────────────────────────────
    # Recording management
    # ──────────────────────────────────────────────

    def _start_recording(self, timestamp: float) -> None:
        """Create a new video file and VideoWriter."""
        # Generate filename from timestamp
        dt = datetime.fromtimestamp(timestamp)
        filename = f"motion_{dt.strftime('%Y-%m-%d_%H-%M-%S')}{self.config.file_extension}"
        filepath = self._output_dir / filename

        # Create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*self.config.codec)
        self._writer = cv2.VideoWriter(
            str(filepath),
            fourcc,
            self.fps,
            (self.frame_width, self.frame_height),
        )

        if not self._writer.isOpened():
            logger.error(f"Failed to create VideoWriter for: {filepath}")
            self._writer = None
            return

        self._current_file = str(filepath)
        self._recording_start_time = timestamp
        self._frames_written = 0

    def _write_frame(self, frame: np.ndarray) -> None:
        """Write a single frame to the active video file."""
        if self._writer is not None and self._writer.isOpened():
            self._writer.write(frame)
            self._frames_written += 1

    def _finalize_recording(self) -> None:
        """Finalize and close the current recording."""
        if self._writer is not None:
            self._writer.release()
            self._writer = None

        duration = time.time() - self._recording_start_time
        self._total_recordings += 1
        self._total_recording_seconds += duration

        logger.info(
            f"💾 Recording saved: {self._current_file} "
            f"({self._frames_written} frames, {duration:.1f}s)"
        )

        self._current_file = None
        self._frames_written = 0
        self._pre_buffer.clear()

    def _check_max_duration(self, timestamp: float) -> bool:
        """Check if recording has exceeded max duration. Returns True if stopped."""
        elapsed = timestamp - self._recording_start_time
        if elapsed >= self.config.max_recording_seconds:
            logger.warning(
                f"⚠️ Max recording duration ({self.config.max_recording_seconds}s) reached. "
                f"Force-stopping recording."
            )
            self._finalize_recording()
            self._state = self.STATE_IDLE
            return True
        return False

    # ──────────────────────────────────────────────
    # Timestamp overlay
    # ──────────────────────────────────────────────

    def _add_timestamp(self, frame: np.ndarray, timestamp: float) -> np.ndarray:
        """
        Add a timestamp overlay to a frame.
        
        Returns a copy of the frame with timestamp text.
        """
        frame = frame.copy()
        dt = datetime.fromtimestamp(timestamp)
        text = dt.strftime("%Y-%m-%d %H:%M:%S")

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = self.config.timestamp_font_scale
        thickness = 2
        color = self.config.timestamp_color
        bg_color = self.config.timestamp_bg_color

        # Calculate text size
        (text_w, text_h), baseline = cv2.getTextSize(text, font, scale, thickness)
        padding = 8

        # Determine position
        pos = self._get_timestamp_position(
            text_w, text_h, padding, baseline,
            frame.shape[1], frame.shape[0]
        )

        # Draw background rectangle
        bg_x1 = pos[0] - padding
        bg_y1 = pos[1] - text_h - padding
        bg_x2 = pos[0] + text_w + padding
        bg_y2 = pos[1] + baseline + padding

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (bg_x1, bg_y1), (bg_x2, bg_y2), bg_color, -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # Draw text
        cv2.putText(frame, text, pos, font, scale, color, thickness, cv2.LINE_AA)

        return frame

    def _get_timestamp_position(
        self, text_w: int, text_h: int, padding: int, baseline: int,
        frame_w: int, frame_h: int
    ) -> Tuple[int, int]:
        """Calculate text position based on config."""
        position = self.config.timestamp_position

        if position == "top-left":
            return (padding * 2, text_h + padding * 2)
        elif position == "top-right":
            return (frame_w - text_w - padding * 2, text_h + padding * 2)
        elif position == "bottom-right":
            return (frame_w - text_w - padding * 2, frame_h - padding * 2 - baseline)
        else:  # bottom-left (default)
            return (padding * 2, frame_h - padding * 2 - baseline)
