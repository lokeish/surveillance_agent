"""
Dynaconf configuration handler.

Initializes Dynaconf to load settings from:
  1. config.yaml  — All pipeline & network settings
  2. .env          — Secrets and environment-specific overrides

Environment variables with the SURVEILLANCE_ prefix will override
config.yaml values. Use double underscores (__) for nested keys.

Examples:
    export SURVEILLANCE_CAMERA__IP="192.168.1.100"
    export SURVEILLANCE_CAMERA__USER="admin"
    export SURVEILLANCE_NETWORK__SCAN_TIMEOUT=2.0
"""

from pathlib import Path
from dynaconf import Dynaconf

# Project root directory (parent of config/)
_PROJECT_ROOT = Path(__file__).parent.parent

settings = Dynaconf(
    envvar_prefix="SURVEILLANCE",
    settings_files=[str(_PROJECT_ROOT / "config.yaml")],
    load_dotenv=True,
    dotenv_path=str(_PROJECT_ROOT / ".env"),
    merge_enabled=True,
)
