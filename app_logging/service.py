"""
Logging Service Module.

Configures application-wide logging (console + file handlers)
based on Dynaconf settings. All configuration values are read
from the 'logging' section of config.yaml.

Injected as a singleton via the DI container — call .configure()
once at application startup.
"""

import logging
from pathlib import Path

from dynaconf import Dynaconf


class LoggingService:
    """
    Application-wide logging configurator.

    Reads from Dynaconf settings.logging:
        - level: Log level (DEBUG, INFO, WARNING, ERROR)
        - log_to_file: Whether to also log to a file
        - log_file: Path to the log file

    Usage (via DI container):
        logging_service = container.logging_service()
        logging_service.configure()
    """

    LOG_FORMAT = "%(asctime)s │ %(levelname)-8s │ %(name)-24s │ %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, settings: Dynaconf) -> None:
        """
        Initialize LoggingService with Dynaconf settings.

        Args:
            settings: Dynaconf settings instance with 'logging' section.
        """
        self._settings = settings
        self._configured = False

    @property
    def is_configured(self) -> bool:
        """Whether logging has been configured."""
        return self._configured

    def configure(self, level_override: str | None = None) -> None:
        """
        Configure application-wide logging.

        Sets up console handler and optionally a file handler
        based on settings. Safe to call multiple times — only
        configures once unless force=True.

        Args:
            level_override: Override log level (e.g., "DEBUG").
                            Takes precedence over config.yaml.
        """
        if self._configured:
            return

        log_cfg = self._settings.logging
        level_str = level_override or log_cfg.get("level", "INFO")
        log_level = getattr(logging, level_str.upper(), logging.INFO)

        formatter = logging.Formatter(
            fmt=self.LOG_FORMAT,
            datefmt=self.LOG_DATE_FORMAT,
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(console_handler)

        # File handler (optional)
        if log_cfg.get("log_to_file", True):
            log_file = log_cfg.get("log_file", "./logs/surveillance.log")
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            logging.getLogger(__name__).debug(
                f"Logging to file: {log_path.absolute()}"
            )

        self._configured = True
        logging.getLogger(__name__).info(
            f"Logging configured: level={level_str}, "
            f"file={'enabled' if log_cfg.get('log_to_file', True) else 'disabled'}"
        )
