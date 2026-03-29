#!/usr/bin/env python3
"""
Entry point for the Motion-Triggered Recording Pipeline.

Usage:
    # Run from project root:
    python3 -m video_pipeline.run

    # Or with custom config:
    python3 -m video_pipeline.run --config /path/to/config.yaml

    # With custom .env:
    python3 -m video_pipeline.run --env /path/to/.env

    # Debug mode (override config):
    python3 -m video_pipeline.run --debug
"""

import sys
import argparse
from pathlib import Path

# Add project root to path so imports work
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from video_pipeline.config import load_config, setup_logging
from video_pipeline.pipeline import SurveillancePipeline


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="📹 Motion-Triggered Surveillance Recording Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                    # Run with default config
  python3 main.py --debug            # Run with debug logging
  python3 main.py --config my.yaml   # Run with custom config
        """,
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
        help="Enable debug logging (overrides config.yaml)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    print("")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  📹 Motion-Triggered Surveillance Recording Pipeline    ║")
    print("║     Phase 2 — Frame Differencing                       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")

    try:
        # Load configuration
        config = load_config(
            config_path=args.config,
            env_path=args.env,
        )

        # Override debug if requested
        if args.debug:
            config.logging.level = "DEBUG"

        # Start the pipeline
        pipeline = SurveillancePipeline(config=config)
        pipeline.start()

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\n🔧 Make sure your .env file is configured correctly.")
        print("   See .env.example for reference.")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user.")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
