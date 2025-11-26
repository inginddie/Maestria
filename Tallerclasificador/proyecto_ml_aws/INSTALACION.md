# 🚀 Guía de Instalación y Configuración

## 📋 Prerrequisitos

- Python 3.10 o superior
- pip (gestor de paquetes de Python)
- Visual Studio Code
- Cuenta de AWS con permisos para S3, SageMaker, Lambda y RDS
- Git (opcional)

## 🔧 Instalación Paso a Paso

### 1. Verificar Python

Abre una terminal (CMD o PowerShell) y verifica tu versión de Python:

```bash
python --version
```

Debería mostrar Python 3.10 o superior.

### 2. Crear Entorno Virtual

Es una buena práctica crear un entorno virtual para aislar las dependencias:

```bash
# Navegar a la carpeta del proyecto
cd C:\Users\Diego\Documents\Maestria\tallerML\proyecto_ml_aws

# Crear entorno virtual
python -m venv venv

# Activar el entorno virtual
# En Windows:
venv\Scripts\activate

# En Mac/Linux:
source venv/bin/activate
```

Cuando el entorno esté activado, verás `(venv)` al inicio de tu línea de comandos.

### 3. Instalar Dependencias

Con el entorno virtual activado, instala todas las librerías:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

⏱️ Esto puede tomar 5-10 minutos dependiendo de tu conexión.

### 4. Configurar Variables de Entorno

```bash
# Copiar el archivo de ejemplo
copy .env.example .env

# Editar el archivo .env con tus credenciales de AWS
notepad .env
```

### 5. Abrir en Visual Studio Code

```bash
code .
```

### 6. Configurar Jupyter en VS Code

1. Abre VS Code
2. Instala la extensión "Jupyter" (Microsoft)
3. Instala la extensión "Python" (Microsoft)
4. Abre el notebook `01_exploracion_datos_industriales.ipynb`
5. Selecciona el kernel: Click en "Select Kernel" → "Python Environments" → Selecciona `venv`

### 7. Verificar Instalación

Ejecuta este código en un notebook nuevo:

```python
import numpy as np
import pandas as pd
import tensorflow as tf
import boto3

print("✅ NumPy:", np.__version__)
print("✅ Pandas:", pd.__version__)
print("✅ TensorFlow:", tf.__version__)
print("✅ Boto3:", boto3.__version__)
print("\n🎉 ¡Todo instalado correctamente!")
```

## 🌐 Configuración de AWS

### Instalar AWS CLI

1. Descarga desde: https://aws.amazon.com/cli/
2. Instala el ejecutable
3. Configura tus credenciales:

```bash
aws configure
```

Ingresa:
- AWS Access Key ID
- AWS Secret Access Key
- Default region name: `us-east-1`
- Default output format: `json`

### Verificar Conexión a AWS

```python
import boto3

# Crear cliente S3
s3 = boto3.client('s3')

# Listar buckets
buckets = s3.list_buckets()
print("Buckets disponibles:", [b['Name'] for b in buckets['Buckets']])
```

## 📚 Estructura de Trabajo

1. **Fase Local:** Desarrollar y entrenar modelos localmente
2. **Fase AWS:** Desplegar en SageMaker, Lambda y configurar servicios

## ❓ Troubleshooting

### Error: "No module named 'tensorflow'"
```bash
pip install tensorflow==2.13.0
```

### Error: GPU no disponible
TensorFlow funcionará en CPU por defecto. Para GPU, instala:
```bash
pip install tensorflow-gpu==2.13.0
```

### Error: AWS credentials not found
Verifica que el archivo `.env` esté configurado correctamente y que hayas ejecutado `aws configure`.

## 📞 Ayuda

Si encuentras problemas:
1. Revisa que el entorno virtual esté activado
2. Verifica las versiones de las librerías
3. Consulta los logs de error completos

---

✅ **¡Listo para comenzar el desarrollo!**
