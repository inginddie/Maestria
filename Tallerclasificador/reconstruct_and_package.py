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

def try_reconstruct_functional(func_cfg):
    # Try multiple reconstruction methods
    try:
        print('Intentando tf.keras.models.model_from_config(functional_config)')
        m = tf.keras.models.model_from_config(func_cfg)
        return m
    except Exception:
        print('model_from_config falló')
    try:
        print('Intentando model_from_json de la config (serializar a JSON)')
        s = json.dumps({'class_name': 'Functional', 'config': func_cfg})
        m = tf.keras.models.model_from_json(s)
        return m
    except Exception:
        print('model_from_json sobre functional falló')
    # As last resort, try deserialize_keras_object
    try:
        from keras.saving import serialization_lib
        print('Intentando deserialize_keras_object (keras.saving.serialization_lib)')
        m = serialization_lib.deserialize_keras_object(func_cfg)
        return m
    except Exception:
        print('deserialize_keras_object falló o no disponible')
    raise RuntimeError('No se pudo reconstruir el Functional con los métodos disponibles')


def main():
    p = Path(MODEL_KERAS)
    if not p.exists():
        # buscar en subdirs
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

        # localizar el layer Functional dentro del Sequential
        layers = cfg.get('config', {}).get('layers', [])
        func_layer = None
        func_index = None
        for i, layer in enumerate(layers):
            cls = layer.get('class_name') or layer.get('module')
            if cls == 'Functional' or (isinstance(layer.get('module'), str) and 'functional' in layer.get('module')):
                func_layer = layer
                func_index = i
                break

        if func_layer is None:
            print('No se encontró un layer Functional dentro del Sequential; intentar reconstruir el modelo completo')
            # intentar model_from_config en todo cfg
            try:
                model = tf.keras.models.model_from_config(cfg)
            except Exception:
                traceback.print_exc()
                print('Fallo reconstruir todo el modelo')
                sys.exit(1)
        else:
            print('Functional encontrado en index', func_index)
            func_cfg = func_layer.get('config')
            # The functional config may itself be a proper model config dict
            try:
                functional_model = try_reconstruct_functional(func_cfg)
            except Exception:
                traceback.print_exc()
                print('Fallo reconstruir el Functional; abortando')
                sys.exit(1)

            # Ahora ensamblar la cabeza: tomar las capas posteriores en layers[func_index+1:]
            head_layers = layers[func_index+1:]
            x = functional_model.output
            from tensorflow.keras.layers import deserialize as layer_deserialize
            from tensorflow.keras.layers import deserialize
            for li, l in enumerate(head_layers):
                conf = l.get('config')
                classname = l.get('class_name')
                try:
                    # la función deserialize espera un dict con 'class_name' y 'config'
                    layer_obj = tf.keras.layers.deserialize({'class_name': classname, 'config': conf})
                except Exception:
                    print(f'Fallo al deserializar la capa {li} ({classname}), intentando crear manualmente')
                    # fallback: intentar crear por nombre simple
                    LayerClass = getattr(tf.keras.layers, classname, None)
                    if LayerClass is None:
                        print('No se encontró la clase de capa en tf.keras.layers:', classname)
                        traceback.print_exc()
                        sys.exit(1)
                    # construir con parámetros desde config
                    params = conf.copy() if isinstance(conf, dict) else {}
                    # quitar keys no constructor-friendly
                    for k in ['name', 'trainable', 'dtype', 'batch_input_shape', 'batch_shape']:
                        params.pop(k, None)
                    layer_obj = LayerClass(**params)
                try:
                    x = layer_obj(x)
                except Exception:
                    print('Error aplicando capa', classname)
                    traceback.print_exc()
                    sys.exit(1)

            # construir nuevo modelo
            from tensorflow.keras import Model
            model = Model(inputs=functional_model.input, outputs=x)

        # Si hay pesos, extraer y cargar por nombre
        if weights_name:
            tmp_weights = Path('tmp_model_weights.h5')
            with zipfile.ZipFile(p, 'r') as z:
                with open(tmp_weights, 'wb') as f:
                    f.write(z.read(weights_name))
            print('Pesos extraídos a', tmp_weights)
            try:
                model.load_weights(str(tmp_weights), by_name=True)
                print('Pesos cargados (by_name=True)')
            except Exception:
                print('Error cargando pesos directamente, intentando load_weights sin by_name')
                try:
                    model.load_weights(str(tmp_weights))
                    print('Pesos cargados sin by_name')
                except Exception:
                    traceback.print_exc()
                    print('No se pudieron cargar los pesos; continuar sin pesos')

        # Guardar SavedModel y empaquetar
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
