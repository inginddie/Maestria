"""
Módulo core del Jira Extractor
Contiene la lógica principal de negocio y componentes centrales
"""

from .api_client import JiraAPIClient, APIResponse, RateLimitInfo
from .processor import JiraIssueProcessor, ProcessingResult
from .storage import StorageManager, JSONStorageStrategy, CSVStorageStrategy, StatsStorageStrategy

__all__ = [
    'JiraAPIClient',
    'APIResponse',
    'RateLimitInfo',
    'JiraIssueProcessor',
    'ProcessingResult',
    'StorageManager',
    'JSONStorageStrategy',
    'CSVStorageStrategy',
    'StatsStorageStrategy'
]