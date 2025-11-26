import os
import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime
import time

# Cargar token desde .env
def load_env_file(path=".env"):
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as fh:
            for line in fh:
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                if '=' not in s:
                    continue
                key, val = s.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val

load_env_file()

# Configuración
JIRA_DOMAIN = "bancodebogota.atlassian.net"
EMAIL = "dbusto3@bancodebogota.com.co"
API_TOKEN = os.getenv("JIRA_API_TOKEN", "").strip()

# Campos configurados igual que script_jira.py
DEFAULT_FIELDS = [
    "sprint", "created", "key", "summary", "description", "issuetype",
    "customfield_11112", "customfield_11113", "customfield_11111", "customfield_11115",
    "customfield_11180", "customfield_11181", "customfield_11365", "customfield_10200",
    "customfield_10103", "customfield_10020",
]

# Campos adicionales útiles para Stories
ADDITIONAL_FIELDS = ["status", "assignee", "reporter", "priority", "updated", "resolution"]

# Combinar todos los campos
ALL_FIELDS = DEFAULT_FIELDS + ADDITIONAL_FIELDS

def extract_all_stories_rsw():
    """Extraer TODAS las Stories (Historia) de RSW - método probado que funciona"""

    url = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"
    # JQL para extraer todas las Stories/Historias de RSW sin restricción de fechas
    jql = 'project = RSW AND issuetype = Story ORDER BY created DESC'

    all_stories = []
    start_at = 0
    max_results = 50
    page = 1
    max_pages = 25  # Límite de 25 páginas = 1250 issues máximo para evitar loops infinitos

    print("=" * 80)
    print("EXTRACCIÓN FINAL DE TODAS LAS STORIES DE RSW")
    print("=" * 80)
    print(f"JQL: {jql}")
    print(f"URL: {url}")
    print(f"Límite: {max_pages} páginas máximo")
    print(f"Campos: {len(ALL_FIELDS)} campos (igual que script_jira.py)")
    print(f"  - Campos básicos: key, summary, description, created, etc.")
    print(f"  - Custom fields: {len([f for f in ALL_FIELDS if f.startswith('customfield')])} campos personalizados")
    print()

    start_time = time.time()

    while page <= max_pages:
        print(f"[PÁGINA {page:2d}/{max_pages}] Extrayendo desde {start_at}...")

        try:
            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": ",".join(ALL_FIELDS)
            }

            response = requests.get(
                url,
                auth=HTTPBasicAuth(EMAIL, API_TOKEN),
                headers={"Accept": "application/json"},
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])

                if not issues:
                    print(f"                      No hay más issues, terminando en página {page}")
                    break

                print(f"                      Obtenidos: {len(issues)} issues")

                # Verificar tipos reales para asegurar que son Stories
                tipos_reales = {}
                stories_validas = 0
                for issue in issues:
                    fields = issue.get('fields', {})
                    issuetype = fields.get('issuetype', {})
                    type_name = issuetype.get('name', 'N/A')
                    tipos_reales[type_name] = tipos_reales.get(type_name, 0) + 1

                    if type_name == 'Historia':  # En español se llama "Historia"
                        stories_validas += 1

                print(f"                      Tipos: {dict(tipos_reales)} | Stories válidas: {stories_validas}")

                all_stories.extend(issues)

                # Condición de salida: menos issues que el máximo
                if len(issues) < max_results:
                    print(f"                      Última página alcanzada (solo {len(issues)} issues)")
                    break

                start_at += max_results
                page += 1
                time.sleep(0.5)  # Pausa para no sobrecargar la API

            else:
                print(f"                      ERROR: Status {response.status_code}")
                print(f"                      Respuesta: {response.text[:200]}...")
                break

        except Exception as e:
            print(f"                      EXCEPCIÓN: {e}")
            break

    end_time = time.time()
    duration = end_time - start_time

    print()
    print("=" * 80)
    print("RESUMEN DE EXTRACCIÓN COMPLETADA")
    print("=" * 80)
    print(f"Total issues extraídos: {len(all_stories)}")
    print(f"Páginas procesadas: {page-1}")
    print(f"Tiempo transcurrido: {duration:.1f} segundos")

    # Análisis de tipos extraídos
    if all_stories:
        tipos_finales = {}
        for issue in all_stories:
            fields = issue.get('fields', {})
            issuetype = fields.get('issuetype', {})
            type_name = issuetype.get('name', 'N/A')
            tipos_finales[type_name] = tipos_finales.get(type_name, 0) + 1

        print("\nTipos de issues extraídos:")
        for tipo, count in sorted(tipos_finales.items()):
            print(f"  - {tipo}: {count} issues")

        historia_count = tipos_finales.get('Historia', 0)
        if historia_count >= 979:
            print(f"\n[EXITO] Se encontraron {historia_count} Stories (>= 979 como esperabas)")
        else:
            print(f"\n[PARCIAL] Se encontraron {historia_count} Stories (< 979 esperadas)")

    return all_stories

