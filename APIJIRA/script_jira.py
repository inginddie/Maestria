import re
import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime
import time
import sys
import os
import html

def load_env_file(path: str = ".env"):
    """Carga variables de un archivo .env simple (KEY=VALUE) al entorno."""
    try:
        if not path or not os.path.isfile(path):
            return
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
    except Exception:
        pass

# ------------------------ Configuración ------------------------
 
JIRA_DOMAIN = "bancodebogota.atlassian.net"
EMAIL = "dbusto3@bancodebogota.com.co"
# Cargar .env (ruta configurable via JIRA_ENV_FILE, por defecto .env en la raíz)
load_env_file(os.getenv("JIRA_ENV_FILE", ".env"))
API_TOKEN = os.getenv("JIRA_API_TOKEN", "").strip()

# Proyectos objetivo divididos en bloques para optimizar consultas
PROJECT_BLOCKS = [
    ["ADP", "CAP", "DEX"],
    ["CAHD", "CGT", "B2B"], 
    ["EFI", "IOD", "COP"],
    ["PEM", "SCDPPPN", "TRX"]
]

def get_project_blocks():
    """Devuelve bloques de proyectos. Si JIRA_PROJECTS está definido, usa esa lista como único bloque."""
    override = os.getenv("JIRA_PROJECTS", "").strip()
    if override:
        projects = [p.strip() for p in override.split(',') if p.strip()]
        if projects:
            return [projects]
    return PROJECT_BLOCKS

def get_date_clause():
    """Construye la cláusula de fechas para created/updated según variables de entorno.
    - JIRA_DATE_FIELD: created | updated (por defecto: created)
    - Si es created: usa JIRA_CREATED_FROM / JIRA_CREATED_TO
    - Si es updated: usa JIRA_UPDATED_FROM / JIRA_UPDATED_TO
    Formato aceptado: YYYY-MM-DD o YYYY/MM/DD (se convierte a YYYY/MM/DD HH:MM)
    """
    field = os.getenv("JIRA_DATE_FIELD", "created").strip().lower()
    if field not in ("created", "updated"):
        field = "created"
    if field == "updated":
        start_env = os.getenv("JIRA_UPDATED_FROM", "").strip()
        end_env = os.getenv("JIRA_UPDATED_TO", "").strip()
    else:
        start_env = os.getenv("JIRA_CREATED_FROM", "").strip()
        end_env = os.getenv("JIRA_CREATED_TO", "").strip()

    if start_env or end_env:
        def _fmt(d, end=False):
            if not d:
                return None
            d = d.replace('-', '/')
            return f"{d} {'23:59' if end else '00:00'}"
        start_str = _fmt(start_env, end=False)
        end_str = _fmt(end_env, end=True)
        parts = []
        if start_str:
            parts.append(f"{field} >= \"{start_str}\"")
        if end_str:
            parts.append(f"{field} <= \"{end_str}\"")
        return (" AND " + " AND ".join(parts) + " ") if parts else ""
    # Fallback por defecto anterior
    return "AND created >= \"2024/04/01 00:00\" AND created <= \"2024/12/31 23:59\" "


def get_order_clause():
    """Devuelve la cláusula ORDER BY según JIRA_ORDER_BY o un valor por defecto."""
    raw = os.getenv("JIRA_ORDER_BY", "").strip()
    if raw:
        return f"ORDER BY {raw}"
    return "ORDER BY project, created ASC"

def get_issuetype_clause():
    raw = os.getenv("JIRA_ISSUETYPES", "Story").strip()
    types = [t.strip() for t in raw.split(',') if t.strip()]
    if not types:
        types = ["Story"]
    if len(types) == 1:
        return f'issuetype = "{types[0]}"'
    quoted = ", ".join(f'"{t}"' for t in types)
    return f"issuetype IN ({quoted})"

def get_status_clause():
    """Construye la cláusula de estados desde JIRA_STATUSES (comma-separated)."""
    raw = os.getenv("JIRA_STATUSES", "").strip()
    if raw:
        statuses = [s.strip() for s in raw.split(',') if s.strip()]
        if len(statuses) == 1:
            return f'status = "{statuses[0]}"'
        joined = ", ".join(f'"{s}"' for s in statuses)
        return f"status IN ({joined})"
    # Si no se define, no filtrar por estado
    return ""

# Plantilla base de consulta JQL
JQL_BASE = (
    "project IN ({projects}) "
    f"AND {get_issuetype_clause()} "
    + (f"AND {get_status_clause()} " if get_status_clause() else "")
    + f"{get_date_clause()}"
    + f"{get_order_clause()}"
)

