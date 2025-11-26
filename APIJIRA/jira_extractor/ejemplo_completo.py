#!/usr/bin/env python3
"""
EJEMPLO COMPLETO DE LA NUEVA ARQUITECTURA MODULAR
Demuestra todas las funcionalidades avanzadas del Jira Extractor
"""

import sys
import os
import time
from pathlib import Path

# Configurar imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from jira_extractor.config import get_settings
from jira_extractor.core import JiraAPIClient, JiraIssueProcessor, StorageManager
from jira_extractor.utils import get_logger, configure_logging


def ejemplo_basico():
    """Ejemplo básico de extracción"""
    print("\n" + "="*60)
    print("EJEMPLO BÁSICO - Extracción Simple")
    print("="*60)

    # Configurar logging básico
    logger = get_logger("ejemplo_basico")

    try:
        # Cargar configuración
        settings = get_settings()
        logger.info(f"Configuración cargada - Proyecto: {settings.jira.projects}")

        # Crear cliente API
        api_client = JiraAPIClient(settings.jira)

        # Validar conexión
        if not api_client.validate_connection():
            logger.error("No se pudo conectar a Jira")
            return

        # Extraer issues básicos
        jql = f"project IN ({', '.join(settings.jira.projects)}) AND issuetype = Story ORDER BY created DESC"
        logger.info(f"Extrayendo con JQL: {jql}")

        response = api_client.search_issues(jql=jql, max_results=10)

        if response.success and response.data.get('issues'):
            issues = response.data['issues']
            logger.info(f"✅ Extraídos {len(issues)} issues exitosamente")

            # Mostrar algunos resultados
            for i, issue in enumerate(issues[:3], 1):
                fields = issue.get('fields', {})
                logger.info(f"  {i}. {issue['key']}: {fields.get('summary', 'N/A')}")

        else:
            logger.warning("No se encontraron issues o hubo un error")

    except Exception as e:
        logger.error(f"Error en ejemplo básico: {e}")

    except Exception as e:
        logger.error(f"Error en ejemplo básico: {e}")


