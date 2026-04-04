"""
Video Processing Watcher.

Monitors the recordings directory for new video files and automatically
processes them through the video analysis pipeline.
"""

import time
import logging
from pathlib import Path
from typing import Optional
from threading import Thread, Event
from queue import Queue, Empty

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from .video_analyzer import VideoAnalyzer
from .processing_state import ProcessingStateManager
from .config import VideoProcessingConfig

logger = logging.getLogger(__name__)


class VideoFileHandler(FileSystemEventHandler):
    """
    Handles filesystem events for video files.
    
    Detects new .mp4 files and queues them for processing.
    """

    def __init__(self, processing_queue: Queue, file_stable_delay: float = 2.0, min_file_size: int = 1024):
        """
        Initialize the file handler.
        
        Args:
            processing_queue: Queue to add detected videos to
            file_stable_delay: Seconds to wait after last modification before processing
            min_file_size: Minimum file size in bytes to consider valid (default: 1KB)
        """
        super().__init__()
        self.processing_queue = processing_queue
        self.file_stable_delay = file_stable_delay
        self.min_file_size = min_file_size
        self._pending_files = {}  # Track file modification times
        self._file_sizes = {}  # Track file sizes to detect completion

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if isinstance(event, FileCreatedEvent):
            file_path = Path(event.src_path)
            
            # Only process .mp4 files
            if file_path.suffix.lower() == '.mp4':
                logger.info(f"📹 New video detected: {file_path.name}")
                self._track_file(file_path)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if isinstance(event, FileModifiedEvent):
            file_path = Path(event.src_path)
            
            # Only track .mp4 files
            if file_path.suffix.lower() == '.mp4':
                self._track_file(file_path)

    def _track_file(self, file_path: Path):
        """
        Track file modifications to detect when writing is complete.
        
        Args:
            file_path: Path to the file being tracked
        """
        file_path_str = str(file_path)
        self._pending_files[file_path_str] = time.time()
        
        # Track file size to detect if it's still being written
        try:
            if file_path.exists():
                self._file_sizes[file_path_str] = file_path.stat().st_size
        except Exception:
            pass

    def get_stable_files(self) -> list:
        """
        Get list of files that haven't been modified for file_stable_delay seconds
        and have a stable file size.
        
        Returns:
            List of file paths that are ready for processing
        """
        current_time = time.time()
        stable_files = []
        
        for file_path_str, last_modified in list(self._pending_files.items()):
            if current_time - last_modified >= self.file_stable_delay:
                file_path = Path(file_path_str)
                
                # Check if file exists and has minimum size
                if not file_path.exists():
                    logger.debug(f"File no longer exists, removing from tracking: {file_path.name}")
                    del self._pending_files[file_path_str]
                    self._file_sizes.pop(file_path_str, None)
                    continue
                
                try:
                    current_size = file_path.stat().st_size
                    
                    # Check minimum file size
                    if current_size < self.min_file_size:
                        logger.debug(f"File too small ({current_size} bytes), skipping: {file_path.name}")
                        del self._pending_files[file_path_str]
                        self._file_sizes.pop(file_path_str, None)
                        continue
                    
                    # Check if file size is stable (hasn't changed since last check)
                    last_size = self._file_sizes.get(file_path_str, 0)
                    if current_size == last_size:
                        # File size is stable, ready for processing
                        stable_files.append(file_path_str)
                        del self._pending_files[file_path_str]
                        del self._file_sizes[file_path_str]
                    else:
                        # File size changed, update and wait longer
                        self._file_sizes[file_path_str] = current_size
                        self._pending_files[file_path_str] = current_time
                        logger.debug(f"File size changed ({last_size} → {current_size}), waiting: {file_path.name}")
                
                except Exception as e:
                    logger.warning(f"Error checking file {file_path.name}: {e}")
                    del self._pending_files[file_path_str]
                    self._file_sizes.pop(file_path_str, None)
        
        return stable_files


