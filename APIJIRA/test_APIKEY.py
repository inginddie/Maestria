import requests
from requests.auth import HTTPBasicAuth
import json
import os

# ------------------------ Configuración ------------------------

JIRA_DOMAIN = "bancodebogota.atlassian.net"
EMAIL = "dbusto3@bancodebogota.com.co"
API_TOKEN = os.getenv("JIRA_API_TOKEN", "").strip()

# ------------------------ Funciones de Prueba ------------------------

def _ensure_token():
    if not API_TOKEN:
        print("ERROR: Falta JIRA_API_TOKEN. Define la variable de entorno antes de ejecutar.")
        return False
    return True

def test_connection():
    """Prueba la conexión básica a Jira"""
    if not _ensure_token():
        return False
    url = f"https://{JIRA_DOMAIN}/rest/api/3/myself"
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(EMAIL, API_TOKEN),
            headers={"Accept": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            user_info = response.json()
            print("OK: Conexión exitosa!")
            print(f"Usuario: {user_info.get('displayName', 'N/A')}")
            print(f"Email: {user_info.get('emailAddress', 'N/A')}")
            return True
        else:
            print("ERROR: Error en la conexión")
            print(f"Respuesta: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"ERROR: Error de conexión: {e}")
        return False

def test_search_endpoint():
    """Prueba el endpoint de búsqueda con una consulta simple"""
    if not _ensure_token():
        return False
    url = f"https://{JIRA_DOMAIN}/rest/api/3/search"
    
    # Consulta simple para probar
    simple_jql = "project = ADP ORDER BY created DESC"
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(EMAIL, API_TOKEN),
            headers={"Accept": "application/json"},
            params={
                "jql": simple_jql,
                "maxResults": 1
            }
        )
        
        print(f"\nPrueba de búsqueda - Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("OK: Endpoint de búsqueda funcional!")
            print(f"Total de issues encontrados: {data.get('total', 0)}")
            return True
        else:
            print("ERROR: Error en el endpoint de búsqueda")
            print(f"Respuesta: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"ERROR: Error en búsqueda: {e}")
        return False

def test_projects():
    """Prueba obtener la lista de proyectos disponibles"""
    if not _ensure_token():
        return False
    url = f"https://{JIRA_DOMAIN}/rest/api/3/project"
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(EMAIL, API_TOKEN),
            headers={"Accept": "application/json"}
        )
        
        print(f"\nPrueba de proyectos - Status Code: {response.status_code}")
        
        if response.status_code == 200:
            projects = response.json()
            print("OK: Acceso a proyectos exitoso!")
            print(f"Número de proyectos disponibles: {len(projects)}")
            
            # Mostrar algunos proyectos
            target_projects = ["ADP", "CAP", "DEX", "CAHD", "CGT", "B2B", "EFI", "IOD", "COP", "PEM", "SCDPPPN", "TRX"]
            available_projects = [p['key'] for p in projects]
            
            print("\nProyectos objetivo encontrados:")
            for project in target_projects:
                if project in available_projects:
                    print(f"  OK: {project}")
                else:
                    print(f"  ERROR: {project} (no disponible)")
            
            return True
        else:
            print("ERROR: Error al obtener proyectos")
            print(f"Respuesta: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"ERROR: Error al obtener proyectos: {e}")
        return False

# ------------------------ Ejecución de Pruebas ------------------------

if __name__ == "__main__":
    print("=== PRUEBA DE CREDENCIALES JIRA ===\n")
    
    # Prueba 1: Conexión básica
    print("1. Probando conexión básica...")
    connection_ok = test_connection()
    
    if connection_ok:
        # Prueba 2: Endpoint de búsqueda
        print("\n2. Probando endpoint de búsqueda...")
        search_ok = test_search_endpoint()
        
        # Prueba 3: Acceso a proyectos
        print("\n3. Probando acceso a proyectos...")
        projects_ok = test_projects()
        
        # Resumen
        print("\n=== RESUMEN ===")
        print(f"Conexión básica: {'OK' if connection_ok else 'ERROR'}")
        print(f"Endpoint búsqueda: {'OK' if search_ok else 'ERROR'}")
        print(f"Acceso proyectos: {'OK' if projects_ok else 'ERROR'}")
        
        if connection_ok and search_ok and projects_ok:
            print("\nSUCCESS: Todas las pruebas pasaron! Las credenciales están funcionando correctamente.")
        else:
            print("\nWARNING: Algunas pruebas fallaron. Revisa las credenciales o permisos.")
    else:
        print("\nERROR: La conexión básica falló. Verifica las credenciales.")