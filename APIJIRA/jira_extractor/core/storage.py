"""
Módulo de almacenamiento para Jira Extractor
Implementa estrategias múltiples de almacenamiento con patrón Strategy
"""

import json
import csv
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime

from ..utils.exceptions import StorageError
from ..utils.logger import get_logger
from .processor import ProcessingResult


class StorageStrategy(ABC):
    """Interfaz base para estrategias de almacenamiento"""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.logger = get_logger(f"storage.{self.__class__.__name__}")

    @abstractmethod
    def save(self, data: List[ProcessingResult], filename_prefix: str, **kwargs) -> Dict[str, Any]:
        """Guarda los datos usando la estrategia específica"""
        pass

    @abstractmethod
    def get_file_info(self, filename_prefix: str) -> Dict[str, Any]:
        """Obtiene información sobre archivos generados"""
        pass

    def ensure_directory(self) -> None:
        """Asegura que el directorio de salida existe"""
        self.base_path.mkdir(parents=True, exist_ok=True)


class JSONStorageStrategy(StorageStrategy):
    """Estrategia de almacenamiento JSON"""

    def save(self, data: List[ProcessingResult], filename_prefix: str, **kwargs) -> Dict[str, Any]:
        """Guarda datos en formato JSON"""
        self.ensure_directory()

        current_date = datetime.now().strftime("%Y%m%d")
        filename = self.base_path / f"{filename_prefix}_{current_date}.json"

        # Convertir ProcessingResult a diccionarios
        json_data = []
        for result in data:
            item = {
                "key": result.key,
                **result.data,
                "_metadata": result.metadata,
                "_errors": result.errors
            }
            json_data.append(item)

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)

            file_size = filename.stat().st_size
            self.logger.info(f"JSON file saved: {filename} ({len(json_data)} records, {file_size} bytes)")

            return {
                "filename": str(filename),
                "format": "json",
                "records": len(json_data),
                "file_size": file_size,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Error saving JSON file: {e}"
            self.logger.error(error_msg)
            raise StorageError(error_msg)

    def get_file_info(self, filename_prefix: str) -> Dict[str, Any]:
        """Obtiene información del archivo JSON"""
        current_date = datetime.now().strftime("%Y%m%d")
        filename = self.base_path / f"{filename_prefix}_{current_date}.json"

        if not filename.exists():
            return {"exists": False}

        stat = filename.stat()
        return {
            "exists": True,
            "filename": str(filename),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }


class CSVStorageStrategy(StorageStrategy):
    """Estrategia de almacenamiento CSV"""

    def save(self, data: List[ProcessingResult], filename_prefix: str, **kwargs) -> Dict[str, Any]:
        """Guarda datos en formato CSV"""
        self.ensure_directory()

        if not data:
            raise StorageError("No data to save")

        current_date = datetime.now().strftime("%Y%m%d")
        filename = self.base_path / f"{filename_prefix}_{current_date}.csv"

        # Determinar columnas del CSV
        preferred_order = kwargs.get('column_order', [
            "team", "boardId", "startDate", "endDate", "completeDate",
            "periodo", "sprint", "sprint_numbers", "cantidad_sprint", "created", "key",
            "summary", "Tribu/Squad", "description", "issue_type", "story_points",
            "paso_a_desarrollo", "paso_a_pruebas", "paso_a_validacion", "paso_a_done",
            "paso_a_release", "paso_a_produccion", "cycle_time", "lead_time", "wait_time"
        ])

        # Recopilar todas las columnas disponibles
        all_columns = set()
        for result in data:
            all_columns.update(result.data.keys())

        # Ordenar columnas: primero las preferidas, luego las demás
        columns = []
        for col in preferred_order:
            if col in all_columns:
                columns.append(col)
                all_columns.remove(col)

        # Agregar columnas restantes
        columns.extend(sorted(all_columns))

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()

                for result in data:
                    row = {}
                    for col in columns:
                        value = result.data.get(col, '')
                        # Convertir valores complejos a string
                        if isinstance(value, (list, dict)):
                            row[col] = json.dumps(value, ensure_ascii=False, default=str)
                        else:
                            row[col] = str(value) if value is not None else ''
                    writer.writerow(row)

            file_size = filename.stat().st_size
            self.logger.info(f"CSV file saved: {filename} ({len(data)} records, {len(columns)} columns, {file_size} bytes)")

            return {
                "filename": str(filename),
                "format": "csv",
                "records": len(data),
                "columns": len(columns),
                "file_size": file_size,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Error saving CSV file: {e}"
            self.logger.error(error_msg)
            raise StorageError(error_msg)

    def get_file_info(self, filename_prefix: str) -> Dict[str, Any]:
        """Obtiene información del archivo CSV"""
        current_date = datetime.now().strftime("%Y%m%d")
        filename = self.base_path / f"{filename_prefix}_{current_date}.csv"

        if not filename.exists():
            return {"exists": False}

        stat = filename.stat()
        return {
            "exists": True,
            "filename": str(filename),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }


class StatsStorageStrategy(StorageStrategy):
    """Estrategia para guardar estadísticas de procesamiento"""

    def save(self, data: List[ProcessingResult], filename_prefix: str, **kwargs) -> Dict[str, Any]:
        """Guarda estadísticas de procesamiento"""
        self.ensure_directory()

        current_date = datetime.now().strftime("%Y%m%d")
        filename = self.base_path / f"{filename_prefix}_stats_{current_date}.csv"

        # Calcular estadísticas
        total_issues = len(data)
        successful_issues = sum(1 for r in data if not r.has_errors)
        failed_issues = total_issues - successful_issues

        # Estadísticas por tipo de issue
        issue_types = {}
        teams = set()

        for result in data:
            if not result.has_errors:
                issue_type = result.data.get('issue_type', 'N/A')
                team = result.data.get('team', 'N/A')

                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
                teams.add(team)

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total_Issues", total_issues])
                writer.writerow(["Successful_Issues", successful_issues])
                writer.writerow(["Failed_Issues", failed_issues])
                writer.writerow(["Unique_Teams", len(teams)])
                writer.writerow(["Extraction_Date", current_date])
                writer.writerow(["Timestamp", datetime.now().isoformat()])

                # Estadísticas por tipo
                writer.writerow([])
                writer.writerow(["Issue_Type", "Count"])
                for issue_type, count in sorted(issue_types.items()):
                    writer.writerow([issue_type, count])

            file_size = filename.stat().st_size
            self.logger.info(f"Stats file saved: {filename} ({file_size} bytes)")

            return {
                "filename": str(filename),
                "format": "stats_csv",
                "total_issues": total_issues,
                "successful_issues": successful_issues,
                "failed_issues": failed_issues,
                "unique_teams": len(teams),
                "file_size": file_size,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Error saving stats file: {e}"
            self.logger.error(error_msg)
            raise StorageError(error_msg)

    def get_file_info(self, filename_prefix: str) -> Dict[str, Any]:
        """Obtiene información del archivo de estadísticas"""
        current_date = datetime.now().strftime("%Y%m%d")
        filename = self.base_path / f"{filename_prefix}_stats_{current_date}.csv"

        if not filename.exists():
            return {"exists": False}

        stat = filename.stat()
        return {
            "exists": True,
            "filename": str(filename),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }


class StorageManager:
    """Gestor de almacenamiento que coordina múltiples estrategias"""

    def __init__(self, base_path: Union[str, Path]):
        self.base_path = Path(base_path)
        self.strategies = {
            'json': JSONStorageStrategy(self.base_path),
            'csv': CSVStorageStrategy(self.base_path),
            'stats': StatsStorageStrategy(self.base_path)
        }
        self.logger = get_logger("storage_manager")

    def save(
        self,
        data: List[ProcessingResult],
        filename_prefix: str = "issues",
        formats: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Guarda datos usando múltiples estrategias"""

        if formats is None:
            formats = ['json', 'csv', 'stats']

        results = {}
        errors = []

        for fmt in formats:
            if fmt not in self.strategies:
                errors.append(f"Unknown format: {fmt}")
                continue

            try:
                strategy_result = self.strategies[fmt].save(data, filename_prefix, **kwargs)
                results[fmt] = strategy_result
                self.logger.info(f"Successfully saved {fmt} format")
            except Exception as e:
                error_msg = f"Error saving {fmt}: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        if errors:
            self.logger.warning(f"Some formats failed to save: {errors}")

        return {
            "results": results,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }

    def get_file_info(self, filename_prefix: str = "issues", formats: Optional[List[str]] = None) -> Dict[str, Any]:
        """Obtiene información de archivos generados"""

        if formats is None:
            formats = list(self.strategies.keys())

        info = {}
        for fmt in formats:
            if fmt in self.strategies:
                info[fmt] = self.strategies[fmt].get_file_info(filename_prefix)

        return info

    def cleanup_old_files(self, days_to_keep: int = 30, filename_prefix: str = "issues") -> Dict[str, Any]:
        """Limpia archivos antiguos"""

        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        deleted_files = []
        errors = []

        try:
            for file_path in self.base_path.glob(f"{filename_prefix}_*.json"):
                if file_path.stat().st_mtime < cutoff_date:
                    file_path.unlink()
                    deleted_files.append(str(file_path))

            for file_path in self.base_path.glob(f"{filename_prefix}_*.csv"):
                if file_path.stat().st_mtime < cutoff_date:
                    file_path.unlink()
                    deleted_files.append(str(file_path))

        except Exception as e:
            errors.append(f"Error during cleanup: {e}")

        self.logger.info(f"Cleanup completed: {len(deleted_files)} files deleted")

        return {
            "deleted_files": deleted_files,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }