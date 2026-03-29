"""
Main Pipeline Orchestrator.

Connects all components:
  StreamCapture → MotionDetector → RecordingManager

Runs the main processing loop with configurable FPS throttling.
"""

import time
import signal
import logging
from datetime import datetime, timedelta
from typing import Optional
from .config import PipelineConfig, load_config, setup_logging
from .stream_capture import StreamCapture
from .motion_detector import MotionDetector
from .recording_manager import RecordingManager

logger = logging.getLogger(__name__)


class SurveillancePipeline:
    """
    Main surveillance pipeline that ties together stream capture,
    motion detection, and recording management.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline.
        
        Args:
            config: Pipeline configuration. If None, loads from default paths.
        """
        # Load configuration
        if config is None:
            config = load_config()
        self.config = config

        # Setup logging
        setup_logging(config.logging)

        # Components (initialized on start)
        self._stream: Optional[StreamCapture] = None
        self._detector: Optional[MotionDetector] = None
        self._recorder: Optional[RecordingManager] = None

        # Pipeline state
        self._running = False
        self._frames_processed = 0
        self._motion_events = 0
        self._start_time: float = 0.0

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start(self) -> None:
        """Initialize all components and start the pipeline."""
        logger.info("=" * 60)
        logger.info("  📹 SURVEILLANCE PIPELINE STARTING")
        logger.info("=" * 60)

        self._start_time = time.time()

        # Initialize stream capture
        logger.info("Initializing stream capture...")
        self._stream = StreamCapture(self.config.stream)
        if not self._stream.start():
            logger.error("Failed to start stream capture. Exiting.")
            return

        # Initialize motion detector
        logger.info("Initializing motion detector...")
        self._detector = MotionDetector(self.config.motion)

        # Initialize recording manager
        logger.info("Initializing recording manager...")
        frame_w, frame_h = self._stream.frame_size
        self._recorder = RecordingManager(
            self.config.recording,
            frame_width=frame_w,
            frame_height=frame_h,
            fps=self.config.stream.process_fps,
        )

        self._running = True

        logger.info("-" * 60)
        logger.info(f"  Stream    : {frame_w}x{frame_h} @ {self._stream.fps:.1f} FPS")
        logger.info(f"  Processing: {self.config.stream.process_fps} FPS")
        logger.info(f"  Sensitivity: {self.config.motion.sensitivity}")
        logger.info(f"  Motion threshold: {self.config.motion.min_motion_area_pct}%")
        logger.info(f"  Pre-buffer: {self.config.recording.pre_buffer_seconds}s")
        logger.info(f"  Post-buffer: {self.config.recording.post_buffer_seconds}s")
        logger.info(f"  Output dir: {self.config.recording.output_dir}")
        logger.info("-" * 60)
        logger.info("🟢 Pipeline running. Press Ctrl+C to stop.")
        logger.info("")

        # Run the main processing loop
        self._run_loop()

    def stop(self) -> None:
        """Gracefully stop all pipeline components."""
        logger.info("")
        logger.info("🛑 Stopping pipeline...")
        self._running = False

        # Stop components in reverse order
        if self._recorder is not None:
            self._recorder.stop()

        if self._stream is not None:
            self._stream.stop()

        # Print summary
        elapsed = time.time() - self._start_time
        self._print_summary(elapsed)

    def _run_loop(self) -> None:
        """
        Main processing loop.
        
        Reads frames from the stream at the configured process_fps rate,
        runs motion detection, and manages recording accordingly.
        """
        frame_interval = 1.0 / self.config.stream.process_fps
        last_status_time = time.time()
        status_interval = 30.0  # Print status every 30 seconds

        while self._running:
            loop_start = time.time()

            # Read latest frame from stream
            ret, frame, timestamp = self._stream.read()

            if not ret or frame is None:
                # No frame available, wait briefly and retry
                time.sleep(0.1)
                continue

            # Run motion detection
            result = self._detector.detect(frame)
            self._frames_processed += 1

            # Track motion events
            if result.motion_detected:
                if not self._recorder.is_recording:
                    self._motion_events += 1

            # Process frame through recording manager
            self._recorder.process_frame(frame, timestamp, result.motion_detected)

            # Periodic status log
            now = time.time()
            if now - last_status_time >= status_interval:
                self._log_status()
                last_status_time = now

            # Throttle to target FPS
            elapsed = time.time() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _log_status(self) -> None:
        """Log periodic status information."""
        elapsed = time.time() - self._start_time
        elapsed_str = str(timedelta(seconds=int(elapsed)))

        recorder_state = self._recorder.state if self._recorder else "N/A"
        stream_frames = self._stream.frame_count if self._stream else 0

        logger.info(
            f"📊 Status | Uptime: {elapsed_str} | "
            f"Processed: {self._frames_processed} frames | "
            f"Stream: {stream_frames} frames | "
            f"Motion events: {self._motion_events} | "
            f"Recordings: {self._recorder.total_recordings if self._recorder else 0} | "
            f"State: {recorder_state}"
        )

    def _print_summary(self, elapsed: float) -> None:
        """Print final summary when pipeline stops."""
        elapsed_str = str(timedelta(seconds=int(elapsed)))

        logger.info("")
        logger.info("=" * 60)
        logger.info("  📊 PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Total uptime         : {elapsed_str}")
        logger.info(f"  Frames processed     : {self._frames_processed}")
        logger.info(f"  Motion events        : {self._motion_events}")
        logger.info(f"  Recordings created   : {self._recorder.total_recordings if self._recorder else 0}")
        logger.info(f"  Avg processing FPS   : {self._frames_processed / max(elapsed, 1):.1f}")
        logger.info("=" * 60)
        logger.info("Pipeline stopped. Goodbye! 👋")

    def _signal_handler(self, signum, frame) -> None:
        """Handle SIGINT/SIGTERM for graceful shutdown."""
        logger.info(f"\n⚡ Received signal {signum}. Initiating graceful shutdown...")
        self.stop()
