import tensorflow as tf
import tarfile
import os
import sys

# Nombre del archivo .keras esperado
model_filename = 'vgg16_industrial_classifier_20251014_203947.keras'

# 1) Localizar el archivo .keras en el directorio de trabajo o subdirectorios
if os.path.exists(model_filename):
    model_path = model_filename
else:
    model_path = None
    for root, dirs, files in os.walk('.'):
        if model_filename in files:
            model_path = os.path.join(root, model_filename)
            break

if model_path is None:
    print('Error: no se encontró el archivo .keras. Current working directory:', os.getcwd())
    candidates = []
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.endswith('.keras') or f.endswith('.h5'):
                candidates.append(os.path.join(root, f))
    if candidates:
        print('Archivos .keras/.h5 encontrados:')
        for c in candidates:
            print(' -', c)
    raise FileNotFoundError(f'Archivo {model_filename} no encontrado. Coloque el archivo en el directorio de trabajo o actualice `model_filename` con la ruta correcta.')

print('Cargando modelo desde:', model_path)
# 2) Cargar tu modelo .keras
model = tf.keras.models.load_model(model_path)

# 3) Guardarlo como SavedModel (creará una carpeta con .pb y variables)
export_dir = 'export/1'
tf.saved_model.save(model, export_dir)

# 4) Comprimir en model.tar.gz (SageMaker exige esta estructura exacta)
with tarfile.open('model.tar.gz', mode='w:gz') as archive:
    # Añadir el contenido de export/ al tar, pero sin la carpeta 'export' raíz
    archive.add('export', arcname='.')

print("Listo: Sube 'model.tar.gz' a S3.")
