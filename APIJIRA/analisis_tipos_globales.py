import requests
from requests.auth import HTTPBasicAuth
import json
from collections import Counter
import time
import os

# Configuración
JIRA_DOMAIN = "bancodebogota.atlassian.net"
EMAIL = "dbusto3@bancodebogota.com.co"
API_TOKEN = os.getenv("JIRA_API_TOKEN", "").strip()

# Lista completa de proyectos
ALL_PROJECTS = [
    "POT", "ADP", "BSB", "FN", "CFU", "RLV", "MANG", "AE", "CEC", "CCS", "CMG", "CAP", "CCL", "CCO", "CCU", 
    "CGA", "CGF", "CGT", "COP", "CRE", "DEX", "CAHD", "DAT", "DSB", "DTA", "DTCB", "DTOB", "DESN", "EFI", 
    "EAP", "EAN", "EBB", "EDI", "FNIM", "COV", "GDA", "GOGA", "HO", "HOGA", "IMP", "IOD", "DDD", "ADPT", 
    "KSCB", "LSG", "LD", "LDD", "LDF", "MPCC", "MNI", "SOP", "OTY", "CMO", "PG", "RSW", "PML", "CMPL", 
    "MNT", "RS", "TITE", "RO", "TKM", "PJL", "RC", "YS", "RPO", "RIS", "CBU", "TSPN", "CTT", "SFUV", 
    "SPI", "STDD", "STDC", "SST", "SCY", "SCP", "SKD", "PCD", "SIN", "SAT", "SSE", "SCD", "PPN", "SSOR", 
    "TDP", "NJ", "TRX", "TCP", "TTO", "TAC", "TIN", "UVC", "UVI", "UV", "MDV"
]

# Validar que existe el token
if not API_TOKEN:
    print("ERROR: Falta JIRA_API_TOKEN. Define la variable de entorno antes de ejecutar.")
    exit(1)

AUTH = HTTPBasicAuth(EMAIL, API_TOKEN)
URL = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"

