import json
import zipfile
import os
import sys
import traceback
from pathlib import Path

import tensorflow as tf

MODEL_KERAS = 'vgg16_industrial_classifier_20251014_203947.keras'

def find_in_zip(z, names):
    for n in names:
        if n in z.namelist():
            return n
    return None

def main():
    p = Path(MODEL_KERAS)
    if not p.exists():
        for root, dirs, files in os.walk('.'):
            if MODEL_KERAS in files:
                p = Path(root) / MODEL_KERAS
                break
    if not p.exists():
        print('No se encontró', MODEL_KERAS)
        sys.exit(1)

    print('Leyendo', p)
    with zipfile.ZipFile(p, 'r') as z:
        cfg_name = find_in_zip(z, ['config.json', 'model_config.json', 'model.json'])
        weights_name = find_in_zip(z, ['model.weights.h5', 'weights.h5', 'model.h5'])
        if not cfg_name:
            print('No se encontró config en el .keras. Contenido:')
            print('\n'.join(z.namelist()[:200]))
            sys.exit(1)

        cfg = json.loads(z.read(cfg_name).decode('utf-8'))

        layers = cfg.get('config', {}).get('layers', [])
        func_index = None
        for i, layer in enumerate(layers):
            cls = layer.get('class_name') or ''
            if cls == 'Functional' or 'vgg' in layer.get('config', {}).get('name', '').lower():
                func_index = i
                break

        if func_index is None:
            print('No se detectó la parte vgg en config; abortando este enfoque')
            sys.exit(1)

        head_layers = layers[func_index+1:]
        print('Head layers count:', len(head_layers))

        # Construir base VGG16 desde tf.keras.applications
        print('Construyendo base VGG16 desde tf.keras.applications (include_top=False)')
        base = tf.keras.applications.VGG16(include_top=False, weights=None, input_shape=(224,224,3))
        x = base.output

        # Añadir capas de la cabeza basadas en head_layers
        for li, l in enumerate(head_layers):
            classname = l.get('class_name')
            conf = l.get('config') or {}
            print(f'Procesando head layer {li}: {classname}')
            try:
                layer_obj = tf.keras.layers.deserialize({'class_name': classname, 'config': conf})
            except Exception:
                print('deserialize falló, intentando crear por clase directamente')
                LayerClass = getattr(tf.keras.layers, classname, None)
                if LayerClass is None:
                    print('Clase no encontrada en tf.keras.layers:', classname)
                    traceback.print_exc()
                    sys.exit(1)
                # try to build with common params
                params = conf.copy() if isinstance(conf, dict) else {}
                for k in ['name', 'trainable', 'dtype', 'batch_input_shape', 'batch_shape', 'build_config']:
                    params.pop(k, None)
                try:
                    layer_obj = LayerClass(**params)
                except Exception:
                    print('No se pudo instanciar la capa con params; usando defaults')
                    layer_obj = LayerClass()
            try:
                x = layer_obj(x)
            except Exception:
                print('Error aplicando la capa al tensor')
                traceback.print_exc()
                sys.exit(1)

        from tensorflow.keras import Model
        model = Model(inputs=base.input, outputs=x)
        print('Modelo ensamblado. Capas totales:', len(model.layers))

        # Cargar pesos si existen
        if weights_name:
            tmp_weights = Path('tmp_weights.h5')
            with z.open(weights_name) as src, open(tmp_weights, 'wb') as dst:
                dst.write(src.read())
            print('Pesos extraídos a', tmp_weights)
            try:
                model.load_weights(str(tmp_weights), by_name=True)
                print('Pesos cargados by_name=True')
            except Exception:
                print('Error cargando pesos por nombre, intentando sin by_name')
                try:
                    model.load_weights(str(tmp_weights))
                    print('Pesos cargados sin by_name')
                except Exception:
                    print('No se pudieron cargar los pesos')
                    traceback.print_exc()

        # Guardar y empaquetar
        export_dir = Path('export') / '1'
        export_dir.parent.mkdir(parents=True, exist_ok=True)
        print('Guardando SavedModel en', export_dir)
        tf.saved_model.save(model, str(export_dir))
        tar_path = Path('model.tar.gz')
        import tarfile as _tar
        with _tar.open(tar_path, mode='w:gz') as archive:
            archive.add(str(export_dir), arcname='.')
        print('model.tar.gz generado en', tar_path)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
