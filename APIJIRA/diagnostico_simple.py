import requests
from requests.auth import HTTPBasicAuth
import json
import os

# Configuración
JIRA_DOMAIN = "bancodebogota.atlassian.net"
EMAIL = "dbusto3@bancodebogota.com.co"
API_TOKEN = os.getenv("JIRA_API_TOKEN", "").strip()

# Validar que existe el token
if not API_TOKEN:
    print("ERROR: Falta JIRA_API_TOKEN. Define la variable de entorno antes de ejecutar.")
    exit(1)

AUTH = HTTPBasicAuth(EMAIL, API_TOKEN)
URL = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"

print("🔍 Diagnóstico Simple de JIRA")
print("=" * 50)

# Prueba 1: Proyecto ADP básico
print("\n1. Probando proyecto ADP...")
try:
    response = requests.get(
        URL,
        auth=AUTH,
        headers={"Accept": "application/json"},
        params={
            "jql": "project = ADP ORDER BY created DESC",
            "fields": "key,summary,status,issuetype,created",
            "maxResults": 5
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        total = data.get('total', 0)
        issues = data.get('issues', [])
        
        print(f"✅ Total issues en ADP: {total}")
        
        if issues:
            print("\nPrimeros 3 issues:")
            for i, issue in enumerate(issues[:3], 1):
                fields = issue.get('fields', {})
                status = fields.get('status', {}).get('name', 'N/A')
                issue_type = fields.get('issuetype', {}).get('name', 'N/A')
                created = fields.get('created', 'N/A')
                
                print(f"  {i}. {issue.get('key', 'N/A')}")
                print(f"     Status: {status}")
                print(f"     Tipo: {issue_type}")
                print(f"     Creado: {created[:10] if created != 'N/A' else 'N/A'}")
        
        # Analizar status únicos
        if issues:
            statuses = set()
            types = set()
            for issue in issues:
                fields = issue.get('fields', {})
                status = fields.get('status', {}).get('name')
                issue_type = fields.get('issuetype', {}).get('name')
                if status:
                    statuses.add(status)
                if issue_type:
                    types.add(issue_type)
            
            print(f"\nStatus encontrados: {', '.join(statuses)}")
            print(f"Tipos encontrados: {', '.join(types)}")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Prueba 2: Buscar issues con Story
print("\n2. Probando tipo 'Story' en ADP...")
try:
    response = requests.get(
        URL,
        auth=AUTH,
        headers={"Accept": "application/json"},
        params={
            "jql": "project = ADP AND type = Story ORDER BY created DESC",
            "maxResults": 1
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        total = data.get('total', 0)
        print(f"✅ Stories en ADP: {total}")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Prueba 3: Buscar con rango de fechas 2024
print("\n3. Probando rango de fechas 2024 en ADP...")
try:
    response = requests.get(
        URL,
        auth=AUTH,
        headers={"Accept": "application/json"},
        params={
            "jql": "project = ADP AND created >= '2024-01-01' ORDER BY created DESC",
            "maxResults": 1
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        total = data.get('total', 0)
        print(f"✅ Issues 2024 en ADP: {total}")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 50)
print("Diagnóstico completado")