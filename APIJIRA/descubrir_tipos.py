import os
import sys
import json
from collections import Counter

# Agregar directorio padre al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar para NO filtrar por tipo de issue (obtener todos)
os.environ.pop("JIRA_ISSUETYPES", None)  # Remover cualquier filtro
os.environ["JIRA_PROJECTS"] = "RSW"
os.environ["JIRA_FILE_PREFIX"] = "issues_RSW_descubrir_tipos"

# Cargar funciones del script principal
from script_jira import fetch_issues, process_issues

if __name__ == "__main__":
    print("=== DESCUBRIENDO TIPOS REALES DE ISSUES EN RSW ===")
    print("Sin filtros de tipo de issue...")
    print()

    # Obtener una muestra pequeña primero
    issues = fetch_issues()

    if issues:
        print(f"Muestra obtenida: {len(issues)} issues")

        # Procesar para obtener información
        processed = process_issues(issues[:100])  # Solo los primeros 100

        # Contar tipos
        type_counts = Counter(item.get('issue_type', 'N/A') for item in processed)

        print(f"\n=== TIPOS DE ISSUES REALMENTE EXISTENTES EN RSW ===")
        for tipo, count in type_counts.most_common():
            print(f"- '{tipo}': {count} issues")

        print(f"\nTOTAL de tipos únicos: {len(type_counts)}")

        # Guardar un archivo JSON con la muestra para análisis
        with open('./exports/muestra_tipos_RSW.json', 'w', encoding='utf-8') as f:
            json.dump([{
                'key': item['key'],
                'issue_type': item['issue_type'],
                'summary': item['summary'][:50] + '...' if len(item.get('summary', '')) > 50 else item.get('summary', '')
            } for item in processed], f, indent=2, ensure_ascii=False)

        print(f"\nArchivo guardado: ./exports/muestra_tipos_RSW.json")

    else:
        print("❌ No se pudieron obtener issues para analizar")