"""
Cliente API profesional para Jira con manejo avanzado de rate limiting
"""

import time
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from urllib.parse import urljoin

from ..config.settings import JiraSettings
from ..utils.exceptions import APIError, RateLimitError, AuthenticationError, ConfigurationError
from ..utils.logger import get_logger


@dataclass
class RateLimitInfo:
    """Información sobre límites de rate"""
    requests_per_hour: int
    requests_per_minute: int = 60  # Asumido por defecto
    concurrent_requests: int = 10  # Asumido por defecto

    def __post_init__(self):
        if self.requests_per_minute > self.requests_per_hour:
            self.requests_per_minute = self.requests_per_hour


@dataclass
class APIResponse:
    """Respuesta estructurada de la API"""
    status_code: int
    data: Dict[str, Any]
    headers: Dict[str, str]
    url: str
    duration: float
    success: bool


class RateLimiter:
    """Manejador inteligente de rate limiting"""

    def __init__(self, rate_limit_info: RateLimitInfo):
        self.rate_limit = rate_limit_info
        self.requests_history: List[datetime] = []
        self.lock = threading.Lock()

        # Calcular intervalos mínimos
        self.min_interval_hour = 3600 / self.rate_limit.requests_per_hour  # segundos entre requests
        self.min_interval_minute = 60 / self.rate_limit.requests_per_minute

        # Usar el intervalo más restrictivo
        self.min_interval = max(self.min_interval_hour, self.min_interval_minute)

    def _cleanup_old_requests(self) -> None:
        """Limpia requests antiguos del historial"""
        cutoff = datetime.now() - timedelta(hours=1)
        self.requests_history = [req for req in self.requests_history if req > cutoff]

    def can_make_request(self) -> bool:
        """Verifica si se puede hacer un request"""
        with self.lock:
            self._cleanup_old_requests()

            if len(self.requests_history) < self.rate_limit.requests_per_hour:
                return True

            # Verificar límite por minuto también
            recent_requests = [req for req in self.requests_history
                             if req > datetime.now() - timedelta(minutes=1)]

            return len(recent_requests) < self.rate_limit.requests_per_minute

    def wait_if_needed(self) -> float:
        """Espera si es necesario para respetar límites. Retorna tiempo esperado."""
        with self.lock:
            if self.can_make_request():
                return 0.0

            # Calcular tiempo de espera necesario
            if self.requests_history:
                oldest_recent = min(self.requests_history)
                time_since_oldest = (datetime.now() - oldest_recent).total_seconds()

                if len(self.requests_history) >= self.rate_limit.requests_per_hour:
                    # Esperar hasta que pase 1 hora desde el más antiguo
                    wait_time = 3600 - time_since_oldest
                else:
                    # Esperar el intervalo mínimo
                    last_request = max(self.requests_history)
                    time_since_last = (datetime.now() - last_request).total_seconds()
                    wait_time = max(0, self.min_interval - time_since_last)

                if wait_time > 0:
                    time.sleep(wait_time)
                    return wait_time

            return 0.0

    def record_request(self) -> None:
        """Registra un request realizado"""
        with self.lock:
            self.requests_history.append(datetime.now())
            self._cleanup_old_requests()


