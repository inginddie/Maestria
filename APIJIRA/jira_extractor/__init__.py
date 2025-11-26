"""
Jira Extractor - Arquitectura modular para extracción de datos de Jira
"""

from .config import get_settings, JiraSettings
from .core import (
    JiraAPIClient,
    JiraIssueProcessor,
    StorageManager,
    ProcessingResult
)
from .utils import get_logger, configure_logging

__version__ = "1.0.0"
__all__ = [
    'get_settings',
    'JiraSettings',
    'JiraAPIClient',
    'JiraIssueProcessor',
    'StorageManager',
    'ProcessingResult',
    'get_logger',
    'configure_logging'
]