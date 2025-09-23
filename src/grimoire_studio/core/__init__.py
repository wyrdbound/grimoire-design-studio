"""
Core functionality for GRIMOIRE Design Studio.

This package contains core services and infrastructure components
including configuration management, project handling, and validation.
"""

from .config import AppConfig
from .project_manager import ProjectManager

__all__ = ["AppConfig", "ProjectManager"]
