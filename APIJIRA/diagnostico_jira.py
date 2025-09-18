import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime
from collections import Counter
import os

# ------------------------ Configuración ------------------------

JIRA_DOMAIN = "bancodebogota.atlassian.net"
EMAIL = "dbusto3@bancodebogota.com.co"
API_TOKEN = os.getenv("JIRA_API_TOKEN", "").strip()

# Proyectos objetivo
TARGET_PROJECTS = ["ADP", "CAP", "DEX", "CAHD", "CGT", "B2B", "EFI", "IOD", "COP", "PEM", "SCDPPPN", "TRX"]

# URL base de la API de Jira
URL = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"

# Validar que existe el token
if not API_TOKEN:
    print("ERROR: Falta JIRA_API_TOKEN. Define la variable de entorno antes de ejecutar.")
    exit(1)

# Configuración de autenticación
AUTH = HTTPBasicAuth(EMAIL, API_TOKEN)

# ------------------------ Funciones de Diagnóstico ------------------------

def get_project_info(project_key):
    """Obtiene información básica de un proyecto específico."""
    try:
        # Consulta simple para obtener algunos issues del proyecto
        jql = f"project = {project_key} ORDER BY created DESC"
        
        response = requests.get(
            URL,
            auth=AUTH,
            headers={"Accept": "application/json"},
            params={
                "jql": jql,
                "fields": "status,issuetype,created,summary",
                "maxResults": 10
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "exists": True,
                "total_issues": data.get('total', 0),
                "sample_issues": data.get('issues', [])
            }
        else:
            return {
                "exists": False,
                "error": f"Status {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }

def analyze_status_values():
    """Analiza los valores de status disponibles en los proyectos."""
    print("🔍 Analizando valores de STATUS...")
    
    all_statuses = []
    
    for project in TARGET_PROJECTS:
        try:
            jql = f"project = {project}"
            
            response = requests.get(
                URL,
                auth=AUTH,
                headers={"Accept": "application/json"},
                params={
                    "jql": jql,
                    "fields": "status",
                    "maxResults": 100
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])
                
                for issue in issues:
                    status = issue.get('fields', {}).get('status', {})
                    if status:
                        all_statuses.append(status.get('name', 'Unknown'))
                        
                print(f"✅ {project}: {len(issues)} issues analizados")
            else:
                print(f"❌ {project}: Error {response.status_code}")
                
        except Exception as e:
            print(f"❌ {project}: {e}")
    
    return Counter(all_statuses)

def analyze_issue_types():
    """Analiza los tipos de issue disponibles en los proyectos."""
    print("\n🔍 Analizando TIPOS DE ISSUE...")
    
    all_types = []
    
    for project in TARGET_PROJECTS:
        try:
            jql = f"project = {project}"
            
            response = requests.get(
                URL,
                auth=AUTH,
                headers={"Accept": "application/json"},
                params={
                    "jql": jql,
                    "fields": "issuetype",
                    "maxResults": 100
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])
                
                for issue in issues:
                    issue_type = issue.get('fields', {}).get('issuetype', {})
                    if issue_type:
                        all_types.append(issue_type.get('name', 'Unknown'))
                        
                print(f"✅ {project}: {len(issues)} issues analizados")
            else:
                print(f"❌ {project}: Error {response.status_code}")
                
        except Exception as e:
            print(f"❌ {project}: {e}")
    
    return Counter(all_types)

def analyze_date_ranges():
    """Analiza los rangos de fechas de creación en los proyectos."""
    print("\n🔍 Analizando RANGOS DE FECHAS...")
    
    date_info = {}
    
    for project in TARGET_PROJECTS:
        try:
            # Obtener el issue más antiguo
            jql_oldest = f"project = {project} ORDER BY created ASC"
            # Obtener el issue más reciente
            jql_newest = f"project = {project} ORDER BY created DESC"
            
            oldest_response = requests.get(
                URL,
                auth=AUTH,
                headers={"Accept": "application/json"},
                params={
                    "jql": jql_oldest,
                    "fields": "created",
                    "maxResults": 1
                },
                timeout=30
            )
            
            newest_response = requests.get(
                URL,
                auth=AUTH,
                headers={"Accept": "application/json"},
                params={
                    "jql": jql_newest,
                    "fields": "created",
                    "maxResults": 1
                },
                timeout=30
            )
            
            if oldest_response.status_code == 200 and newest_response.status_code == 200:
                oldest_data = oldest_response.json()
                newest_data = newest_response.json()
                
                oldest_issues = oldest_data.get('issues', [])
                newest_issues = newest_data.get('issues', [])
                
                if oldest_issues and newest_issues:
                    oldest_date = oldest_issues[0].get('fields', {}).get('created', 'N/A')
                    newest_date = newest_issues[0].get('fields', {}).get('created', 'N/A')
                    
                    date_info[project] = {
                        "oldest": oldest_date,
                        "newest": newest_date,
                        "total": oldest_data.get('total', 0)
                    }
                    
                    print(f"✅ {project}: {date_info[project]['total']} issues total")
                else:
                    date_info[project] = {"error": "Sin issues"}
                    print(f"ℹ️  {project}: Sin issues")
            else:
                date_info[project] = {"error": f"Error en consulta"}
                print(f"❌ {project}: Error en consulta")
                
        except Exception as e:
            date_info[project] = {"error": str(e)}
            print(f"❌ {project}: {e}")
    
    return date_info

def test_specific_criteria():
    """Prueba consultas con criterios específicos para encontrar issues."""
    print("\n🔍 Probando CRITERIOS ESPECÍFICOS...")
    
    test_queries = [
        {
            "name": "Solo proyectos objetivo",
            "jql": f"project IN ({', '.join(TARGET_PROJECTS)}) ORDER BY created DESC"
        },
        {
            "name": "Proyectos + Stories",
            "jql": f"project IN ({', '.join(TARGET_PROJECTS)}) AND type = Story ORDER BY created DESC"
        },
        {
            "name": "Proyectos + rango 2024",
            "jql": f"project IN ({', '.join(TARGET_PROJECTS)}) AND created >= '2024-01-01' ORDER BY created DESC"
        },
        {
            "name": "Solo ADP con cualquier criterio",
            "jql": "project = ADP ORDER BY created DESC"
        }
    ]
    
    results = {}
    
    for test in test_queries:
        try:
            response = requests.get(
                URL,
                auth=AUTH,
                headers={"Accept": "application/json"},
                params={
                    "jql": test["jql"],
                    "fields": "key,summary,status,issuetype,created",
                    "maxResults": 5
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                issues = data.get('issues', [])
                
                results[test["name"]] = {
                    "total": total,
                    "sample_issues": issues[:3]  # Solo los primeros 3
                }
                
                print(f"✅ {test['name']}: {total} issues encontrados")
            else:
                results[test["name"]] = {
                    "error": f"Status {response.status_code}: {response.text}"
                }
                print(f"❌ {test['name']}: Error {response.status_code}")
                
        except Exception as e:
            results[test["name"]] = {"error": str(e)}
            print(f"❌ {test['name']}: {e}")
    
    return results

def generate_diagnostic_report():
    """Genera un reporte completo de diagnóstico."""
    print("=" * 80)
    print("🔬 DIAGNÓSTICO COMPLETO DE JIRA")
    print("=" * 80)
    
    # 1. Verificar proyectos
    print("\n1️⃣ VERIFICANDO PROYECTOS...")
    project_status = {}
    for project in TARGET_PROJECTS:
        info = get_project_info(project)
        project_status[project] = info
        if info.get("exists"):
            print(f"✅ {project}: {info.get('total_issues', 0)} issues")
        else:
            print(f"❌ {project}: {info.get('error', 'Error desconocido')}")
    
    # 2. Analizar status
    print(f"\n2️⃣ ANÁLISIS DE STATUS...")
    status_counts = analyze_status_values()
    
    # 3. Analizar tipos de issue
    print(f"\n3️⃣ ANÁLISIS DE TIPOS DE ISSUE...")
    type_counts = analyze_issue_types()
    
    # 4. Analizar fechas
    print(f"\n4️⃣ ANÁLISIS DE FECHAS...")
    date_ranges = analyze_date_ranges()
    
    # 5. Probar criterios específicos
    print(f"\n5️⃣ PRUEBAS DE CRITERIOS...")
    test_results = test_specific_criteria()
    
    # Generar reporte
    report = {
        "timestamp": datetime.now().isoformat(),
        "projects": project_status,
        "status_values": dict(status_counts.most_common()),
        "issue_types": dict(type_counts.most_common()),
        "date_ranges": date_ranges,
        "test_results": test_results
    }
    
    # Guardar reporte
    filename = f"diagnostico_jira_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    
    # Mostrar resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DEL DIAGNÓSTICO")
    print("=" * 80)
    
    print(f"\n🏢 PROYECTOS DISPONIBLES:")
    available_projects = [p for p, info in project_status.items() if info.get("exists")]
    print(f"   Disponibles: {len(available_projects)}/{len(TARGET_PROJECTS)}")
    print(f"   Lista: {', '.join(available_projects)}")
    
    if status_counts:
        print(f"\n📋 STATUS MÁS COMUNES:")
        for status, count in status_counts.most_common(10):
            print(f"   - {status}: {count}")
    
    if type_counts:
        print(f"\n🎯 TIPOS DE ISSUE MÁS COMUNES:")
        for issue_type, count in type_counts.most_common(10):
            print(f"   - {issue_type}: {count}")
    
    print(f"\n💾 Reporte completo guardado en: {filename}")
    
    return report

# ------------------------ Ejecución ------------------------

if __name__ == "__main__":
    print("🚀 Iniciando diagnóstico de JIRA...")
    try:
        report = generate_diagnostic_report()
        print("\n🎉 Diagnóstico completado exitosamente!")
    except Exception as e:
        print(f"\n❌ Error durante el diagnóstico: {e}")
        import traceback
        traceback.print_exc()