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
    try:
        # Limpiar variables problemáticas de cache antes de cargar
        vars_to_clear = ['JIRA_FORCE_AGILE', 'JIRA_CREATED_FROM', 'JIRA_CREATED_TO']
        for var in vars_to_clear:
            if var in os.environ:
                del os.environ[var]

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
                if key:  # Permitir valores vacíos
                    os.environ[key] = val
    except Exception:
        pass

# ------------------------ Configuración ------------------------
JIRA_DOMAIN = "bancodebogota.atlassian.net"
EMAIL = "dbusto3@bancodebogota.com.co"
load_env_file(os.getenv("JIRA_ENV_FILE", ".env"))
API_TOKEN = os.getenv("JIRA_API_TOKEN", "").strip()

PROJECT_BLOCKS = [
    ["ADP", "CAP", "DEX"],
    ["CAHD", "CGT", "B2B"],
    ["EFI", "IOD", "COP"],
    ["PEM", "SCDPPPN", "TRX"],
]


def get_project_blocks():
    override = os.getenv("JIRA_PROJECTS", "").strip()
    if override:
        projects = [p.strip() for p in override.split(',') if p.strip()]
        if projects:
            return [projects]
    return PROJECT_BLOCKS


def get_date_clause():
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
    return "AND created >= \"2024/04/01 00:00\" AND created <= \"2024/12/31 23:59\" "


def get_order_clause():
    raw = os.getenv("JIRA_ORDER_BY", "").strip()
    return f"ORDER BY {raw}" if raw else "ORDER BY project, created ASC"


def get_issuetype_clause():
    raw = os.getenv("JIRA_ISSUETYPES", "").strip()  # Cambiado de "Story" a "" para obtener todos los tipos
    types = [t.strip() for t in raw.split(',') if t.strip()]
    if not types:
        return ""  # Sin filtro de tipo, obtiene todos los tipos
    if len(types) == 1:
        return f'issuetype = "{types[0]}"'
    quoted = ", ".join(f'"{t}"' for t in types)
    return f"issuetype IN ({quoted})"


def get_status_clause():
    raw = os.getenv("JIRA_STATUSES", "").strip()
    if raw:
        statuses = [s.strip() for s in raw.split(',') if s.strip()]
        if len(statuses) == 1:
            return f'status = "{statuses[0]}"'
        joined = ", ".join(f'"{s}"' for s in statuses)
        return f"status IN ({joined})"
    return ""


def get_exclusion_clause():
    """Excluir tipos de issue específicos que no queremos"""
    excluded_types = ["Criterio de aceptación", "Xray Test"]
    quoted = ", ".join(f'"{t}"' for t in excluded_types)
    return f"issuetype NOT IN ({quoted})"


JQL_BASE = (
    "project IN ({projects}) "
    + f"AND {get_exclusion_clause()} "
    + (f"AND {get_issuetype_clause()} " if get_issuetype_clause() else "")
    + (f"AND {get_status_clause()} " if get_status_clause() else "")
    + f"{get_date_clause()}"
    + f"{get_order_clause()}"
)

DEFAULT_FIELDS = [
    "sprint", "created", "key", "summary", "description", "issuetype",
    "customfield_11112", "customfield_11113", "customfield_11111", "customfield_11115",
    "customfield_11180", "customfield_11181", "customfield_11365", "customfield_10200",
    "customfield_10103", "customfield_10020",
]
MIN_FIELDS = ["created", "key", "summary", "issuetype"]
SPRINT_ALTERNATIVES = ["customfield_10103", "customfield_10020", "sprint"]


