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

# JQL ESPECÍFICO - Los tipos exactos que solicitaste
JQL_TIPOS_ESPECIFICOS = '''issuetype IN (Error, Story, "Historia No Funcional ( Habilitadora)", "Incidente Produccion", "Soporte ", Spike, Tarea, Epica, Iniciativa, Defect) AND project = RSW ORDER BY issuetype ASC, created DESC'''

def fetch_issues_tipos_especificos():
    """Extraer los tipos específicos con límite de páginas"""
    url = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"

    all_issues = []
    start_at = 0
    max_results = 50
    page = 1
    max_pages = 50  # Límite para evitar loops infinitos

    print("=== EXTRAYENDO TIPOS ESPECÍFICOS DE RSW ===")
    print(f"JQL: {JQL_TIPOS_ESPECIFICOS}")
    print(f"Límite máximo: {max_pages} páginas\n")

    tipos_totales = {}

    while page <= max_pages:
        print(f"Página {page}/{max_pages} (desde {start_at})...")

        try:
            params = {
                "jql": JQL_TIPOS_ESPECIFICOS,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": "key,summary,issuetype,created,description"
            }

            response = requests.get(
                url,
                auth=HTTPBasicAuth(EMAIL, API_TOKEN),
                headers={"Accept": "application/json"},
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])

                if not issues:
                    print("No hay más issues, terminando...")
                    break

                all_issues.extend(issues)

                # Contar tipos en esta página
                tipos_pagina = {}
                for issue in issues:
                    fields = issue.get('fields', {})
                    issuetype = fields.get('issuetype', {})
                    type_name = issuetype.get('name', 'N/A') if isinstance(issuetype, dict) else str(issuetype)
                    tipos_pagina[type_name] = tipos_pagina.get(type_name, 0) + 1
                    tipos_totales[type_name] = tipos_totales.get(type_name, 0) + 1

                print(f"  Issues obtenidos: {len(issues)} | Tipos: {dict(tipos_pagina)}")

                if len(issues) < max_results:
                    print("  Última página alcanzada (menos issues)")
                    break

                start_at += max_results
                page += 1
                time.sleep(0.5)  # Pausa entre requests

            else:
                print(f"Error API: {response.status_code}")
                if response.status_code == 400:
                    print("Posible error en JQL")
                break

        except Exception as e:
            print(f"Error en request: {e}")
            break

    print(f"\n=== RESUMEN FINAL ===")
    print(f"Total issues extraídos: {len(all_issues)}")
    print(f"Páginas procesadas: {page-1}")

    if tipos_totales:
        print("TIPOS EXTRAÍDOS (EXACTAMENTE LOS QUE SOLICITASTE):")
        for tipo, count in sorted(tipos_totales.items()):
            print(f"  - {tipo}: {count} issues")

    return all_issues

def save_results(issues):
    """Guardar resultados con timestamp"""
    if not issues:
        print("No hay issues para guardar")
        return

    os.makedirs("./exports", exist_ok=True)
    current_date = datetime.now().strftime("%Y%m%d")

    # Procesar issues
    processed = []
    for issue in issues:
        fields = issue.get('fields', {})
        issuetype = fields.get('issuetype', {})
        type_name = issuetype.get('name', 'N/A') if isinstance(issuetype, dict) else str(issuetype)

        processed.append({
            "key": issue.get('key'),
            "issue_type": type_name,
            "summary": fields.get('summary', ''),
            "created": fields.get('created', ''),
            "description": fields.get('description', '')
        })

    # Guardar JSON principal
    json_filename = f"./exports/issues_RSW_board1825_{current_date}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    # Guardar CSV con estadísticas por tipo
    csv_filename = f"./exports/issues_RSW_board1825_stats_{current_date}.csv"
    tipos_stats = {}
    for item in processed:
        issue_type = item.get('issue_type', 'N/A')
        tipos_stats[issue_type] = tipos_stats.get(issue_type, 0) + 1

    with open(csv_filename, 'w', encoding='utf-8') as f:
        f.write("Issue_Type,Count\n")
        for tipo, count in sorted(tipos_stats.items()):
            f.write(f'"{tipo}",{count}\n')

    print(f"\n=== ARCHIVOS GUARDADOS ===")
    print(f"JSON: {json_filename} ({len(processed)} issues)")
    print(f"CSV:  {csv_filename} ({len(tipos_stats)} tipos)")

    return json_filename, csv_filename

if __name__ == "__main__":
    if not API_TOKEN:
        print("ERROR: No se encontró JIRA_API_TOKEN en .env")
        exit(1)

    print("=" * 60)
    print("EXTRACCIÓN DE TIPOS ESPECÍFICOS - PROYECTO RSW")
    print("=" * 60)

    # Extraer issues
    issues = fetch_issues_tipos_especificos()

    if issues:
        # Guardar resultados
        json_file, csv_file = save_results(issues)

        print("\n" + "=" * 60)
        print("¡ÉXITO! EXTRACCIÓN COMPLETADA")
        print("=" * 60)
        print(f"Total extraído: {len(issues)} issues")
        print("Tipos obtenidos:")

        tipos_finales = {}
        for issue in issues:
            fields = issue.get('fields', {})
            issuetype = fields.get('issuetype', {})
            type_name = issuetype.get('name', 'N/A') if isinstance(issuetype, dict) else str(issuetype)
            tipos_finales[type_name] = tipos_finales.get(type_name, 0) + 1

        for tipo, count in sorted(tipos_finales.items()):
            print(f"  {tipo}: {count} issues")

        print(f"\nArchivos disponibles en ./exports/")

    else:
        print("\n" + "=" * 60)
        print("NO SE OBTUVIERON ISSUES")
        print("=" * 60)