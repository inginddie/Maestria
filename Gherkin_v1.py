import csv
import re
import statistics
import os
from collections import defaultdict
import openai
from typing import Tuple, Dict, List, Any, Optional

# Configuración de la clave API de OpenAI (usa variables de entorno para mayor seguridad)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or not api_key.startswith("sk-"):
    raise ValueError(
        "Error: La clave API de OpenAI no está configurada correctamente. "
        "Verifica tu variable de entorno OPENAI_API_KEY."
    )
print(f"API Key usada: {api_key[:5]}... (oculta por seguridad)")

client = None
try:
    # Verificar si la versión de openai tiene la clase OpenAI, si no, usar Client
    client = openai.OpenAI(api_key=api_key) if hasattr(openai, 'OpenAI') else openai.Client(api_key=api_key)
    client.models.list()
    print("✅ Conexión exitosa con OpenAI API")
except openai.AuthenticationError:
    raise ValueError(
        "❌ Error: La clave API de OpenAI es incorrecta o ha sido revocada. "
        "Genera una nueva en https://platform.openai.com/account/api-keys"
    )
except Exception as e:
    print(f"⚠️ Advertencia: No se pudo validar la API Key. Error: {e}")

# Palabras clave para INVEST
INVEST_KEYWORDS = ["independiente", "negociable", "valiosa", "estimable", "pequeña", "testeable"]

# Palabras clave para SMART (para referencia, aunque ahora usaremos prompt)
SMART_KEYWORDS = ["específic", "medible", "alcanzabl", "relevant", "tiempo"]

# Caché para resultados de análisis de OpenAI
cache_analisis = {}

###################################################################
# FUNCIONES DE ANÁLISIS - RETORNAN (puntaje, explicación) EN VEZ DE BOOL
###################################################################

def normalizar_tipo_incidencia(tipo_original: str) -> str:
    """
    Normaliza el tipo de incidencia (historia, historia no funcional, criterios de aceptación, etc.)
    """
    if not tipo_original:
        return ""

    tipo_limpio = re.sub(r"\s+", " ", tipo_original.strip().lower())

    tipo_mapped = {
        "historia": "historia",
        "historia de usuario": "historia",
        "hu": "historia",
        "historia no funcional": "historia no funcional",
        "historia no funcional ( habilitadora)": "historia no funcional",
        "historia no funcional (habilitadora)": "historia no funcional",
        "historia no funcional (habilitadora )": "historia no funcional",
        "historia no funcional ( habilitadora )": "historia no funcional",
        "hnf": "historia no funcional",
        "criterios de aceptación": "criterios de aceptación",
        "criterio de aceptación": "criterios de aceptación",
        "ca": "criterios de aceptación",
    }

    if tipo_limpio in tipo_mapped:
        return tipo_mapped[tipo_limpio]
    if re.search(r"historia\s+no\s+funcional", tipo_limpio):
        return "historia no funcional"
    if re.search(r"historia(\s+de\s+usuario)?$", tipo_limpio):
        return "historia"
    if re.search(r"criterios?\s+de\s+aceptaci[oó]n", tipo_limpio):
        return "criterios de aceptación"
    return ""

