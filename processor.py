# processor.py
# Funciones de procesado: HSV, visión nocturna/termal, detección de movimiento y caras, actualización de trayectoria
import cv2
import numpy as np

def apply_hsv_adjust(frame, hue_shift=0, sat_shift=0, val_shift=0):
    if hue_shift == 0 and sat_shift == 0 and val_shift == 0:
        return frame
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.int16)
    h, s, v = cv2.split(hsv)
    h = (h + hue_shift) % 180
    s = np.clip(s + sat_shift, 0, 255)
    v = np.clip(v + val_shift, 0, 255)
    hsv_mod = cv2.merge((h.astype(np.uint8), s.astype(np.uint8), v.astype(np.uint8)))
    return cv2.cvtColor(hsv_mod, cv2.COLOR_HSV2BGR)

def aplicar_vision_nocturna_verde(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    frame_nv = cv2.merge([np.zeros_like(gray), gray, np.zeros_like(gray)])
    frame_nv = cv2.GaussianBlur(frame_nv, (7, 7), 0)
    cv2.putText(frame_nv, "Vision nocturna (verde)", (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    return frame_nv

def aplicar_vision_termica(frame):
    """Simula visión térmica usando mapa HSV + ajuste adaptativo."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Normalizar a rango 0–255 (aumenta contraste térmico)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    
    # Suavizado para evitar ruido térmico
    gray = cv2.GaussianBlur(gray, (9, 9), 0)
    
    # Aplicar mapa de color tipo térmico (HSV da colores más 'naturales')
    thermal = cv2.applyColorMap(gray, cv2.COLORMAP_HSV)
    
    # Opcional: invertir modo “negativo térmico”
    # thermal = cv2.applyColorMap(255 - gray, cv2.COLORMAP_HSV)
    
    # Añadir etiqueta
    cv2.putText(thermal, "Vision termica", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    
    return thermal


def calcular_luminosidad(frame):
    return np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))

def detect_motion_and_update(frame, prev_frame, backSub, min_area,
                             trayectoria_img=None, puntos=None, tray_w=320, tray_h=240):
    """Aplica background subtractor + diferencia de frames + dibuja trayectorias (si se pasan objetos). 
    Devuelve: dict {movimiento_mog (bool), motion_diff(bool), mov_combined(bool), cnts, frame_out}
    Además actualiza trayectoria_img y puntos si hay movimiento.
    """
    result = {}
    frame_out = frame.copy()

    # MOG/KNN mask (MOG funciona mejor para entornos dinámicos que KNN)
    mask = backSub.apply(frame)
    mask[mask == 127] = 0 # Eliminar sombras
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)) # suavizado
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel) # Apertura morfológica Dilate -> Erode para limpiar ruido
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel) # Cierre morfológico Erode -> Dilate para cerrar huecos
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    movimiento_mog = False
    for c in cnts:
        if cv2.contourArea(c) >= min_area:
            movimiento_mog = True
            x,y,w,h = cv2.boundingRect(c)
            cv2.rectangle(frame_out, (x,y), (x+w, y+h), (0,255,0), 2)
            if trayectoria_img is not None and puntos is not None:
                cx = x + w//2
                cy = y + h//2
                tx = int(cx * tray_w / frame.shape[1])
                ty = int(cy * tray_h / frame.shape[0])
                puntos.append((tx, ty))
                if len(puntos) >= 2:
                    for i in range(1, len(puntos)):
                        cv2.line(trayectoria_img, puntos[i-1], puntos[i], (0,255,255), 2)
            break

    # difference motion
    motion_diff = False
    if prev_frame is not None:
        diff = cv2.absdiff(prev_frame, frame) # Diferencia absoluta para mantener color
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY) # Escala grises
        _, diff_bin = cv2.threshold(gray_diff, 25, 255, cv2.THRESH_BINARY) # Umbral para binarizar
        diff_bin = cv2.morphologyEx(diff_bin, cv2.MORPH_OPEN, kernel) # Apertura morfológica Dilate -> Erode para limpiar ruido
        diff_bin = cv2.morphologyEx(diff_bin, cv2.MORPH_CLOSE, kernel) # Cierre morfológico Erode -> Dilate para cerrar huecos
        cnts_diff, _ = cv2.findContours(diff_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts_diff:
            if cv2.contourArea(c) >= min_area:
                motion_diff = True
                break

    result['mask'] = mask
    result['cnts'] = cnts
    result['movimiento_mog'] = movimiento_mog
    result['motion_diff'] = motion_diff
    result['mov'] = movimiento_mog and motion_diff
    result['frame_out'] = frame_out
    return result
