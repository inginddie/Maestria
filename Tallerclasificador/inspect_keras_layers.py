import zipfile
import json
import os
import sys

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
    cfg_name = 'config.json' if 'config.json' in names else ('model_config.json' if 'model_config.json' in names else 'model.json')
    with z.open(cfg_name) as f:
        cfg = json.load(f)

layers = None
if isinstance(cfg, dict) and 'config' in cfg and isinstance(cfg['config'], dict):
    root_cfg = cfg['config']
    # For Sequential, layers are under root_cfg['layers']
    if 'layers' in root_cfg:
        layers = root_cfg['layers']
    # For some structures, layers may be nested

if not layers:
    print('No se detectaron capas en la estructura esperada. Top-level keys:', list(cfg.keys()))
    sys.exit(1)

print(f'Número de capas en la secuencia: {len(layers)}')
for i, layer in enumerate(layers):
    cls = layer.get('class_name') or layer.get('module')
    name = layer.get('config', {}).get('name') if isinstance(layer.get('config'), dict) else layer.get('name')
    inbound = layer.get('inbound_nodes') or layer.get('inbound_nodes', [])
    inbound_len = len(inbound) if inbound is not None else 0
    print(f'{i:03d}: {cls}  name={name}  inbound_nodes={inbound_len}')
    if inbound_len>0:
        # Print first inbound node detail
        try:
            node = inbound[0]
            print('    first inbound node (truncated):', str(node)[:200])
        except Exception:
            pass