def analizar_gherkin_con_openai(texto: str) -> Tuple[float, str]:
    """
    Verifica si un texto (la descripción o resumen) sigue la estructura Gherkin
    en inglés (Given/When/Then) o en español (Dado/Cuando/Entonces).
    Devuelve (puntaje, explicación).
      - Si cumple => (20, explicación)
      - Si no cumple => (0, explicación)
    """
    if not texto or len(texto.strip()) < 5:
        return (0.0, "Texto demasiado corto para evaluar Gherkin.")

    # Revisar caché
    if texto in cache_analisis:
        return cache_analisis[texto]

    prompt = (
        "Evalúa si el siguiente texto está en formato Gherkin (Given/When/Then) o (Dado/Cuando/Entonces). "
        "Responde 'sí' o 'no', y explica brevemente el porqué.\n\n"
        f"Texto: {texto}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        full_respuesta = response.choices[0].message.content.strip()
        respuesta_lower = full_respuesta.lower()

        if "sí" in respuesta_lower or "si" in respuesta_lower:
            puntaje = 20.0
            explicacion = f"SÍ cumple Gherkin. Respuesta LLM: {full_respuesta}"
        else:
            puntaje = 0.0
            explicacion = f"NO cumple Gherkin. Respuesta LLM: {full_respuesta}"

        cache_analisis[texto] = (puntaje, explicacion)
        return (puntaje, explicacion)

    except Exception as e:
        return (0.0, f"Error al analizar Gherkin con OpenAI: {e}")

def analizar_claridad_consistencia(resumen: str, descripcion: str) -> Tuple[float, str]:
    """
    Analiza si la historia es clara y consistente (historia de usuario).
    Devuelve (puntaje, explicación).
      - Si cumple => (10, explicación)
      - Si no => (0, explicación)
    """
    if not descripcion or len(descripcion.strip()) < 10:
        return (0.0, "Descripción muy corta o vacía para evaluar claridad.")

    clave_cache = f"claridad_{hash(resumen)}_{hash(descripcion)}"
    if clave_cache in cache_analisis:
        return cache_analisis[clave_cache]

    prompt = f"""
    Analiza si la siguiente historia de usuario es clara, concisa y fácil de entender.

    Resumen/Título: {resumen}

    Descripción: {descripcion}

    Una historia clara y consistente debe:
    1. Ser fácil de entender para cualquier miembro del equipo
    2. Evitar ambigüedades y jerga innecesaria
    3. Tener una descripción que expanda y sea consistente con el resumen/título
    4. Expresar claramente qué se necesita y por qué

    Responde solo 'sí' o 'no' y explica brevemente el porqué.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        full_respuesta = response.choices[0].message.content.strip()
        respuesta_lower = full_respuesta.lower()

        if "sí" in respuesta_lower or "si" in respuesta_lower:
            puntaje = 10.0
            explicacion = f"SÍ cumple claridad. Respuesta LLM: {full_respuesta}"
        else:
            puntaje = 0.0
            explicacion = f"NO cumple claridad. Respuesta LLM: {full_respuesta}"

        cache_analisis[clave_cache] = (puntaje, explicacion)
        return (puntaje, explicacion)

    except Exception as e:
        return (0.0, f"Error al analizar claridad con OpenAI: {e}")

def analizar_invest_con_openai(descripcion: str) -> Tuple[float, str]:
    """
    Analiza si la descripción de la historia cumple con los criterios INVEST
    Devuelve (puntaje, explicación).
      - Si cumple => (10, explicación)
      - Si no => (0, explicación)
    """
    if not descripcion or len(descripcion.strip()) < 10:
        return (0.0, "Descripción muy corta o vacía para evaluar INVEST.")

    clave_cache = f"invest_{hash(descripcion)}"
    if clave_cache in cache_analisis:
        return cache_analisis[clave_cache]

    prompt = f"""
    El siguiente texto es la descripción de una historia de usuario. ¿Cumple con los criterios INVEST
    (independiente, negociable, valiosa, estimable, pequeña, testeable)? Responde solo 'sí' o 'no' y explica brevemente el porqué.

    Texto: {descripcion}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        full_respuesta = response.choices[0].message.content.strip()
        respuesta_lower = full_respuesta.lower()

        if "sí" in respuesta_lower or "si" in respuesta_lower:
            puntaje = 10.0
            explicacion = f"SÍ cumple INVEST. Respuesta LLM: {full_respuesta}"
        else:
            puntaje = 0.0
            explicacion = f"NO cumple INVEST. Respuesta LLM: {full_respuesta}"

        cache_analisis[clave_cache] = (puntaje, explicacion)
        return (puntaje, explicacion)

    except Exception as e:
        return (0.0, f"Error al analizar INVEST con OpenAI: {e}")

def analizar_titulo_descriptivo_con_openai(resumen: str, descripcion: str) -> Tuple[float, str]:
    """
    Analiza si el título (resumen) es descriptivo y correlaciona con la descripción.
    Retorna (puntaje, explicación).
      - (10, explicacion) si cumple
      - (0, explicacion) si no cumple
    """
    if not resumen or not descripcion:
        return (0.0, "No se puede evaluar: resumen o descripción vacíos.")

    clave_cache = f"titulo_descriptivo_{hash(resumen)}_{hash(descripcion)}"
    if clave_cache in cache_analisis:
        return cache_analisis[clave_cache]

    prompt = f"""
    Evalúa si el siguiente título describe claramente el objetivo o funcionalidad,
    y está correlacionado con la descripción. Responde 'sí' o 'no' y explica brevemente.

    Título: {resumen}
    Descripción: {descripcion}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        full_respuesta = response.choices[0].message.content.strip()
        respuesta_lower = full_respuesta.lower()

        if "sí" in respuesta_lower or "si" in respuesta_lower:
            puntaje = 10.0
            explicacion = f"SÍ es título descriptivo. Respuesta LLM: {full_respuesta}"
        else:
            puntaje = 0.0
            explicacion = f"NO es título descriptivo. Respuesta LLM: {full_respuesta}"

        cache_analisis[clave_cache] = (puntaje, explicacion)
        return (puntaje, explicacion)
    except Exception as e:
        return (0.0, f"Error al analizar título descriptivo con OpenAI: {e}")

def analizar_smart_en_resumen_ca(resumen_ca: str) -> Tuple[float, str]:
    """
    Analiza si el "Resumen" de un Criterio de Aceptación cumple con las características SMART.
    (Específico, Medible, Alcanzable, Relevante y con Tiempo definido)
    Retorna (puntaje, explicación).
    """
    if not resumen_ca or len(resumen_ca.strip()) < 5:
        return (0.0, "Resumen muy corto para evaluar SMART.")

    clave_cache = f"smart_ca_{hash(resumen_ca)}"
    if clave_cache in cache_analisis:
        return cache_analisis[clave_cache]

    prompt = f"""
    Este es el resumen de un Criterio de Aceptación. Verifica si es un criterio SMART:
    - Específico
    - Medible
    - Alcanzable
    - Relevante
    - Tiempo definido

    Responde 'sí' o 'no' y explica brevemente. Resumen: {resumen_ca}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        full_respuesta = response.choices[0].message.content.strip()
        respuesta_lower = full_respuesta.lower()

        if "sí" in respuesta_lower or "si" in respuesta_lower:
            puntaje = 10.0
            explicacion = f"SÍ cumple SMART. Respuesta LLM: {full_respuesta}"
        else:
            puntaje = 0.0
            explicacion = f"NO cumple SMART. Respuesta LLM: {full_respuesta}"

        cache_analisis[clave_cache] = (puntaje, explicacion)
        return (puntaje, explicacion)
    except Exception as e:
        return (0.0, f"Error al analizar SMART en Resumen CA: {e}")

###################################################################
# EVALUACIÓN DE HISTORIAS Y CRITERIOS DE ACEPTACIÓN
###################################################################

def evaluar_hu_hnf(resumen: str, descripcion: str, tipo: str) -> Dict[str, Any]:
    """
    Evalúa criterios de Historias de Usuario (HU) y de Historias No Funcionales (HNF).
    """
    resultado = {
        "j": 0.0,    # Título descriptivo
        "ex_j": "",  # Explicación Título descriptivo
        "k": 0.0,    # Claridad y consistencia
        "ex_k": "",  # Explicación Claridad y consistencia
        "o": 0.0,    # Segmentación INVEST
        "ex_o": "",  # Explicación Segmentación INVEST
        "t": 0.0,    # Uso de plantilla estándar
        "ex_t": "",  # Explicación Uso de plantilla estándar
    }

    # j -> Título descriptivo (10%)
    if tipo in ["historia", "historia no funcional"]:
        pj, ej = analizar_titulo_descriptivo_con_openai(resumen, descripcion)
        resultado["j"] = pj
        resultado["ex_j"] = ej

    # k -> Claridad y consistencia (10%)
    pk, ek = analizar_claridad_consistencia(resumen, descripcion)
    resultado["k"] = pk
    resultado["ex_k"] = ek

    # o -> Segmentación INVEST (10%)
    if tipo in ["historia", "historia no funcional"]:
        po, eo = analizar_invest_con_openai(descripcion)
        resultado["o"] = po
        resultado["ex_o"] = eo

    # t -> Uso de plantilla estándar (5%)
    # Este no es IA, pero podemos poner una lógica y explicación
    pattern_plantilla = r"como\s+\w+.+?\s+,?\s*quiero\s+\w+.+?\s+,?\s*para\s+\w+.+?"
    if re.search(pattern_plantilla, (descripcion or "").lower()):
        resultado["t"] = 5.0
        resultado["ex_t"] = "SÍ usa plantilla 'Como..., quiero..., para...'."
    else:
        resultado["t"] = 0.0
        resultado["ex_t"] = "No se detecta plantilla 'Como..., quiero..., para...'."

    return resultado

def evaluar_criterios_aceptacion(resumen_ca: str) -> Dict[str, Any]:
    """
    Evalúa Criterios de Aceptación (CA):
      - m (20%): Uso de Gherkin en el campo 'Resumen' del CA
      - n (10%): Criterios SMART en el 'Resumen' del CA
    """
    resultado = {
        "m": 0.0,   # Uso de Gherkin
        "ex_m": "", # Explicación Uso de Gherkin
        "n": 0.0,   # Criterios SMART
        "ex_n": "", # Explicación Criterios SMART
    }

    # m -> Uso de Gherkin (20%)
    pm, em = analizar_gherkin_con_openai(resumen_ca)
    # Nota: la función ya regresa 20 si sí cumple, 0 si no.
    resultado["m"] = pm
    resultado["ex_m"] = em

    # n -> Criterios SMART (10%)
    pn, en = analizar_smart_en_resumen_ca(resumen_ca)
    resultado["n"] = pn
    resultado["ex_n"] = en

    return resultado

###################################################################
# ANÁLISIS POR PROYECTO, INFERIR TIPO, MAIN, ETC.
###################################################################

def analizar_proyecto(data: Dict[str, Any]) -> Tuple[str, str]:
    eval_hu = data.get("eval_hu", [])
    eval_hnf = data.get("eval_hnf", [])
    all_evals = eval_hu + eval_hnf

    if not all_evals:
        return ("Sin datos suficientes.", "Sin datos suficientes.")

    criterios = defaultdict(list)
    for issue in data["detalles_issues"]:
        for crit in ["j", "k", "m", "n", "o", "t"]:
            criterios[crit].append(issue.get(crit, 0.0))

    promedios = {k: sum(v)/len(v) if v else 0.0 for k, v in criterios.items()}

    # Identificar fortalezas y debilidades
    fortalezas = sorted(promedios.items(), key=lambda x: x[1], reverse=True)[:2]
    debilidades = sorted(promedios.items(), key=lambda x: x[1])[:2]

    mensajes_positivos = []
    for crit, score in fortalezas:
        if crit == "j" and score > 7:
            mensajes_positivos.append("títulos descriptivos y concisos")
        elif crit == "k" and score > 7:
            mensajes_positivos.append("consistencia entre resumen y descripción")
        elif crit == "m" and score > 14:
            mensajes_positivos.append("uso de Gherkin y coherencia en criterios de aceptación")
        elif crit == "n" and score > 7:
            mensajes_positivos.append("criterios de aceptación SMART")
        elif crit == "o" and score > 7:
            mensajes_positivos.append("uso de principios INVEST")
        elif crit == "t" and score > 3:
            mensajes_positivos.append("uso de la plantilla estándar")

    mensajes_mejoras = []
    for crit, score in debilidades:
        if crit == "j" and score < 5:
            mensajes_mejoras.append("mejorar los títulos para que sean más descriptivos")
        elif crit == "k" and score < 5:
            mensajes_mejoras.append("aumentar la consistencia entre resumen y descripción")
        elif crit == "m" and score < 10:
            mensajes_mejoras.append("reforzar el uso de Gherkin y la coherencia en criterios de aceptación")
        elif crit == "n" and score < 5:
            mensajes_mejoras.append("definir criterios de aceptación más SMART")
        elif crit == "o" and score < 5:
            mensajes_mejoras.append("mejorar la segmentación según INVEST")
        elif crit == "t" and score < 2.5:
            mensajes_mejoras.append("usar la plantilla estándar adecuadamente")

    positivo = (
        "El proyecto destaca en " + " y ".join(mensajes_positivos) + "."
        if mensajes_positivos
        else "Sin fortalezas destacadas."
    )
    mejora = (
        "Se recomienda " + " y ".join(mensajes_mejoras) + "."
        if mensajes_mejoras
        else "Sin áreas de mejora identificadas."
    )

    return (positivo, mejora)

def inferir_tipo_incidencia(descripcion: str, principal: str) -> str:
    if principal:
        return "criterios de aceptación"
    if re.search(r"como\s+\w+.+?\s+,?\s*quiero\s+\w+.+?\s+,?\s*para\s+\w+.+?", (descripcion or "").lower()):
        return "historia"
    return "historia no funcional"

def main():
    ruta_csv = input("Ruta del CSV (Enter para predeterminado): ").strip("\"'") or "prueba Ai 1.csv"
    if not os.path.exists(ruta_csv):
        print(f"Error: Archivo no encontrado en {ruta_csv}")
        return

    codificaciones = ["utf-8", "ISO-8859-1", "Windows-1252"]
    issues = None
    for codificacion in codificaciones:
        try:
            with open(ruta_csv, mode="r", encoding=codificacion) as f:
                reader = csv.DictReader(f)
                issues = list(reader)
            print(f"Archivo leído correctamente con codificación: {codificacion}")
            break
        except UnicodeDecodeError:
            print(f"Error al leer con codificación {codificacion}")
    else:
        print("No se pudo leer el archivo con ninguna de las codificaciones probadas.")
        return

    if not issues:
        print(f"Advertencia: El archivo {ruta_csv} no contiene datos o no se pudo leer correctamente.")
        return

    # Estructura para evaluaciones
    # Además de j,k,m,n,o,t,... agregamos ex_j, ex_k, ex_m, ex_n, ex_o, ex_t para explicaciones
    evaluaciones = {}
    for row in issues:
        clave = row.get("Clave de incidencia", "").strip()
        if not clave:
            continue
        evaluaciones[clave] = {
            "j": 0.0, "ex_j": "",
            "k": 0.0, "ex_k": "",
            "l": 10.0,  # Estándar JIT
            "m": 0.0, "ex_m": "",
            "n": 0.0, "ex_n": "",
            "o": 0.0, "ex_o": "",
            "p": 5.0,  # Revisión colaborativa => lo consideramos siempre 5
            "q": 10.0, # Seguimiento => siempre 10
            "r": 5.0,  # Prioridad => siempre 5
            "s": 5.0,  # Documentación => siempre 5
            "t": 0.0, "ex_t": "",
            "v": 0.0,
        }

    descripciones_historias = {}
    tipos_issues = {}

    # Determinar tipos
    for row in issues:
        clave = row.get("Clave de incidencia", "").strip()
        if not clave:
            continue
        tipo_original = row.get("Tipo de Incidencia", "").strip()
        tipo_norm = normalizar_tipo_incidencia(tipo_original)
        descripcion = row.get("Descripción", "")
        principal = row.get("Principal", "").strip()
        if not tipo_norm:
            tipo_norm = inferir_tipo_incidencia(descripcion, principal)
            print(f"Inferido tipo '{tipo_norm}' para {clave}")
        tipos_issues[clave] = tipo_norm
        # Guardar descripciones de HU/HNF
        if tipo_norm in ["historia", "historia no funcional"]:
            descripciones_historias[clave] = {
                "descripcion": descripcion,
                "tipo": tipo_norm,
            }

    # Evaluar
    for row in issues:
        clave = row.get("Clave de incidencia", "").strip()
        if not clave:
            continue
        tipo_issue = tipos_issues.get(clave, "")
        resumen = row.get("Resumen", "")
        descripcion = row.get("Descripción", "")
        principal = row.get("Principal", "").strip()

        if tipo_issue in ["historia", "historia no funcional"]:
            eval_hu = evaluar_hu_hnf(resumen, descripcion, tipo_issue)
            # actualizar en evaluaciones
            for k_ in eval_hu:
                evaluaciones[clave][k_] = eval_hu[k_]

        elif tipo_issue == "criterios de aceptación":
            eval_ca = evaluar_criterios_aceptacion(resumen)
            for k_ in eval_ca:
                evaluaciones[clave][k_] = eval_ca[k_]

    # Ponderar CA en HU/HNF
    principal_map = defaultdict(list)
    for row in issues:
        clave = row.get("Clave de incidencia", "").strip()
        if not clave:
            continue
        tipo_issue = tipos_issues.get(clave, "")
        principal = row.get("Principal", "").strip()
        if tipo_issue == "criterios de aceptación" and principal in evaluaciones:
            principal_map[principal].append({
                "clave_ca": clave,
                "m": evaluaciones[clave].get("m", 0.0),
                "n": evaluaciones[clave].get("n", 0.0),
            })

    for hu_key, lista_cas in principal_map.items():
        if hu_key in evaluaciones:
            m_vals = [x["m"] for x in lista_cas]
            n_vals = [x["n"] for x in lista_cas]
            if m_vals:
                evaluaciones[hu_key]["m"] = sum(m_vals)/len(m_vals)
                # Podríamos concatenar explicaciones, pero te sugiero
                # almacenar la "media" explicando algo:
                evaluaciones[hu_key]["ex_m"] = f"Promedio de m de {len(m_vals)} CA: {m_vals}"
            if n_vals:
                evaluaciones[hu_key]["n"] = sum(n_vals)/len(n_vals)
                evaluaciones[hu_key]["ex_n"] = f"Promedio de n de {len(n_vals)} CA: {n_vals}"

    # Calcular v
    for ckey, vals in evaluaciones.items():
        vals["v"] = sum(vals[k] for k in ["j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t"])

    # Agrupar por proyecto
    proyectos_data = defaultdict(lambda: {
        "hu": [], "hnf": [],
        "eval_hu": [], "eval_hnf": [],
        "detalles_issues": []
    })
    for row in issues:
        clave = row.get("Clave de incidencia", "").strip()
        if not clave or clave not in evaluaciones:
            continue
        proyecto = row.get("Nombre del proyecto", "") or "SIN_PROYECTO"
        t = tipos_issues.get(clave, "")
        score = evaluaciones[clave]["v"]
        proyectos_data[proyecto]["detalles_issues"].append(evaluaciones[clave])
        if t == "historia":
            proyectos_data[proyecto]["hu"].append(clave)
            proyectos_data[proyecto]["eval_hu"].append(score)
        elif t == "historia no funcional":
            proyectos_data[proyecto]["hnf"].append(clave)
            proyectos_data[proyecto]["eval_hnf"].append(score)

    # Crear directorio de salida
    output_dir = "resultados_evaluacion"
    os.makedirs(output_dir, exist_ok=True)

    # Generar informe_proyectos.txt
    with open(os.path.join(output_dir, "informe_proyectos.txt"), "w", encoding="utf-8") as f_txt:
        for proyecto, data in proyectos_data.items():
            total_hu = len(data["hu"])
            total_hnf = len(data["hnf"])
            prom_hu = statistics.mean(data["eval_hu"]) if data["eval_hu"] else 0.0
            prom_hnf = statistics.mean(data["eval_hnf"]) if data["eval_hnf"] else 0.0
            all_scores = data["eval_hu"] + data["eval_hnf"]
            prom_total = statistics.mean(all_scores) if all_scores else 0.0
            positivo, mejora = analizar_proyecto(data)

            f_txt.write(f"Nombre del proyecto: {proyecto}\n")
            f_txt.write(f"Total de historias de usuario: {total_hu}\n")
            f_txt.write(f"Total de historias no funcionales (habilitadoras): {total_hnf}\n")
            f_txt.write(f"Promedio de evaluación de historias de usuario: {round(prom_hu, 2)}\n")
            f_txt.write(f"Promedio de evaluación de historias no funcionales (habilitadoras): {round(prom_hnf, 2)}\n")
            f_txt.write(f"Promedio de evaluación total: {round(prom_total, 2)}\n")
            f_txt.write(f"Análisis LLM temas positivos: {positivo}\n")
            f_txt.write(f"Análisis LLM temas por mejorar: {mejora}\n")
            f_txt.write("\n---------------------------------------------------------\n\n")

    # Generar evaluacion_issues.csv
    # Agregamos columnas para explicaciones: "ex_j", "ex_k", "ex_l", ... etc
    columnas_issues = [
        "Clave de incidencia",
        "Nombre del proyecto",
        "Resumen",
        "Descripción",
        "Tipo de Incidencia",
        "Principal",
        "Story Point",
        "Creada",
        "Paso a Done",

        "j.10% Título descriptivo",
        "k.10% Claridad y consistencia",
        "l.10% Estándar JIT",
        "m.20% Uso de Gherkin",
        "n.10% Criterios SMART",
        "o.10% Segmentación INVEST",
        "p.5% Revisión colaborativa",
        "q.10% Seguimiento y ajustes",
        "r.5% Prioridad y valor",
        "s.5% Documentación adecuada",
        "t.5% Uso de plantilla estándar",
        "v. Suma de checklist",
        "Tipo Normalizado",

        # Explicaciones
        "Explicación Título descriptivo",
        "Explicación Claridad y consistencia",
        "Explicación Uso de Gherkin",
        "Explicación Criterios SMART",
        "Explicación Segmentación INVEST",
        "Explicación Uso de plantilla estándar"
    ]

    with open(os.path.join(output_dir, "evaluacion_issues.csv"), "w", encoding="utf-8", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(columnas_issues)
        for row in issues:
            clave = row.get("Clave de incidencia", "").strip()
            if not clave or clave not in evaluaciones:
                continue
            vals = evaluaciones[clave]
            tipo_norm = tipos_issues.get(clave, "")

            writer.writerow([
                row.get("Clave de incidencia", ""),
                row.get("Nombre del proyecto", ""),
                row.get("Resumen", ""),
                row.get("Descripción", ""),
                row.get("Tipo de Incidencia", ""),
                row.get("Principal", ""),
                row.get("Story Point", ""),
                row.get("Creada", ""),
                row.get("Paso a Done", ""),

                round(vals["j"], 2),
                round(vals["k"], 2),
                round(vals["l"], 2),
                round(vals["m"], 2),
                round(vals["n"], 2),
                round(vals["o"], 2),
                round(vals["p"], 2),
                round(vals["q"], 2),
                round(vals["r"], 2),
                round(vals["s"], 2),
                round(vals["t"], 2),
                round(vals["v"], 2),
                tipo_norm,

                # Explicaciones:
                vals.get("ex_j", ""),
                vals.get("ex_k", ""),
                vals.get("ex_m", ""),
                vals.get("ex_n", ""),
                vals.get("ex_o", ""),
                vals.get("ex_t", "")
            ])

    # Generar evaluacion_proyectos.csv
    columnas_proyectos = [
        "Nombre del proyecto",
        "Total de historias de usuario",
        "Total de historias no funcionales (habilitadoras)",
        "Promedio de evaluación de historias de usuario",
        "Promedio de evaluación de historias no funcionales (habilitadoras)",
        "Promedio de evaluación total",
        "Análisis LLM temas positivos",
        "Análisis LLM temas por mejorar",
    ]
    with open(os.path.join(output_dir, "evaluacion_proyectos.csv"), "w", encoding="utf-8", newline="") as f_proj:
        writer = csv.writer(f_proj)
        writer.writerow(columnas_proyectos)
        for proyecto, data in proyectos_data.items():
            total_hu = len(data["hu"])
            total_hnf = len(data["hnf"])
            prom_hu = statistics.mean(data["eval_hu"]) if data["eval_hu"] else 0.0
            prom_hnf = statistics.mean(data["eval_hnf"]) if data["eval_hnf"] else 0.0
            all_scores = data["eval_hu"] + data["eval_hnf"]
            prom_total = statistics.mean(all_scores) if all_scores else 0.0
            positivo, mejora = analizar_proyecto(data)
            writer.writerow([
                proyecto,
                total_hu,
                total_hnf,
                round(prom_hu, 2),
                round(prom_hnf, 2),
                round(prom_total, 2),
                positivo,
                mejora,
            ])

    print("Archivos generados en 'resultados_evaluacion'.")


if __name__ == "__main__":
    main()