# 🚀 FASE 1: Pruebas Locales del Modelo

## ✅ Estado Actual

Ya tienes:
- ✅ Modelo VGG16 entrenado (85.28% accuracy)
- ✅ Archivos de metadatos y clases
- ✅ Dataset de piezas industriales
- ✅ Notebook de pruebas creado
- ✅ Script de inferencia Python

## 📋 Pasos para Probar el Modelo Localmente

### Paso 1: Abrir el Proyecto en VS Code

```bash
cd C:\Users\Diego\Documents\Maestria\tallerML\proyecto_ml_aws
code .
```

### Paso 2: Activar el Entorno Virtual

En la terminal de VS Code (Ctrl + `):

```bash
# Activar entorno virtual
venv\Scripts\activate

# Verificar que está activado (deberías ver (venv) al inicio)
```

### Paso 3: Instalar/Verificar Dependencias

```bash
# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Verificar instalación
python -c "import tensorflow as tf; print('TensorFlow:', tf.__version__)"
```

### Paso 4: Abrir el Notebook de Pruebas

1. En VS Code, navega a: `notebooks/03_prueba_inferencia_local.ipynb`
2. Abre el archivo
3. Selecciona el kernel: Click en "Select Kernel" → "Python Environments" → Selecciona `venv`
4. Ejecuta las celdas una por una (Shift + Enter)

### Paso 5: Probar con el Script Python (Alternativa)

```bash
# Ver información del modelo
python scripts/inferencia_local.py --image ruta/a/imagen.jpg --info

# Clasificar una imagen
python scripts/inferencia_local.py --image ../datos/industrial_classification_data_set/screw/screw_001.jpg

# Con umbral personalizado
python scripts/inferencia_local.py --image ../datos/industrial_classification_data_set/screw/screw_001.jpg --threshold 0.8
```

## 🎯 Qué Vas a Aprender

### En el Notebook:

1. **Cargar el modelo**: Cómo cargar un modelo .keras entrenado
2. **Preprocesamiento**: Cómo preparar imágenes para VGG16
3. **Inferencia**: Cómo hacer predicciones
4. **Análisis de confianza**: Cómo evaluar diferentes umbrales
5. **Simulación AWS**: Cómo funcionará el flujo en producción

### Conceptos Clave:

- **Transfer Learning**: Usaste VGG16 preentrenado
- **Umbral de confianza**: Si la predicción es < 70%, va a "no-identificadas"
- **Top-3 predicciones**: Ver las 3 clases más probables
- **Preprocesamiento VGG16**: Normalización específica de ImageNet

## 📊 Resultados Esperados

Tu modelo debería:
- ✅ Clasificar correctamente ~85% de las imágenes
- ✅ Dar alta confianza (>70%) en la mayoría de casos
- ✅ Identificar correctamente las 10 clases de piezas

## 🔍 Análisis Recomendado

Prueba el modelo con:

1. **Imágenes de cada categoría** (al menos 5-10 por clase)
2. **Diferentes umbrales** (0.5, 0.6, 0.7, 0.8, 0.9)
3. **Casos difíciles** (imágenes borrosas, mal iluminadas)

Esto te ayudará a:
- Entender el comportamiento del modelo
- Elegir el umbral óptimo para producción
- Identificar clases problemáticas

## 🎓 Preguntas para Reflexionar

Mientras pruebas, piensa en:

1. **¿Qué umbral es mejor?** 
   - Umbral bajo = más imágenes clasificadas, pero más errores
   - Umbral alto = menos errores, pero más imágenes en "no-identificadas"

2. **¿Qué clases confunde el modelo?**
   - ¿Hay piezas similares que se confunden?
   - ¿Necesitas más datos de entrenamiento?

3. **¿Cómo manejar errores en producción?**
   - Carpeta "no-identificadas" para revisión manual
   - Reentrenamiento periódico con nuevos datos

## 🚀 Próximos Pasos (Fase 2)

Una vez que entiendas bien cómo funciona el modelo localmente:

1. Preparar el código de inferencia para SageMaker
2. Crear el script de despliegue
3. Configurar la función Lambda
4. Integrar con S3

## 💡 Tips

- **Ejecuta celda por celda**: No corras todo de golpe, entiende cada paso
- **Experimenta**: Cambia parámetros, prueba diferentes imágenes
- **Toma notas**: Anota qué umbral funciona mejor
- **Pregunta**: Si algo no está claro, pregúntame

## ❓ Troubleshooting

### Error: "No module named 'tensorflow'"
```bash
pip install tensorflow==2.13.0
```

### Error: "Model file not found"
Verifica que los archivos estén en la raíz del proyecto:
- `vgg16_industrial_classifier_20251014_203947.keras`
- `vgg16_industrial_classifier_20251014_203947_classes.json`
- `vgg16_industrial_classifier_20251014_203947_metadata.json`

### Error: "Dataset not found"
Ajusta la ruta `DATASET_PATH` en el notebook según donde tengas el dataset.

## 📞 ¿Necesitas Ayuda?

Si tienes dudas:
1. Lee los comentarios en el código
2. Revisa los mensajes de error completos
3. Pregúntame específicamente qué no entiendes

---

✅ **¡Estás listo para comenzar!**

Abre el notebook `03_prueba_inferencia_local.ipynb` y empieza a experimentar.