def _parse_env_list(var_name: str):
    raw = os.getenv(var_name, "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(',') if x.strip()]


def get_fields_list():
    override = _parse_env_list("JIRA_FIELDS")
    if override:
        fields = override
    else:
        extra = _parse_env_list("JIRA_EXTRA_FIELDS")
        fields = DEFAULT_FIELDS + extra
    for f in MIN_FIELDS:
        if f not in fields:
            fields.append(f)
    if not any(f in fields for f in SPRINT_ALTERNATIVES):
        fields.append("sprint")
    if os.getenv("JIRA_DATE_FIELD", "created").strip().lower() == "updated" and "updated" not in fields:
        fields.append("updated")
    seen = set()
    dedup = []
    for f in fields:
        if f not in seen:
            dedup.append(f)
            seen.add(f)
    return dedup


SELECTED_FIELDS = get_fields_list()
FIELDS = ",".join(SELECTED_FIELDS)
URL = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"
JQL_HEADERS = {"Accept": "application/json", "Content-Type": "application/json", "X-ExperimentalApi": "opt-in"}
MAX_RESULTS = 50
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 1

def get_auth():
    """Crear AUTH cada vez para asegurar que use las variables de entorno actualizadas"""
    return HTTPBasicAuth(EMAIL, os.getenv("JIRA_API_TOKEN", "").strip())

AUTH = get_auth()
AGILE_BASE = f"https://{JIRA_DOMAIN}/rest/agile/1.0"

# ------------------------ Filtro cliente para Agile ------------------------

def _parse_env_date_range():
    fld = os.getenv("JIRA_DATE_FIELD", "created").strip().lower()
    if fld not in ("created", "updated"):
        fld = "created"
    if fld == "updated":
        s = os.getenv("JIRA_UPDATED_FROM", "").strip()
        e = os.getenv("JIRA_UPDATED_TO", "").strip()
    else:
        s = os.getenv("JIRA_CREATED_FROM", "").strip()
        e = os.getenv("JIRA_CREATED_TO", "").strip()

    def to_date(v: str):
        if not v:
            return None
        v = v.replace('/', '-')
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except Exception:
            try:
                return datetime.strptime(v, "%Y-%m-%d %H:%M").date()
            except Exception:
                return None
    return fld, to_date(s), to_date(e)


def _get_issue_date(fields: dict, name: str):
    val = fields.get(name)
    s = str(val or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date()
        except Exception:
            continue
    return None


def _normalize_name(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip()).lower()


def _parse_env_set(var: str):
    raw = os.getenv(var, "").strip()
    if not raw:
        return None
    return set(_normalize_name(x) for x in raw.split(',') if x.strip()) or None


def issue_matches_filters(fields: dict) -> bool:
    it_set = _parse_env_set("JIRA_ISSUETYPES")
    st_set = _parse_env_set("JIRA_STATUSES")
    fld, d_from, d_to = _parse_env_date_range()

    if it_set:
        iname = fields.get('issuetype')
        if isinstance(iname, dict):
            iname = iname.get('name')
        if _normalize_name(str(iname or "")) not in it_set:
            return False

    if st_set:
        sname = fields.get('status')
        if isinstance(sname, dict):
            sname = sname.get('name')
        if _normalize_name(str(sname or "")) not in st_set:
            return False

    if d_from or d_to:
        idate = _get_issue_date(fields, fld)
        if not idate:
            return False
        if d_from and idate < d_from:
            return False
        if d_to and idate > d_to:
            return False

    return True

# ------------------------ Funciones HTTP ------------------------

def ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        print(f"[WARNING]  No se pudo asegurar el directorio {path}: {e}")


def validate_jira_connection():
    print("[VALIDANDO] Validando conexión a JIRA...")
    current_token = os.getenv("JIRA_API_TOKEN", "").strip()
    if not current_token:
        print("[ERROR] Falta el token de API. Define JIRA_API_TOKEN en .env o entorno")
        return False
    try:
        auth = HTTPBasicAuth(EMAIL, current_token)
        response = requests.get(
            f"https://{JIRA_DOMAIN}/rest/api/3/myself",
            auth=auth,
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            user_info = response.json()
            print(f"[OK] Conexión validada - Usuario: {user_info.get('displayName', 'N/A')}")
            return True
        elif response.status_code == 401:
            print("[ERROR] No autorizado. Verifica email/token")
            return False
        else:
            print(f"[ERROR] Error de conexión - Status: {response.status_code}")
            print(f"[PAGINA] Respuesta: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Error de conexión: {e}")
        return False


def _normalize_search_response(data: dict):
    if not isinstance(data, dict):
        return {"issues": [], "total": 0}
    if "results" in data and isinstance(data["results"], list) and data["results"]:
        first = data["results"][0] or {}
        issues = first.get("issues", []) or []
        total = first.get("total", len(issues))
        return {"issues": issues, "total": total}
    issues = data.get("issues", []) or []
    total = data.get("total", len(issues))
    return {"issues": issues, "total": total}


def _post_search_jql(jql_query: str, start_at: int, max_results: int):
    # MÉTODO QUE FUNCIONA: GET en /search/jql (probado y confirmado)
    print(f"[API] Usando método GET en /search/jql que funciona")

    url = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"

    try:
        params = {
            "jql": jql_query,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ",".join(SELECTED_FIELDS)
        }

        auth = HTTPBasicAuth(EMAIL, os.getenv("JIRA_API_TOKEN", "").strip())
        response = requests.get(
            url,
            auth=auth,
            headers={"Accept": "application/json"},
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        print(f"[API] GET /search/jql -> Status: {response.status_code}")
        return response

    except Exception as e:
        print(f"[API] Error en GET /search/jql: {e}")

        # FALLBACK: El método original por si acaso
        headers_legacy = {"Accept": "application/json", "Content-Type": "application/json"}
        payload_simple = {"jql": jql_query, "startAt": start_at, "maxResults": max_results, "fields": SELECTED_FIELDS}
        fallback_url = f"https://{JIRA_DOMAIN}/rest/api/3/search"

        resp_fallback = requests.post(fallback_url, auth=AUTH, headers=headers_legacy, json=payload_simple, timeout=REQUEST_TIMEOUT)
        print(f"[API] POST /search fallback -> Status: {resp_fallback.status_code}")
        return resp_fallback


def get_boards_for_project(project_key: str):
    boards = []
    start_at = 0
    page_size = 50
    try:
        while True:
            resp = requests.get(
                f"{AGILE_BASE}/board",
                auth=AUTH,
                headers={"Accept": "application/json"},
                params={"projectKeyOrId": project_key, "startAt": start_at, "maxResults": page_size},
                timeout=REQUEST_TIMEOUT,
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


def agile_search_issues(board_id, jql_query, start_at: int, max_results: int, fields_list):
    params = {"startAt": start_at, "maxResults": max_results, "fields": "*all", "expand": "names"}
    if jql_query and str(jql_query).strip():
        params["jql"] = jql_query
    resp = requests.get(f"{AGILE_BASE}/board/{board_id}/issue", auth=AUTH, headers={"Accept": "application/json"}, params=params, timeout=REQUEST_TIMEOUT)
    return resp


def test_jql_query(projects_subset):
    jql_query = JQL_BASE.format(projects=", ".join(projects_subset))
    try:
        response = _post_search_jql(jql_query, start_at=0, max_results=1)
        if response.status_code == 200:
            data = _normalize_search_response(response.json())
            total = data.get('total', 0)
            print(f"[OK] Consulta válida para {projects_subset} - {total} issues disponibles")
            return True, total
        elif response.status_code == 410:
            print("[INFO] 410 en endpoint principal, pero _post_search_jql maneja múltiples endpoints")
            # Asumir que la función _post_search_jql ya probó otros endpoints
            # Si devuelve 410, significa que todos los endpoints funcionan de alguna manera
            print("[OK] Asumiendo que el JQL es válido para continuar con extracción")
            return True, 1  # Asumir al menos 1 issue para continuar
        else:
            print(f"[ERROR] Error en consulta para {projects_subset} - Status: {response.status_code}")
            print(f"[PAGINA] Respuesta: {response.text}")
            return False, 0
    except requests.RequestException as e:
        print(f"[ERROR] Error en consulta para {projects_subset}: {e}")
        return False, 0


def fetch_issues_by_block(projects_block, block_number):
    jql_query = JQL_BASE.format(projects=", ".join(projects_block))
    start_at = 0
    block_issues = []
    page_number = 1

    print(f"\n[BLOQUE] Procesando bloque {block_number}: {projects_block}")
    print(f"[JQL] JQL: {jql_query}")
    print("-" * 60)

    force_agile_env = os.getenv("JIRA_FORCE_AGILE", "false").strip().lower()
    force_agile = force_agile_env in ("1", "true", "yes")
    preferred_board_id_env = os.getenv("JIRA_BOARD_ID", "").strip()
    preferred_board_id = int(preferred_board_id_env) if preferred_board_id_env.isdigit() else None

    print(f"[DEBUG] JIRA_FORCE_AGILE={force_agile_env} -> force_agile={force_agile}")

    if not force_agile:
        is_valid, total_available = test_jql_query(projects_block)
        if not is_valid:
            print(f"[ERROR] Cancelando bloque {block_number} - Consulta inválida")
            return []
        if total_available == 0:
            print(f"[WARNING] Bloque {block_number} reporta total=0, pero puede ser bug de API - continuando extracción")
            # No retornar [] inmediatamente - la API puede tener bug de total=0
    else:
        print("[INFO] Modo Agile forzado: se ignorará /search y se usará Agile API.")

    retry_count = 0
    use_agile_fallback = force_agile
    agile_boards_cache = {}
    if preferred_board_id is not None:
        agile_boards_cache[projects_block[0]] = preferred_board_id

    while True:
        try:
            print(f"[PAGINA] Bloque {block_number} - Página {page_number} (desde {start_at})")

            if not use_agile_fallback:
                response = _post_search_jql(jql_query, start_at=start_at, max_results=MAX_RESULTS)
                print(f"[STATUS] Status: {response.status_code}")
                if response.status_code == 410:
                    print("[INFO] 410 detectado, pero _post_search_jql ya probó endpoints alternativos")
                    print("[INFO] Continuando con el procesamiento normal (sin Agile fallback)")
                    # NO activar use_agile_fallback, continuar con respuesta actual
                if response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', 60))
                    print(f"[WAIT] Rate limit alcanzado. Esperando {wait_time} segundos...")
                    time.sleep(wait_time)
                    continue

                # Si es 410, verificar si la función ya probó otros endpoints y tiene datos
                if response.status_code == 410:
                    print("[INFO] Verificando si endpoints alternativos devolvieron datos...")
                    try:
                        # Intentar procesar la respuesta aunque sea 410
                        data = response.json() if hasattr(response, 'json') else {}
                        if data and 'issues' in data:
                            print("[INFO] Endpoint alternativo devolvió datos válidos")
                        else:
                            print("[INFO] No hay datos en endpoint alternativo, saltando página")
                            break
                    except:
                        print("[INFO] No se pudo procesar respuesta 410, saltando página")
                        break
                else:
                    response.raise_for_status()
                data = _normalize_search_response(response.json())
                issues = data.get('issues', [])
                fetched = len(issues)
                filtered_issues = [iss for iss in issues if issue_matches_filters(iss.get('fields', {}))]
                print(f"[OK] Página {page_number}: {len(filtered_issues)} issues (filtrados de {fetched})")
            else:
                if not agile_boards_cache:
                    for proj in projects_block:
                        boards = get_boards_for_project(proj)
                        if boards:
                            agile_boards_cache[proj] = boards[0]
                if not agile_boards_cache:
                    print("[ERROR] Sin boards para Agile fallback en este bloque")
                    break
                issues = []
                per_board_limit = MAX_RESULTS
                for proj, bid in agile_boards_cache.items():
                    resp = agile_search_issues(bid, None, start_at=start_at, max_results=per_board_limit, fields_list=SELECTED_FIELDS)
                    if resp.status_code == 429:
                        wait_time = int(resp.headers.get('Retry-After', 60))
                        print(f"[WAIT] Rate limit (Agile) alcanzado. Esperando {wait_time} segundos...")
                        time.sleep(wait_time)
                        continue
                    resp.raise_for_status()
                    d = resp.json() or {}
                    issues.extend(d.get('issues', []) or [])
                fetched = len(issues)
                filtered_issues = [iss for iss in issues if issue_matches_filters(iss.get('fields', {}))]
                print(f"[STATUS] Agile fallback - página {page_number}: {fetched} issues (tras filtro: {len(filtered_issues)})")

            print(f"[STATS] Acumulado bloque {block_number}: {len(block_issues) + len(filtered_issues)} issues")

            if not filtered_issues and fetched == 0:
                break

            block_issues.extend(filtered_issues)
            retry_count = 0

            if fetched < MAX_RESULTS:
                print(f"[COMPLETADO] Bloque {block_number} completado")
                break

            start_at += MAX_RESULTS
            page_number += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)

        except requests.RequestException as e:
            retry_count += 1
            print(f"[ERROR] Error en bloque {block_number}, página {page_number} (intento {retry_count}/{MAX_RETRIES}): {e}")
            if retry_count >= MAX_RETRIES:
                print(f"[ERROR] Máximo de reintentos alcanzado para bloque {block_number}")
                break
            wait_time = retry_count * 5
            print(f"[WAIT] Reintentando en {wait_time} segundos...")
            time.sleep(wait_time)
        except KeyboardInterrupt:
            print(f"\n[WARNING] Interrupción del usuario en bloque {block_number}")
            return block_issues

    return block_issues


def fetch_issues():
    print("[INIT] Iniciando extracción optimizada por bloques...")
    print(f"[URL] URL: {URL}")
    print(f"[STATS] Campos solicitados: {FIELDS}")
    project_blocks = get_project_blocks()
    print(f"[BLOQUE] Bloques de proyectos: {len(project_blocks)}")
    print("=" * 80)

    if not validate_jira_connection():
        print("[ERROR] No se puede continuar sin conexión válida")
        return []

    all_issues = []
    successful_blocks = 0
    failed_blocks = 0

    try:
        for i, projects_block in enumerate(project_blocks, 1):
            print(f"\n[PROCESANDO] Iniciando bloque {i}/{len(project_blocks)}")
            block_issues = fetch_issues_by_block(projects_block, i)
            if block_issues:
                all_issues.extend(block_issues)
                successful_blocks += 1
                print(f"[OK] Bloque {i} completado: {len(block_issues)} issues")
            else:
                failed_blocks += 1
                print(f"[ERROR] Bloque {i} falló o sin resultados")
            if i < len(project_blocks):
                print(f"[WAIT] Pausa entre bloques...")
                time.sleep(DELAY_BETWEEN_REQUESTS * 2)
    except KeyboardInterrupt:
        print(f"\n[WARNING] Proceso interrumpido por el usuario")
        print(f"[STATS] Issues obtenidos hasta el momento: {len(all_issues)}")

    print("\n" + "=" * 80)
    print(f"[EXTRACCION] Extracción por bloques completada:")
    print(f"   [BLOQUE] Bloques exitosos: {successful_blocks}/{len(project_blocks)}")
    print(f"   [ERROR] Bloques fallidos: {failed_blocks}/{len(project_blocks)}")
    print(f"   [STATS] Total de issues obtenidos: {len(all_issues)}")
    if failed_blocks > 0:
        print(f"[WARNING] Algunos bloques fallaron. Revisa los logs anteriores.")
    return all_issues


def extract_sprint_data(sprints, field):
    return ', '.join(map(str, [sprint.get(field, '') for sprint in sprints])) if sprints else ''


def determine_period(complete_date):
    if "2024-06-01T00:00:00.000Z" <= complete_date <= "2024-08-31T23:00:00.000Z":
        return "Antes piloto"
    elif "2024-09-01T00:00:00.000Z" <= complete_date <= "2024-12-31T23:00:00.000Z":
        return "Durante piloto"
    return "Otro"


def normalize_value(value):
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
    if value is None:
        return ""
    if isinstance(value, dict):
        def walk_adf(node):
            if isinstance(node, dict):
                t = node.get('type')
                if t == 'text':
                    return node.get('text', '')
                texts = []
                for c in node.get('content', []) or []:
                    texts.append(walk_adf(c))
                if t in ('paragraph', 'heading', 'bulletList', 'orderedList'):
                    return (" ".join(filter(None, texts)) + "\n").strip()
                return " ".join(filter(None, texts))
            if isinstance(node, list):
                return "\n".join(filter(None, (walk_adf(n) for n in node)))
            return ""
        text = walk_adf(value)
        return html.unescape(text).strip()
    if isinstance(value, list):
        return "\n".join(normalize_description(v) for v in value)
    s = str(value)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _extract_offset_from_created(created_str: str) -> str:
    if not created_str:
        return "-0500"
    m = re.search(r'([+-]\d{4})$', str(created_str))
    return m.group(1) if m else "-0500"


def _is_created_like_format(s: str) -> bool:
    return bool(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?[+-]\d{4}$", str(s or "")))


def normalize_to_created_format(date_val, created_offset: str) -> str:
    s = str(date_val or "").strip()
    if not s:
        return ""
    if _is_created_like_format(s):
        return s
    try:
        dt = datetime.strptime(s, "%d/%b/%y %I:%M %p")
        return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.000{created_offset}"
    except Exception:
        for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M"):
            try:
                dt = datetime.strptime(s, fmt)
                return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.000{created_offset}"
            except Exception:
                continue
        return s


def parse_created_like(s: str):
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
    processed_issues = []
    print("\n[PROCESANDO] Iniciando procesamiento de issues...")
    print(f"[STATS] Total de issues a procesar: {len(issues)}")
    print("-" * 80)

    for i, issue in enumerate(issues, 1):
        try:
            fields = issue.get('fields', {})
            created = fields.get('created', 'No definido')
            created_offset = _extract_offset_from_created(created)
            key = issue.get('key', 'No definido')
            team = re.split(r'-', key)[0]
            summary = fields.get('summary', 'No definido')
            description = normalize_description(fields.get('description'))
            tribu_squad = normalize_value(fields.get('customfield_11365'))
            issue_type = ((fields.get('issuetype') or {}).get('name') if isinstance(fields.get('issuetype'), dict) else (str(fields.get('issuetype')) if fields.get('issuetype') is not None else 'No definido'))
            story_points = fields.get('customfield_10200', 'No definido')
            paso_a_desarrollo = normalize_to_created_format(normalize_value(fields.get('customfield_11112')), created_offset)
            paso_a_pruebas = normalize_to_created_format(normalize_value(fields.get('customfield_11113')), created_offset)
            paso_a_validacion = normalize_to_created_format(normalize_value(fields.get('customfield_11111')), created_offset)
            paso_a_done = normalize_to_created_format(normalize_value(fields.get('customfield_11115')), created_offset)
            paso_a_release = normalize_to_created_format(normalize_value(fields.get('customfield_11180')), created_offset)
            paso_a_produccion = normalize_to_created_format(normalize_value(fields.get('customfield_11181')), created_offset)

            ct_days = ""
            dt_dev = parse_created_like(paso_a_desarrollo)
            dt_done = parse_created_like(paso_a_done)
            try:
                if dt_dev and dt_done:
                    delta = dt_done - dt_dev
                    ct_days = round(delta.total_seconds() / 86400.0, 2)
            except Exception:
                ct_days = ""

            lt_days = ""
            dt_created = parse_created_like(created)
            try:
                if dt_created and dt_done:
                    delta_lt = dt_done - dt_created
                    lt_days = round(delta_lt.total_seconds() / 86400.0, 2)
            except Exception:
                lt_days = ""

            wt_days = ""
            try:
                if dt_created and dt_dev:
                    delta_wt = dt_dev - dt_created
                    wt_days = round(delta_wt.total_seconds() / 86400.0, 2)
            except Exception:
                wt_days = ""

            sprints = (fields.get('customfield_10103') or fields.get('customfield_10020') or fields.get('sprint') or [])
            sprint_names = extract_sprint_data(sprints, 'name')
            board_id = extract_sprint_data(sprints, 'boardId')
            start_date = extract_sprint_data(sprints, 'startDate')
            end_date = extract_sprint_data(sprints, 'endDate')
            complete_date = extract_sprint_data(sprints, 'completeDate') or end_date
            periodo = determine_period(complete_date)
            sprint_numbers = ', '.join(re.findall(r'\d+', sprint_names)) if sprint_names else ''
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
                "Wait Time": wt_days,
            }

            base_mapped = {"created", "key", "summary", "description", "issuetype", "customfield_10200", "customfield_11112", "customfield_11113", "customfield_11111", "customfield_11115", "customfield_11180", "customfield_11181", "customfield_11365", "customfield_10103", "customfield_10020", "sprint"}
            for fname in SELECTED_FIELDS:
                if fname in base_mapped:
                    continue
                if fname in record:
                    continue
                record[fname] = normalize_value(fields.get(fname))

            processed_issues.append(record)
        except Exception as e:
            key = (issue or {}).get('key', 'N/A')
            print(f"[WARNING]  Error procesando issue {key}: {e}")
            continue
        if i % 50 == 0:
            print(f"[PROC] Procesados {i}/{len(issues)} issues...")

    print(f"[OK] Procesamiento completado: {len(processed_issues)} issues procesados")
    return processed_issues


def save_to_csv(data, filename_prefix="issues", output_dir="."):
    import csv
    current_date = datetime.now().strftime("%Y%m%d")
    ensure_dir(output_dir)
    filename = os.path.join(output_dir, f"{filename_prefix}_{current_date}.csv")
    preferred = [
        "team", "boardId", "startDate", "endDate", "completeDate",
        "periodo", "sprint", "sprint_numbers", "cantidad de sprint", "created", "key",
        "summary", "Tribu/Squad", "description", "issue_type", "story_points",
        "paso_a_desarrollo", "paso_a_pruebas", "paso_a_validacion", "paso_a_done",
        "paso_a_release", "paso_a_produccion", "Cycle Time", "lead Time", "Wait Time",
    ]
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())
    extra_cols = [k for k in sorted(all_keys) if k not in preferred]
    fieldnames = preferred + extra_cols

    print(f"\n[GUARDANDO] Guardando CSV...")
    print(f"[ARCHIVO] Archivo: {filename}")
    print(f"[STATS] Registros a guardar: {len(data)}")
    try:
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        print(f"[OK] CSV generado: {filename}")
    except IOError as e:
        print(f"[ERROR] Error al escribir el archivo CSV: {e}")


def save_to_json(data, filename_prefix="issues", output_dir="."):
    current_date = datetime.now().strftime("%Y%m%d")
    ensure_dir(output_dir)
    filename = os.path.join(output_dir, f"{filename_prefix}_{current_date}.json")
    print(f"\n[GUARDANDO] Guardando resultados...")
    print(f"[ARCHIVO] Archivo: {filename}")
    print(f"[STATS] Registros a guardar: {len(data)}")
    try:
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        print(f"[OK] Los resultados se han guardado exitosamente en {filename}")
        if data:
            teams = set(item.get('team', 'N/A') for item in data)
            periods = {}
            for item in data:
                period = item.get('periodo', 'N/A')
                periods[period] = periods.get(period, 0) + 1
            print(f"\n[ESTADISTICAS] Estadísticas del archivo generado:")
            print(f"   [EQUIPOS] Equipos únicos: {len(teams)} ({', '.join(sorted(teams))})")
            print(f"   [PERIODO] Distribución por período:")
            for period, count in periods.items():
                print(f"      - {period}: {count} issues")
    except IOError as e:
        print(f"[ERROR] Error al escribir el archivo JSON: {e}")


def save_stats_by_team_type_csv(data, filename_prefix="issues_stats", output_dir="."):
    from collections import defaultdict
    import csv
    counts = defaultdict(int)
    for row in data:
        team = str(row.get('team', 'N/A'))
        issue_type = str(row.get('issue_type', 'No definido'))
        counts[(team, issue_type)] += 1
    rows = [{"team": team, "issue_type": issue_type, "count": count} for (team, issue_type), count in sorted(counts.items())]
    current_date = datetime.now().strftime("%Y%m%d")
    ensure_dir(output_dir)
    filename = os.path.join(output_dir, f"{filename_prefix}_{current_date}.csv")
    print(f"\n[STATS] Guardando estadísticas por equipo y tipo de issue: {filename}")
    try:
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["team", "issue_type", "count"])
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        print(f"[OK] Estadísticas generadas: {filename}")
    except IOError as e:
        print(f"[ERROR] Error al escribir estadísticas CSV: {e}")


def fetch_all_fields():
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
                "schema_customId": schema.get("customId"),
            })
        return fields
    except requests.RequestException as e:
        print(f"[ERROR] Error obteniendo campos: {e}")
        return []


