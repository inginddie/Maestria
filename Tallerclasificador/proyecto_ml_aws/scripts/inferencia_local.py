"""
Script de Inferencia Local para Modelo VGG16
Clasificación de Piezas Industriales

Uso:
    python inferencia_local.py --image ruta/a/imagen.jpg
    python inferencia_local.py --image ruta/a/imagen.jpg --threshold 0.8
"""

import numpy as np
import json
import tensorflow as tf
from tensorflow import keras
from PIL import Image
import argparse
import os
import sys

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, '..', 'vgg16_industrial_classifier_20251014_203947.keras')
CLASSES_PATH = os.path.join(BASE_DIR, '..', 'vgg16_industrial_classifier_20251014_203947_classes.json')
METADATA_PATH = os.path.join(BASE_DIR, '..', 'vgg16_industrial_classifier_20251014_203947_metadata.json')


class IndustrialClassifier:
    """Clasificador de piezas industriales usando VGG16"""
    
    def __init__(self, model_path, classes_path, metadata_path):
        """
        Inicializa el clasificador
        
        Args:
            model_path: Ruta al modelo .keras
            classes_path: Ruta al archivo de clases JSON
            metadata_path: Ruta al archivo de metadatos JSON
        """
        print("🔄 Cargando modelo...")
        self.model = keras.models.load_model(model_path)
        print("✅ Modelo cargado")
        
        # Cargar clases
        with open(classes_path, 'r') as f:
            classes_data = json.load(f)
            self.idx_to_class = classes_data['idx_to_class']
            self.class_to_idx = classes_data['class_to_idx']
        
        # Cargar metadatos
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)
        
        print(f"✅ {len(self.idx_to_class)} clases cargadas")
    
    def preprocess_image(self, image_path, target_size=(224, 224)):
        """
        Preprocesa una imagen para el modelo
        
        Args:
            image_path: Ruta de la imagen
            target_size: Tamaño objetivo (224x224 para VGG16)
        
        Returns:
            Imagen preprocesada
        """
        # Cargar imagen
        img = Image.open(image_path)
        
        # Convertir a RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Redimensionar
        img = img.resize(target_size)
        
        # Convertir a array
        img_array = np.array(img)
        
        # Expandir dimensiones
        img_array = np.expand_dims(img_array, axis=0)
        
        # Normalizar (VGG16)
        img_array = tf.keras.applications.vgg16.preprocess_input(img_array)
        
        return img_array
    
    def predict(self, image_path, threshold=0.7):
        """
        Predice la clase de una imagen
        
        Args:
            image_path: Ruta de la imagen
            threshold: Umbral de confianza
        
        Returns:
            Diccionario con resultados
        """
        # Preprocesar
        img_array = self.preprocess_image(image_path)
        
        # Predicción
        predictions = self.model.predict(img_array, verbose=0)
        
        # Clase predicha
        predicted_idx = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_idx])
        predicted_class = self.idx_to_class[str(predicted_idx)]
        
        # Verificar umbral
        is_identified = confidence >= threshold
        
        # Top 3
        top_3_idx = np.argsort(predictions[0])[-3:][::-1]
        top_3 = [
            {
                'class': self.idx_to_class[str(i)],
                'confidence': float(predictions[0][i])
            }
            for i in top_3_idx
        ]
        
        return {
            'predicted_class': predicted_class,
            'confidence': confidence,
            'is_identified': is_identified,
            'threshold': threshold,
            'top_3': top_3,
            'destination_folder': predicted_class if is_identified else 'no-identificadas'
        }
    
    def print_info(self):
        """Imprime información del modelo"""
        print("\n" + "="*60)
        print("📊 INFORMACIÓN DEL MODELO")
        print("="*60)
        print(f"Arquitectura: {self.metadata['model_info']['architecture']}")
        print(f"Accuracy en Test: {self.metadata['performance']['test']['accuracy']:.2%}")
        print(f"Parámetros: {self.metadata['architecture']['total_params']:,}")
        print(f"Listo para producción: {self.metadata['analysis']['production_ready']}")
        print("\n📋 Clases:")
        for idx, class_name in self.idx_to_class.items():
            print(f"  {idx}: {class_name}")
        print("="*60 + "\n")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Clasificador de Piezas Industriales')
    parser.add_argument('--image', type=str, required=True, help='Ruta de la imagen a clasificar')
    parser.add_argument('--threshold', type=float, default=0.7, help='Umbral de confianza (default: 0.7)')
    parser.add_argument('--info', action='store_true', help='Mostrar información del modelo')
    
    args = parser.parse_args()
    
    # Verificar que la imagen existe
    if not os.path.exists(args.image):
        print(f"❌ Error: Imagen no encontrada: {args.image}")
        sys.exit(1)
    
    # Inicializar clasificador
    try:
        classifier = IndustrialClassifier(MODEL_PATH, CLASSES_PATH, METADATA_PATH)
    except Exception as e:
        print(f"❌ Error al cargar el modelo: {e}")
        sys.exit(1)
    
    # Mostrar info si se solicita
    if args.info:
        classifier.print_info()
    
    # Hacer predicción
    print(f"\n🖼️ Clasificando: {args.image}")
    print(f"🎯 Umbral: {args.threshold}\n")
    
    try:
        result = classifier.predict(args.image, args.threshold)
        
        # Mostrar resultados
        print("="*60)
        print("🎯 RESULTADO")
        print("="*60)
        print(f"\n🤖 Clase Predicha: {result['predicted_class']}")
        print(f"📊 Confianza: {result['confidence']:.2%}")
        print(f"✅ Identificada: {'SÍ' if result['is_identified'] else 'NO (baja confianza)'}")
        print(f"📁 Carpeta destino: {result['destination_folder']}")
        
        print(f"\n🏆 Top 3 Predicciones:")
        for i, pred in enumerate(result['top_3'], 1):
            print(f"  {i}. {pred['class']}: {pred['confidence']:.2%}")
        
        print("\n" + "="*60)
        
        # Simular flujo AWS
        print("\n🔄 SIMULACIÓN FLUJO AWS:")
        print(f"  1. Imagen subida a S3: s3://bucket/uploads/{os.path.basename(args.image)}")
        print(f"  2. Lambda invoca SageMaker endpoint")
        print(f"  3. Predicción: {result['predicted_class']} ({result['confidence']:.2%})")
        
        if result['is_identified']:
            print(f"  4. ✅ Mover a: s3://bucket/clasificadas/{result['predicted_class']}/")
        else:
            print(f"  4. ⚠️ Mover a: s3://bucket/no-identificadas/")
        
        print("\n✅ Proceso completado\n")
        
    except Exception as e:
        print(f"❌ Error durante la predicción: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