def get_all_issue_types_globally():
    """Obtiene todos los tipos de issue de todos los proyectos sin filtrar por equipo."""
    print("🔍 ANÁLISIS GLOBAL DE TIPOS DE ISSUE")
    print("=" * 80)
    print(f"📊 Analizando {len(ALL_PROJECTS)} proyectos...")
    
    # Dividir proyectos en bloques más pequeños para evitar URLs muy largas
    project_blocks = [ALL_PROJECTS[i:i + 20] for i in range(0, len(ALL_PROJECTS), 20)]
    
    all_issue_types = []
    
    for block_num, project_block in enumerate(project_blocks, 1):
        projects_jql = ", ".join(project_block)
        
        print(f"\n🚀 Bloque {block_num}/{len(project_blocks)} - Proyectos: {', '.join(project_block)}")
        print(f"📋 JQL: project IN ({projects_jql})")
        
        start_at = 0
        max_results = 50  # Reducido para mejor rendimiento
        page = 1
        
        try:
            while True:
                print(f"  📄 Página {page} - Desde registro {start_at}...")
                
                response = requests.get(
                    URL,
                    auth=AUTH,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    },
                    params={
                        "jql": f"project IN ({projects_jql}) ORDER BY created DESC",
                        "fields": "issuetype,project,key",
                        "startAt": start_at,
                        "maxResults": max_results,
                        "expand": ""  # No expandir campos adicionales
                    },
                    timeout=30
                )
                
                print(f"  � tStatus: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    issues = data.get('issues', [])
                    total = data.get('total', 0)
                    
                    print(f"  ✅ Página {page}: {len(issues)} issues obtenidos (Total: {total})")
                    
                    # Extraer tipos de issue
                    for issue in issues:
                        fields = issue.get('fields', {})
                        issue_type = fields.get('issuetype', {})
                        project_info = fields.get('project', {})
                        
                        if issue_type and project_info:
                            type_name = issue_type.get('name', 'Unknown')
                            project_key = project_info.get('key', 'Unknown')
                            
                            all_issue_types.append({
                                'type': type_name,
                                'project': project_key,
                                'type_id': issue_type.get('id', 'Unknown'),
                                'issue_key': issue.get('key', 'Unknown')
                            })
                    
                    # Verificar si hay más páginas
                    if len(issues) < max_results:
                        print(f"  🏁 Bloque {block_num} completado")
                        break
                    
                    start_at += max_results
                    page += 1
                    
                elif response.status_code == 400:
                    print(f"  ❌ JQL inválido para bloque {block_num}")
                    print(f"  📄 Error: {response.text}")
                    break
                    
                elif response.status_code == 401:
                    print(f"  ❌ Error de autenticación")
                    return all_issue_types
                    
                else:
                    print(f"  ❌ Error {response.status_code}: {response.text}")
                    break
                
                # Pausa entre requests
                time.sleep(0.5)
                
        except Exception as e:
            print(f"  ❌ Error en bloque {block_num}: {e}")
            continue
        
        # Pausa entre bloques
        if block_num < len(project_blocks):
            print(f"  ⏳ Pausa entre bloques...")
            time.sleep(2)
    
    print(f"\n📊 Total de issues recopilados: {len(all_issue_types)}")
    return all_issue_types

def analyze_issue_types(issue_types_data):
    """Analiza los tipos de issue obtenidos."""
    print(f"\n📊 ANÁLISIS DE TIPOS DE ISSUE")
    print("=" * 60)
    
    if not issue_types_data:
        print("❌ No se encontraron datos para analizar")
        return
    
    print(f"📈 Total de issues analizados: {len(issue_types_data)}")
    
    # Contar tipos únicos
    type_names = [item['type'] for item in issue_types_data]
    type_counter = Counter(type_names)
    unique_types = len(type_counter)
    
    print(f"🎯 Tipos únicos encontrados: {unique_types}")
    
    # Mostrar los tipos más comunes
    print(f"\n📋 TIPOS MÁS COMUNES (Top 20):")
    for i, (issue_type, count) in enumerate(type_counter.most_common(20), 1):
        percentage = (count / len(issue_types_data)) * 100
        print(f"   {i:2d}. '{issue_type}': {count:,} issues ({percentage:.1f}%)")
    
    # Análisis por proyecto
    projects_with_types = {}
    for item in issue_types_data:
        project = item['project']
        issue_type = item['type']
        
        if project not in projects_with_types:
            projects_with_types[project] = set()
        projects_with_types[project].add(issue_type)
    
    print(f"\n🏢 DISTRIBUCIÓN POR PROYECTO:")
    print(f"   Proyectos con datos: {len(projects_with_types)}")
    
    # Tipos que aparecen en múltiples proyectos
    type_project_count = {}
    for project, types in projects_with_types.items():
        for issue_type in types:
            if issue_type not in type_project_count:
                type_project_count[issue_type] = 0
            type_project_count[issue_type] += 1
    
    # Tipos más distribuidos
    print(f"\n🌐 TIPOS MÁS DISTRIBUIDOS (aparecen en más proyectos):")
    sorted_by_distribution = sorted(type_project_count.items(), key=lambda x: x[1], reverse=True)
    
    for i, (issue_type, project_count) in enumerate(sorted_by_distribution[:15], 1):
        total_occurrences = type_counter[issue_type]
        percentage_projects = (project_count / len(projects_with_types)) * 100
        print(f"   {i:2d}. '{issue_type}':")
        print(f"       📦 En {project_count}/{len(projects_with_types)} proyectos ({percentage_projects:.1f}%)")
        print(f"       📊 Total issues: {total_occurrences:,}")
    
    # Tipos universales o casi universales
    high_distribution_types = [
        (issue_type, project_count) for issue_type, project_count in type_project_count.items()
        if project_count >= len(projects_with_types) * 0.5  # Aparece en al menos 50% de proyectos
    ]
    
    if high_distribution_types:
        print(f"\n⭐ TIPOS CON ALTA DISTRIBUCIÓN (50%+ proyectos):")
        for issue_type, project_count in sorted(high_distribution_types, key=lambda x: x[1], reverse=True):
            percentage = (project_count / len(projects_with_types)) * 100
            total_issues = type_counter[issue_type]
            print(f"   - '{issue_type}': {project_count}/{len(projects_with_types)} proyectos ({percentage:.1f}%) - {total_issues:,} issues")
    
    # Guardar reporte
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_issues_analyzed": len(issue_types_data),
        "unique_issue_types": unique_types,
        "projects_analyzed": len(projects_with_types),
        "type_frequency": dict(type_counter.most_common()),
        "type_distribution": type_project_count,
        "high_distribution_types": {t: c for t, c in high_distribution_types}
    }
    
    filename = f"analisis_tipos_globales_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Reporte guardado en: {filename}")
    
    return report

def main():
    print("🎯 ANÁLISIS GLOBAL DE TIPOS DE ISSUE EN JIRA")
    print("=" * 80)
    
    try:
        # Obtener todos los tipos de issue
        issue_types_data = get_all_issue_types_globally()
        
        if issue_types_data:
            # Analizar los datos
            report = analyze_issue_types(issue_types_data)
            
            print(f"\n🎉 Análisis completado exitosamente!")
            print(f"📊 {len(issue_types_data):,} issues analizados")
            print(f"🎯 {report['unique_issue_types']} tipos únicos encontrados")
        else:
            print(f"\n❌ No se pudieron obtener datos para el análisis")
            
    except Exception as e:
        print(f"\n❌ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()