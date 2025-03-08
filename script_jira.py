import re
import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime
 
# ------------------------ Configuración ------------------------
 
JIRA_DOMAIN = "bancodebogota.atlassian.net"
EMAIL = ""
API_TOKEN = ""
 
# Definir la consulta JQL
JQL_QUERY = (
    "project IN (ADP, CAP, DEX, CAHD, CGT, B2B, EFI, IOD, COP, PEM, SCDPPPN, TRX) "
    "AND type IN (Story, \"Historia No Funcional (Habilitadora)\") "
    "AND status IN (\"EN PRODUCCIÓN\", TERMINADO) "
    "AND created >= \"2024/04/01 00:00\" AND created <= \"2024/12/31 6:00\" "
    "ORDER BY project, created ASC"
)
 
# Campos específicos a recuperar de los issues
FIELDS = "sprint,created,key,summary,customfield_10200,customfield_10103"
 
# URL base de la API de Jira
URL = f"https://{JIRA_DOMAIN}/rest/api/2/search"
 
# Número máximo de resultados por página
MAX_RESULTS = 100
 
# Configuración de autenticación
AUTH = HTTPBasicAuth(EMAIL, API_TOKEN)
 
# ------------------------ Funciones ------------------------
 
def fetch_issues():
    """Obtiene todos los issues de Jira con paginación."""
    start_at = 0
    total_issues = []
 
    while True:
        try:
            response = requests.get(
                URL,
                auth=AUTH,
                headers={"Accept": "application/json"},
                params={
                    "jql": JQL_QUERY,
                    "fields": FIELDS,
                    "startAt": start_at,
                    "maxResults": MAX_RESULTS,
                }
            )
 
            response.raise_for_status()  # Lanza un error si la respuesta es incorrecta
 
            data = response.json()
            issues = data.get('issues', [])
            total_issues.extend(issues)
 
            if len(issues) < MAX_RESULTS:
                break
 
            start_at += MAX_RESULTS
 
        except requests.RequestException as e:
            print(f"Error en la solicitud a Jira: {e}")
            break
 
    return total_issues
 
 
def extract_sprint_data(sprints, field):
    """Extrae y concatena datos específicos de los sprints."""
    return ', '.join(map(str, [sprint.get(field, '') for sprint in sprints])) if sprints else ''
 
 
def determine_period(complete_date):
    """Determina el período basado en la fecha de finalización."""
    if "2024-06-01T00:00:00.000Z" <= complete_date <= "2024-08-31T23:00:00.000Z":
        return "Antes piloto"
    elif "2024-09-01T00:00:00.000Z" <= complete_date <= "2024-12-31T23:00:00.000Z":
        return "Durante piloto"
    return "Otro"
 
 
def process_issues(issues):
    """Procesa los issues obtenidos y estructura los datos."""
    processed_issues = []
 
    for issue in issues:
        fields = issue.get('fields', {})
 
        created = fields.get('created', 'No definido')
        key = issue.get('key', 'No definido')
        team = re.split(r'-', key)[0]  # Extrae el equipo del key
        summary = fields.get('summary', 'No definido')
        story_points = fields.get('customfield_10200', 'No definido')
        sprints = fields.get('customfield_10103', [])
 
        sprint_names = extract_sprint_data(sprints, 'name')
        board_id = extract_sprint_data(sprints, 'boardId')
        start_date = extract_sprint_data(sprints, 'startDate')
        end_date = extract_sprint_data(sprints, 'endDate')
        complete_date = extract_sprint_data(sprints, 'completeDate') or end_date
        periodo = determine_period(complete_date)
 
        sprint_numbers = ', '.join(re.findall(r'\d+', sprint_names)) if sprint_names else ''
 
        processed_issues.append({
            "team": team,
            "boardId": board_id,
            "startDate": start_date,
            "endDate": end_date,
            "completeDate": complete_date,
            "periodo": periodo,
            "sprint": sprint_names,
            "sprint_numbers": sprint_numbers,
            "created": created,
            "key": key,
            "summary": summary,
            "story_points": story_points
        })
 
    return processed_issues
 
 
def save_to_json(data, filename_prefix="issues"):
    """Guarda los datos procesados en un archivo JSON con timestamp."""
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{current_datetime}.json"
 
    try:
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        print(f"Los resultados se han guardado en {filename}")
    except IOError as e:
        print(f"Error al escribir el archivo JSON: {e}")
 
 
# ------------------------ Ejecución del Script ------------------------
 
if __name__ == "__main__":
    issues = fetch_issues()  # Obtener los issues de Jira
    processed_issues = process_issues(issues)  # Procesar los issues obtenidos
    save_to_json(processed_issues)  # Guardar en un archivo JSON