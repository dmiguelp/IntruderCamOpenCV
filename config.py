# config.py
# Constantes globales y rutas
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EVID_DIR = os.path.join(BASE_DIR, "Evidencias") # carpeta para videos e imágenes capturados que se crea automáticamente
ALARM_DIR = os.path.join(BASE_DIR, "Alarmas") # carpeta para sonidos de alarma
os.makedirs(EVID_DIR, exist_ok=True)
os.makedirs(ALARM_DIR, exist_ok=True)

# Ajustes
TIMELAPSE = 1.0          # segundos entre fotos cuando hay movimiento
MIN_AREA = 2000          # área mínima para considerar movimiento
SONIDO_ALARMA = os.path.join(ALARM_DIR, 'alarma_suave.wav')  # ajustar para cambiar de archivo
VIDEO_DURATION = 6       # segundos posteriores a la detección (auto-record)
FRAME_BUFFER_SIZE = 60   # frames previos para buffer
FPS_FALLBACK = 20        # FPS por defecto si no se puede obtener de la cámara
UMBRAL_LUZ = 40          # umbral de luminosidad para activar visión nocturna