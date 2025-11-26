#!/usr/bin/env python3
"""
Ejemplo de uso de la nueva arquitectura modular de Jira Extractor
"""

import time
from pathlib import Path

import sys
import os

# Agregar el directorio padre al path para poder importar módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from jira_extractor.config import get_settings
from jira_extractor.core import JiraAPIClient, JiraIssueProcessor, StorageManager
from jira_extractor.utils import get_logger, configure_logging


def main():
    """Ejemplo completo de extracción de datos de Jira"""

    # Configurar logging
    configure_logging(
        level="INFO",
        log_file="./logs/jira_extractor.log",
        format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = get_logger("example")
    logger.info("Iniciando ejemplo de Jira Extractor")

    try:
        # 1. Cargar configuración
        settings = get_settings()
        logger.info(f"Configuración cargada para dominio: {settings.jira.domain}")

        # 2. Crear cliente API
        api_client = JiraAPIClient(settings.jira)
        logger.info("Cliente API creado con rate limiting inteligente")

        # 3. Validar conexión
        if not api_client.validate_connection():
            logger.error("No se pudo validar la conexión a Jira")
            return

        logger.info("Conexión a Jira validada exitosamente")

        # 4. Extraer datos usando JQL
        jql = "project = RSW AND issuetype = Story ORDER BY created DESC"
        logger.info(f"Extrayendo issues con JQL: {jql}")

        all_issues = []
        start_at = 0
        max_results = 50

        while True:
            response = api_client.search_issues(
                jql=jql,
                start_at=start_at,
                max_results=max_results,
                fields=[
                    "key", "summary", "description", "issuetype", "status",
                    "created", "updated", "assignee", "reporter", "priority",
                    "sprint", "customfield_10200"  # story points
                ]
            )

            if not response.success:
                logger.error(f"Error en la búsqueda: {response.data}")
                break

            issues = response.data.get('issues', [])
            if not issues:
                break

            all_issues.extend(issues)
            logger.info(f"Extraídos {len(issues)} issues (total: {len(all_issues)})")

            if len(issues) < max_results:
                break

            start_at += max_results

        logger.info(f"Extracción completada: {len(all_issues)} issues obtenidos")

        # 5. Procesar datos
        if all_issues:
            processor = JiraIssueProcessor()
            logger.info("Procesando issues...")

            start_time = time.time()
            processed_results = processor.process_issues_batch(all_issues)
            processing_time = time.time() - start_time

            successful = sum(1 for r in processed_results if not r.has_errors)
            failed = len(processed_results) - successful

            logger.info(f"Procesamiento completado en {processing_time:.2f}s")
            logger.info(f"Resultados: {successful} exitosos, {failed} con errores")

            # 6. Guardar resultados
            output_dir = Path("./exports")
            storage_manager = StorageManager(output_dir)

            logger.info("Guardando resultados en múltiples formatos...")
            save_results = storage_manager.save(
                processed_results,
                filename_prefix="jira_issues_example",
                formats=['json', 'csv', 'stats']
            )

            logger.info("Archivos generados:")
            for fmt, result in save_results['results'].items():
                logger.info(f"  - {fmt.upper()}: {result['filename']}")

            if save_results['errors']:
                logger.warning(f"Errores durante el guardado: {save_results['errors']}")

        # 7. Mostrar estadísticas del cliente API
        stats = api_client.get_stats()
        logger.info("Estadísticas de la sesión:")
        logger.info(f"  - Requests realizados: {stats['requests_made']}")
        logger.info(f"  - Requests fallidos: {stats['requests_failed']}")
        logger.info(f"  - Tiempo total esperando rate limits: {stats['total_wait_time']:.2f}s")
        logger.info(f"  - Hits de rate limit: {stats['rate_limit_hits']}")

        logger.info("Ejemplo completado exitosamente!")

    except Exception as e:
        logger.error(f"Error durante la ejecución del ejemplo: {e}")
        raise

    finally:
        # Cerrar conexiones
        if 'api_client' in locals():
            api_client.close()


if __name__ == "__main__":
    main()