def extract_field_value(fields, field_name):
    """Extraer valor de campo con manejo de errores"""
    try:
        field_value = fields.get(field_name)
        if field_value is None:
            return ''

        # Manejar campos de objeto (como status, assignee, etc.)
        if isinstance(field_value, dict):
            # Para campos como status, issuetype, priority
            if 'name' in field_value:
                return field_value.get('name', '')
            # Para campos como assignee, reporter
            elif 'displayName' in field_value:
                return field_value.get('displayName', '')
            # Para otros objetos, convertir a string
            else:
                return str(field_value)

        # Para arrays de objetos (como sprints)
        elif isinstance(field_value, list):
            if len(field_value) > 0 and isinstance(field_value[0], dict):
                # Para sprints, extraer nombres
                if 'name' in field_value[0]:
                    return ', '.join([item.get('name', '') for item in field_value if item.get('name')])
                else:
                    return ', '.join([str(item) for item in field_value])
            else:
                return ', '.join([str(item) for item in field_value])

        # Para valores simples
        else:
            return str(field_value)

    except Exception as e:
        return f'ERROR: {str(e)}'

def save_stories_results(stories):
    """Guardar resultados en archivos JSON y CSV con todos los campos del script original"""
    if not stories:
        print("No hay stories para guardar")
        return

    os.makedirs("./exports", exist_ok=True)
    current_date = datetime.now().strftime("%Y%m%d")

    # Procesar solo las Stories/Historias válidas
    processed_stories = []
    for issue in stories:
        fields = issue.get('fields', {})
        issuetype = fields.get('issuetype', {})
        type_name = issuetype.get('name', 'N/A')

        # Solo procesar si es "Historia" (Story en español)
        if type_name == 'Historia':
            # Crear registro con TODOS los campos del script original
            story_record = {
                "key": issue.get('key', ''),
                "issue_type": type_name,
                "summary": fields.get('summary', ''),
                "description": fields.get('description', ''),
                "created": fields.get('created', ''),
                "updated": fields.get('updated', ''),
                "status": extract_field_value(fields, 'status'),
                "assignee": extract_field_value(fields, 'assignee'),
                "reporter": extract_field_value(fields, 'reporter'),
                "priority": extract_field_value(fields, 'priority'),
                "resolution": extract_field_value(fields, 'resolution'),
                "sprint": extract_field_value(fields, 'sprint'),
            }

            # Agregar todos los custom fields del script original
            custom_fields = [
                "customfield_11112", "customfield_11113", "customfield_11111", "customfield_11115",
                "customfield_11180", "customfield_11181", "customfield_11365", "customfield_10200",
                "customfield_10103", "customfield_10020"
            ]

            for cf in custom_fields:
                story_record[cf] = extract_field_value(fields, cf)

            processed_stories.append(story_record)

    if not processed_stories:
        print("No se encontraron Stories válidas para guardar")
        return

    # Guardar JSON principal
    json_filename = f"./exports/stories_RSW_final_{current_date}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(processed_stories, f, indent=2, ensure_ascii=False)

    # Guardar CSV con estadísticas
    csv_filename = f"./exports/stories_RSW_final_stats_{current_date}.csv"
    with open(csv_filename, 'w', encoding='utf-8') as f:
        f.write("Metric,Count\n")
        f.write(f"Total_Stories,{len(processed_stories)}\n")
        f.write(f"Project,RSW\n")
        f.write(f"Issue_Type,Historia\n")
        f.write(f"Extraction_Date,{current_date}\n")

    print()
    print("=" * 80)
    print("ARCHIVOS GUARDADOS")
    print("=" * 80)
    print(f"JSON: {json_filename}")
    print(f"      {len(processed_stories)} stories guardadas")
    print(f"      {len(ALL_FIELDS)} campos por story (igual que script_jira.py)")
    print(f"      Incluye todos los custom fields configurados")
    print(f"CSV:  {csv_filename}")
    print(f"      Estadísticas de extracción")

    return json_filename, csv_filename, len(processed_stories)

if __name__ == "__main__":
    if not API_TOKEN:
        print("ERROR: No se encontró JIRA_API_TOKEN en archivo .env")
        exit(1)

    print("INICIANDO EXTRACCIÓN FINAL DE STORIES DE RSW")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Extraer todas las stories
    all_stories = extract_all_stories_rsw()

    if all_stories:
        # Guardar resultados
        json_file, csv_file, story_count = save_stories_results(all_stories)

        print()
        print("=" * 80)
        print("EXTRACCION COMPLETADA CON EXITO")
        print("=" * 80)
        print(f"Total de Stories extraidas: {story_count}")

        if story_count >= 979:
            print(f"Objetivo cumplido: {story_count} >= 979 stories como esperabas")
        else:
            print(f"Objetivo parcial: {story_count} < 979 stories esperadas")
            print("   Puede ser que haya más páginas por extraer")

        print(f"Archivos disponibles en ./exports/")

    else:
        print()
        print("=" * 80)
        print("NO SE PUDIERON EXTRAER STORIES")
        print("=" * 80)
        print("Verifica la conexión a JIRA y el token de acceso")