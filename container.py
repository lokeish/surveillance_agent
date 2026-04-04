"""
Dependency Injection Container for the Surveillance Agent.

Uses dependency-injector to wire all components together.
All dependencies are declared here and injected into components —
no component creates its own dependencies.
"""

from dependency_injector import containers, providers

from config.dynaconf import settings
from config.factory import PipelineConfigFactory
from network.camera_scanner import CameraScanner
from app_logging.service import LoggingService


class Container(containers.DeclarativeContainer):
    """
    Root dependency injection container.

    Wiring order:
        1. Dynaconf settings (loaded from config.yaml + .env)
        2. LoggingService (configures app-wide logging)
        3. CameraScanner (receives settings, discovers camera IP)
        4. PipelineConfigFactory (builds config from settings + scanner)
        5. PipelineConfig (the built result)
    """

    # ── Configuration ────────────────────────────
    config = providers.Object(settings)

    # ── Logging ──────────────────────────────────
    logging_service = providers.Singleton(
        LoggingService,
        settings=config,
    )

    # ── Network ──────────────────────────────────
    camera_scanner = providers.Singleton(
        CameraScanner,
        settings=config,
    )

    # ── Config Factory ───────────────────────────
    config_factory = providers.Singleton(
        PipelineConfigFactory,
        settings=config,
        camera_scanner=camera_scanner,
    )

    # ── Pipeline Config ──────────────────────────
    pipeline_config = providers.Singleton(
        lambda factory: factory.build(),
        factory=config_factory,
    )