# Configuración de campos dinámicos
DEFAULT_FIELDS = [
    "sprint", "created", "key", "summary", "description", "issuetype",
    "customfield_11112",  # Paso a Desarrollo
    "customfield_11113",  # Paso a Pruebas
    "customfield_11111",  # Paso a Validación
    "customfield_11115",  # Paso a Done
    "customfield_11180",  # Paso a Release
    "customfield_11181",  # Paso a Producción
    "customfield_11365",  # Tribu/Squad
    "customfield_10200",  # Story Points (ajústalo si tu instancia usa otro ID)
    "customfield_10103",  # Sprint (variante 1)
    "customfield_10020"   # Sprint (variante 2)
]
MIN_FIELDS = ["created", "key", "summary", "issuetype"]
SPRINT_ALTERNATIVES = ["customfield_10103", "customfield_10020", "sprint"]

def _parse_env_list(var_name: str):
    raw = os.getenv(var_name, "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(',') if x.strip()]

def get_fields_list():
    # Override completo si JIRA_FIELDS está definido
    override = _parse_env_list("JIRA_FIELDS")
    if override:
        fields = override
    else:
        extra = _parse_env_list("JIRA_EXTRA_FIELDS")
        fields = DEFAULT_FIELDS + extra
    # Asegurar mínimos
    for f in MIN_FIELDS:
        if f not in fields:
            fields.append(f)
    # Asegurar al menos un campo de sprint
    if not any(f in fields for f in SPRINT_ALTERNATIVES):
        fields.append("sprint")
    # Deduplicar preservando orden
    seen = set()
    dedup = []
    for f in fields:
        if f not in seen:
            dedup.append(f)
            seen.add(f)
    return dedup

SELECTED_FIELDS = get_fields_list()
# Campos específicos a recuperar de los issues
FIELDS = ",".join(SELECTED_FIELDS)
 
# URL base de la API de Jira (actualizada al nuevo endpoint)
URL = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"
JQL_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-ExperimentalApi": "opt-in"
}
 
# Configuración optimizada
MAX_RESULTS = 50  # Reducido para evitar timeouts
REQUEST_TIMEOUT = 30  # Timeout en segundos
MAX_RETRIES = 3  # Número máximo de reintentos
DELAY_BETWEEN_REQUESTS = 1  # Pausa entre requests en segundos
 
# Configuración de autenticación
AUTH = HTTPBasicAuth(EMAIL, API_TOKEN)

AGILE_BASE = f"https://{JIRA_DOMAIN}/rest/agile/1.0"

# ------------------------ Funciones ------------------------

def ensure_dir(path: str):
    """Crea el directorio si no existe."""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        print(f"⚠️  No se pudo asegurar el directorio {path}: {e}")

