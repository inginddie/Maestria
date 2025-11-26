# 📚 Notebooks Disponibles

## 🌐 Para Google Colab (RECOMENDADO)

### ✅ Listos para usar:

1. **`01_exploracion_datos_COLAB.ipynb`** ⭐
   - Exploración completa del dataset
   - Análisis de categorías y distribución
   - Visualización de muestras
   - Estadísticas de imágenes
   - ⏱️ Tiempo: ~10 minutos

### 📝 Próximamente:

2. **`02_modelo_cnn_COLAB.ipynb`**
   - Transfer Learning con VGG16
   - Entrenamiento del modelo
   - Evaluación y métricas
   - Guardado del modelo

3. **`03_despliegue_sagemaker_COLAB.ipynb`**
   - Empaquetado del modelo
   - Despliegue en SageMaker
   - Testing del endpoint

4. **`04_serie_temporal_COLAB.ipynb`**
   - Obtención datos de acciones (Google)
   - Modelo LSTM
   - Predicción de precios

---

## 💻 Para Ejecución Local

### Notebooks locales:

1. **`01_exploracion_datos_industriales.ipynb`**
   - Versión para ejecución local
   - Requiere instalación de dependencias
   - ⚠️ Más lento en máquinas sin GPU

---

## 🎯 ¿Cuál usar?

### Usa COLAB si:
- ✅ Quieres entrenar modelos rápidamente (GPU gratuita)
- ✅ Tu máquina es lenta
- ✅ No quieres instalar librerías localmente
- ✅ Necesitas más RAM
- ✅ Trabajas con datasets grandes

### Usa LOCAL si:
- 💻 Tienes GPU potente (NVIDIA)
- 💻 Prefieres trabajar offline
- 💻 Necesitas control total del entorno

---

## 📂 Estructura en Google Drive

Para usar los notebooks de Colab, sube tu carpeta así:

```
Mi unidad/
└── Maestria/
    └── tallerML/
        ├── datos/
        │   └── DataSet/
        │       ├── Train_Dataset/
        │       ├── Valid_Dataset/
        │       └── Test_Dataset/
        └── notebooks_colab/
            └── 01_exploracion_datos_COLAB.ipynb
```

---

## 🚀 Inicio Rápido en Colab

1. Sube tus datos a Google Drive
2. Abre `01_exploracion_datos_COLAB.ipynb` en Colab
3. Activa GPU: `Entorno de ejecución` → `Cambiar tipo` → `GPU`
4. Monta Drive (celda 2)
5. Ajusta ruta en celda 4: `BASE_DIR = Path('/content/drive/MyDrive/Maestria/tallerML')`
6. ¡Ejecuta todas las celdas!

---

## 📞 Ayuda

- 📖 Lee `GUIA_COLAB.md` para instrucciones detalladas
- 📖 Lee `INSTALACION.md` para setup local
- 📖 Lee `README.md` para visión general del proyecto
