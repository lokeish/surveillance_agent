"""
Application logging module for the Surveillance Agent.

Provides a LoggingService that configures application-wide logging
based on Dynaconf settings. Injected via the DI container.
"""

from app_logging.service import LoggingService

__all__ = ["LoggingService"]
