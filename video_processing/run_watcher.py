#!/usr/bin/env python3
"""
Video Processing Watcher Runner.

Entry point for the automated video processing watcher service.

Usage:
    # Run with default settings:
    python3 -m video_processing.run_watcher

    # Process existing videos on startup:
    python3 -m video_processing.run_watcher --process-existing

    # Custom recordings directory:
    python3 -m video_processing.run_watcher --recordings-dir /path/to/recordings

    # Debug mode:
    python3 -m video_processing.run_watcher --debug
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from video_processing.config import load_config
from video_processing.watcher import VideoProcessingWatcher


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


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="🔍 Automated Video Processing Watcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m video_processing.run_watcher
  python3 -m video_processing.run_watcher --process-existing
  python3 -m video_processing.run_watcher --recordings-dir ./recordings --debug
        """,
    )

    parser.add_argument(
        "--recordings-dir",
        type=str,
        default="./recordings",
        help="Directory to monitor for new videos (default: ./recordings)",
    )
    parser.add_argument(
        "--process-existing",
        action="store_true",
        help="Process existing videos in the directory on startup",
    )
    parser.add_argument(
        "--file-stable-delay",
        type=float,
        default=5.0,
        help="Seconds to wait after file modification stops before processing (default: 5.0)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum retry attempts for invalid videos (default: 2)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=3.0,
        help="Seconds to wait before retrying a failed video (default: 3.0)",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default="video_processing/processed_videos.json",
        help="Path to state persistence file (default: video_processing/processed_videos.json)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config.yaml (default: ./config.yaml)",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Path to .env file (default: ./.env)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Setup logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(log_level)

    logger = logging.getLogger(__name__)

    print("")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  🔍 Automated Video Processing Watcher                  ║")
    print("║     Monitors recordings and processes videos            ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")

    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(
            config_path=args.config,
            env_path=args.env,
        )

        # Initialize watcher
        watcher = VideoProcessingWatcher(
            config=config,
            recordings_dir=args.recordings_dir,
            process_existing=args.process_existing,
            file_stable_delay=args.file_stable_delay,
            state_file=args.state_file,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
        )

        # Start watching
        watcher.start()

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user.")
        sys.exit(0)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
