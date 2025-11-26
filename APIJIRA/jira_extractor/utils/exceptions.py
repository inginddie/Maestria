"""
Excepciones personalizadas para Jira Extractor
Proporciona manejo de errores específico y consistente
"""

from typing import Optional, Dict, Any


class JiraExtractorError(Exception):
    """Excepción base para Jira Extractor"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ConfigurationError(JiraExtractorError):
    """Error en la configuración"""
    pass


class AuthenticationError(JiraExtractorError):
    """Error de autenticación con Jira"""
    pass


class APIError(JiraExtractorError):
    """Error en la comunicación con la API de Jira"""

    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        details = {}
        if status_code is not None:
            details["status_code"] = status_code
        if response_text:
            details["response_text"] = response_text[:200] + "..." if len(response_text) > 200 else response_text
        super().__init__(message, details)
        self.status_code = status_code
        self.response_text = response_text


class RateLimitError(APIError):
    """Error de rate limiting"""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
        if retry_after is not None:
            self.details["retry_after"] = retry_after


class ValidationError(JiraExtractorError):
    """Error de validación de datos"""
    pass


class ProcessingError(JiraExtractorError):
    """Error durante el procesamiento de datos"""
    pass


class StorageError(JiraExtractorError):
    """Error en operaciones de almacenamiento"""

    def __init__(self, message: str, file_path: Optional[str] = None):
        details = {}
        if file_path:
            details["file_path"] = file_path
        super().__init__(message, details)


class NetworkError(JiraExtractorError):
    """Error de red o conectividad"""
    pass


class TimeoutError(NetworkError):
    """Error de timeout en operaciones"""
    pass


class ProjectNotFoundError(JiraExtractorError):
    """Proyecto no encontrado en Jira"""

    def __init__(self, project_key: str):
        super().__init__(f"Proyecto '{project_key}' no encontrado", {"project_key": project_key})
        self.project_key = project_key


class FieldNotFoundError(JiraExtractorError):
    """Campo personalizado no encontrado"""

    def __init__(self, field_id: str):
        super().__init__(f"Campo '{field_id}' no encontrado", {"field_id": field_id})
        self.field_id = field_id


class JQLSyntaxError(JiraExtractorError):
    """Error de sintaxis en consulta JQL"""

    def __init__(self, jql: str, error_details: Optional[str] = None):
        details = {"jql": jql}
        if error_details:
            details["error_details"] = error_details
        super().__init__(f"Error de sintaxis JQL: {jql}", details)
        self.jql = jql
        self.error_details = error_details


class DataIntegrityError(JiraExtractorError):
    """Error de integridad de datos"""
    pass


class ConcurrencyError(JiraExtractorError):
    """Error relacionado con concurrencia"""
    pass


# Funciones helper para manejo de excepciones
def handle_api_error(response, operation: str = "API call") -> None:
    """Maneja errores de respuesta de API de manera centralizada"""
    if response.status_code == 401:
        raise AuthenticationError("Credenciales inválidas o token expirado")
    elif response.status_code == 403:
        raise AuthenticationError("Acceso denegado - verificar permisos")
    elif response.status_code == 404:
        raise APIError(f"Recurso no encontrado en {operation}", 404, response.text)
    elif response.status_code == 429:
        retry_after = response.headers.get('Retry-After')
        raise RateLimitError(
            f"Rate limit excedido en {operation}",
            retry_after=int(retry_after) if retry_after else None
        )
    elif response.status_code >= 500:
        raise APIError(f"Error del servidor en {operation}", response.status_code, response.text)
    elif response.status_code >= 400:
        raise APIError(f"Error del cliente en {operation}", response.status_code, response.text)


def handle_request_exception(exc: Exception, operation: str = "request") -> None:
    """Convierte excepciones de requests a excepciones personalizadas"""
    from requests.exceptions import Timeout, ConnectionError, RequestException

    if isinstance(exc, Timeout):
        raise TimeoutError(f"Timeout en {operation}")
    elif isinstance(exc, ConnectionError):
        raise NetworkError(f"Error de conexión en {operation}: {str(exc)}")
    elif isinstance(exc, RequestException):
        raise NetworkError(f"Error de red en {operation}: {str(exc)}")
    else:
        raise JiraExtractorError(f"Error inesperado en {operation}: {str(exc)}")


def validate_config_value(value: Any, field_name: str, expected_type: Optional[type] = None) -> None:
    """Valida valores de configuración"""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ConfigurationError(f"Campo requerido '{field_name}' está vacío o None")

    if expected_type and not isinstance(value, expected_type):
        raise ConfigurationError(
            f"Campo '{field_name}' debe ser de tipo {expected_type.__name__}, "
            f"recibido {type(value).__name__}"
        )