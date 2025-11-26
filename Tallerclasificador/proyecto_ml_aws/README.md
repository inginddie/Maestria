# Proyecto ML con AWS - Maestría
## Desarrollo de Software Inteligente - Proyecto Final

### 📁 Estructura del Proyecto

```
proyecto_ml_aws/
│
├── notebooks/              # Jupyter notebooks para desarrollo y análisis
│   ├── 01_exploracion_datos_industriales.ipynb
│   ├── 02_modelo_cnn_clasificacion.ipynb
│   ├── 03_exploracion_datos_acciones.ipynb
│   └── 04_modelo_lstm_prediccion.ipynb
│
├── modelos/               # Modelos entrenados guardados
│   ├── cnn_industrial/
│   └── lstm_acciones/
│
├── scripts/               # Scripts de Python auxiliares
│   ├── data_preprocessing.py
│   └── model_evaluation.py
│
├── lambda_functions/      # Funciones Lambda para AWS
│   ├── clasificacion_imagenes/
│   └── prediccion_acciones/
│
└── requirements.txt       # Dependencias del proyecto
```

### 🎯 Objetivos

#### Punto 1: Clasificación de Piezas Industriales
- Transfer Learning con VGG16
- Despliegue en Amazon SageMaker
- Automatización con AWS Lambda + S3

#### Punto 2: Predicción de Acciones de Google
- Modelo LSTM para series temporales
- Despliegue en Amazon SageMaker
- Almacenamiento en Amazon RDS

### 👨‍💻 Autor
Diego - Maestría en Desarrollo de Software Inteligente

### 📅 Fecha de Entrega
30 de octubre de 2024
