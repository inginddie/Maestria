import zipfile
import json
import sys
import os

path = 'vgg16_industrial_classifier_20251014_203947.keras'
if not os.path.exists(path):
    for root, dirs, files in os.walk('.'):
        if path in files:
            path = os.path.join(root, path)
            break

if not os.path.exists(path):
    print('No se encontró el .keras')
    sys.exit(1)

with zipfile.ZipFile(path, 'r') as z:
    names = z.namelist()
    for candidate in ['config.json','model_config.json','model.json','config']: 
        if candidate in names:
            cfg_name = candidate
            break
    else:
        print('No se encontró config.json en el .keras. Contenido:')
        for n in names[:50]:
            print(' -', n)
        sys.exit(1)

    print('Mostrando inicio de', cfg_name)
    with z.open(cfg_name) as f:
        raw = f.read()
        try:
            text = raw.decode('utf-8')
        except Exception:
            text = raw.decode('latin-1')
    # print first 4000 chars
    print(text[:4000])
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            print('\nTop-level keys:', list(obj.keys()))
            # If it's a model config, try to show model type
            if 'class_name' in obj:
                print('class_name:', obj.get('class_name'))
        else:
            print('\nConfig parsed but top-level is', type(obj))
    except Exception:
        print('\nNo se pudo parsear JSON del config.')
