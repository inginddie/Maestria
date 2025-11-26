# 🚀 Guía Rápida - Google Colab

## 📋 Pasos para usar los notebooks en Google Colab

### 1️⃣ Subir Datos a Google Drive

Sube tu carpeta `tallerML` a Google Drive con esta estructura:

```
Mi unidad/
└── Maestria/
    └── tallerML/
        └── datos/
            └── DataSet/
                ├── Train_Dataset/
                ├── Valid_Dataset/
                └── Test_Dataset/
```

### 2️⃣ Subir el Notebook a Colab

**Opción A - Desde Google Drive:**
1. Sube el notebook `01_exploracion_datos_COLAB.ipynb` a tu Drive
2. Haz doble click → Se abrirá en Google Colab

**Opción B - Desde GitHub/archivo local:**
1. Ve a [Google Colab](https://colab.research.google.com)
2. Click en `Archivo` → `Subir notebook`
3. Selecciona el archivo `01_exploracion_datos_COLAB.ipynb`

### 3️⃣ Activar GPU (IMPORTANTE)

1. En Colab, ve a: `Entorno de ejecución` → `Cambiar tipo de entorno de ejecución`
2. Selecciona: **GPU** → `T4 GPU`
3. Click en `Guardar`

### 4️⃣ Ejecutar el Notebook

1. **Primera celda:** Verifica que estás en Colab y que tienes GPU
2. **Segunda celda:** Monta Google Drive (te pedirá autorización)
3. **Tercera celda:** Ajusta la ruta `BASE_DIR` según donde subiste tus datos
4. Ejecuta el resto de celdas con `Shift + Enter`

---

## 🎯 Ruta Importante

En el notebook, ajusta esta línea según tu estructura:

```python
BASE_DIR = Path('/content/drive/MyDrive/Maestria/tallerML')
```

Posibles variaciones:
- `/content/drive/MyDrive/Maestria/tallerML`
- `/content/drive/My Drive/Maestria/tallerML`
- `/content/drive/MyDrive/tallerML`

---

## ⚡ Ventajas de Colab

✅ **GPU Tesla T4 gratuita** - 16GB VRAM
✅ **RAM:** 12-16GB disponible
✅ **Sesión:** 12 horas continuas
✅ **TensorFlow/Keras/PyTorch pre-instalados**
✅ **No consume recursos de tu PC**

---

## 📝 Atajos de Teclado en Colab

- `Ctrl + Enter`: Ejecutar celda actual
- `Shift + Enter`: Ejecutar celda y avanzar
- `Ctrl + M + B`: Insertar celda abajo
- `Ctrl + M + A`: Insertar celda arriba
- `Ctrl + M + D`: Eliminar celda

---

## 🔄 Guardar tu Progreso

Colab guarda automáticamente en Drive. Para asegurar:
- `Archivo` → `Guardar` (o `Ctrl + S`)
- `Archivo` → `Guardar una copia en Drive`

---

## ⚠️ Limitaciones de Colab Gratuito

- Sesión máxima: **12 horas**
- Inactividad: Se desconecta tras **90 minutos** sin uso
- **Solución:** Ejecuta celdas periódicamente para mantener sesión activa

---

## 🆘 Troubleshooting

### "No module named X"
```python
!pip install nombre_libreria
```

### "Drive not mounted"
Ejecuta nuevamente la celda de montar Drive y autoriza

### "GPU not available"
Verifica: `Entorno de ejecución` → `Cambiar tipo de entorno de ejecución` → GPU

### "Out of Memory"
- Reduce `batch_size` en el entrenamiento
- Limpia variables: `del variable_name`
- Reinicia: `Entorno de ejecución` → `Reiniciar entorno de ejecución`

---

## 🎓 Próximos Notebooks

1. ✅ `01_exploracion_datos_COLAB.ipynb` - Exploración
2. 📝 `02_modelo_cnn_COLAB.ipynb` - Modelo CNN (próximamente)
3. 📝 `03_serie_temporal_COLAB.ipynb` - Predicción acciones (próximamente)

---

**¡Listo para comenzar en Colab!** 🚀
