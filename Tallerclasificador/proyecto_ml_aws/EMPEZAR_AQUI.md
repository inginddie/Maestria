# 🚀 EMPEZAR AQUÍ - Guía Rápida

## ✅ Estado: Todo Listo para Probar

Tu entorno está configurado correctamente:
- ✅ Python 3.13.5 instalado
- ✅ TensorFlow 2.20.0 funcionando
- ✅ Entorno virtual activo
- ✅ Modelo VGG16 entrenado disponible

## 📝 PASO A PASO - Ejecuta el Notebook

### 1️⃣ Abre el Notebook en VS Code

En VS Code, navega a:
```
notebooks/03_prueba_inferencia_local.ipynb
```

O usa el explorador de archivos de VS Code (panel izquierdo).

### 2️⃣ Selecciona el Kernel Correcto

Cuando abras el notebook, VS Code te pedirá seleccionar un kernel:

1. Click en **"Select Kernel"** (arriba a la derecha)
2. Selecciona **"Python Environments"**
3. Elige el que dice **"venv"** o **"Python 3.13.5 ('venv')"**

### 3️⃣ Ejecuta las Celdas

Hay dos formas:

**Opción A - Una por una (RECOMENDADO para aprender):**
- Click en una celda
- Presiona `Shift + Enter` para ejecutarla
- Lee el resultado antes de continuar

**Opción B - Todas a la vez:**
- Click en "Run All" (arriba)
- Espera a que termine

### 4️⃣ Ajusta las Rutas si es Necesario

En la celda que dice:
```python
MODEL_PATH = '../../vgg16_industrial_classifier_20251014_203947.keras'
```

Si ves un error de "archivo no encontrado", ajusta la ruta según donde tengas el modelo.

### 5️⃣ Prueba con Tus Imágenes

En la celda que dice:
```python
test_category = 'screw'  # Cambia por la categoría que quieras probar
```

Cambia `'screw'` por cualquiera de estas categorías:
- adapter_plate_triangular
- bracket_big
- clamp_small
- engine_part_cooler_round
- engine_part_cooler_square
- injection_pump
- screw
- star
- tee_connector
- thread

## 🎯 Qué Observar

Mientras ejecutas el notebook, presta atención a:

1. **Accuracy del modelo**: ¿Clasifica correctamente?
2. **Confianza de las predicciones**: ¿Son altas (>70%)?
3. **Clases confundidas**: ¿Qué piezas se parecen?
4. **Umbral óptimo**: ¿70% es bueno o necesitas ajustar?

## 📊 Resultados Esperados

Deberías ver:
- ✅ Modelo cargado exitosamente
- ✅ 10 clases de piezas industriales
- ✅ Predicciones con ~85% de accuracy
- ✅ Visualización de imágenes clasificadas
- ✅ Análisis de confianza

## 🐛 Si Algo Sale Mal

### Error: "Model file not found"
```python
# Verifica dónde está el modelo
import os
print(os.path.exists('../../vgg16_industrial_classifier_20251014_203947.keras'))
```

Si dice `False`, ajusta la ruta en el notebook.

### Error: "Dataset not found"
```python
# Ajusta esta línea en el notebook
DATASET_PATH = 'C:/Users/Diego/Documents/Maestria/tallerML/datos/industrial_classification_data_set'
```

### Error: "No module named 'tensorflow'"
En la terminal de VS Code:
```bash
.\venv\Scripts\Activate.ps1
pip install tensorflow
```

## 💡 Tips para Aprender

1. **Lee los comentarios**: Cada celda tiene explicaciones
2. **Experimenta**: Cambia parámetros y ve qué pasa
3. **Toma notas**: Anota qué funciona mejor
4. **Pregunta**: Si algo no está claro, pregúntame

## 🎓 Conceptos Clave que Aprenderás

- **Transfer Learning**: Cómo usar VGG16 preentrenado
- **Preprocesamiento**: Normalización de imágenes
- **Inferencia**: Hacer predicciones con el modelo
- **Umbral de confianza**: Decidir cuándo confiar en la predicción
- **Flujo AWS**: Cómo funcionará en producción

## 🚀 Después de Probar

Una vez que entiendas cómo funciona el modelo:

1. ✅ Habrás validado que el modelo funciona localmente
2. ✅ Conocerás el umbral óptimo de confianza
3. ✅ Entenderás el flujo de clasificación
4. 🎯 Estarás listo para **Fase 2: Preparar para AWS**

---

## 📞 ¿Listo?

**Abre el notebook ahora:**
```
notebooks/03_prueba_inferencia_local.ipynb
```

**Y empieza a ejecutar las celdas una por una.**

¡Disfruta aprendiendo! 🎉
