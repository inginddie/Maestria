"""
Sistema de logging profesional para Jira Extractor
Utiliza structlog para logging estructurado y consistente
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    import json

from .exceptions import ConfigurationError


class JiraExtractorLogger:
    """Logger personalizado para Jira Extractor con soporte para logging estructurado"""

    def __init__(self, name: str = "jira_extractor"):
        self.name = name
        self._logger = None
        self._configured = False

    def configure(
        self,
        level: str = "INFO",
        log_file: Optional[Path] = None,
        format_string: Optional[str] = None,
        max_file_size: int = 10*1024*1024,  # 10MB
        backup_count: int = 5
    ) -> None:
        """Configura el sistema de logging"""

        if self._configured:
            return

        # Configurar nivel de logging
        numeric_level = getattr(logging, level.upper(), logging.INFO)

        # Configurar logger raíz
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        # Limpiar handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Formato por defecto
        if format_string is None:
            if STRUCTLOG_AVAILABLE:
                format_string = "%(asctime)s %(levelname)s %(message)s"
            else:
                format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Crear formatter
        formatter = logging.Formatter(format_string)

        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Handler para archivo (opcional)
        if log_file:
            try:
                log_file.parent.mkdir(parents=True, exist_ok=True)

                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_file_size,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                file_handler.setLevel(numeric_level)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)

            except Exception as e:
                print(f"Warning: Could not configure file logging: {e}")

        # Configurar structlog si está disponible
        if STRUCTLOG_AVAILABLE:
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )

        self._logger = logging.getLogger(self.name)
        self._configured = True

    def get_logger(self) -> logging.Logger:
        """Obtiene el logger configurado"""
        if not self._configured:
            self.configure()
        return self._logger

    def log_operation_start(self, operation: str, **context) -> None:
        """Registra el inicio de una operación"""
        logger = self.get_logger()
        if STRUCTLOG_AVAILABLE:
            logger.info("operation_started", operation=operation, **context)
        else:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            logger.info(f"Started {operation} {context_str}")

    def log_operation_end(self, operation: str, duration: Optional[float] = None, **context) -> None:
        """Registra el fin de una operación"""
        logger = self.get_logger()
        if STRUCTLOG_AVAILABLE:
            log_data = {"operation": operation, **context}
            if duration is not None:
                log_data["duration_seconds"] = round(duration, 2)
            logger.info("operation_completed", **log_data)
        else:
            duration_str = f" in {duration:.2f}s" if duration else ""
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            logger.info(f"Completed {operation}{duration_str} {context_str}")

    def log_error(self, error: Exception, operation: str = None, **context) -> None:
        """Registra un error con contexto"""
        logger = self.get_logger()
        error_msg = str(error)
        error_type = type(error).__name__

        if STRUCTLOG_AVAILABLE:
            log_data = {
                "error_type": error_type,
                "error_message": error_msg,
                **context
            }
            if operation:
                log_data["operation"] = operation
            logger.error("error_occurred", **log_data, exc_info=True)
        else:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            op_str = f" during {operation}" if operation else ""
            logger.error(f"{error_type}: {error_msg}{op_str} {context_str}", exc_info=True)

    def log_api_call(self, method: str, url: str, status_code: Optional[int] = None,
                    duration: Optional[float] = None, **context) -> None:
        """Registra una llamada a API"""
        logger = self.get_logger()
        if STRUCTLOG_AVAILABLE:
            log_data = {
                "method": method,
                "url": url,
                **context
            }
            if status_code:
                log_data["status_code"] = status_code
            if duration:
                log_data["duration_seconds"] = round(duration, 2)
            logger.info("api_call", **log_data)
        else:
            status_str = f" -> {status_code}" if status_code else ""
            duration_str = f" ({duration:.2f}s)" if duration else ""
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            logger.info(f"API {method} {url}{status_str}{duration_str} {context_str}")

    def log_performance(self, operation: str, items_processed: int,
                       duration: float, **context) -> None:
        """Registra métricas de rendimiento"""
        logger = self.get_logger()
        items_per_second = items_processed / duration if duration > 0 else 0

        if STRUCTLOG_AVAILABLE:
            logger.info("performance_metric", operation=operation,
                       items_processed=items_processed,
                       duration_seconds=round(duration, 2),
                       items_per_second=round(items_per_second, 2),
                       **context)
        else:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            logger.info(f"Performance: {operation} processed {items_processed} items "
                       f"in {duration:.2f}s ({items_per_second:.2f} items/s) {context_str}")


# Instancia global del logger
_logger_instance = JiraExtractorLogger()


def get_logger(name: str = None) -> logging.Logger:
    """Obtiene el logger configurado para Jira Extractor"""
    if name:
        return logging.getLogger(f"{_logger_instance.name}.{name}")
    return _logger_instance.get_logger()


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    max_file_size: int = 10*1024*1024,
    backup_count: int = 5
) -> None:
    """Configura el sistema de logging global"""
    log_file_path = Path(log_file) if log_file else None
    _logger_instance.configure(level, log_file_path, format_string, max_file_size, backup_count)


def log_function_call(func_name: str, args: Dict[str, Any] = None, **context) -> None:
    """Decorator helper para logging de llamadas a funciones"""
    logger = get_logger()
    args_str = f" with args {args}" if args else ""
    context_str = " ".join(f"{k}={v}" for k, v in context.items())
    logger.debug(f"Calling {func_name}{args_str} {context_str}")


# Configuración por defecto al importar
def _setup_default_logging():
    """Configura logging básico por defecto"""
    if not _logger_instance._configured:
        _logger_instance.configure()

_setup_default_logging()