class VideoProcessingWatcher:
    """
    Main watcher service that monitors recordings directory and processes videos.
    """

    def __init__(
        self,
        config: VideoProcessingConfig,
        recordings_dir: str = "./recordings",
        process_existing: bool = False,
        file_stable_delay: float = 5.0,
        state_file: str = "video_processing/processed_videos.json",
        max_retries: int = 2,
        retry_delay: float = 3.0,
    ):
        """
        Initialize the video processing watcher.
        
        Args:
            config: Video processing configuration
            recordings_dir: Directory to monitor for new videos
            process_existing: Whether to process existing videos on startup
            file_stable_delay: Seconds to wait after file modification stops (default: 5.0)
            state_file: Path to state persistence file
            max_retries: Maximum number of retry attempts for failed videos (default: 2)
            retry_delay: Seconds to wait before retrying a failed video (default: 3.0)
        """
        self.config = config
        self.recordings_dir = Path(recordings_dir)
        self.process_existing = process_existing
        self.file_stable_delay = file_stable_delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Create recordings directory if it doesn't exist
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.state_manager = ProcessingStateManager(state_file=state_file)
        self.video_analyzer = VideoAnalyzer(config)
        
        # Processing queue and control
        self.processing_queue = Queue()
        self.retry_queue = Queue()  # Queue for videos that need retry
        self.stop_event = Event()
        
        # Filesystem observer
        self.file_handler = VideoFileHandler(
            processing_queue=self.processing_queue,
            file_stable_delay=file_stable_delay,
        )
        self.observer = Observer()
        self.observer.schedule(self.file_handler, str(self.recordings_dir), recursive=False)
        
        # Processing thread
        self.processing_thread: Optional[Thread] = None
        self.stability_check_thread: Optional[Thread] = None
        
        logger.info("=" * 60)
        logger.info("  🔍 VIDEO PROCESSING WATCHER INITIALIZED")
        logger.info("=" * 60)
        logger.info(f"  Monitoring: {self.recordings_dir.absolute()}")
        logger.info(f"  File stable delay: {file_stable_delay}s")
        logger.info(f"  Max retries: {max_retries}")
        logger.info(f"  Retry delay: {retry_delay}s")
        logger.info(f"  Process existing: {process_existing}")
        logger.info(f"  State file: {state_file}")
        logger.info("=" * 60)

    def start(self):
        """Start the watcher service."""
        logger.info("🚀 Starting video processing watcher...")
        
        # Process existing videos if requested
        if self.process_existing:
            self._process_existing_videos()
        
        # Start filesystem observer
        self.observer.start()
        logger.info("✅ Filesystem observer started")
        
        # Start stability check thread
        self.stability_check_thread = Thread(target=self._stability_checker, daemon=True)
        self.stability_check_thread.start()
        logger.info("✅ File stability checker started")
        
        # Start processing thread
        self.processing_thread = Thread(target=self._processing_worker, daemon=True)
        self.processing_thread.start()
        logger.info("✅ Processing worker started")
        
        logger.info("🎬 Watcher is now monitoring for new videos...")
        
        # Keep main thread alive
        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n👋 Shutdown requested...")
            self.stop()

    def stop(self):
        """Stop the watcher service."""
        logger.info("🛑 Stopping video processing watcher...")
        
        # Signal threads to stop
        self.stop_event.set()
        
        # Stop filesystem observer
        self.observer.stop()
        self.observer.join()
        logger.info("✅ Filesystem observer stopped")
        
        # Wait for processing to complete
        if self.processing_thread and self.processing_thread.is_alive():
            logger.info("⏳ Waiting for processing to complete...")
            self.processing_thread.join(timeout=30)
        
        # Print statistics
        stats = self.state_manager.get_statistics()
        logger.info("=" * 60)
        logger.info("  📊 PROCESSING STATISTICS")
        logger.info("=" * 60)
        logger.info(f"  Total processed: {stats['total_processed']}")
        logger.info(f"  With triggers: {stats['with_triggers']}")
        logger.info(f"  With unknown faces: {stats['with_unknown_faces']}")
        logger.info(f"  Notifications sent: {stats['notifications_sent']}")
        logger.info(f"  Total analysis time: {stats['total_analysis_time']:.1f}s")
        logger.info(f"  Avg analysis time: {stats['avg_analysis_time']:.1f}s")
        logger.info("=" * 60)
        
        logger.info("✅ Watcher stopped")

    def _stability_checker(self):
        """Background thread that checks for stable files and queues them."""
        while not self.stop_event.is_set():
            stable_files = self.file_handler.get_stable_files()
            
            for file_path in stable_files:
                # Check if already processed
                if not self.state_manager.is_processed(file_path):
                    logger.info(f"✅ File stable and ready: {Path(file_path).name}")
                    self.processing_queue.put(file_path)
                else:
                    logger.debug(f"Skipping already processed file: {Path(file_path).name}")
            
            time.sleep(0.5)  # Check every 500ms

    def _processing_worker(self):
        """Background thread that processes videos from the queue."""
        while not self.stop_event.is_set():
            try:
                # Get video from queue with timeout
                item = self.processing_queue.get(timeout=1)
                
                # Handle both old format (string) and new format (tuple)
                if isinstance(item, tuple):
                    video_path, retry_count = item
                else:
                    video_path, retry_count = item, 0
                
                # Process the video
                self._process_video(video_path, retry_count)
                
                self.processing_queue.task_done()
            
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in processing worker: {e}", exc_info=True)

    def _is_valid_mp4(self, video_path: Path) -> bool:
        """
        Check if an MP4 file is valid and ready for processing.
        
        Args:
            video_path: Path to video file
        
        Returns:
            True if video is valid and can be opened, False otherwise
        """
        import cv2
        
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return False
            
            # Try to read the first frame
            ret, _ = cap.read()
            cap.release()
            
            return ret
        except Exception:
            return False

    def _process_video(self, video_path: str, retry_count: int = 0):
        """
        Process a single video file with retry support.
        
        Args:
            video_path: Path to video file
            retry_count: Current retry attempt number
        """
        video_path = Path(video_path)
        
        # Double-check it hasn't been processed
        if self.state_manager.is_processed(str(video_path)):
            logger.debug(f"Skipping already processed: {video_path.name}")
            return
        
        # Check if file still exists
        if not video_path.exists():
            logger.warning(f"Video file no longer exists: {video_path.name}")
            return
        
        # Validate MP4 file before processing
        if not self._is_valid_mp4(video_path):
            if retry_count < self.max_retries:
                logger.warning(
                    f"⚠️ Video not ready (moov atom missing): {video_path.name} "
                    f"(retry {retry_count + 1}/{self.max_retries})"
                )
                # Schedule retry after delay
                import threading
                def retry_later():
                    time.sleep(self.retry_delay)
                    self.processing_queue.put((str(video_path), retry_count + 1))
                
                threading.Thread(target=retry_later, daemon=True).start()
                return
            else:
                logger.error(
                    f"❌ Video still invalid after {self.max_retries} retries: {video_path.name}"
                )
                # Mark as processed with error
                self.state_manager.mark_processed(
                    video_path=str(video_path),
                    trigger_count=0,
                    analyzed_frames=0,
                    total_frames=0,
                    analysis_duration=0.0,
                    has_unknown_faces=False,
                    error="Invalid MP4 file (moov atom not found) after retries",
                )
                return
        
        logger.info("=" * 60)
        logger.info(f"  🎬 PROCESSING: {video_path.name}")
        if retry_count > 0:
            logger.info(f"  (Retry attempt {retry_count})")
        logger.info("=" * 60)
        
        try:
            # Analyze the video
            result = self.video_analyzer.analyze_video(
                video_path=str(video_path),
                use_ai_summary=True,
            )
            
            # Determine if unknown faces were detected
            has_unknown = any(
                frame.is_trigger for frame in result.trigger_frames
            )
            
            # Mark as processed
            self.state_manager.mark_processed(
                video_path=str(video_path),
                trigger_count=len(result.trigger_frames),
                analyzed_frames=result.analyzed_frames,
                total_frames=result.total_frames,
                analysis_duration=result.analysis_duration,
                has_unknown_faces=has_unknown,
                notification_sent=has_unknown and self.config.whatsapp_notification.enabled,
            )
            
            logger.info(f"✅ Processing complete: {video_path.name}")
            logger.info(f"   Triggers: {len(result.trigger_frames)}, Unknown faces: {has_unknown}")
        
        except Exception as e:
            logger.error(f"❌ Failed to process {video_path.name}: {e}", exc_info=True)
            
            # Mark as processed with error
            self.state_manager.mark_processed(
                video_path=str(video_path),
                trigger_count=0,
                analyzed_frames=0,
                total_frames=0,
                analysis_duration=0.0,
                has_unknown_faces=False,
                error=str(e),
            )

    def _process_existing_videos(self):
        """Process any existing videos in the recordings directory."""
        logger.info("🔍 Scanning for existing unprocessed videos...")
        
        unprocessed = self.state_manager.get_unprocessed_videos(str(self.recordings_dir))
        
        if not unprocessed:
            logger.info("   No unprocessed videos found")
            return
        
        logger.info(f"   Found {len(unprocessed)} unprocessed video(s)")
        
        for video_path in unprocessed:
            logger.info(f"   Queuing: {video_path.name}")
            self.processing_queue.put(str(video_path))
