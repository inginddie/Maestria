"""
Configuración simplificada para Jira Extractor
Versión compatible con Pydantic V2 sin configuraciones complejas
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class JiraSettings:
    """Configuración específica para Jira API"""

    # Credenciales
    api_token: str = ""
    email: str = "dbusto3@bancodebogota.com.co"
    domain: str = "bancodebogota.atlassian.net"

    # Proyectos
    projects: List[str] = field(default_factory=lambda: ["RSW"])
    project_blocks: List[List[str]] = field(
        default_factory=lambda: [["RSW"]]
    )

    # Campos
    default_fields: List[str] = field(
        default_factory=lambda: [
            "sprint", "created", "key", "summary", "description", "issuetype",
            "customfield_11112", "customfield_11113", "customfield_11111", "customfield_11115",
            "customfield_11180", "customfield_11181", "customfield_11365", "customfield_10200",
            "customfield_10103", "customfield_10020",
        ]
    )
    min_fields: List[str] = field(default_factory=lambda: ["created", "key", "summary", "issuetype"])
    sprint_alternatives: List[str] = field(default_factory=lambda: ["customfield_10103", "customfield_10020", "sprint"])

    # Filtros
    issue_types: Optional[List[str]] = None
    statuses: Optional[List[str]] = None
    excluded_types: List[str] = field(default_factory=lambda: ["Criterio de aceptación", "Xray Test"])

    # Fechas
    date_field: str = "created"
    created_from: Optional[str] = None
    created_to: Optional[str] = None
    updated_from: Optional[str] = None
    updated_to: Optional[str] = None

    # API Configuration
    max_results: int = 50
    request_timeout: int = 30
    max_retries: int = 3
    delay_between_requests: float = 1.0

    # Rate Limiting
    rate_limit_max_calls: int = 50
    rate_limit_period: float = 60.0
    backoff_multiplier: float = 2.0
    max_backoff_time: float = 300.0

    # Flags
    force_agile: bool = False
    export_csv: bool = True
    list_fields: Optional[str] = None


@dataclass
class StorageSettings:
    """Configuración para almacenamiento de datos"""

    output_dir: Path = field(default_factory=lambda: Path("./exports"))
    file_prefix: str = "issues"
    ensure_dir: bool = True

    # Formatos de salida
    json_indent: int = 2
    csv_delimiter: str = ","


@dataclass
class LoggingSettings:
    """Configuración para logging"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[Path] = None
    max_file_size: int = 10*1024*1024  # 10MB
    backup_count: int = 5


@dataclass
class AppSettings:
    """Configuración general de la aplicación"""

    jira: JiraSettings = field(default_factory=JiraSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    # Configuración de paralelización
    max_workers: int = 4
    chunk_size: int = 1000


def load_env_file(path: str = ".env") -> Dict[str, str]:
    """Carga variables de entorno desde archivo .env"""
    env_vars = {}

    if os.path.isfile(path):
        try:
            from dotenv import load_dotenv
            load_dotenv(path)
        except ImportError:
            # Fallback si dotenv no está disponible
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"')
                        os.environ[key.strip()] = value.strip().strip('"')

    # Agregar variables de entorno existentes
    for key, value in os.environ.items():
        if key.startswith('JIRA_') or key.startswith('LOG_'):
            env_vars[key] = value

    return env_vars


def create_settings_from_env() -> AppSettings:
    """Crea configuración desde variables de entorno"""
    env_vars = load_env_file()

    # Configuración Jira
    jira_settings = JiraSettings(
        api_token=env_vars.get('JIRA_API_TOKEN', ''),
        email=env_vars.get('JIRA_EMAIL', 'dbusto3@bancodebogota.com.co'),
        domain=env_vars.get('JIRA_DOMAIN', 'bancodebogota.atlassian.net'),
        projects=env_vars.get('JIRA_PROJECTS', 'RSW').split(','),
        force_agile=env_vars.get('JIRA_FORCE_AGILE', 'false').lower() == 'true',
        created_from=env_vars.get('JIRA_CREATED_FROM'),
        created_to=env_vars.get('JIRA_CREATED_TO'),
        max_results=int(env_vars.get('JIRA_MAX_RESULTS', '50')),
        request_timeout=int(env_vars.get('JIRA_REQUEST_TIMEOUT', '30')),
        max_retries=int(env_vars.get('JIRA_MAX_RETRIES', '3'))
    )

    # Configuración Storage
    storage_settings = StorageSettings(
        output_dir=Path(env_vars.get('JIRA_OUTPUT_DIR', './exports')),
        file_prefix=env_vars.get('JIRA_FILE_PREFIX', 'issues')
    )

    # Configuración Logging
    log_file = env_vars.get('LOG_FILE')
    logging_settings = LoggingSettings(
        level=env_vars.get('LOG_LEVEL', 'INFO'),
        file_path=Path(log_file) if log_file else None
    )

    return AppSettings(
        jira=jira_settings,
        storage=storage_settings,
        logging=logging_settings
    )


def get_settings() -> AppSettings:
    """Obtiene la configuración de la aplicación"""
    return create_settings_from_env()


# Instancia global de configuración (lazy loading)
_settings = None

def get_global_settings() -> AppSettings:
    """Obtiene la configuración global (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings