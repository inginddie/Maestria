import requests
from requests.auth import HTTPBasicAuth
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

print("🔍 Probando diferentes endpoints de JIRA")
print("=" * 50)

# Probar diferentes endpoints
endpoints = [
    "/rest/api/3/search",
    "/rest/api/3/search/jql", 
    "/rest/api/2/search"
]

for endpoint in endpoints:
    print(f"\n🚀 Probando: {endpoint}")
    url = f"https://{JIRA_DOMAIN}{endpoint}"
    
    try:
        response = requests.get(
            url,
            auth=AUTH,
            headers={"Accept": "application/json"},
            params={
                "jql": "project = ADP ORDER BY created DESC",
                "fields": "key,issuetype",
                "maxResults": 1
            },
            timeout=30
        )
        
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            issues = data.get('issues', [])
            print(f"✅ Funciona! Total: {total}, Issues obtenidos: {len(issues)}")
            
            if issues:
                issue = issues[0]
                print(f"   Ejemplo: {issue.get('key', 'N/A')}")
                issue_type = issue.get('fields', {}).get('issuetype', {})
                print(f"   Tipo: {issue_type.get('name', 'N/A')}")
        else:
            print(f"❌ Error: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Excepción: {e}")

print(f"\n" + "=" * 50)