#!/usr/bin/env python3
"""
EXTRACCIÓN ESPECÍFICA DE HISTORIAS DE USUARIO (HU) - PROYECTO RSW
Objetivo: Extraer las 979 historias de usuario esperadas del proyecto RSW
"""

import sys
import os
import time
from pathlib import Path

# Configurar imports para la nueva arquitectura
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from jira_extractor.config import get_settings
from jira_extractor.core import JiraAPIClient, JiraIssueProcessor, StorageManager
from jira_extractor.utils import get_logger, configure_logging


def extraer_historias_rsw():
    """Extrae todas las historias de usuario del proyecto RSW"""

    print("="*80)
    print("EXTRACCIÓN DE HISTORIAS DE USUARIO - PROYECTO RSW")
    print("="*80)
    print("Objetivo: Extraer 979 historias de usuario (HU)")
    print("Tipo de issue: Historia")
    print("Proyecto: RSW")
    print()

    # Configurar logging
    configure_logging(
        level="INFO",
        log_file="./logs/extraccion_historias_rsw.log",
        format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = get_logger("extraccion_historias")

    try:
        # Cargar configuración
        settings = get_settings()

        # Modificar configuración para esta extracción específica
        settings.jira.projects = ["RSW"]
        settings.jira.issue_types = ["Historia"]  # Solo historias
        settings.jira.max_results = 50  # Optimizado para Jira

        logger.info("=== CONFIGURACIÓN DE EXTRACCIÓN ===")
        logger.info(f"Proyecto: {settings.jira.projects[0]}")
        logger.info(f"Tipo de issue: {settings.jira.issue_types[0]}")
        logger.info(f"Campos a extraer: {len(settings.jira.default_fields)}")
        logger.info(f"Directorio de salida: {settings.storage.output_dir}")
        logger.info(f"Prefijo de archivos: {settings.storage.file_prefix}")

        # Crear componentes
        api_client = JiraAPIClient(settings.jira)
        processor = JiraIssueProcessor()
        storage = StorageManager(settings.storage.output_dir)

        # Validar conexión
        logger.info("=== VALIDANDO CONEXIÓN ===")
        if not api_client.validate_connection():
            logger.error("❌ No se pudo conectar a Jira")
            return False

        logger.info("✅ Conexión a Jira validada")

        # Construir JQL específico para historias
        jql = "project = RSW AND issuetype = Historia ORDER BY created DESC"
        logger.info(f"JQL construido: {jql}")

        # Extraer todas las historias con paginación completa
        logger.info("=== INICIANDO EXTRACCIÓN COMPLETA ===")

        all_issues = []
        start_at = 0
        page = 1
        total_expected = 979

        logger.info(f"Objetivo esperado: {total_expected} historias")
        logger.info("Iniciando paginación completa...")

        start_time = time.time()

        while True:
            logger.info(f"📄 Página {page} - Desde registro {start_at}")

            try:
                response = api_client.search_issues(
                    jql=jql,
                    start_at=start_at,
                    max_results=settings.jira.max_results
                )

                if not response.success:
                    logger.error(f"❌ Error en página {page}: {response.data}")
                    break

                issues = response.data.get('issues', [])

                if not issues:
                    logger.info(f"🏁 No hay más historias. Página {page} completada.")
                    break

                # Filtrar solo historias válidas
                historias_validas = []
                for issue in issues:
                    fields = issue.get('fields', {})
                    issuetype = fields.get('issuetype', {}).get('name', '')
                    if issuetype == 'Historia':
                        historias_validas.append(issue)

                all_issues.extend(historias_validas)

                logger.info(f"✅ Página {page}: {len(historias_validas)} historias válidas")
                logger.info(f"📊 Total acumulado: {len(all_issues)} historias")

                # Verificar si hemos alcanzado el objetivo
                if len(all_issues) >= total_expected:
                    logger.info(f"🎯 ¡Objetivo alcanzado! {len(all_issues)} >= {total_expected}")
                    break

                # Condición de salida: menos issues que el máximo
                if len(issues) < settings.jira.max_results:
                    logger.info("🏁 Última página alcanzada")
                    break

                start_at += settings.jira.max_results
                page += 1

                # Pequeña pausa entre páginas para no sobrecargar
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ Error en página {page}: {e}")
                break

        extraction_time = time.time() - start_time

        logger.info("=== EXTRACCIÓN COMPLETADA ===")
        logger.info(f"📊 Total historias extraídas: {len(all_issues)}")
        logger.info(f"⏱️  Tiempo de extracción: {extraction_time:.2f} segundos")
        logger.info(f"📈 Tasa: {len(all_issues)/extraction_time:.1f} historias/segundo")

        # Verificar objetivo
        if len(all_issues) >= total_expected:
            logger.info(f"✅ ¡ÉXITO! Se alcanzó el objetivo de {total_expected} historias")
            logger.info(f"📊 Resultado: {len(all_issues)} historias (>= {total_expected})")
        else:
            logger.warning(f"⚠️  Objetivo parcial: {len(all_issues)} historias (< {total_expected})")
            logger.info("Puede haber más páginas o filtros aplicados")

        # Procesar datos si hay historias
        if all_issues:
            logger.info("=== PROCESANDO DATOS ===")

            processing_start = time.time()
            processed_results = processor.process_issues_batch(all_issues)
            processing_time = time.time() - processing_start

            successful = sum(1 for r in processed_results if not r.has_errors)
            failed = len(processed_results) - successful

            logger.info(f"🔄 Procesamiento completado en {processing_time:.2f}s")
            logger.info(f"✅ Procesamiento exitoso: {successful} historias")
            if failed > 0:
                logger.warning(f"⚠️  Con errores: {failed} historias")

            # Guardar resultados en múltiples formatos
            logger.info("=== GUARDANDO RESULTADOS ===")

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"historias_RSW_{timestamp}"

            save_results = storage.save(
                processed_results,
                filename_prefix=filename_prefix,
                formats=['json', 'csv', 'stats']
            )

            logger.info("📁 Archivos generados:")
            for fmt, result in save_results['results'].items():
                logger.info(f"  • {fmt.upper()}: {result['filename']}")
                logger.info(f"    📊 {result.get('records', 'N/A')} registros")

            # Mostrar estadísticas finales
            logger.info("=== ESTADÍSTICAS FINALES ===")
            logger.info(f"🎯 Historias extraídas: {len(all_issues)}")
            logger.info(f"📊 Historias procesadas: {successful}")
            logger.info(f"💾 Archivos guardados: {len(save_results['results'])}")

            # Estadísticas del cliente API
            api_stats = api_client.get_stats()
            logger.info("📈 Estadísticas de API:")
            logger.info(f"  • Requests realizados: {api_stats['requests_made']}")
            logger.info(f"  • Tiempo esperando rate limit: {api_stats['total_wait_time']:.2f}s")
            logger.info(f"  • Hits de rate limit: {api_stats['rate_limit_hits']}")

            logger.info("🎉 === EXTRACCIÓN COMPLETADA CON ÉXITO ===")

            return True

        else:
            logger.warning("⚠️  No se encontraron historias para procesar")
            return False

    except Exception as e:
        logger.error(f"❌ Error general en extracción: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if 'api_client' in locals():
            api_client.close()


def main():
    """Función principal"""
    print("EXTRACCIÓN DE HISTORIAS DE USUARIO - PROYECTO RSW")
    print("="*80)

    # Crear directorios necesarios
    os.makedirs("./logs", exist_ok=True)
    os.makedirs("./exports", exist_ok=True)

    try:
        success = extraer_historias_rsw()

        print("\n" + "="*80)
        if success:
            print("✅ EXTRACCIÓN COMPLETADA EXITOSAMENTE")
            print("📁 Revisa los archivos en ./exports/")
            print("📋 Revisa los logs en ./logs/extraccion_historias_rsw.log")
        else:
            print("❌ EXTRACCIÓN FALLIDA")
            print("Revisa los logs para más detalles")

    except KeyboardInterrupt:
        print("\n⚠️  Extracción interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error general: {e}")


if __name__ == "__main__":
    main()