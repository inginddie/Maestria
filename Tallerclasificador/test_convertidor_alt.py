import tensorflow as tf
import tarfile
import os
import sys
import traceback
import zipfile
import json

# Nombre del archivo .keras esperado
model_filename = 'vgg16_industrial_classifier_20251014_203947.keras'

# Localizar el archivo .keras
model_path = None
if os.path.exists(model_filename):
    model_path = model_filename
else:
    for root, dirs, files in os.walk('.'):
        if model_filename in files:
            model_path = os.path.join(root, model_filename)
            break

if model_path is None:
    print('Error: no se encontró el archivo .keras. Current working directory:', os.getcwd())
    raise FileNotFoundError(model_filename)

print('Intentando cargar modelo desde:', model_path, 'con compile=False')
try:
    model = tf.keras.models.load_model(model_path, compile=False)
    print('Modelo cargado OK. Guardando SavedModel...')
    export_dir = 'export/1'
    tf.saved_model.save(model, export_dir)
    with tarfile.open('model.tar.gz', mode='w:gz') as archive:
        archive.add('export', arcname='.')
    print("Listo: Sube 'model.tar.gz' a S3.")
except Exception as e:
    print('Error al cargar el modelo:')
    traceback.print_exc()
    print('\nInspeccionando el archivo .keras como ZIP:')
    try:
        with zipfile.ZipFile(model_path, 'r') as z:
            names = z.namelist()
            print('Contenido del ZIP (.keras) — primeras 40 entradas:')
            for n in names[:40]:
                print(' -', n)
            # Intentar mostrar keras_metadata.json o model_config
            for candidate in ['keras_metadata.json', 'metadata.json', 'model_config.json', 'model.json']:
                if candidate in names:
                    print(f"\nMostrando {candidate}:")
                    with z.open(candidate) as f:
                        try:
                            data = json.load(f)
                            print(json.dumps(data, indent=2)[:2000])
                        except Exception:
                            txt = f.read().decode('utf-8', errors='ignore')
                            print(txt[:2000])
                    break
    except zipfile.BadZipFile:
        print('El archivo .keras no parece ser un ZIP legible. Puede ser otra variante.')
    sys.exit(1)
