#!/usr/bin/env python3
"""
Entry point for the Motion-Triggered Recording Pipeline.

Uses the DI container to resolve all dependencies and start the pipeline.

Usage:
    # Run from project root:
    python3 main.py

    # With debug mode:
    python3 main.py --debug
"""

import sys
import argparse

from container import Container
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
        """,
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
    print("║     Phase 2 — Frame Differencing + DI Container         ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")

    try:
        # Initialize DI container
        container = Container()

        # Configure logging first (via DI)
        logging_service = container.logging_service()
        logging_service.configure(
            level_override="DEBUG" if args.debug else None
        )

        # Build pipeline config from DI container
        # (resolves camera IP via config or auto-discovery)
        config = container.pipeline_config()

        # Start the pipeline with injected config
        pipeline = SurveillancePipeline(config=config)
        pipeline.start()

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\n🔧 Make sure your .env file is configured correctly.")
        print("   Required variables:")
        print("     SURVEILLANCE_CAMERA__USER=<camera_username>")
        print("     SURVEILLANCE_CAMERA__PASSWORD=<camera_password>")
        print("     SURVEILLANCE_CAMERA__IP=<camera_ip>  (optional — auto-discovers if not set)")
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
