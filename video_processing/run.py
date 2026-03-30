"""
Video Processing Runner.

Command-line interface for running video analysis.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from .config import load_config, VideoProcessingConfig
from .video_analyzer import VideoAnalyzer


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)-24s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)


def print_analysis_result(result) -> None:
    """Print formatted analysis results."""
    print("\n" + "=" * 60)
    print("  📊 VIDEO ANALYSIS RESULTS")
    print("=" * 60)
    print(f"  Video: {Path(result.video_path).name}")
    print(f"  Total frames: {result.total_frames}")
    print(f"  Analyzed frames: {result.analyzed_frames}")
    print(f"  Trigger frames: {len(result.trigger_frames)}")
    print(f"  Analysis duration: {result.analysis_duration:.2f}s")
    print("=" * 60)

    if result.trigger_frames:
        print("\n🔔 TRIGGER EVENTS:")
        print("-" * 60)
        for i, frame_analysis in enumerate(result.trigger_frames[:10], 1):
            timestamp_str = f"{int(frame_analysis.timestamp // 60):02d}:{int(frame_analysis.timestamp % 60):02d}"
            print(f"  {i}. Frame {frame_analysis.frame_idx} @ {timestamp_str}")
            print(f"     Faces detected: {len(frame_analysis.faces)}")
            
            for j, match in enumerate(frame_analysis.face_matches):
                if match:
                    status = "✓ Known" if match.is_match else "✗ Unknown"
                    print(f"       Face {j+1}: {status} - {match.person_name} "
                          f"(score: {match.similarity_score:.3f})")
                else:
                    print(f"       Face {j+1}: ✗ Unknown (no match)")
        
        if len(result.trigger_frames) > 10:
            print(f"  ... and {len(result.trigger_frames) - 10} more trigger events")
        print("-" * 60)

    if result.ai_summary:
        print("\n🤖 AI ANALYSIS SUMMARY:")
        print("-" * 60)
        print(result.ai_summary)
        print("-" * 60)
    
    print()


def main(video_path: Optional[str] = None, use_ai: bool = True) -> None:
    """
    Main entry point for video processing.
    
    Args:
        video_path: Path to video file to analyze
        use_ai: Whether to use AI for summary generation
    """
    # Setup logging
    setup_logging("INFO")
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()

        # Initialize analyzer
        logger.info("Initializing video analyzer...")
        analyzer = VideoAnalyzer(config)

        # Get video path from command line if not provided
        if video_path is None:
            if len(sys.argv) < 2:
                print("Usage: python -m video_processing.run <video_path>")
                print("\nExample:")
                print("  python -m video_processing.run recordings/motion_2026-03-29_17-03-06.mp4")
                sys.exit(1)
            video_path = sys.argv[1]

        # Analyze video
        result = analyzer.analyze_video(video_path, use_ai_summary=use_ai)

        # Print results
        print_analysis_result(result)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during video analysis: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
