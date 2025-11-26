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

# JQL ESPECÍFICO
JQL_TIPOS_ESPECIFICOS = '''issuetype IN (Error, Story, "Historia No Funcional ( Habilitadora)", "Incidente Produccion", "Soporte ", Spike, Tarea, Epica, Iniciativa, Defect) AND project = RSW ORDER BY issuetype ASC, created DESC'''

def fetch_issues_con_api_search():
    """Usar la API /search/jql con método GET que es más confiable"""
    url = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"

    all_issues = []
    start_at = 0
    max_results = 50
    page = 1

    print("=== EXTRAYENDO ISSUES CON JQL ESPECÍFICO ===")
    print(f"JQL: {JQL_TIPOS_ESPECIFICOS}")
    print()

    while True:
        print(f"Página {page} (desde {start_at})...")

        try:
            # Usar GET con parámetros
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

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])
                total = data.get('total', 0)

                print(f"Obtenidos: {len(issues)} issues | Total reportado: {total}")

                if not issues:
                    print("No hay más issues, terminando...")
                    break

                all_issues.extend(issues)

                # Mostrar tipos en esta página
                tipos_pagina = {}
                for issue in issues:
                    fields = issue.get('fields', {})
                    issuetype = fields.get('issuetype', {})
                    type_name = issuetype.get('name', 'N/A') if isinstance(issuetype, dict) else str(issuetype)
                    tipos_pagina[type_name] = tipos_pagina.get(type_name, 0) + 1

                print(f"Tipos en esta página: {dict(tipos_pagina)}")

                # Condición de salida más robusta
                if len(issues) < max_results:
                    print("Última página alcanzada (menos issues que max_results)")
                    break

                start_at += max_results
                page += 1
                time.sleep(1)  # Pausa entre requests

            else:
                print(f"Error: {response.status_code}")
                print(f"Respuesta: {response.text}")
                break

        except Exception as e:
            print(f"Error en request: {e}")
            break

    print(f"\n=== RESUMEN FINAL ===")
    print(f"Total issues extraídos: {len(all_issues)}")

    if all_issues:
        # Contar tipos finales
        tipos_finales = {}
        for issue in all_issues:
            fields = issue.get('fields', {})
            issuetype = fields.get('issuetype', {})
            type_name = issuetype.get('name', 'N/A') if isinstance(issuetype, dict) else str(issuetype)
            tipos_finales[type_name] = tipos_finales.get(type_name, 0) + 1

        print("TIPOS FINALES OBTENIDOS:")
        for tipo, count in sorted(tipos_finales.items()):
            print(f"- {tipo}: {count} issues")

        return all_issues
    else:
        return []

def save_results(issues):
    """Guardar resultados en archivos JSON y CSV"""
    if not issues:
        print("No hay issues para guardar")
        return

    # Crear directorio exports si no existe
    os.makedirs("./exports", exist_ok=True)

    current_date = datetime.now().strftime("%Y%m%d")

    # Procesar issues para formato más legible
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

    # Guardar JSON
    json_filename = f"./exports/issues_RSW_tipos_especificos_{current_date}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)
    print(f"JSON guardado: {json_filename}")

    # Guardar CSV con estadísticas
    csv_filename = f"./exports/issues_RSW_tipos_especificos_stats_{current_date}.csv"
    tipos_stats = {}
    for item in processed:
        issue_type = item.get('issue_type', 'N/A')
        tipos_stats[issue_type] = tipos_stats.get(issue_type, 0) + 1

    with open(csv_filename, 'w', encoding='utf-8') as f:
        f.write("Issue Type,Count\n")
        for tipo, count in sorted(tipos_stats.items()):
            f.write(f"{tipo},{count}\n")
    print(f"CSV estadísticas guardado: {csv_filename}")

    print(f"\nArchivos guardados exitosamente:")
    print(f"- {len(processed)} issues en JSON")
    print(f"- {len(tipos_stats)} tipos diferentes en CSV")

if __name__ == "__main__":
    if not API_TOKEN:
        print("ERROR: No se encontró JIRA_API_TOKEN")
        exit(1)

    print("SCRIPT FINAL PARA EXTRAER TIPOS ESPECÍFICOS DE RSW")
    print("=" * 60)

    # Extraer issues
    issues = fetch_issues_con_api_search()

    # Guardar resultados
    save_results(issues)

    print("\n" + "=" * 60)
    if issues:
        print("SCRIPT COMPLETADO CON ÉXITO")
        print(f"Se obtuvieron {len(issues)} issues de los tipos especificados")

        # Mostrar resumen final
        tipos_finales = {}
        for issue in issues:
            fields = issue.get('fields', {})
            issuetype = fields.get('issuetype', {})
            type_name = issuetype.get('name', 'N/A') if isinstance(issuetype, dict) else str(issuetype)
            tipos_finales[type_name] = tipos_finales.get(type_name, 0) + 1

        print("\nRESUMEN DE TIPOS EXTRAÍDOS:")
        for tipo, count in sorted(tipos_finales.items()):
            print(f"  {tipo}: {count} issues")
    else:
        print("NO se obtuvieron issues")
        print("Verifica el JQL o los tipos de issue especificados")