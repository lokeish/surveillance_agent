"""
Configuration module for the Surveillance Agent.

Uses Dynaconf to load settings from config.yaml and .env files.
Uses PipelineConfigFactory to build typed config dataclasses.
"""

from config.dynaconf import settings
from config.factory import PipelineConfigFactory

__all__ = ["settings", "PipelineConfigFactory"]
