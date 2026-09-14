# Proyecto de Detección de Intrusos con OpenCV

Este proyecto detecta **movimiento, intrusos y rostros** en tiempo real usando **OpenCV**, con soporte para **visión nocturna**, **visión térmica**, **grabación automática y manual**, y una **interfaz gráfica** en Tkinter para visualizar, gestionar y reproducir las evidencias.

---

## 📸 Características principales

-  **Detección de movimiento** usando diferencia de imagenes y el algoritmo MOG2.
-  **Detección de rostros** con clasificadores Haar.
-  **Modo visión nocturna** automático o manual.
-  **Modo visión térmica** (colormap HSV).
-  **Grabación automática** al detectar movimiento.
-  **Grabación manual** (toggle desde botón GUI).
-  **Lista de evidencias** (vídeos e imágenes) con botones para ver, eliminar o limpiar.
-  **Trackbars HSV** para ajustar color, saturación y brillo.
-  **Interfaz gráfica (GUI)** basada en Tkinter.
-  **Reproductor multimedia con barra de progreso**.

---

##  Requisitos
 **Python 3.10+**  
Instala las dependencias con:

```bash
pip install -r requirements.txt
````

**requirements.txt** incluye:

```
opencv-python
numpy
Pillow
pygame
```

---

##  Ejecución

Para iniciar el programa principal:

```bash
python main.py
```

Luego:

* Pulsa **N** para alternar visión nocturna.
* Pulsa **T** para alternar visión térmica.
* Pulsa **S** para activar/desactivar alarma.
* Pulsa **Q** para salir de forma segura.

La interfaz también tiene **botones equivalentes** y una lista de evidencias.

---



## Ejemplo de funcionamiento

1. El sistema detecta movimiento en cámara.
2. Se guarda automáticamente un archivo `intruso_DDMMYYYY_HHMMSS.jpg`.
3. Se inicia grabación de vídeo (modo automático).
4. La interfaz muestra la trayectoria, el frame procesado y los clips guardados.
5. Puedes abrir o eliminar archivos desde la lista de evidencias.

---

## Futuras mejoras

* Detección de intrusos con redes neuronales (YOLOv8 / MobileNet SSD).
* Envío de alertas por red o correo.
* Integración con una base de datos de registros.

---

## Autor

**David de Miguel Palomino**
Universidad de Extremadura
Asignatura: *Imagen Digital / Proyecto de OpenCV*
Año: 2025

---

