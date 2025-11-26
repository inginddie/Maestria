"""
Procesador de datos para Jira Extractor
Separa la lógica de procesamiento de datos en componentes reutilizables
"""

import re
import html
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from ..utils.exceptions import ProcessingError
from ..utils.logger import get_logger


@dataclass
class ProcessingResult:
    """Resultado del procesamiento de un issue"""
    key: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class FieldProcessor(ABC):
    """Procesador abstracto para campos específicos"""

    def __init__(self, field_name: str):
        self.field_name = field_name
        self.logger = get_logger(f"field_processor.{field_name}")

    @abstractmethod
    def process(self, raw_value: Any, context: Dict[str, Any]) -> Any:
        """Procesa un valor crudo del campo"""
        pass

    def validate(self, value: Any) -> bool:
        """Valida si el valor procesado es correcto"""
        return True

    def get_default_value(self) -> Any:
        """Retorna el valor por defecto si el procesamiento falla"""
        return None


class DateFieldProcessor(FieldProcessor):
    """Procesador especializado para campos de fecha"""

    def __init__(self, field_name: str, input_formats: Optional[List[str]] = None, output_format: str = "%Y-%m-%dT%H:%M:%S.%f%z"):
        super().__init__(field_name)
        self.input_formats = input_formats or [
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%d/%b/%y %I:%M %p",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M"
        ]
        self.output_format = output_format

    def process(self, raw_value: Any, context: Dict[str, Any]) -> Optional[str]:
        if not raw_value:
            return None

        raw_str = str(raw_value).strip()
        if not raw_str:
            return None

        # Si ya está en el formato correcto, retornarlo
        if self._is_correct_format(raw_str):
            return raw_str

        # Intentar parsear con diferentes formatos
        for fmt in self.input_formats:
            try:
                dt = datetime.strptime(raw_str, fmt)
                # Si no tiene timezone, asumir UTC
                if dt.tzinfo is None:
                    # Obtener offset del contexto o usar -0500 por defecto
                    offset_str = context.get('created_offset', '-0500')
                    if offset_str.startswith('+') or offset_str.startswith('-'):
                        # Convertir offset a horas y minutos
                        offset_hours = int(offset_str[:3])
                        offset_minutes = int(offset_str[3:]) if len(offset_str) > 3 else 0
                        tz = timezone(timedelta(hours=offset_hours, minutes=offset_minutes))
                        dt = dt.replace(tzinfo=tz)
                    else:
                        dt = dt.replace(tzinfo=timezone(timedelta(hours=-5)))  # UTC-5 por defecto

                return dt.strftime(self.output_format)
            except ValueError:
                continue

        self.logger.warning(f"Could not parse date '{raw_str}' for field {self.field_name}")
        return raw_str  # Retornar original si no se puede parsear

    def _is_correct_format(self, date_str: str) -> bool:
        """Verifica si la fecha ya está en el formato correcto"""
        try:
            datetime.strptime(date_str, self.output_format)
            return True
        except ValueError:
            return False


class ObjectFieldProcessor(FieldProcessor):
    """Procesador para campos que son objetos (status, issuetype, assignee, etc.)"""

    def __init__(self, field_name: str, extract_keys: Optional[List[str]] = None):
        super().__init__(field_name)
        self.extract_keys = extract_keys or ['name', 'displayName', 'value', 'id']

    def process(self, raw_value: Any, context: Dict[str, Any]) -> Any:
        if raw_value is None:
            return None

        if isinstance(raw_value, dict):
            # Intentar extraer valores de las claves preferidas
            for key in self.extract_keys:
                if key in raw_value and raw_value[key] is not None:
                    return str(raw_value[key])

            # Si no encuentra ninguna clave preferida, convertir a string
            return str(raw_value)

        if isinstance(raw_value, list):
            # Para listas de objetos, extraer valores de cada elemento
            processed_items = []
            for item in raw_value:
                if isinstance(item, dict):
                    for key in self.extract_keys:
                        if key in item and item[key] is not None:
                            processed_items.append(str(item[key]))
                            break
                    else:
                        processed_items.append(str(item))
                else:
                    processed_items.append(str(item))
            return ', '.join(processed_items)

        return str(raw_value)


