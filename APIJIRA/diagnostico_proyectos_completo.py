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

def test_project_batch(projects_batch, batch_num):
    """Prueba un lote de proyectos para obtener información básica."""
    print(f"\n📦 Lote {batch_num} - Proyectos: {', '.join(projects_batch)}")
    
    results = {}
    all_statuses = []
    all_types = []
    
    for project in projects_batch:
        try:
            # Consulta básica para obtener información del proyecto
            response = requests.get(
                URL,
                auth=AUTH,
                headers={"Accept": "application/json"},
                params={
                    "jql": f"project = {project} ORDER BY created DESC",
                    "fields": "key,status,issuetype,created",
                    "maxResults": 10
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                issues = data.get('issues', [])
                
                # Recopilar status y tipos
                project_statuses = set()
                project_types = set()
                
                for issue in issues:
                    fields = issue.get('fields', {})
                    status = fields.get('status', {}).get('name')
                    issue_type = fields.get('issuetype', {}).get('name')
                    
                    if status:
                        project_statuses.add(status)
                        all_statuses.append(status)
                    if issue_type:
                        project_types.add(issue_type)
                        all_types.append(issue_type)
                
                results[project] = {
                    "exists": True,
                    "total_issues": total,
                    "statuses": list(project_statuses),
                    "types": list(project_types),
                    "sample_count": len(issues)
                }
                
                print(f"  ✅ {project}: {total} issues, {len(project_statuses)} status, {len(project_types)} tipos")
                
            elif response.status_code == 400:
                results[project] = {"exists": False, "error": "Proyecto no existe"}
                print(f"  ❌ {project}: No existe")
            else:
                results[project] = {"exists": False, "error": f"Status {response.status_code}"}
                print(f"  ⚠️  {project}: Error {response.status_code}")
                
        except Exception as e:
            results[project] = {"exists": False, "error": str(e)}
            print(f"  ❌ {project}: {e}")
        
        # Pequeña pausa para no sobrecargar la API
        time.sleep(0.5)
    
    return results, all_statuses, all_types

def main():
    print("🔍 DIAGNÓSTICO COMPLETO DE PROYECTOS JIRA")
    print("=" * 80)
    print(f"📊 Total de proyectos a analizar: {len(ALL_PROJECTS)}")
    
    # Dividir proyectos en lotes de 10 para mejor manejo
    batch_size = 10
    batches = [ALL_PROJECTS[i:i + batch_size] for i in range(0, len(ALL_PROJECTS), batch_size)]
    
    all_results = {}
    global_statuses = []
    global_types = []
    
    for i, batch in enumerate(batches, 1):
        print(f"\n🔄 Procesando lote {i}/{len(batches)}...")
        
        try:
            batch_results, batch_statuses, batch_types = test_project_batch(batch, i)
            
            all_results.update(batch_results)
            global_statuses.extend(batch_statuses)
            global_types.extend(batch_types)
            
            # Pausa entre lotes
            if i < len(batches):
                print(f"⏳ Pausa entre lotes...")
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(f"\n⚠️ Proceso interrumpido por el usuario en lote {i}")
            break
        except Exception as e:
            print(f"\n❌ Error en lote {i}: {e}")
            continue
    
    # Análisis de resultados
    print("\n" + "=" * 80)
    print("📊 ANÁLISIS DE RESULTADOS")
    print("=" * 80)
    
    # Proyectos existentes vs no existentes
    existing_projects = [p for p, info in all_results.items() if info.get("exists")]
    non_existing_projects = [p for p, info in all_results.items() if not info.get("exists")]
    
    print(f"\n🏢 PROYECTOS:")
    print(f"   ✅ Existentes: {len(existing_projects)}/{len(ALL_PROJECTS)}")
    print(f"   ❌ No existentes: {len(non_existing_projects)}")
    
    if existing_projects:
        print(f"\n📋 PROYECTOS EXISTENTES:")
        for project in sorted(existing_projects):
            info = all_results[project]
            print(f"   {project}: {info.get('total_issues', 0)} issues")
    
    # Análisis de status
    if global_statuses:
        status_counts = Counter(global_statuses)
        print(f"\n📊 STATUS MÁS COMUNES (Top 15):")
        for status, count in status_counts.most_common(15):
            print(f"   - {status}: {count}")
    
    # Análisis de tipos
    if global_types:
        type_counts = Counter(global_types)
        print(f"\n🎯 TIPOS DE ISSUE MÁS COMUNES (Top 15):")
        for issue_type, count in type_counts.most_common(15):
            print(f"   - {issue_type}: {count}")
    
    # Guardar reporte completo
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_projects_analyzed": len(ALL_PROJECTS),
        "existing_projects": len(existing_projects),
        "project_details": all_results,
        "status_summary": dict(Counter(global_statuses).most_common()),
        "type_summary": dict(Counter(global_types).most_common())
    }
    
    filename = f"diagnostico_completo_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Reporte completo guardado en: {filename}")
    
    # Análisis de tipos y status comunes entre proyectos
    print(f"\n� ANCÁLISIS DE ELEMENTOS COMUNES ENTRE PROYECTOS")
    print("=" * 60)
    
    # Obtener proyectos con datos
    projects_with_data = {p: info for p, info in all_results.items() 
                         if info.get("exists") and (info.get("statuses") or info.get("types"))}
    
    if projects_with_data:
        print(f"📊 Proyectos con datos analizables: {len(projects_with_data)}")
        
        # Análisis de status comunes
        status_by_project = {}
        for project, info in projects_with_data.items():
            if info.get("statuses"):
                status_by_project[project] = set(info["statuses"])
        
        if status_by_project:
            print(f"\n📋 ANÁLISIS DE STATUS COMUNES:")
            
            # Status que aparecen en múltiples proyectos
            all_unique_statuses = set()
            for statuses in status_by_project.values():
                all_unique_statuses.update(statuses)
            
            status_frequency = {}
            for status in all_unique_statuses:
                count = sum(1 for statuses in status_by_project.values() if status in statuses)
                status_frequency[status] = count
            
            # Status más comunes (aparecen en más proyectos)
            common_statuses = sorted(status_frequency.items(), key=lambda x: x[1], reverse=True)
            
            print(f"   Status que aparecen en más proyectos:")
            for status, project_count in common_statuses[:10]:
                percentage = (project_count / len(status_by_project)) * 100
                print(f"   - '{status}': {project_count}/{len(status_by_project)} proyectos ({percentage:.1f}%)")
            
            # Status universales (aparecen en todos los proyectos con datos)
            universal_statuses = [status for status, count in status_frequency.items() 
                                if count == len(status_by_project)]
            
            if universal_statuses:
                print(f"\n   ✅ Status UNIVERSALES (en todos los proyectos):")
                for status in universal_statuses:
                    print(f"      - '{status}'")
            else:
                print(f"\n   ⚠️ No hay status universales en todos los proyectos")
        
        # Análisis de tipos comunes
        types_by_project = {}
        for project, info in projects_with_data.items():
            if info.get("types"):
                types_by_project[project] = set(info["types"])
        
        if types_by_project:
            print(f"\n🎯 ANÁLISIS DE TIPOS DE ISSUE COMUNES:")
            
            # Tipos que aparecen en múltiples proyectos
            all_unique_types = set()
            for types in types_by_project.values():
                all_unique_types.update(types)
            
            type_frequency = {}
            for issue_type in all_unique_types:
                count = sum(1 for types in types_by_project.values() if issue_type in types)
                type_frequency[issue_type] = count
            
            # Tipos más comunes (aparecen en más proyectos)
            common_types = sorted(type_frequency.items(), key=lambda x: x[1], reverse=True)
            
            print(f"   Tipos que aparecen en más proyectos:")
            for issue_type, project_count in common_types[:15]:
                percentage = (project_count / len(types_by_project)) * 100
                print(f"   - '{issue_type}': {project_count}/{len(types_by_project)} proyectos ({percentage:.1f}%)")
            
            # Tipos universales
            universal_types = [issue_type for issue_type, count in type_frequency.items() 
                             if count == len(types_by_project)]
            
            if universal_types:
                print(f"\n   ✅ Tipos UNIVERSALES (en todos los proyectos):")
                for issue_type in universal_types:
                    print(f"      - '{issue_type}'")
            else:
                print(f"\n   ⚠️ No hay tipos universales en todos los proyectos")
            
            # Tipos más prometedores para consultas masivas
            promising_types = [t for t, count in common_types[:5] if count >= len(types_by_project) * 0.3]
            if promising_types:
                print(f"\n   🎯 Tipos MÁS PROMETEDORES (aparecen en 30%+ proyectos):")
                for issue_type in promising_types:
                    count = type_frequency[issue_type]
                    percentage = (count / len(types_by_project)) * 100
                    print(f"      - '{issue_type}' ({percentage:.1f}% proyectos)")
        
        # Combinaciones recomendadas
        print(f"\n💡 COMBINACIONES RECOMENDADAS PARA CONSULTAS:")
        
        if status_frequency and type_frequency:
            # Status más frecuentes
            top_statuses = [s for s, c in sorted(status_frequency.items(), key=lambda x: x[1], reverse=True)[:3]]
            # Tipos más frecuentes
            top_types = [t for t, c in sorted(type_frequency.items(), key=lambda x: x[1], reverse=True)[:3]]
            
            print(f"   📋 Status recomendados: {top_statuses}")
            print(f"   🎯 Tipos recomendados: {top_types}")
            
            # Generar JQL sugerido
            status_jql = " OR ".join([f'status = "{s}"' for s in top_statuses])
            types_jql = " OR ".join([f'type = "{t}"' for t in top_types])
            
            print(f"\n   📝 JQL SUGERIDO:")
            print(f"      ({status_jql}) AND ({types_jql})")
    
    # Recomendaciones finales
    print(f"\n💡 RECOMENDACIONES PARA EL SCRIPT PRINCIPAL:")
    if global_statuses:
        top_statuses = [status for status, _ in Counter(global_statuses).most_common(5)]
        print(f"   📋 Status recomendados: {', '.join(top_statuses)}")
    
    if global_types:
        top_types = [t for t, _ in Counter(global_types).most_common(5)]
        print(f"   🎯 Tipos recomendados: {', '.join(top_types)}")
    
    print(f"   🏢 Proyectos con datos: {', '.join(sorted(existing_projects[:10]))}{'...' if len(existing_projects) > 10 else ''}")

if __name__ == "__main__":
    try:
        main()
        print("\n🎉 Diagnóstico completado exitosamente!")
    except Exception as e:
        print(f"\n❌ Error durante el diagnóstico: {e}")
        import traceback
        traceback.print_exc()