class JiraAPIClient:
    """Cliente API profesional para Jira con rate limiting inteligente"""

    def __init__(self, settings: JiraSettings):
        self.settings = settings
        self.logger = get_logger("api_client")

        # Crear base_url
        self.base_url = f"https://{settings.domain}"

        # Configurar rate limiting
        self.rate_limit_info = RateLimitInfo(
            requests_per_hour=settings.rate_limit_max_calls,
            requests_per_minute=int(settings.rate_limit_period),
            concurrent_requests=10  # Valor fijo por ahora
        )

        self.rate_limiter = RateLimiter(self.rate_limit_info)

        # Configurar autenticación
        self.auth = HTTPBasicAuth(settings.email, settings.api_token)

        # Configurar sesión HTTP
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'JiraExtractor/1.0'
        })

        # Configurar timeouts
        self.request_timeout = getattr(settings, 'request_timeout', 30)
        self.max_retries = getattr(settings, 'max_retries', 3)

        # Estadísticas
        self.stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'total_wait_time': 0.0,
            'rate_limit_hits': 0
        }

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Maneja errores de rate limit"""
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            wait_time = int(retry_after)
            self.logger.warning(f"Rate limit hit, waiting {wait_time} seconds")
            self.stats['rate_limit_hits'] += 1
            time.sleep(wait_time)
            self.stats['total_wait_time'] += wait_time

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> APIResponse:
        """Realiza una petición HTTP con manejo de errores y rate limiting"""

        url = urljoin(self.base_url, endpoint.lstrip('/'))

        # Esperar si es necesario por rate limiting
        wait_time = self.rate_limiter.wait_if_needed()
        if wait_time > 0:
            self.logger.debug(f"Rate limiter waited {wait_time:.2f} seconds")

        start_time = time.time()

        try:
            self.logger.info(f"API {method} {url}")

            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.request_timeout
            )

            duration = time.time() - start_time
            self.stats['requests_made'] += 1

            # Registrar el request en el rate limiter
            self.rate_limiter.record_request()

            # Manejar rate limit
            if response.status_code == 429:
                self._handle_rate_limit(response)
                if retry_count < self.max_retries:
                    self.logger.info(f"Retrying request after rate limit (attempt {retry_count + 1})")
                    return self._make_request(method, endpoint, params, json_data, retry_count + 1)

            # Manejar errores de autenticación
            if response.status_code == 401:
                raise AuthenticationError("Invalid API token or email")

            # Manejar errores de configuración
            if response.status_code == 400:
                raise ConfigurationError(f"Bad request: {response.text}")

            # Para otros errores, intentar parsear JSON
            try:
                data = response.json() if response.content else {}
            except ValueError:
                data = {"error": "Invalid JSON response", "raw_content": response.text[:500]}

            success = 200 <= response.status_code < 300

            if not success:
                self.stats['requests_failed'] += 1
                error_msg = data.get('message', data.get('error', f'HTTP {response.status_code}'))
                raise APIError(f"API request failed: {error_msg}", status_code=response.status_code)

            api_response = APIResponse(
                status_code=response.status_code,
                data=data,
                headers=dict(response.headers),
                url=url,
                duration=duration,
                success=success
            )

            self.logger.info(f"API {method} {url} -> {response.status_code} ({duration:.2f}s)")

            return api_response

        except requests.RequestException as e:
            duration = time.time() - start_time
            self.stats['requests_failed'] += 1

            if retry_count < self.max_retries:
                wait_time = min(2 ** retry_count, 30)  # Exponential backoff, max 30s
                self.logger.warning(f"Request failed, retrying in {wait_time}s (attempt {retry_count + 1}): {e}")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, json_data, retry_count + 1)

            raise APIError(f"Request failed after {self.max_retries} retries: {e}")

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        """Realiza una petición GET"""
        return self._make_request('GET', endpoint, params=params)

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> APIResponse:
        """Realiza una petición POST"""
        return self._make_request('POST', endpoint, json_data=json_data)

    def search_issues(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
        expand: Optional[List[str]] = None
    ) -> APIResponse:
        """Busca issues usando JQL"""

        params = {
            'jql': jql,
            'startAt': start_at,
            'maxResults': max_results
        }

        if fields:
            params['fields'] = ','.join(fields)

        if expand:
            params['expand'] = ','.join(expand)

        return self.get('/rest/api/3/search', params=params)

    def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> APIResponse:
        """Obtiene un issue específico"""

        params = {}
        if fields:
            params['fields'] = ','.join(fields)

        return self.get(f'/rest/api/3/issue/{issue_key}', params=params)

    def get_projects(self) -> APIResponse:
        """Obtiene la lista de proyectos disponibles"""
        return self.get('/rest/api/3/project')

    def get_boards(self, project_key: Optional[str] = None, start_at: int = 0, max_results: int = 50) -> APIResponse:
        """Obtiene boards de proyecto"""

        params = {
            'startAt': start_at,
            'maxResults': max_results
        }

        if project_key:
            params['projectKeyOrId'] = project_key  # Puede ser string o int

        return self.get('/rest/agile/1.0/board', params=params)

    def get_board_issues(
        self,
        board_id: int,
        jql: Optional[str] = None,
        start_at: int = 0,
        max_results: int = 50,
        fields: Optional[List[str]] = None
    ) -> APIResponse:
        """Obtiene issues de un board específico"""

        params = {
            'startAt': start_at,
            'maxResults': max_results,
            'fields': ','.join(fields) if fields else '*all',
            'expand': 'names'
        }

        if jql:
            params['jql'] = jql

        return self.get(f'/rest/agile/1.0/board/{board_id}/issue', params=params)

    def get_myself(self) -> APIResponse:
        """Obtiene información del usuario autenticado"""
        return self.get('/rest/api/3/myself')

    def get_fields(self) -> APIResponse:
        """Obtiene la lista de campos disponibles"""
        return self.get('/rest/api/3/field')

    def validate_connection(self) -> bool:
        """Valida la conexión y credenciales"""
        try:
            response = self.get_myself()
            return response.success
        except Exception as e:
            self.logger.error(f"Connection validation failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cliente"""
        return {
            **self.stats,
            'rate_limit_info': {
                'requests_per_hour': self.rate_limit_info.requests_per_hour,
                'requests_per_minute': self.rate_limit_info.requests_per_minute,
                'concurrent_requests': self.rate_limit_info.concurrent_requests
            },
            'current_queue_size': len(self.rate_limiter.requests_history)
        }

    def close(self) -> None:
        """Cierra la sesión HTTP"""
        self.session.close()