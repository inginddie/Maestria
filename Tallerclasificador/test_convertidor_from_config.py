import tensorflow as tf
import tarfile
import os
import sys
import traceback
import zipfile
import json

model_filename = 'vgg16_industrial_classifier_20251014_203947.keras'

if not os.path.exists(model_filename):
    for root, dirs, files in os.walk('.'):
        if model_filename in files:
            model_filename = os.path.join(root, model_filename)
            break

if not os.path.exists(model_filename):
    print('No se encontró el archivo .keras en el workspace.')
    sys.exit(1)

print('Leyendo', model_filename)
with zipfile.ZipFile(model_filename, 'r') as z:
    names = z.namelist()
    if 'config.json' not in names and 'model_config.json' not in names and 'model.json' not in names:
        print('No se encontró un archivo de configuración reconocible en el .keras. Contenido:')
        for n in names[:50]:
            print(' -', n)
        sys.exit(1)

    # Preferencias de nombres
    cfg_name = 'config.json' if 'config.json' in names else ('model_config.json' if 'model_config.json' in names else 'model.json')
    weights_name = None
    for candidate in ['model.weights.h5', 'weights.h5', 'model.h5']:
        if candidate in names:
            weights_name = candidate
            break

    print('Configuración encontrada en:', cfg_name)
    if weights_name:
        print('Archivo de pesos encontrado en:', weights_name)
    else:
        print('No se encontró un archivo de pesos HDF5 en el .keras. Contenido parcial:')
        for n in names[:50]:
            print(' -', n)

    # Leer configuración
    with z.open(cfg_name) as f:
        cfg_bytes = f.read()
        try:
            cfg_text = cfg_bytes.decode('utf-8')
        except Exception:
            cfg_text = cfg_bytes.decode('latin-1')

    # Intentar reconstruir el modelo desde JSON/config
    model = None
    try:
        try:
            model = tf.keras.models.model_from_json(cfg_text)
            print('Modelo reconstruido con model_from_json')
        except Exception:
            cfg_obj = json.loads(cfg_text)
            try:
                model = tf.keras.models.model_from_config(cfg_obj)
                print('Modelo reconstruido con model_from_config')
            except Exception:
                print('No fue posible reconstruir el modelo desde la configuración.')
                raise

    except Exception:
        print('Error al reconstruir la arquitectura del modelo:')
        traceback.print_exc()
        sys.exit(1)

    # Si hay pesos, extraer y cargar
    if weights_name:
        weights_path = os.path.join('.', weights_name)
        with z.open(weights_name) as src, open(weights_path, 'wb') as dst:
            dst.write(src.read())
        print('Pesos extraídos a:', weights_path)
        try:
            model.load_weights(weights_path)
            print('Pesos cargados con éxito.')
        except Exception:
            print('Error cargando pesos directamente, intentando por nombre...')
            try:
                model.load_weights(weights_path, by_name=True)
                print('Pesos cargados por nombre.')
            except Exception:
                print('No se pudieron cargar los pesos.')
                traceback.print_exc()
                sys.exit(1)

    # Guardar como SavedModel
    export_dir = 'export/1'
    try:
        tf.saved_model.save(model, export_dir)
        print('SavedModel guardado en', export_dir)
    except Exception:
        print('Error guardando SavedModel:')
        traceback.print_exc()
        sys.exit(1)

    # Empaquetar
    with tarfile.open('model.tar.gz', mode='w:gz') as archive:
        archive.add('export', arcname='.')
    print("Listo: model.tar.gz generado.")
