import shutil
import os

# Archivos a copiar
archivos = [
    'vgg16_industrial_classifier_20251014_203947.keras',
    'vgg16_industrial_classifier_20251014_203947_metadata.json',
    'vgg16_industrial_classifier_20251014_203947_classes.json'
]

# Directorio destino
destino = 'proyecto_ml_aws/modelos/cnn_industrial/'

# Copiar archivos
for archivo in archivos:
    if os.path.exists(archivo):
        shutil.copy2(archivo, destino)
        print(f"✅ Copiado: {archivo}")
    else:
        print(f"❌ No encontrado: {archivo}")

print("\n🎉 Modelo organizado correctamente!")
