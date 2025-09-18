# Jira Cloud Data Extractor — Guía rápida

Este script extrae issues desde Jira Cloud (REST API v3) y exporta un archivo JSON (y opcionalmente CSV) con todos los registros.

## Requisitos

- Python 3.8+
- Paquete `requests`

Instalación rápida (opcional si ya está instalado):

```powershell
pip install requests
```

## Configuración

### Opción 1: Usar archivo .env (Recomendado)

1. Copia el archivo `.env.example` como `.env`:
   ```bash
   cp APIJIRA/.env.example APIJIRA/.env
   ```

2. Edita el archivo `.env` y completa tu token real:
   ```bash
   JIRA_API_TOKEN=tu_token_real_aqui
   ```

### Opción 2: Variables de entorno (PowerShell)

Defina estas variables antes de ejecutar el script:

```powershell
# Credenciales
$env:JIRA_API_TOKEN = "<tu_api_token>"

# Salida
$env:JIRA_OUTPUT_DIR = ".\exports"          # Carpeta de salida (opcional, por defecto .\exports)
$env:JIRA_FILE_PREFIX = "jira_issues"         # Prefijo de archivos (opcional, por defecto "issues")
$env:JIRA_EXPORT_CSV = "true"                 # Generar CSV además de JSON (true/false)

# Campos (elija UNA de estas opciones)
# Opción A: Sobrescribir completamente los campos a pedir a la API
# $env:JIRA_FIELDS = "key,summary,created,issuetype,priority,assignee,customfield_10200"

# Opción B: Mantener los campos por defecto y añadir campos extra
# $env:JIRA_EXTRA_FIELDS = "priority,assignee,reporter,labels"
```

Notas sobre campos:

- El script garantiza mínimos: `created`, `key`, `summary`, `issuetype`.
- Incluye automáticamente al menos un campo de Sprint (`customfield_10103`, `customfield_10020` o `sprint`).
- Story Points está mapeado por defecto a `customfield_10200`. Si tu instancia usa otro ID, añádelo en `JIRA_FIELDS` o `JIRA_EXTRA_FIELDS`.

## Ejecución

Desde la raíz del repositorio:

```powershell
python .\APIJIRA\script_jira.py
```

## Salida

- JSON completo: `<JIRA_FILE_PREFIX>_YYYYMMDD.json`
- CSV completo (si `JIRA_EXPORT_CSV=true`): `<JIRA_FILE_PREFIX>_YYYYMMDD.csv`
- Ubicación: carpeta definida en `JIRA_OUTPUT_DIR` (por defecto `.\exports`).

## Ajustes del alcance de datos

- Proyectos consultados: se definen en `PROJECT_BLOCKS` dentro del script.
- Ventana temporal (JQL): por defecto `created >= "2024/04/01 00:00" AND created <= "2024/12/31 23:59"`. Ajustar en `JQL_BASE` si se requiere.

## Scripts disponibles

- `script_jira.py`: Extractor principal con configuración avanzada
- `test_APIKEY.py`: Prueba rápida de credenciales
- `diagnostico_jira.py`: Diagnóstico completo de proyectos
- `analisis_tipos_globales.py`: Análisis de tipos de issue
- `diagnostico_simple.py`: Prueba simple de conectividad
- `test_endpoint.py`: Prueba de diferentes endpoints

## Solución de problemas

- "Falta JIRA_API_TOKEN": Define la variable de entorno o crea el archivo `.env`.
- 401 Unauthorized: verifica email, token y permisos en Jira.
- 410 Gone: revisa el endpoint y/o la consulta JQL (los scripts usan REST API v3: `/rest/api/3/search`).

## Seguridad

⚠️ **Importante**: Nunca commitees el archivo `.env` con credenciales reales. El archivo está en `.gitignore` para prevenir esto.
