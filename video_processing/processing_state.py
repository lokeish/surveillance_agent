"""
Processing State Manager.

Tracks which videos have been processed to avoid duplicate processing
and maintain processing history.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ProcessingRecord:
    """Record of a processed video."""
    video_path: str
    processed_at: str  # ISO format timestamp
    trigger_count: int
    analyzed_frames: int
    total_frames: int
    analysis_duration: float
    has_unknown_faces: bool
    notification_sent: bool = False
    error: Optional[str] = None


class ProcessingStateManager:
    """
    Manages state of processed videos.
    
    Persists processing records to JSON file for crash recovery
    and duplicate prevention.
    """

    def __init__(self, state_file: str = "video_processing/processed_videos.json"):
        """
        Initialize the state manager.
        
        Args:
            state_file: Path to JSON file for state persistence
        """
        self.state_file = Path(state_file)
        self._records: Dict[str, ProcessingRecord] = {}
        
        # Create parent directory if needed
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing state
        self._load_state()
        
        logger.info(f"ProcessingStateManager initialized with {len(self._records)} existing records")

    def is_processed(self, video_path: str) -> bool:
        """
        Check if a video has already been processed.
        
        Args:
            video_path: Path to video file
        
        Returns:
            True if video has been processed, False otherwise
        """
        # Normalize path for consistent comparison
        normalized_path = str(Path(video_path).absolute())
        return normalized_path in self._records

    def mark_processed(
        self,
        video_path: str,
        trigger_count: int,
        analyzed_frames: int,
        total_frames: int,
        analysis_duration: float,
        has_unknown_faces: bool,
        notification_sent: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """
        Mark a video as processed and save the record.
        
        Args:
            video_path: Path to video file
            trigger_count: Number of trigger frames detected
            analyzed_frames: Number of frames analyzed
            total_frames: Total frames in video
            analysis_duration: Time taken for analysis (seconds)
            has_unknown_faces: Whether unknown faces were detected
            notification_sent: Whether notification was sent
            error: Error message if processing failed
        """
        normalized_path = str(Path(video_path).absolute())
        
        record = ProcessingRecord(
            video_path=normalized_path,
            processed_at=datetime.now().isoformat(),
            trigger_count=trigger_count,
            analyzed_frames=analyzed_frames,
            total_frames=total_frames,
            analysis_duration=analysis_duration,
            has_unknown_faces=has_unknown_faces,
            notification_sent=notification_sent,
            error=error,
        )
        
        self._records[normalized_path] = record
        self._save_state()
        
        logger.debug(f"Marked as processed: {Path(video_path).name}")

    def get_record(self, video_path: str) -> Optional[ProcessingRecord]:
        """
        Get processing record for a video.
        
        Args:
            video_path: Path to video file
        
        Returns:
            ProcessingRecord if found, None otherwise
        """
        normalized_path = str(Path(video_path).absolute())
        return self._records.get(normalized_path)

    def get_all_records(self) -> List[ProcessingRecord]:
        """Get all processing records."""
        return list(self._records.values())

    def get_unprocessed_videos(self, video_dir: str) -> List[Path]:
        """
        Get list of video files in directory that haven't been processed.
        
        Args:
            video_dir: Directory containing video files
        
        Returns:
            List of Path objects for unprocessed videos
        """
        video_dir = Path(video_dir)
        if not video_dir.exists():
            logger.warning(f"Video directory does not exist: {video_dir}")
            return []
        
        # Find all .mp4 files
        all_videos = list(video_dir.glob("*.mp4"))
        
        # Filter out processed ones
        unprocessed = [
            video for video in all_videos
            if not self.is_processed(str(video))
        ]
        
        return unprocessed

    def clear_state(self) -> None:
        """Clear all processing records (use with caution)."""
        self._records.clear()
        self._save_state()
        logger.warning("All processing records cleared")

    def _load_state(self) -> None:
        """Load state from JSON file."""
        if not self.state_file.exists():
            logger.debug(f"State file not found, starting fresh: {self.state_file}")
            return
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            # Convert dict to ProcessingRecord objects
            for video_path, record_dict in data.items():
                self._records[video_path] = ProcessingRecord(**record_dict)
            
            logger.info(f"Loaded {len(self._records)} processing records from {self.state_file}")
        
        except Exception as e:
            logger.error(f"Failed to load state file: {e}")
            logger.warning("Starting with empty state")

    def _save_state(self) -> None:
        """Save state to JSON file."""
        try:
            # Convert ProcessingRecord objects to dicts
            data = {
                video_path: asdict(record)
                for video_path, record in self._records.items()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"State saved to {self.state_file}")
        
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def get_statistics(self) -> Dict:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with statistics
        """
        total = len(self._records)
        with_triggers = sum(1 for r in self._records.values() if r.trigger_count > 0)
        with_unknown = sum(1 for r in self._records.values() if r.has_unknown_faces)
        with_errors = sum(1 for r in self._records.values() if r.error is not None)
        notifications_sent = sum(1 for r in self._records.values() if r.notification_sent)
        
        total_duration = sum(r.analysis_duration for r in self._records.values())
        avg_duration = total_duration / total if total > 0 else 0
        
        return {
            "total_processed": total,
            "with_triggers": with_triggers,
            "with_unknown_faces": with_unknown,
            "with_errors": with_errors,
            "notifications_sent": notifications_sent,
            "total_analysis_time": total_duration,
            "avg_analysis_time": avg_duration,
        }