def ejemplo_avanzado():
    """Ejemplo avanzado con procesamiento completo y múltiples formatos"""
    print("\n" + "="*60)
    print("EJEMPLO AVANZADO - Procesamiento Completo + Múltiples Formatos")
    print("="*60)

    # Configurar logging avanzado
    configure_logging(
        level="INFO",
        log_file="./logs/ejemplo_avanzado.log",
        format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = get_logger("ejemplo_avanzado")

    try:
        # Cargar configuración
        settings = get_settings()
        logger.info("=== INICIANDO EXTRACCIÓN AVANZADA ===")
        logger.info(f"Proyecto: {settings.jira.projects[0]}")
        logger.info(f"Campos incluidos: {len(settings.jira.default_fields)}")

        # Crear componentes
        api_client = JiraAPIClient(settings.jira)
        processor = JiraIssueProcessor()
        storage = StorageManager(settings.storage.output_dir)

        # Validar conexión
        if not api_client.validate_connection():
            logger.error("❌ Falló validación de conexión")
            return

        logger.info("✅ Conexión a Jira validada")

        # Extraer issues con paginación
        all_issues = []
        jql = f"project = {settings.jira.projects[0]} ORDER BY created DESC"
        start_at = 0
        max_pages = 3  # Limitar para el ejemplo

        logger.info(f"📊 Extrayendo issues con JQL: {jql}")

        for page in range(max_pages):
            logger.info(f"📄 Página {page + 1}/{max_pages} (desde {start_at})")

            response = api_client.search_issues(
                jql=jql,
                start_at=start_at,
                max_results=settings.jira.max_results
            )

            if not response.success:
                logger.error(f"❌ Error en página {page + 1}: {response.data}")
                break

            issues = response.data.get('issues', [])
            if not issues:
                logger.info("🏁 No hay más issues")
                break

            all_issues.extend(issues)
            logger.info(f"✅ Página {page + 1}: {len(issues)} issues")

            if len(issues) < settings.jira.max_results:
                break

            start_at += settings.jira.max_results

        logger.info(f"📈 Total extraído: {len(all_issues)} issues")

        if all_issues:
            # Procesar datos
            logger.info("🔄 Procesando issues...")
            start_time = time.time()

            processed_results = processor.process_issues_batch(all_issues)

            processing_time = time.time() - start_time
            successful = sum(1 for r in processed_results if not r.has_errors)
            failed = len(processed_results) - successful

            logger.info(f"🔄 Procesamiento completado en {processing_time:.2f}s")
            logger.info(f"✅ Procesamiento exitoso: {successful} issues")
            if failed > 0:
                logger.warning(f"⚠️  Con errores: {failed} issues")

            # Guardar en múltiples formatos
            logger.info("💾 Guardando en múltiples formatos...")

            save_results = storage.save(
                processed_results,
                filename_prefix="ejemplo_completo",
                formats=['json', 'csv', 'stats']
            )

            logger.info("📁 Archivos generados:")
            for fmt, result in save_results['results'].items():
                logger.info(f"  • {fmt.upper()}: {result['filename']}")
                logger.info(f"    📊 {result.get('records', 'N/A')} registros")

            # Mostrar estadísticas del cliente API
            stats = api_client.get_stats()
            logger.info("📈 Estadísticas de la sesión:")
            logger.info(f"  • Requests realizados: {stats['requests_made']}")
            logger.info(f"  • Tiempo total esperando: {stats['total_wait_time']:.2f}s")
            logger.info(f"  • Rate limit hits: {stats['rate_limit_hits']}")

        logger.info("🎉 === EJEMPLO AVANZADO COMPLETADO ===")

    except Exception as e:
        logger.error(f"❌ Error en ejemplo avanzado: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if 'api_client' in locals():
            api_client.close()


def ejemplo_personalizado():
    """Ejemplo de personalización avanzada"""
    print("\n" + "="*60)
    print("EJEMPLO PERSONALIZADO - Configuración Avanzada")
    print("="*60)

    logger = get_logger("personalizado")

    try:
        # Configuración personalizada
        settings = get_settings()

        # Modificar configuración en runtime
        settings.jira.max_results = 25
        settings.jira.projects = ["RSW"]  # Solo RSW

        logger.info("🔧 Configuración personalizada:")
        logger.info(f"  • Proyecto: {settings.jira.projects}")
        logger.info(f"  • Máximo resultados: {settings.jira.max_results}")
        logger.info(f"  • Timeout: {settings.jira.request_timeout}s")

        # Crear cliente con configuración personalizada
        api_client = JiraAPIClient(settings.jira)

        # Extraer con filtros específicos
        jql = """
        project = RSW
        AND issuetype IN (Story, Epic)
        AND status IN ("To Do", "In Progress")
        ORDER BY priority DESC, created DESC
        """.strip()

        logger.info("🎯 Extracción con filtros avanzados")
        logger.info(f"JQL: {jql}")

        response = api_client.search_issues(jql=jql, max_results=10)

        if response.success:
            issues = response.data.get('issues', [])
            logger.info(f"✅ Encontrados {len(issues)} issues con filtros")

            # Mostrar resumen por tipo y estado
            tipos = {}
            estados = {}

            for issue in issues:
                fields = issue.get('fields', {})

                # Contar por tipo
                issuetype = fields.get('issuetype', {}).get('name', 'N/A')
                tipos[issuetype] = tipos.get(issuetype, 0) + 1

                # Contar por estado
                status = fields.get('status', {}).get('name', 'N/A')
                estados[status] = estados.get(status, 0) + 1

            logger.info("📊 Resumen por tipo:")
            for tipo, count in tipos.items():
                logger.info(f"  • {tipo}: {count}")

            logger.info("📊 Resumen por estado:")
            for estado, count in estados.items():
                logger.info(f"  • {estado}: {count}")

        logger.info("✨ === EJEMPLO PERSONALIZADO COMPLETADO ===")

    except Exception as e:
        logger.error(f"❌ Error en ejemplo personalizado: {e}")


def main():
    """Función principal que ejecuta todos los ejemplos"""
    print("JIRA EXTRACTOR - EJEMPLOS COMPLETOS")
    print("="*60)
    print("Demostrando todas las funcionalidades de la nueva arquitectura modular")

    # Crear directorios necesarios
    os.makedirs("./logs", exist_ok=True)
    os.makedirs("./exports", exist_ok=True)

    try:
        # Ejecutar ejemplos
        ejemplo_basico()
        ejemplo_avanzado()
        ejemplo_personalizado()

        print("\n" + "="*60)
        print("🎊 TODOS LOS EJEMPLOS COMPLETADOS EXITOSAMENTE")
        print("="*60)
        print("📁 Revisa los archivos generados en ./exports/")
        print("📋 Revisa los logs en ./logs/")
        print("🔧 Modifica .env para personalizar la configuración")

    except KeyboardInterrupt:
        print("\n⚠️  Ejecución interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error general: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()