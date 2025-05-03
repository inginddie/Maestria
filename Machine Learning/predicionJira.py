#!/usr/bin/env python3
"""
Análisis Predictivo de Completitud de Historias en Jira
--------------------------------------------------------

Este script implementa un flujo de trabajo completo para estimar la completitud de historias
(en 15 días calendario) usando un modelo de regresión logística. Incluye:

1. Carga del dataset (CSV o JSON) mediante un diálogo de selección.
2. Análisis Exploratorio de Datos (EDA): distribuciones de Story Points, tipo de incidencia,
   equipo y tiempos de desarrollo.
3. Preprocesamiento: generación de la variable objetivo, normalización de variables numéricas
   y codificación de variables categóricas.
4. Entrenamiento y evaluación del modelo (accuracy, precision, recall, F1, AUC, matriz de confusión
   y curva ROC).
5. Simulación interactiva (por consola) para predecir la probabilidad de completitud.
6. Generación de un informe dinámico con las métricas y coeficientes del modelo.

El script está pensado para ser adaptable a diferentes datasets y para analizar distintos grupos de equipos.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mtick

# Librerías para preprocesamiento y modelado
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
                             confusion_matrix, roc_curve)
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# Para visualizaciones interactivas con Plotly (si se desea abrir en navegador)
import plotly.express as px
import plotly.graph_objects as go

# Para el diálogo de selección de archivo
from tkinter import Tk
from tkinter.filedialog import askopenfilename

def cargar_dataset():
    """
    Función para cargar el dataset de Jira.
    Permite seleccionar un archivo CSV o JSON usando un diálogo.
    """
    # Ocultar la ventana principal de Tkinter
    Tk().withdraw()
    print("Selecciona el archivo CSV o JSON del dataset de Jira...")
    file_path = askopenfilename()
    if not file_path:
        print("No se seleccionó ningún archivo. Abortando.")
        return None

    _, file_extension = os.path.splitext(file_path)
    if file_extension.lower() == '.csv':
        df = pd.read_csv(file_path)
    elif file_extension.lower() in ['.json']:
        df = pd.read_json(file_path)
    else:
        print("Formato de archivo no soportado. Utilice CSV o JSON.")
        return None

    print(f"Dataset cargado correctamente: {df.shape[0]} registros y {df.shape[1]} columnas.")
    return df

def convertir_fechas(df, date_columns):
    """
    Convierte las columnas de fecha al formato datetime.
    """
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    print("Conversión de fechas completada.")
    return df

def crear_variable_objetivo(df):
    """
    Crea la variable objetivo 'completitud_15d' basada en la diferencia en días
    entre 'startDate' y 'fechaDone'. Se considera completada (1) si la diferencia
    es menor o igual a 15 días, o 0 en caso contrario.
    """
    df['completion_time'] = (df['fechaDone'] - df['startDate']).dt.days
    df['completitud_15d'] = df['completion_time'].apply(lambda x: 1 if pd.notnull(x) and x <= 15 else 0)
    print("Variable objetivo 'completitud_15d' creada.")
    return df

def realizar_eda(df):
    """
    Realiza un análisis exploratorio de datos (EDA) mostrando:
      - Distribución de Story Points.
      - Tasa de completitud por Story Points.
      - Tasa de completitud por equipo.
      - Distribución del tiempo de desarrollo.
    """
    sns.set(style="darkgrid", palette='viridis')
    
    # Distribución de Story Points
    plt.figure(figsize=(8, 5))
    sns.countplot(data=df, x='story_points', palette='viridis')
    plt.title('Distribución de Story Points')
    plt.xlabel('Story Points')
    plt.ylabel('Cantidad de historias')
    plt.show()

    # Tasa de completitud por Story Points
    sp_completion = df.groupby('story_points')['completitud_15d'].mean().reset_index()
    plt.figure(figsize=(8, 5))
    sns.barplot(data=sp_completion, x='story_points', y='completitud_15d', palette='viridis')
    plt.title('Tasa de Completitud en 15 días por Story Points')
    plt.xlabel('Story Points')
    plt.ylabel('Tasa de Completitud')
    plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    plt.show()

    # Tasa de completitud por equipo
    team_completion = df.groupby('team')['completitud_15d'].mean().reset_index()
    plt.figure(figsize=(10, 6))
    sns.barplot(data=team_completion, x='team', y='completitud_15d', palette='viridis')
    plt.title('Tasa de Completitud en 15 días por Equipo')
    plt.xlabel('Equipo')
    plt.ylabel('Tasa de Completitud')
    plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    plt.xticks(rotation=45)
    plt.show()

    # Distribución del Tiempo de Desarrollo
    plt.figure(figsize=(8, 5))
    sns.histplot(df['tiempo_desarrollo'], bins=20, kde=True, color='skyblue')
    plt.title('Distribución del Tiempo de Desarrollo (días)')
    plt.xlabel('Tiempo de Desarrollo (días)')
    plt.ylabel('Frecuencia')
    plt.show()

def preprocesamiento_y_modelado(df, features, target, test_size=0.20, random_state=42):
    """
    Separa features y target, realiza la división en train/test, 
    configura el preprocesamiento (normalización y codificación) y entrena un modelo de regresión logística.
    Devuelve el pipeline entrenado, los conjuntos de train/test y las métricas.
    """
    X = df[features]
    y = df[target]

    # Dividir en train y test
    X_train, X_test, y_train, y_test = train_test_split(X, y,
                                                        test_size=test_size,
                                                        random_state=random_state)
    print(f"División: {X_train.shape[0]} registros en train y {X_test.shape[0]} en test.")

    # Definir variables numéricas y categóricas
    numeric_features = ['story_points', 'tiempo_desarrollo']
    categorical_features = ['tipo', 'team']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('cat', OneHotEncoder(drop='first'), categorical_features)
        ]
    )

    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(max_iter=1000))
    ])

    # Entrenar el modelo
    pipeline.fit(X_train, y_train)
    print("Modelo entrenado.")

    # Predicciones y evaluación
    y_pred = pipeline.predict(X_test)
    y_pred_prob = pipeline.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_prob)

    print(f"Accuracy: {acc:.3f}")
    print(f"Precision: {prec:.3f}")
    print(f"Recall: {rec:.3f}")
    print(f"F1-Score: {f1:.3f}")
    print(f"AUC: {auc:.3f}")

    return pipeline, X_train, X_test, y_train, y_test, (acc, prec, rec, f1, auc)

def graficar_evaluacion(y_test, y_pred, y_pred_prob, auc):
    """
    Genera las gráficas de evaluación: matriz de confusión y curva ROC.
    """
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6, 4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title('Matriz de Confusión')
    plt.xlabel('Predicción')
    plt.ylabel('Valor Real')
    plt.show()

    fpr, tpr, thresholds = roc_curve(y_test, y_pred_prob)
    plt.figure(figsize=(6, 4))
    plt.plot(fpr, tpr, label=f'AUC = {auc:.3f}')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Curva ROC')
    plt.legend(loc='lower right')
    plt.show()

def simulate_dashboard(pipeline):
    """
    Función interactiva (por consola) para simular la probabilidad de completitud.
    Se piden los valores de entrada y se muestra la probabilidad predicha.
    """
    print("\n--- Simulación de Predicción ---")
    try:
        sp = int(input("Ingrese Story Points (ej. 5): "))
    except:
        sp = 5
    try:
        td = int(input("Ingrese Tiempo de Desarrollo (días, ej. 7): "))
    except:
        td = 7
    tipo = input("Ingrese Tipo de incidencia (Historia de Usuario / Tarea/Bug) [Historia de Usuario]: ") or "Historia de Usuario"
    team = input("Ingrese Equipo (molécula) [Ingrese el nombre tal como aparece en el dataset]: ")

    df_sim = pd.DataFrame({
        'story_points': [sp],
        'tiempo_desarrollo': [td],
        'tipo': [tipo],
        'team': [team]
    })

    prob = pipeline.predict_proba(df_sim)[:, 1][0]
    print(f"\nProbabilidad de completar en 15 días: {prob*100:.1f}%")

def generar_informe(pipeline, data_clean, acc, prec, rec, f1, auc):
    """
    Imprime en consola un informe técnico con las métricas y coeficientes del modelo.
    """
    print("\n--- Informe Técnico del Modelo de Regresión Logística ---")
    print(f"Número de registros (limpios): {data_clean.shape[0]}")
    print(f"Accuracy en Test: {acc:.3f}")
    print(f"Precision: {prec:.3f}")
    print(f"Recall: {rec:.3f}")
    print(f"F1-Score: {f1:.3f}")
    print(f"AUC: {auc:.3f}\n")

    # Extraer coeficientes del modelo a través del pipeline
    model = pipeline.named_steps['classifier']
    # Obtener nombres de variables luego del preprocesamiento
    ohe = pipeline.named_steps['preprocessor'].named_transformers_['cat']
    categorical_features = ['tipo', 'team']
    numeric_features = ['story_points', 'tiempo_desarrollo']
    cat_features = ohe.get_feature_names_out(categorical_features)
    feature_names = numeric_features + list(cat_features)
    coef_df = pd.DataFrame({"Feature": feature_names, "Coeficiente": model.coef_[0]})
    print("Coeficientes del modelo:")
    print(coef_df.to_string(index=False))

def main():
    # Paso 1: Cargar dataset
    data = cargar_dataset()
    if data is None:
        return

    # Paso 2: Convertir columnas de fecha (ajustar según columnas disponibles)
    date_columns = ['startDate', 'fechaDesarrollo', 'fechaDone']
    data = convertir_fechas(data, date_columns)

    # Paso 3: Crear la variable objetivo (completitud en 15 días)
    data = crear_variable_objetivo(data)

    # Si no existe la columna 'tipo' se crea por defecto
    if 'tipo' not in data.columns:
        data['tipo'] = 'Historia de Usuario'

    # Calcular tiempo de desarrollo (días)
    if 'fechaDesarrollo' in data.columns and 'fechaDone' in data.columns:
        data['tiempo_desarrollo'] = (data['fechaDone'] - data['fechaDesarrollo']).dt.days
    else:
        data['tiempo_desarrollo'] = np.nan

    # Selección de variables
    features = ['story_points', 'tipo', 'team', 'tiempo_desarrollo']
    target = 'completitud_15d'

    # Eliminar registros con valores faltantes en las columnas de interés
    data_clean = data.dropna(subset=features + [target]).copy()
    print(f"Dataset limpio: {data_clean.shape[0]} registros restantes.\n")

    # Paso 4: Realizar EDA
    realizar_eda(data_clean)

    # Paso 5: Preprocesamiento y Modelado
    pipeline, X_train, X_test, y_train, y_test, metrics = preprocesamiento_y_modelado(data_clean, features, target)
    acc, prec, rec, f1, auc = metrics

    # Paso 6: Evaluación (matriz de confusión y curva ROC)
    y_pred = pipeline.predict(X_test)
    y_pred_prob = pipeline.predict_proba(X_test)[:, 1]
    graficar_evaluacion(y_test, y_pred, y_pred_prob, auc)

    # Paso 7: Informe Técnico
    generar_informe(pipeline, data_clean, acc, prec, rec, f1, auc)

    # Paso 8: Simulación interactiva (Dashboard por consola)
    seguir = 's'
    while seguir.lower() == 's':
        simulate_dashboard(pipeline)
        seguir = input("\n¿Desea realizar otra simulación? (s/n): ")

if __name__ == '__main__':
    main()