def validate_jira_connection():
    """Valida la conexión a JIRA antes de iniciar consultas masivas."""
    print("🔍 Validando conexión a JIRA...")
    
    if not API_TOKEN:
        print("❌ Falta el token de API. Define JIRA_API_TOKEN en variables de entorno o en un archivo .env")
        return False
 
    try:
        response = requests.get(
            f"https://{JIRA_DOMAIN}/rest/api/3/myself",
            auth=AUTH,
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Conexión validada - Usuario: {user_info.get('displayName', 'N/A')}")
            return True
        elif response.status_code == 401:
            print("❌ No autorizado. Verifica email/API token y permisos.")
            return False
        else:
            print(f"❌ Error de conexión - Status: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return False

def _normalize_search_response(data: dict):
    """Normaliza la respuesta del endpoint /search/jql o /search a {'issues': [], 'total': n}."""
    if not isinstance(data, dict):
        return {"issues": [], "total": 0}
    # Formato nuevo: { results: [ { issues: [...], total: X, startAt, maxResults } ] }
    if "results" in data and isinstance(data["results"], list) and data["results"]:
        first = data["results"][0] or {}
        issues = first.get("issues", []) or []
        total = first.get("total", len(issues))
        return {"issues": issues, "total": total}
    # Formato clásico: { issues: [...], total: X }
    issues = data.get("issues", []) or []
    total = data.get("total", len(issues))
    return {"issues": issues, "total": total}

def _post_search_jql(jql_query: str, start_at: int, max_results: int):
    """Intenta varias formas de consulta:
    1) POST /search/jql con payload simple
    2) POST /search/jql con payload 'queries'
    3) Fallback: POST /search legacy
    Devuelve la response cruda.
    """
    headers_jql = JQL_HEADERS
    headers_legacy = {"Accept": "application/json", "Content-Type": "application/json"}

    # Variante 1: payload simple
    payload_simple = {
        "jql": jql_query,
        "startAt": start_at,
        "maxResults": max_results,
        "fields": SELECTED_FIELDS
    }
    resp = requests.post(
        URL,
        auth=AUTH,
        headers=headers_jql,
        json=payload_simple,
        timeout=REQUEST_TIMEOUT
    )
    if resp.status_code == 200:
        return resp

    # Variante 2: payload con 'queries'
    payload_queries = {
        "queries": [
            {
                "jql": jql_query,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": SELECTED_FIELDS
            }
        ]
    }
    resp2 = requests.post(
        URL,
        auth=AUTH,
        headers=headers_jql,
        json=payload_queries,
        timeout=REQUEST_TIMEOUT
    )
    if resp2.status_code == 200:
        return resp2

    # Fallback a /search legacy
    fallback_url = f"https://{JIRA_DOMAIN}/rest/api/3/search"
    payload_legacy = payload_simple
    resp3 = requests.post(
        fallback_url,
        auth=AUTH,
        headers=headers_legacy,
        json=payload_legacy,
        timeout=REQUEST_TIMEOUT
    )
    return resp3

def get_boards_for_project(project_key: str):
    """Obtiene IDs de tableros (boards) asociados a un proyecto (Scrum/Kanban)."""
    boards = []
    start_at = 0
    page_size = 50
    try:
        while True:
            resp = requests.get(
                f"{AGILE_BASE}/board",
                auth=AUTH,
                headers={"Accept": "application/json"},
                params={
                    "projectKeyOrId": project_key,
                    "startAt": start_at,
                    "maxResults": page_size
                },
                timeout=REQUEST_TIMEOUT
            )
            if resp.status_code != 200:
                break
            data = resp.json() or {}
            values = data.get("values", []) or []
            for b in values:
                bid = b.get("id")
                if bid is not None:
                    boards.append(bid)
            if len(values) < page_size:
                break
            start_at += page_size
    except requests.RequestException:
        pass
    return boards

def agile_search_issues(board_id: int, jql_query: str, start_at: int, max_results: int, fields_list):
    """Consulta issues vía Agile API para un board con soporte de JQL y campos."""
    params = {
        "jql": jql_query,
        "startAt": start_at,
        "maxResults": max_results,
        # Para garantizar custom fields en Agile fallback, pedir todo
        "fields": "*all",
        "expand": "names"
    }
    resp = requests.get(
        f"{AGILE_BASE}/board/{board_id}/issue",
        auth=AUTH,
        headers={"Accept": "application/json"},
        params=params,
        timeout=REQUEST_TIMEOUT
    )
    return resp

def test_jql_query(projects_subset):
    """Prueba una consulta JQL con un subconjunto de proyectos."""
    jql_query = JQL_BASE.format(projects=", ".join(projects_subset))
    
    try:
        response = _post_search_jql(jql_query, start_at=0, max_results=1)
        
        if response.status_code == 200:
            data = _normalize_search_response(response.json())
            total = data.get('total', 0)
            print(f"✅ Consulta válida para {projects_subset} - {total} issues disponibles")
            return True, total
        elif response.status_code == 410:
            print("ℹ️  410 en /search. Probando fallback Agile API...")
            # Fallback Agile: probar con el primer proyecto y primer board
            first_proj = projects_subset[0]
            boards = get_boards_for_project(first_proj)
            if not boards:
                print("❌ Agile fallback sin boards disponibles")
                return False, 0
            resp_ag = agile_search_issues(boards[0], jql_query, start_at=0, max_results=1, fields_list=SELECTED_FIELDS)
            if resp_ag.status_code == 200:
                data = resp_ag.json() or {}
                issues = data.get('issues', []) or []
                total = data.get('total', len(issues))
                if issues:
                    print(f"✅ Agile fallback OK para {first_proj} - {total} issues (muestra 1)")
                    return True, total
                else:
                    print("ℹ️  Agile fallback sin resultados")
                    return True, 0
            else:
                print(f"❌ Agile fallback falló - Status: {resp_ag.status_code}")
                print(f"📄 Respuesta: {resp_ag.text}")
                return False, 0
        else:
            print(f"❌ Error en consulta para {projects_subset} - Status: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
            return False, 0
            
    except requests.RequestException as e:
        print(f"❌ Error en consulta para {projects_subset}: {e}")
        return False, 0

def fetch_issues_by_block(projects_block, block_number):
    """Obtiene issues de un bloque específico de proyectos."""
    jql_query = JQL_BASE.format(projects=", ".join(projects_block))
    start_at = 0
    block_issues = []
    page_number = 1
    
    print(f"\n📦 Procesando bloque {block_number}: {projects_block}")
    print(f"📋 JQL: {jql_query}")
    print("-" * 60)
    
    # Validar consulta antes de proceder
    is_valid, total_available = test_jql_query(projects_block)
    if not is_valid:
        print(f"❌ Cancelando bloque {block_number} - Consulta inválida")
        return []
    
    if total_available == 0:
        print(f"ℹ️  Bloque {block_number} sin resultados")
        return []
    
    retry_count = 0
    use_agile_fallback = False
    agile_boards_cache = {}
    
    while True:
        try:
            print(f"📄 Bloque {block_number} - Página {page_number} (desde {start_at})")
            
            if not use_agile_fallback:
                response = _post_search_jql(jql_query, start_at=start_at, max_results=MAX_RESULTS)
                print(f"📡 Status: {response.status_code}")
                if response.status_code == 410:
                    print("ℹ️  Activando Agile fallback para este bloque...")
                    use_agile_fallback = True
                    # Reiniciar paginación en modo Agile
                    start_at = 0
                    page_number = 1
                    continue
                if response.status_code == 429:  # Rate limit
                    wait_time = int(response.headers.get('Retry-After', 60))
                    print(f"⏳ Rate limit alcanzado. Esperando {wait_time} segundos...")
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                data = _normalize_search_response(response.json())
                issues = data.get('issues', [])
            else:
                # Agile fallback: iterar por proyectos del bloque y primer board
                if not agile_boards_cache:
                    for proj in projects_block:
                        boards = get_boards_for_project(proj)
                        if boards:
                            agile_boards_cache[proj] = boards[0]
                # Si no hay boards para ninguno, abortar
                if not agile_boards_cache:
                    print("❌ Sin boards para Agile fallback en este bloque")
                    break
                # Consultar uno por uno y concatenar hasta MAX_RESULTS
                issues = []
                per_board_limit = MAX_RESULTS
                for proj, bid in agile_boards_cache.items():
                    resp = agile_search_issues(bid, jql_query, start_at=start_at, max_results=per_board_limit, fields_list=SELECTED_FIELDS)
                    if resp.status_code == 429:
                        wait_time = int(resp.headers.get('Retry-After', 60))
                        print(f"⏳ Rate limit (Agile) alcanzado. Esperando {wait_time} segundos...")
                        time.sleep(wait_time)
                        continue
                    resp.raise_for_status()
                    d = resp.json() or {}
                    issues.extend(d.get('issues', []) or [])
                print(f"📡 Agile fallback - página {page_number}: {len(issues)} issues")
            
            print(f"✅ Página {page_number}: {len(issues)} issues obtenidos")
            print(f"📊 Acumulado bloque {block_number}: {len(block_issues) + len(issues)} issues")
            
            if not issues:
                # Si no hay más issues en esta página, finalizar
                break
            
            block_issues.extend(issues)
            retry_count = 0  # Reset retry counter on success
            
            if len(issues) < MAX_RESULTS:
                print(f"🏁 Bloque {block_number} completado")
                break
                
            start_at += MAX_RESULTS
            page_number += 1
            
            # Pausa entre requests para ser amigable con la API
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except requests.RequestException as e:
            retry_count += 1
            print(f"❌ Error en bloque {block_number}, página {page_number} (intento {retry_count}/{MAX_RETRIES}): {e}")
            
            if retry_count >= MAX_RETRIES:
                print(f"❌ Máximo de reintentos alcanzado para bloque {block_number}")
                break
                
            wait_time = retry_count * 5  # Backoff exponencial
            print(f"⏳ Reintentando en {wait_time} segundos...")
            time.sleep(wait_time)
            
        except KeyboardInterrupt:
            print(f"\n⚠️ Interrupción del usuario en bloque {block_number}")
            return block_issues
    
    return block_issues
 
 
def fetch_issues():
    """Obtiene todos los issues de Jira procesando por bloques de proyectos."""
    print("🚀 Iniciando extracción optimizada por bloques...")
    print(f"🔗 URL: {URL}")
    print(f"📊 Campos solicitados: {FIELDS}")
    project_blocks = get_project_blocks()
    print(f"📦 Bloques de proyectos: {len(project_blocks)}")
    print("=" * 80)
    
    # Validar conexión antes de empezar
    if not validate_jira_connection():
        print("❌ No se puede continuar sin conexión válida")
        return []
    
    all_issues = []
    successful_blocks = 0
    failed_blocks = 0
    
    try:
        for i, projects_block in enumerate(project_blocks, 1):
            print(f"\n🔄 Iniciando bloque {i}/{len(project_blocks)}")
            
            block_issues = fetch_issues_by_block(projects_block, i)
            
            if block_issues:
                all_issues.extend(block_issues)
                successful_blocks += 1
                print(f"✅ Bloque {i} completado: {len(block_issues)} issues")
            else:
                failed_blocks += 1
                print(f"❌ Bloque {i} falló o sin resultados")
            
            # Pausa entre bloques
            if i < len(project_blocks):
                print(f"⏳ Pausa entre bloques...")
                time.sleep(DELAY_BETWEEN_REQUESTS * 2)
                
    except KeyboardInterrupt:
        print(f"\n⚠️ Proceso interrumpido por el usuario")
        print(f"📊 Issues obtenidos hasta el momento: {len(all_issues)}")
    
    print("\n" + "=" * 80)
    print(f"🎯 Extracción por bloques completada:")
    print(f"   📦 Bloques exitosos: {successful_blocks}/{len(project_blocks)}")
    print(f"   ❌ Bloques fallidos: {failed_blocks}/{len(project_blocks)}")
    print(f"   📊 Total de issues obtenidos: {len(all_issues)}")
    
    if failed_blocks > 0:
        print(f"⚠️ Algunos bloques fallaron. Revisa los logs anteriores.")
    
    return all_issues
 
 
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
 
 
def normalize_value(value):
    """Normaliza valores diversos a representaciones legibles."""
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("name", "displayName", "value", "id"):
            if key in value and value[key] is not None:
                return str(value[key])
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return ", ".join(normalize_value(v) for v in value)
    return str(value)

def normalize_description(value):
    """Devuelve la descripción como texto plano.
    Soporta string HTML/wiki y objetos ADF (Atlassian Document Format)."""
    if value is None:
        return ""
    # Si es ADF (dict con content)
    if isinstance(value, dict):
        def walk_adf(node):
            if isinstance(node, dict):
                t = node.get('type')
                if t == 'text':
                    return node.get('text', '')
                texts = []
                for c in node.get('content', []) or []:
                    texts.append(walk_adf(c))
                # Agregar saltos para párrafos/listas
                if t in ('paragraph', 'heading', 'bulletList', 'orderedList'): 
                    return (" ".join(filter(None, texts)) + "\n").strip()
                return " ".join(filter(None, texts))
            if isinstance(node, list):
                return "\n".join(filter(None, (walk_adf(n) for n in node)))
            return ""
        text = walk_adf(value)
        return html.unescape(text).strip()
    # Si es lista/dict desconocido
    if isinstance(value, list):
        return "\n".join(normalize_description(v) for v in value)
    # Si es string: quitar HTML simple
    s = str(value)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

# Helpers de fechas
def _extract_offset_from_created(created_str: str) -> str:
    """Extrae el offset de zona horaria de la cadena created (por ejemplo -0500)."""
    if not created_str:
        return "-0500"
    m = re.search(r'([+-]\d{4})$', str(created_str))
    return m.group(1) if m else "-0500"

def _is_created_like_format(s: str) -> bool:
    """Detecta si ya está en formato tipo created (ISO + offset)."""
    return bool(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?[+-]\d{4}$", str(s or "")))

def normalize_to_created_format(date_val, created_offset: str) -> str:
    """Convierte valores tipo '06/Dec/24 9:15 PM' al formato de 'created':
    YYYY-MM-DDTHH:MM:SS.000±ZZZZ. Si no se puede parsear, retorna el valor original.
    """
    s = str(date_val or "").strip()
    if not s:
        return ""
    if _is_created_like_format(s):
        return s
    # Intentar patrón conocido '06/Dec/24 9:15 PM'
    try:
        dt = datetime.strptime(s, "%d/%b/%y %I:%M %p")
        return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.000{created_offset}"
    except Exception:
        # Intentar otros patrones comunes si fuera necesario (extensible)
        for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M"):
            try:
                dt = datetime.strptime(s, fmt)
                return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.000{created_offset}"
            except Exception:
                continue
        return s

def parse_created_like(s: str):
    """Parsea fechas en formato tipo created (YYYY-MM-DDTHH:MM:SS(.fff)±ZZZZ). Devuelve datetime o None."""
    s = str(s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None

def process_issues(issues):
    """Procesa los issues obtenidos y estructura los datos."""
    processed_issues = []
    
    print("\n🔄 Iniciando procesamiento de issues...")
    print(f"📊 Total de issues a procesar: {len(issues)}")
    print("-" * 80)
 
    for i, issue in enumerate(issues, 1):
        try:
            fields = issue.get('fields', {})
 
            created = fields.get('created', 'No definido')
            created_offset = _extract_offset_from_created(created)
            key = issue.get('key', 'No definido')
            team = re.split(r'-', key)[0]  # Extrae el equipo del key
            summary = fields.get('summary', 'No definido')
            description = normalize_description(fields.get('description'))
            tribu_squad = normalize_value(fields.get('customfield_11365'))
            issue_type = (
                (fields.get('issuetype') or {}).get('name')
                if isinstance(fields.get('issuetype'), dict)
                else (str(fields.get('issuetype')) if fields.get('issuetype') is not None else 'No definido')
            )
            story_points = fields.get('customfield_10200', 'No definido')
            paso_a_desarrollo = normalize_to_created_format(normalize_value(fields.get('customfield_11112')), created_offset)
            paso_a_pruebas = normalize_to_created_format(normalize_value(fields.get('customfield_11113')), created_offset)
            paso_a_validacion = normalize_to_created_format(normalize_value(fields.get('customfield_11111')), created_offset)
            paso_a_done = normalize_to_created_format(normalize_value(fields.get('customfield_11115')), created_offset)
            paso_a_release = normalize_to_created_format(normalize_value(fields.get('customfield_11180')), created_offset)
            paso_a_produccion = normalize_to_created_format(normalize_value(fields.get('customfield_11181')), created_offset)

            # Calcular Cycle Time (días calendario) = done - desarrollo
            ct_days = ""
            dt_dev = parse_created_like(paso_a_desarrollo)
            dt_done = parse_created_like(paso_a_done)
            try:
                if dt_dev and dt_done:
                    delta = dt_done - dt_dev
                    ct_days = round(delta.total_seconds() / 86400.0, 2)
            except Exception:
                ct_days = ""

            # Calcular lead Time (días calendario) = done - created
            lt_days = ""
            dt_created = parse_created_like(created)
            try:
                if dt_created and dt_done:
                    delta_lt = dt_done - dt_created
                    lt_days = round(delta_lt.total_seconds() / 86400.0, 2)
            except Exception:
                lt_days = ""
 
            # Calcular Wait Time (días calendario) = desarrollo - created
            wt_days = ""
            try:
                if dt_created and dt_dev:
                    delta_wt = dt_dev - dt_created
                    wt_days = round(delta_wt.total_seconds() / 86400.0, 2)
            except Exception:
                wt_days = ""
 
            # Soporta diferentes IDs del campo Sprint en Cloud/Server
            sprints = (
                fields.get('customfield_10103')
                or fields.get('customfield_10020')
                or fields.get('sprint')
                or []
            )
 
            sprint_names = extract_sprint_data(sprints, 'name')
            board_id = extract_sprint_data(sprints, 'boardId')
            start_date = extract_sprint_data(sprints, 'startDate')
            end_date = extract_sprint_data(sprints, 'endDate')
            complete_date = extract_sprint_data(sprints, 'completeDate') or end_date
            periodo = determine_period(complete_date)
 
            sprint_numbers = ', '.join(re.findall(r'\d+', sprint_names)) if sprint_names else ''
 
            # Cantidad de sprint: contar elementos en la lista de sprints o, en su defecto, por 'sprint_numbers'
            if isinstance(sprints, list):
                cantidad_sprint = sum(1 for s in sprints if s)
            else:
                cantidad_sprint = len([x for x in (sprint_numbers.split(',') if sprint_numbers else []) if x.strip()])
 
            record = {
                "team": team,
                "boardId": board_id,
                "startDate": start_date,
                "endDate": end_date,
                "completeDate": complete_date,
                "periodo": periodo,
                "sprint": sprint_names,
                "sprint_numbers": sprint_numbers,
                "cantidad de sprint": cantidad_sprint,
                "created": created,
                "key": key,
                "summary": summary,
                "description": description,
                "Tribu/Squad": tribu_squad,
                "issue_type": issue_type,
                "story_points": story_points,
                "paso_a_desarrollo": paso_a_desarrollo,
                "paso_a_pruebas": paso_a_pruebas,
                "paso_a_validacion": paso_a_validacion,
                "paso_a_done": paso_a_done,
                "paso_a_release": paso_a_release,
                "paso_a_produccion": paso_a_produccion,
                "Cycle Time": ct_days,
                "lead Time": lt_days,
                "Wait Time": wt_days
            }
 
            # Agregar dinámicamente campos seleccionados adicionales
            base_mapped = {
                "created", "key", "summary", "description", "issuetype",
                "customfield_10200", "customfield_11112", "customfield_11113", "customfield_11111", "customfield_11115", "customfield_11180", "customfield_11181", "customfield_11365", "customfield_10103", "customfield_10020", "sprint"
            }
            for fname in SELECTED_FIELDS:
                if fname in base_mapped:
                    continue
                if fname in record:
                    continue
                record[fname] = normalize_value(fields.get(fname))
 
            processed_issues.append(record)
        except Exception as e:
            key = (issue or {}).get('key', 'N/A')
            print(f"⚠️  Error procesando issue {key}: {e}")
            continue
        
        # Log cada 50 issues procesados
        if i % 50 == 0:
            print(f"⚙️  Procesados {i}/{len(issues)} issues...")
 
    print(f"✅ Procesamiento completado: {len(processed_issues)} issues procesados")
    return processed_issues
 
 
def save_to_csv(data, filename_prefix="issues", output_dir="."):
    """Exporta los datos procesados a CSV (UTF-8). Incluye dinámicamente columnas adicionales."""
    import csv
    current_date = datetime.now().strftime("%Y%m%d")
    ensure_dir(output_dir)
    filename = os.path.join(output_dir, f"{filename_prefix}_{current_date}.csv")

    # Orden preferido y columnas adicionales detectadas
    preferred = [
        "team", "boardId", "startDate", "endDate", "completeDate",
        "periodo", "sprint", "sprint_numbers", "cantidad de sprint", "created", "key",
        "summary", "Tribu/Squad", "description", "issue_type", "story_points",
        "paso_a_desarrollo", "paso_a_pruebas", "paso_a_validacion", "paso_a_done",
        "paso_a_release", "paso_a_produccion", "Cycle Time", "lead Time", "Wait Time"
    ]
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())
    extra_cols = [k for k in sorted(all_keys) if k not in preferred]
    fieldnames = preferred + extra_cols

    print(f"\n💾 Guardando CSV...")
    print(f"📁 Archivo: {filename}")
    print(f"📊 Registros a guardar: {len(data)}")

    try:
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        print(f"✅ CSV generado: {filename}")
    except IOError as e:
        print(f"❌ Error al escribir el archivo CSV: {e}")

def save_to_json(data, filename_prefix="issues", output_dir="."):
    """Guarda los datos procesados en un archivo JSON con timestamp."""
    current_date = datetime.now().strftime("%Y%m%d")
    ensure_dir(output_dir)
    filename = os.path.join(output_dir, f"{filename_prefix}_{current_date}.json")

    print(f"\n💾 Guardando resultados...")
    print(f"📁 Archivo: {filename}")
    print(f"📊 Registros a guardar: {len(data)}")
    
    try:
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        print(f"✅ Los resultados se han guardado exitosamente en {filename}")
        
        # Mostrar estadísticas básicas
        if data:
            teams = set(item.get('team', 'N/A') for item in data)
            periods = {}
            for item in data:
                period = item.get('periodo', 'N/A')
                periods[period] = periods.get(period, 0) + 1
            
            print(f"\n📈 Estadísticas del archivo generado:")
            print(f"   🏢 Equipos únicos: {len(teams)} ({', '.join(sorted(teams))})")
            print(f"   📅 Distribución por período:")
            for period, count in periods.items():
                print(f"      - {period}: {count} issues")
                
    except IOError as e:
        print(f"❌ Error al escribir el archivo JSON: {e}")

def save_stats_by_team_type_csv(data, filename_prefix="issues_stats", output_dir="."):
    """Genera un CSV de conteos por equipo y tipo de issue."""
    from collections import defaultdict
    import csv
    counts = defaultdict(int)
    for row in data:
        team = str(row.get('team', 'N/A'))
        issue_type = str(row.get('issue_type', 'No definido'))
        counts[(team, issue_type)] += 1

    # Preparar filas
    rows = [
        {"team": team, "issue_type": issue_type, "count": count}
        for (team, issue_type), count in sorted(counts.items())
    ]

    current_date = datetime.now().strftime("%Y%m%d")
    ensure_dir(output_dir)
    filename = os.path.join(output_dir, f"{filename_prefix}_{current_date}.csv")
    print(f"\n📊 Guardando estadísticas por equipo y tipo de issue: {filename}")
    try:
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["team", "issue_type", "count"])
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        print(f"✅ Estadísticas generadas: {filename}")
    except IOError as e:
        print(f"❌ Error al escribir estadísticas CSV: {e}")

def fetch_all_fields():
    """Obtiene todos los campos de Jira (id, nombre y esquema)."""
    url = f"https://{JIRA_DOMAIN}/rest/api/3/field"
    try:
        resp = requests.get(url, auth=AUTH, headers={"Accept": "application/json"}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        items = resp.json()
        fields = []
        for it in items:
            schema = it.get("schema", {}) or {}
            fields.append({
                "id": it.get("id"),
                "name": it.get("name"),
                "custom": it.get("custom"),
                "type": it.get("type"),
                "schema_type": schema.get("type"),
                "schema_system": schema.get("system"),
                "schema_custom": schema.get("custom"),
                "schema_customId": schema.get("customId")
            })
        return fields
    except requests.RequestException as e:
        print(f"❌ Error obteniendo campos: {e}")
        return []

def fetch_story_fields_createmeta(project_key: str, issuetype_name: str = "Story"):
    """Obtiene campos aplicables a un tipo de issue específico usando CreateMeta."""
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/createmeta"
    params = {
        "projectKeys": project_key,
        "issuetypeNames": issuetype_name,
        "expand": "projects.issuetypes.fields"
    }
    try:
        resp = requests.get(url, auth=AUTH, headers={"Accept": "application/json"}, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        projects = data.get("projects", [])
        if not projects:
            print("⚠️  CreateMeta no devolvió proyectos. Verifica el project key y permisos.")
            return []
        issuetypes = projects[0].get("issuetypes", [])
        if not issuetypes:
            print("⚠️  CreateMeta sin tipos de issue para el proyecto dado.")
            return []
        fields_meta = issuetypes[0].get("fields", {})
        fields = []
        for fid, meta in fields_meta.items():
            schema = meta.get("schema", {}) or {}
            fields.append({
                "id": fid,
                "name": meta.get("name"),
                "required": bool(meta.get("required")),
                "schema_type": schema.get("type"),
                "schema_system": schema.get("system"),
                "schema_custom": schema.get("custom"),
                "schema_customId": schema.get("customId")
            })
        return fields
    except requests.RequestException as e:
        print(f"❌ Error obteniendo CreateMeta: {e}")
        return []

def _field_category(f: dict) -> str:
    """Devuelve 'system' o 'custom' según los metadatos del campo."""
    # Heurística: si tiene schema_system o no es custom → system; si id comienza con customfield_ → custom
    fid = str(f.get("id", ""))
    is_custom_flag = f.get("custom")
    schema_system = f.get("schema_system")
    schema_custom = f.get("schema_custom")
    if schema_system and not schema_custom:
        return "system"
    if is_custom_flag is False:
        return "system"
    if fid.startswith("customfield_"):
        return "custom"
    # Fallback por tipo
    return "custom" if (is_custom_flag or schema_custom) else "system"

def save_fields_catalog_csv(fields, filename_prefix="jira_fields", output_dir="."):
    """Guarda un catálogo de campos (id, nombre y metadatos) a CSV."""
    import csv
    current_date = datetime.now().strftime("%Y%m%d")
    ensure_dir(output_dir)
    filename = os.path.join(output_dir, f"{filename_prefix}_{current_date}.csv")
    fieldnames = [
        "id", "name", "required", "custom", "type",
        "schema_type", "schema_system", "schema_custom", "schema_customId"
    ]

    # Orden: primero system, luego custom; dentro de cada grupo, por nombre
    sorted_fields = sorted(
        fields,
        key=lambda f: (0 if _field_category(f) == "system" else 1, str(f.get("name", "")).lower())
    )

    # Normalizar claves faltantes
    norm_rows = []
    for f in sorted_fields:
        row = {k: f.get(k, "") for k in fieldnames}
        norm_rows.append(row)

    print(f"\n💾 Guardando catálogo de campos: {filename}")
    try:
        with open(filename, mode="w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for r in norm_rows:
                w.writerow(r)
        print(f"✅ Catálogo de campos generado: {filename} (total {len(norm_rows)})")
    except IOError as e:
        print(f"❌ Error al escribir catálogo de campos: {e}")

# ------------------------ Ejecución del Script ------------------------
 
if __name__ == "__main__":
    print("=" * 80)
    print("🎯 SCRIPT DE EXTRACCIÓN DE DATOS JIRA")
    print("=" * 80)

    start_time = datetime.now()
    print(f"⏰ Inicio: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Modo catálogo de campos si está habilitado por variables de entorno
        list_fields_mode = os.getenv("JIRA_LIST_FIELDS", "").strip().lower()  # valores: "all" | "story"
        output_dir = os.getenv("JIRA_OUTPUT_DIR", os.path.join(".", "exports"))
        file_prefix = os.getenv("JIRA_FILE_PREFIX", "issues")
        ensure_dir(output_dir)

        if list_fields_mode in ("all", "story"):
            if not validate_jira_connection():
                print("❌ No se puede continuar sin conexión válida")
                sys.exit(1)
            if list_fields_mode == "all":
                fields = fetch_all_fields()
                save_fields_catalog_csv(fields, filename_prefix=f"{file_prefix}_fields_all", output_dir=output_dir)
            else:
                project_key = os.getenv("JIRA_PROJECT_KEY", "").strip()
                if not project_key:
                    print("⚠️  JIRA_PROJECT_KEY no definido; listando todos los campos en su lugar.")
                    fields = fetch_all_fields()
                    save_fields_catalog_csv(fields, filename_prefix=f"{file_prefix}_fields_all", output_dir=output_dir)
                else:
                    fields = fetch_story_fields_createmeta(project_key, "Story")
                    save_fields_catalog_csv(fields, filename_prefix=f"{file_prefix}_fields_story_{project_key}", output_dir=output_dir)
            # Finalizar en modo catálogo de campos
            end_time = datetime.now()
            duration = end_time - start_time
            print("\n" + "=" * 80)
            print("📘 CATÁLOGO DE CAMPOS GENERADO")
            print("=" * 80)
            print(f"⏰ Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️  Duración total: {duration}")
            sys.exit(0)

        # Ejecución normal de extracción de issues
        issues = fetch_issues()  # Obtener los issues de Jira
        processed_issues = process_issues(issues)  # Procesar los issues obtenidos
        save_to_json(processed_issues, filename_prefix=file_prefix, output_dir=output_dir)

        export_csv_flag = os.getenv("JIRA_EXPORT_CSV", "false").lower() in ("1", "true", "yes")
        if export_csv_flag:
            save_to_csv(processed_issues, filename_prefix=file_prefix, output_dir=output_dir)

        # Generar estadísticas por equipo y tipo de issue (CSV)
        save_stats_by_team_type_csv(processed_issues, filename_prefix=f"{file_prefix}_stats", output_dir=output_dir)

        end_time = datetime.now()
        duration = end_time - start_time

        print("\n" + "=" * 80)
        print("🎉 EJECUCIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 80)
        print(f"⏰ Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Duración total: {duration}")

    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        print("=" * 80)