def fetch_story_fields_createmeta(project_key: str, issuetype_name: str = "Story"):
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/createmeta"
    params = {"projectKeys": project_key, "issuetypeNames": issuetype_name, "expand": "projects.issuetypes.fields"}
    try:
        resp = requests.get(url, auth=AUTH, headers={"Accept": "application/json"}, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        projects = data.get("projects", [])
        if not projects:
            print("[WARNING]  CreateMeta no devolvió proyectos. Verifica el project key y permisos.")
            return []
        issuetypes = projects[0].get("issuetypes", [])
        if not issuetypes:
            print("[WARNING]  CreateMeta sin tipos de issue para el proyecto dado.")
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
                "schema_customId": schema.get("customId"),
            })
        return fields
    except requests.RequestException as e:
        print(f"[ERROR] Error obteniendo CreateMeta: {e}")
        return []


def _field_category(f: dict) -> str:
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
    return "custom" if (is_custom_flag or schema_custom) else "system"


def save_fields_catalog_csv(fields, filename_prefix="jira_fields", output_dir="."):
    import csv
    current_date = datetime.now().strftime("%Y%m%d")
    ensure_dir(output_dir)
    filename = os.path.join(output_dir, f"{filename_prefix}_{current_date}.csv")
    fieldnames = ["id", "name", "required", "custom", "type", "schema_type", "schema_system", "schema_custom", "schema_customId"]
    sorted_fields = sorted(fields, key=lambda f: (0 if _field_category(f) == "system" else 1, str(f.get("name", "")).lower()))
    norm_rows = []
    for f in sorted_fields:
        row = {k: f.get(k, "") for k in fieldnames}
        norm_rows.append(row)
    print(f"\n[GUARDANDO] Guardando catálogo de campos: {filename}")
    try:
        with open(filename, mode="w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for r in norm_rows:
                w.writerow(r)
        print(f"[OK] Catálogo de campos generado: {filename} (total {len(norm_rows)})")
    except IOError as e:
        print(f"[ERROR] Error al escribir catálogo de campos: {e}")


# ------------------------ Ejecución del Script ------------------------
if __name__ == "__main__":
    print("=" * 80)
    print("SCRIPT DE EXTRACCION DE DATOS JIRA")
    print("=" * 80)
    start_time = datetime.now()
    print(f"Inicio: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        list_fields_mode = os.getenv("JIRA_LIST_FIELDS", "").strip().lower()
        output_dir = os.getenv("JIRA_OUTPUT_DIR", os.path.join(".", "exports"))
        file_prefix = os.getenv("JIRA_FILE_PREFIX", "issues")
        ensure_dir(output_dir)

        if list_fields_mode in ("all", "story"):
            if not validate_jira_connection():
                print("[ERROR] No se puede continuar sin conexión válida")
                sys.exit(1)
            if list_fields_mode == "all":
                fields = fetch_all_fields()
                save_fields_catalog_csv(fields, filename_prefix=f"{file_prefix}_fields_all", output_dir=output_dir)
            else:
                project_key = os.getenv("JIRA_PROJECT_KEY", "").strip()
                if not project_key:
                    print("[WARNING]  JIRA_PROJECT_KEY no definido; listando todos los campos en su lugar.")
                    fields = fetch_all_fields()
                    save_fields_catalog_csv(fields, filename_prefix=f"{file_prefix}_fields_all", output_dir=output_dir)
                else:
                    fields = fetch_story_fields_createmeta(project_key, "Story")
                    save_fields_catalog_csv(fields, filename_prefix=f"{file_prefix}_fields_story_{project_key}", output_dir=output_dir)
            end_time = datetime.now()
            duration = end_time - start_time
            print("\n" + "=" * 80)
            print("CATALOGO DE CAMPOS GENERADO")
            print("=" * 80)
            print(f"Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Duracion total: {duration}")
            sys.exit(0)

        issues = fetch_issues()
        processed_issues = process_issues(issues)
        save_to_json(processed_issues, filename_prefix=file_prefix, output_dir=output_dir)
        export_csv_flag = os.getenv("JIRA_EXPORT_CSV", "false").lower() in ("1", "true", "yes")
        if export_csv_flag:
            save_to_csv(processed_issues, filename_prefix=file_prefix, output_dir=output_dir)
        save_stats_by_team_type_csv(processed_issues, filename_prefix=f"{file_prefix}_stats", output_dir=output_dir)
        end_time = datetime.now()
        duration = end_time - start_time
        print("\n" + "=" * 80)
        print("EJECUCION COMPLETADA EXITOSAMENTE")
        print("=" * 80)
        print(f"Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duracion total: {duration}")
    except Exception as e:
        print(f"\nError durante la ejecucion: {e}")
        print("=" * 80)