class SprintFieldProcessor(FieldProcessor):
    """Procesador especializado para campos de sprint"""

    def process(self, raw_value: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        if not raw_value:
            return {}

        sprints = raw_value if isinstance(raw_value, list) else [raw_value]
        result = {}

        # Extraer información de sprints
        sprint_names = []
        board_ids = []
        start_dates = []
        end_dates = []
        complete_dates = []

        for sprint in sprints:
            if isinstance(sprint, dict):
                if sprint.get('name'):
                    sprint_names.append(sprint['name'])
                if sprint.get('boardId'):
                    board_ids.append(str(sprint['boardId']))
                if sprint.get('startDate'):
                    start_dates.append(sprint['startDate'])
                if sprint.get('endDate'):
                    end_dates.append(sprint['endDate'])
                if sprint.get('completeDate'):
                    complete_dates.append(sprint['completeDate'])

        result['sprint'] = ', '.join(sprint_names) if sprint_names else ''
        result['boardId'] = ', '.join(board_ids) if board_ids else ''
        result['startDate'] = ', '.join(start_dates) if start_dates else ''
        result['endDate'] = ', '.join(end_dates) if end_dates else ''
        result['completeDate'] = ', '.join(complete_dates) if complete_dates else ''

        # Calcular campos adicionales
        if sprint_names:
            result['sprint_numbers'] = ', '.join(re.findall(r'\d+', ' '.join(sprint_names)))
            result['cantidad_sprint'] = len(sprint_names)
        else:
            result['sprint_numbers'] = ''
            result['cantidad_sprint'] = 0

        # Determinar período basado en completeDate
        if complete_dates:
            result['periodo'] = self._determine_period(complete_dates[0])
        else:
            result['periodo'] = 'Otro'

        return result

    def _determine_period(self, complete_date: str) -> str:
        """Determina el período basado en la fecha de completación"""
        try:
            # Parsear fecha (asumiendo formato ISO)
            dt = datetime.fromisoformat(complete_date.replace('Z', '+00:00'))

            # Definir rangos
            piloto_inicio = datetime(2024, 6, 1)
            piloto_fin = datetime(2024, 12, 31)

            if piloto_inicio <= dt <= piloto_fin:
                return "Durante piloto"
            elif dt < piloto_inicio:
                return "Antes piloto"
            else:
                return "Otro"
        except Exception:
            return "Otro"


class DescriptionFieldProcessor(FieldProcessor):
    """Procesador especializado para campos de descripción con formato ADF"""

    def process(self, raw_value: Any, context: Dict[str, Any]) -> str:
        if raw_value is None:
            return ""

        if isinstance(raw_value, dict):
            return self._walk_adf(raw_value)
        elif isinstance(raw_value, list):
            return "\n".join(self._walk_adf(item) if isinstance(item, dict) else str(item) for item in raw_value)
        else:
            # Limpiar HTML básico si es string
            text = str(raw_value)
            text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = html.unescape(text)
            return re.sub(r"\s+", " ", text).strip()

    def _walk_adf(self, node: Dict[str, Any]) -> str:
        """Recorre un documento ADF (Atlassian Document Format)"""
        if not isinstance(node, dict):
            return str(node)

        node_type = node.get('type', '')
        content = node.get('content', [])

        if node_type in ('paragraph', 'heading', 'bulletList', 'orderedList'):
            texts = []
            for child in content:
                texts.append(self._walk_adf(child))
            result = " ".join(filter(None, texts))
            return result + "\n" if node_type in ('paragraph', 'heading') else result

        elif node_type == 'text':
            return node.get('text', '')

        elif node_type in ('listItem',):
            texts = []
            for child in content:
                texts.append(self._walk_adf(child))
            return "• " + " ".join(filter(None, texts))

        else:
            # Para otros tipos, procesar recursivamente
            texts = []
            for child in content:
                texts.append(self._walk_adf(child))
            return " ".join(filter(None, texts))


class JiraIssueProcessor:
    """Procesador principal para issues de Jira"""

    def __init__(self):
        self.logger = get_logger("issue_processor")

        # Configurar procesadores de campo
        self.field_processors = {
            'created': DateFieldProcessor('created'),
            'updated': DateFieldProcessor('updated'),
            'paso_a_desarrollo': DateFieldProcessor('paso_a_desarrollo'),
            'paso_a_pruebas': DateFieldProcessor('paso_a_pruebas'),
            'paso_a_validacion': DateFieldProcessor('paso_a_validacion'),
            'paso_a_done': DateFieldProcessor('paso_a_done'),
            'paso_a_release': DateFieldProcessor('paso_a_release'),
            'paso_a_produccion': DateFieldProcessor('paso_a_produccion'),
            'status': ObjectFieldProcessor('status'),
            'issuetype': ObjectFieldProcessor('issuetype'),
            'assignee': ObjectFieldProcessor('assignee'),
            'reporter': ObjectFieldProcessor('reporter'),
            'priority': ObjectFieldProcessor('priority'),
            'resolution': ObjectFieldProcessor('resolution'),
            'sprint': SprintFieldProcessor('sprint'),
            'description': DescriptionFieldProcessor('description'),
        }

        # Configurar campos calculados
        self.calculated_fields = {
            'team': self._extract_team,
            'cycle_time': self._calculate_cycle_time,
            'lead_time': self._calculate_lead_time,
            'wait_time': self._calculate_wait_time,
        }

    def process_issue(self, raw_issue: Dict[str, Any]) -> ProcessingResult:
        """Procesa un issue crudo de la API de Jira"""

        try:
            key = raw_issue.get('key', 'N/A')
            fields = raw_issue.get('fields', {})

            # Extraer offset de fecha de creación para contexto
            created_offset = self._extract_created_offset(fields.get('created', ''))

            context = {
                'created_offset': created_offset,
                'issue_key': key,
                'all_fields': fields
            }

            processed_data = {}
            errors = []

            # Procesar campos básicos
            processed_data.update(self._process_basic_fields(fields, context, errors))

            # Procesar campos con procesadores especializados
            processed_data.update(self._process_specialized_fields(fields, context, errors))

            # Calcular campos derivados
            processed_data.update(self._calculate_derived_fields(processed_data, context, errors))

            return ProcessingResult(
                key=key,
                data=processed_data,
                metadata={
                    'processing_timestamp': datetime.now().isoformat(),
                    'field_count': len(processed_data),
                    'error_count': len(errors)
                },
                errors=errors
            )

        except Exception as e:
            self.logger.error(f"Error processing issue {raw_issue.get('key', 'N/A')}: {e}")
            return ProcessingResult(
                key=raw_issue.get('key', 'N/A'),
                data={},
                errors=[f"Processing failed: {str(e)}"]
            )

    def process_issues_batch(self, raw_issues: List[Dict[str, Any]]) -> List[ProcessingResult]:
        """Procesa un lote de issues"""
        self.logger.info(f"Processing batch of {len(raw_issues)} issues")

        results = []
        for i, issue in enumerate(raw_issues):
            result = self.process_issue(issue)
            results.append(result)

            if (i + 1) % 50 == 0:
                success_count = sum(1 for r in results if not r.has_errors)
                self.logger.info(f"Processed {i + 1}/{len(raw_issues)} issues ({success_count} successful)")

        return results

    def _process_basic_fields(self, fields: Dict[str, Any], context: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """Procesa campos básicos que no requieren procesadores especializados"""
        basic_fields = {}

        # Campos directos
        direct_fields = ['summary', 'customfield_10200']  # story_points
        for field in direct_fields:
            value = fields.get(field)
            if value is not None:
                basic_fields[field] = str(value)
            else:
                basic_fields[field] = ''

        # Campos de custom fields específicos
        custom_fields = [
            'customfield_11112', 'customfield_11113', 'customfield_11111',
            'customfield_11115', 'customfield_11180', 'customfield_11181',
            'customfield_11365', 'customfield_10103', 'customfield_10020'
        ]

        for cf in custom_fields:
            value = fields.get(cf)
            if value is not None:
                basic_fields[cf] = str(value)
            else:
                basic_fields[cf] = ''

        return basic_fields

    def _process_specialized_fields(self, fields: Dict[str, Any], context: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """Procesa campos con procesadores especializados"""
        processed = {}

        for field_name, processor in self.field_processors.items():
            try:
                raw_value = fields.get(field_name)
                processed_value = processor.process(raw_value, context)

                if field_name == 'sprint' and isinstance(processed_value, dict):
                    # El procesador de sprint retorna un diccionario con múltiples campos
                    processed.update(processed_value)
                else:
                    processed[field_name] = processed_value

            except Exception as e:
                error_msg = f"Error processing field {field_name}: {str(e)}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
                processed[field_name] = processor.get_default_value()

        return processed

    def _calculate_derived_fields(self, processed_data: Dict[str, Any], context: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """Calcula campos derivados"""
        derived = {}

        for field_name, calculator in self.calculated_fields.items():
            try:
                value = calculator(processed_data, context)
                derived[field_name] = value
            except Exception as e:
                error_msg = f"Error calculating field {field_name}: {str(e)}"
                errors.append(error_msg)
                derived[field_name] = None

        return derived

    def _extract_created_offset(self, created_str: str) -> str:
        """Extrae el offset de timezone de la fecha de creación"""
        if not created_str:
            return "-0500"
        match = re.search(r'([+-]\d{4})$', str(created_str))
        return match.group(1) if match else "-0500"

    def _extract_team(self, data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Extrae el equipo del key del issue"""
        key = data.get('key', '')
        match = re.split(r'-', key)
        return match[0] if match else 'N/A'

    def _calculate_cycle_time(self, data: Dict[str, Any], context: Dict[str, Any]) -> Optional[float]:
        """Calcula el cycle time (desarrollo a done)"""
        start_date = data.get('paso_a_desarrollo')
        end_date = data.get('paso_a_done')

        if not start_date or not end_date:
            return None

        try:
            start = self._parse_datetime(start_date)
            end = self._parse_datetime(end_date)

            if start and end and end > start:
                return round((end - start).total_seconds() / 86400.0, 2)
        except Exception:
            pass

        return None

    def _calculate_lead_time(self, data: Dict[str, Any], context: Dict[str, Any]) -> Optional[float]:
        """Calcula el lead time (creación a done)"""
        start_date = data.get('created')
        end_date = data.get('paso_a_done')

        if not start_date or not end_date:
            return None

        try:
            start = self._parse_datetime(start_date)
            end = self._parse_datetime(end_date)

            if start and end and end > start:
                return round((end - start).total_seconds() / 86400.0, 2)
        except Exception:
            pass

        return None

    def _calculate_wait_time(self, data: Dict[str, Any], context: Dict[str, Any]) -> Optional[float]:
        """Calcula el wait time (creación a desarrollo)"""
        start_date = data.get('created')
        end_date = data.get('paso_a_desarrollo')

        if not start_date or not end_date:
            return None

        try:
            start = self._parse_datetime(start_date)
            end = self._parse_datetime(end_date)

            if start and end and end > start:
                return round((end - start).total_seconds() / 86400.0, 2)
        except Exception:
            pass

        return None

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parsea una fecha string a datetime object"""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None